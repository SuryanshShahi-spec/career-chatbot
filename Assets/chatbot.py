"""
chatbot.py — LangGraph-based Job Search chatbot with comprehensive error handling + monitoring.

Error handling:
  - Fail-fast GROQ_API_KEY validation at startup
  - search_jobs tool catches all scraper exceptions and returns a user-friendly string
    (LangChain tools must never raise — they return their error as a string)
  - chatbot_node wraps LLM invocation: handles Groq rate limits, auth errors,
    connection errors, and unexpected failures
  - run() loop handles KeyboardInterrupt / EOFError cleanly

Monitoring:
  - session_id (UUID) generated per run() call
  - Tracks message_count, tool_calls, unique titles/locations, error_count
  - LLM call latency recorded via monitor.record_api_call()
  - monitor.record_session() called on every exit path
"""

import os
import time
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from scraper import job_scrape as _job_scrape
from monitor import monitor as _monitor
from errors import (
    get_logger,
    require_env_vars,
    AuthError,
    RateLimitError,
    NetworkError,
    APIError,
)

load_dotenv()

logger = get_logger("chatbot.groq")

# ── 1. Fail-fast credential check ─────────────────────────────────────────────

try:
    _creds = require_env_vars("Groq", "GROQ_API_KEY")
    GROQ_API_KEY = _creds["GROQ_API_KEY"]
except AuthError as _auth_err:
    logger.critical("Cannot start chatbot — %s", _auth_err)
    raise SystemExit(f"\n❌ {_auth_err}\nSet GROQ_API_KEY in your .env file and restart.") from _auth_err


# ── 2. Tool — wraps scraper; NEVER raises (tools must return strings) ──────────

# Session-level engagement counters (updated by search_jobs tool during a run)
_session_tool_calls    = 0
_session_titles:  set  = set()
_session_locations: set = set()

@tool
def search_jobs(
    job_title: str,
    location: str,
    country_code: str = "in",
    results_per_page: int = 5,
) -> str:
    """
    Search for job listings using the Adzuna API.
    Use this whenever the user asks about jobs, openings, vacancies, or careers.

    Args:
        job_title:        The job role or keyword (e.g. 'Data Analyst', 'Software Engineer').
        location:         City or region to search in (e.g. 'Bangalore', 'Mumbai', 'Delhi').
        country_code:     ISO country code. Use 'in' for India (default), 'gb' for UK, 'us' for USA.
        results_per_page: Number of results to fetch (default 5, max 50).
    """
    global _session_tool_calls, _session_titles, _session_locations
    _session_tool_calls += 1
    _session_titles.add(job_title.lower().strip())
    _session_locations.add(location.lower().strip())

    try:
        return _job_scrape(
            job_title=job_title,
            location=location,
            country_code=country_code,
            results_per_page=results_per_page,
        )
    except AuthError as exc:
        logger.error("Auth error in search_jobs tool: %s", exc)
        return f"❌ Job search unavailable: API credentials error ({exc.service})."
    except RateLimitError as exc:
        wait_hint = f" Retry in {exc.retry_after:.0f}s." if exc.retry_after else ""
        logger.warning("Rate limit in search_jobs tool: %s", exc)
        return f"⏳ Job search rate-limited.{wait_hint} Please try again shortly."
    except NetworkError as exc:
        logger.error("Network error in search_jobs tool: %s", exc)
        return "❌ Could not reach the job search API. Check your internet connection."
    except APIError as exc:
        logger.error("API error in search_jobs tool: %s", exc)
        return f"❌ Job search API returned an error (HTTP {exc.status_code}). Try again later."
    except Exception as exc:
        logger.exception("Unexpected error in search_jobs tool: %s", exc)
        return f"❌ An unexpected error occurred during job search: {exc}"


# ── 3. LLM + tool binding ──────────────────────────────────────────────────────

tools = [search_jobs]

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.3,
)

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = SystemMessage(content="""You are a helpful Job Search Assistant.

Your job is to help users find relevant job listings based on their preferences.

Guidelines:
- When a user asks about jobs, ALWAYS call the `search_jobs` tool to fetch real listings.
- Extract the job title, location, and country from the user's message.
- If country is not mentioned but location sounds Indian (e.g. Bangalore, Mumbai, Delhi, Pune, Hyderabad), use country_code='in'.
- After receiving tool results, present EACH job with ALL of the following fields — never omit any:
    • Job Title
    • Company
    • Location
    • Salary (show exact value from tool; write 'Not specified' only if truly absent)
    • Apply Link (copy the FULL URL exactly as-is from the tool output — NEVER shorten, omit, or paraphrase it)
- CRITICAL: The apply link must ALWAYS be included for every job listing. Do not summarise or skip it.
- After listing results, offer to refine the search (different title, location, or more results).
- If no jobs are found, suggest alternative titles or locations.
- Be conversational and helpful.
""")


# ── 4. Graph state ─────────────────────────────────────────────────────────────

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ── 5. Nodes ───────────────────────────────────────────────────────────────────

# Groq-specific rate-limit / auth exception classes (may not exist if groq not installed)
try:
    from groq import RateLimitError as GroqRateLimitError
    from groq import AuthenticationError as GroqAuthError
    from groq import APIConnectionError as GroqConnectionError
except ImportError:
    GroqRateLimitError = RateLimitError      # type: ignore[misc,assignment]
    GroqAuthError = AuthError                # type: ignore[misc,assignment]
    GroqConnectionError = NetworkError       # type: ignore[misc,assignment]

_GROQ_RETRY_DELAY = 10  # seconds to wait after a Groq 429


def chatbot_node(state: ChatState) -> dict:
    """Call the LLM with the current message history, handling all Groq error cases."""
    messages = [SYSTEM_PROMPT] + state["messages"]

    for attempt in range(3):
        _t0 = time.perf_counter()
        try:
            response = llm_with_tools.invoke(messages)
            _latency = (time.perf_counter() - _t0) * 1000
            _monitor.record_api_call("groq", "chat_completion", _latency,
                                     status_code=200, success=True)
            return {"messages": [response]}

        except GroqRateLimitError as exc:
            _latency = (time.perf_counter() - _t0) * 1000
            wait = _GROQ_RETRY_DELAY * (attempt + 1)
            logger.warning("Groq rate limit (attempt %d/3). Waiting %ds... %s", attempt + 1, wait, exc)
            _monitor.record_api_call("groq", "chat_completion", _latency,
                                     status_code=429, success=False,
                                     error_type="RateLimitError", retries=attempt)
            if attempt < 2:
                time.sleep(wait)
                continue
            return {"messages": [AIMessage(
                content=(
                    "I'm currently rate-limited by the AI service. "
                    f"Please wait {wait}s and try again."
                )
            )]}

        except GroqAuthError as exc:
            _latency = (time.perf_counter() - _t0) * 1000
            logger.error("Groq authentication error: %s", exc)
            _monitor.record_api_call("groq", "chat_completion", _latency,
                                     status_code=401, success=False, error_type="AuthError")
            return {"messages": [AIMessage(
                content="AI service authentication failed. Please check the GROQ_API_KEY in your .env file."
            )]}

        except GroqConnectionError as exc:
            _latency = (time.perf_counter() - _t0) * 1000
            logger.error("Groq connection error (attempt %d/3): %s", attempt + 1, exc)
            _monitor.record_api_call("groq", "chat_completion", _latency,
                                     status_code=0, success=False,
                                     error_type="NetworkError", retries=attempt)
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return {"messages": [AIMessage(
                content="Could not connect to the AI service. Check your internet connection and try again."
            )]}

        except Exception as exc:
            _latency = (time.perf_counter() - _t0) * 1000
            logger.exception("Unexpected LLM error: %s", exc)
            _monitor.record_api_call("groq", "chat_completion", _latency,
                                     status_code=0, success=False, error_type=type(exc).__name__)
            return {"messages": [AIMessage(
                content=f"An unexpected error occurred: {exc}. Please try again."
            )]}

    return {"messages": [AIMessage(content="Failed to get a response after multiple attempts.")]}


tool_node = ToolNode(tools=tools)


# ── 6. Build graph ─────────────────────────────────────────────────────────────

graph = StateGraph(ChatState)

graph.add_node("chatbot", chatbot_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", tools_condition)  # routes to 'tools' or END
graph.add_edge("tools", "chatbot")                       # loop back after tool call

chatbot = graph.compile()


# ── 7. CLI conversation loop ───────────────────────────────────────────────────

def run():
    print("\n🤖 Job Search Assistant (powered by Groq + Adzuna)")
    print("   Type your job query, or 'quit' / 'exit' to stop.\n")
    print("─" * 55)

    # ── Session tracking ───────────────────────────────────────────────────────
    global _session_tool_calls, _session_titles, _session_locations
    _session_tool_calls = 0
    _session_titles     = set()
    _session_locations  = set()

    session_id    = str(uuid.uuid4())
    _ts_format    = "%Y-%m-%dT%H:%M:%S+00:00"
    started_at    = datetime.now(timezone.utc).strftime(_ts_format)
    _start_time   = time.perf_counter()
    message_count = 0
    error_count   = 0
    # ──────────────────────────────────────────────────────────────────────────

    conversation_history: list[BaseMessage] = []

    def _save_session():
        """Persist session metrics — called on every exit path."""
        ended_at   = datetime.now(timezone.utc).strftime(_ts_format)
        duration_s = time.perf_counter() - _start_time
        _monitor.record_session(
            session_id       = session_id,
            started_at       = started_at,
            ended_at         = ended_at,
            duration_s       = duration_s,
            message_count    = message_count,
            tool_calls       = _session_tool_calls,
            unique_titles    = len(_session_titles),
            unique_locations = len(_session_locations),
            error_count      = error_count,
        )

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! Good luck with your job search! 👋")
            _save_session()
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit", "bye"}:
            print("\nGoodbye! Good luck with your job search! 👋")
            _save_session()
            break

        message_count += 1
        conversation_history.append(HumanMessage(content=user_input))

        try:
            result = chatbot.invoke({"messages": conversation_history})
        except Exception as exc:
            logger.exception("Graph invocation failed: %s", exc)
            print(f"\n❌ Assistant error: {exc}. Please try again.")
            error_count += 1
            # Remove the last user message so history stays clean
            conversation_history.pop()
            message_count -= 1
            continue

        # Keep full history for multi-turn context
        conversation_history = result["messages"]

        # Print raw tool output (job listings) so links are never lost
        from langchain_core.messages import ToolMessage
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage):
                print(f"\n📋 Job Listings:\n{msg.content}")
                print("─" * 55)

        # Print the LLM's final reply
        assistant_reply = result["messages"][-1].content
        if assistant_reply:
            print(f"\n🤖 Assistant:\n{assistant_reply}")
            print("─" * 55)


if __name__ == "__main__":
    run()
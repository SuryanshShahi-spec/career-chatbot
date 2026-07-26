import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from scraper import job_scrape as _job_scrape

load_dotenv()

# 1. Wrap scraper as a LangChain tool ──────────────────────────────────────

@tool
def search_jobs(job_title: str, location: str, country_code: str = "in", results_per_page: int = 5) -> str:
    """
    Search for job listings using the Adzuna API.
    Use this whenever the user asks about jobs, openings, vacancies, or careers.

    Args:
        job_title: The job role or keyword (e.g. 'Data Analyst', 'Software Engineer').
        location: City or region to search in (e.g. 'Bangalore', 'Mumbai', 'Delhi').
        country_code: ISO country code. Use 'in' for India (default), 'gb' for UK, 'us' for USA.
        results_per_page: Number of results to fetch (default 5, max 50).
    """
    return _job_scrape(
        job_title=job_title,
        location=location,
        country_code=country_code,
        results_per_page=results_per_page,
    )


# ── 2. LLM + tool binding ─────────────────────────────────────────────────────

tools = [search_jobs]

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
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
- CRITICAL: The apply link (🔗) must ALWAYS be included for every job listing. Do not summarise or skip it.
- After listing results, offer to refine the search (different title, location, or more results).
- If no jobs are found, suggest alternative titles or locations.
- Be conversational and helpful.
""")


# ── 3. Graph state ────────────────────────────────────────────────────────────

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ── 4. Nodes ──────────────────────────────────────────────────────────────────

def chatbot_node(state: ChatState) -> dict:
    """Call the LLM with the current message history."""
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(tools=tools)


# ── 5. Build graph ────────────────────────────────────────────────────────────

graph = StateGraph(ChatState)

graph.add_node("chatbot", chatbot_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", tools_condition)  # routes to 'tools' or END
graph.add_edge("tools", "chatbot")                       # loop back after tool call

chatbot = graph.compile()


# ── 6. CLI conversation loop ──────────────────────────────────────────────────

def run():
    print("\n🤖 Job Search Assistant (powered by Groq + Adzuna)")
    print("   Type your job query, or 'quit' / 'exit' to stop.\n")
    print("─" * 55)

    conversation_history: list[BaseMessage] = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! Good luck with your job search! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit", "bye"}:
            print("\nGoodbye! Good luck with your job search! 👋")
            break

        conversation_history.append(HumanMessage(content=user_input))

        result = chatbot.invoke({"messages": conversation_history})

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
        if assistant_reply:  # LLM sometimes has empty content after a tool call
            print(f"\n🤖 Assistant:\n{assistant_reply}")
            print("─" * 55)


if __name__ == "__main__":
    run()
"""
company_lookup.py — Company research via Tavily + Groq with comprehensive error handling.

Error handling:
  - Fail-fast key validation for both GROQ_API_KEY and TAVILY_API_KEY at class init
  - Tavily search: typed exceptions for auth, rate-limit, network, and unexpected errors
  - Groq LLM call: retry up to 3 times on rate-limits, handles auth / connection errors
  - All errors logged to logs/api_errors.log
"""

import os
import time
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from tavily import TavilyClient

from errors import (
    get_logger,
    require_env_vars,
    retry_with_backoff,
    AuthError,
    RateLimitError,
    NetworkError,
    APIError,
)

load_dotenv(dotenv_path=".env")

logger = get_logger("company_lookup")

# Groq SDK exceptions (graceful fallback if not importable)
try:
    from groq import RateLimitError as GroqRateLimitError
    from groq import AuthenticationError as GroqAuthError
    from groq import APIConnectionError as GroqConnectionError
except ImportError:
    GroqRateLimitError = Exception    # type: ignore[misc,assignment]
    GroqAuthError = Exception         # type: ignore[misc,assignment]
    GroqConnectionError = Exception   # type: ignore[misc,assignment]


class CompanyResearch:
    """Looks up a company using Tavily web search and summarises findings with Groq LLM."""

    def __init__(self):
        # Validate credentials immediately — fail fast with a clear message
        try:
            creds = require_env_vars("CompanyResearch", "GROQ_API_KEY", "TAVILY_API_KEY")
            self._groq_key   = creds["GROQ_API_KEY"]
            self._tavily_key = creds["TAVILY_API_KEY"]
        except AuthError as exc:
            logger.critical("Cannot initialise CompanyResearch — %s", exc)
            raise

        self._tavily = TavilyClient(api_key=self._tavily_key)
        self._llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=self._groq_key,
            temperature=0.3,
        )

    # ── Tavily search ─────────────────────────────────────────────────────────

    def lookup(self) -> tuple[str, dict]:
        """
        Prompt for a company name, search Tavily, and return (company, results).

        Raises:
            AuthError      if Tavily rejects the API key
            RateLimitError if Tavily rate-limits the request
            NetworkError   on connectivity problems
            APIError       for unexpected Tavily errors
        """
        query = input("Enter the Company name: ").strip()
        if not query:
            raise ValueError("Company name cannot be empty.")

        logger.debug("Tavily search query: %s", query)
        try:
            response = self._tavily.search(query=query, max_results=10)
            return query, response

        except Exception as exc:
            exc_str = str(exc).lower()

            # Tavily raises plain exceptions — inspect the message to classify
            if "401" in exc_str or "403" in exc_str or "invalid api key" in exc_str or "unauthorized" in exc_str:
                logger.error("Tavily auth error: %s", exc)
                raise AuthError("Tavily", str(exc)) from exc

            if "429" in exc_str or "rate limit" in exc_str or "too many requests" in exc_str:
                logger.warning("Tavily rate limit: %s", exc)
                raise RateLimitError("Tavily") from exc

            if any(k in exc_str for k in ("timeout", "connection", "network", "unreachable", "dns")):
                logger.error("Tavily network error: %s", exc)
                raise NetworkError("Tavily", str(exc)) from exc

            logger.error("Unexpected Tavily error: %s", exc)
            raise APIError("Tavily", 0, str(exc)) from exc

    # ── Groq LLM summarisation ────────────────────────────────────────────────

    def llm(self, company: str, search_data: dict) -> None:
        """
        Use Groq to extract structured company information from Tavily results.
        Retries up to 3 times on rate-limit or connection errors.

        Args:
            company:     Company name string (used in the prompt).
            search_data: Raw dict from Tavily search.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a precise corporate data extraction assistant.
Using ONLY the provided background search results, extract the following information about the company.
If a specific piece of information is completely missing from the text, write "Not found in search results".

Format your output EXACTLY like this:
Owner Name: [Extract owner, founder, or parent organization]
Company Establishment Date: [Extract founding date or year]
Company Currently Working On: [Summarize current main products, projects, or focus areas]
Company's Required Technologies: [List core technologies, programming languages, framework tools, or tech stacks used]"""),
            ("human", "Company to analyze: {company}\n\nSearch Results:\n{search_data}")
        ])

        formatted_prompt = prompt.format(company=company, search_data=search_data)

        last_exc: Exception = RuntimeError("LLM call failed — no attempts made.")
        for attempt in range(3):
            try:
                response = self._llm.invoke(formatted_prompt)
                print("\n" + "=" * 40)
                print(f"STRUCTURED PROFILE FOR: {company.upper()}")
                print("=" * 40)
                print(response.content)
                print("=" * 40)
                return  # success

            except GroqRateLimitError as exc:
                wait = 10 * (attempt + 1)
                logger.warning("Groq rate limit (attempt %d/3). Waiting %ds: %s", attempt + 1, wait, exc)
                print(f"\n⏳ AI rate-limited. Waiting {wait}s before retry ({attempt + 1}/3)...")
                last_exc = exc
                if attempt < 2:
                    time.sleep(wait)

            except GroqAuthError as exc:
                logger.error("Groq auth error: %s", exc)
                print("\n❌ AI authentication failed. Check GROQ_API_KEY in your .env file.")
                return

            except GroqConnectionError as exc:
                wait = 2 ** attempt
                logger.error("Groq connection error (attempt %d/3): %s", attempt + 1, exc)
                print(f"\n❌ Cannot reach AI service (attempt {attempt + 1}/3). Retrying in {wait}s...")
                last_exc = exc
                if attempt < 2:
                    time.sleep(wait)

            except Exception as exc:
                logger.exception("Unexpected error calling Groq LLM: %s", exc)
                print(f"\n❌ Unexpected AI error: {exc}")
                return

        print(f"\n❌ Failed to get AI response after 3 attempts: {last_exc}")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        research = CompanyResearch()
    except AuthError as e:
        print(f"\n❌ {e}")
        raise SystemExit(1) from e

    try:
        company, search_data = research.lookup()
    except ValueError as e:
        print(f"\n❌ Input error: {e}")
        raise SystemExit(1) from e
    except AuthError as e:
        print(f"\n❌ {e}")
        raise SystemExit(1) from e
    except RateLimitError as e:
        print(f"\n⏳ {e} — please wait and try again.")
        raise SystemExit(1) from e
    except NetworkError as e:
        print(f"\n❌ {e}")
        raise SystemExit(1) from e
    except APIError as e:
        print(f"\n❌ {e}")
        raise SystemExit(1) from e

    research.llm(company, search_data)

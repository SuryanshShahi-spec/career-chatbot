from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field

#------Logging----------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

# ---------Environment-------

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------
class CompanyResearchInput(BaseModel):
    company_name: str = Field(description="Full name of the company to research")
    focus_areas: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional list of specific topics to focus on, e.g. "
            "['culture', 'salary', 'interview process', 'tech stack']"
        ),
    )
    max_web_results: int = Field(
        default=6,
        description="Number of web search results to pull per sub-query",
    )


# ---------------------------------------------------------------------------
# Web Research helper
# ---------------------------------------------------------------------------
_RESEARCH_QUERIES = [
    "{company} company overview mission culture values",
    "{company} salary compensation benefits glassdoor",
    "{company} interview process hiring experience",
    "{company} tech stack engineering blog products",
    "{company} recent news funding growth 2024 2025",
]


def _gather_web_data(company: str, max_results: int) -> str:
    """Run multiple Tavily queries and concatenate the raw results."""
    if not TAVILY_API_KEY:
        return "No Tavily API key — web research unavailable."

    tavily = TavilySearch(max_results=max_results)
    all_snippets: list[str] = []

    for query_template in _RESEARCH_QUERIES:
        query = query_template.format(company=company)
        try:
            raw = tavily.invoke({"query": query})
            results_list = (
                raw.get("results", []) if isinstance(raw, dict)
                else (raw if isinstance(raw, list) else [])
            )
            for r in results_list:
                if isinstance(r, dict) and r.get("content"):
                    snippet = (
                        f"SOURCE: {r.get('url', 'N/A')}\n"
                        f"TITLE: {r.get('title', '')}\n"
                        f"CONTENT: {r.get('content', '')[:600]}\n"
                        "---"
                    )
                    all_snippets.append(snippet)
        except Exception as exc:
            logger.warning("Tavily query failed for '%s': %s", query, exc)

    logger.info("Collected %d snippets for '%s'.", len(all_snippets), company)
    return "\n".join(all_snippets) if all_snippets else "No web data found."


# ---------------------------------------------------------------------------
# LLM Synthesis helper
# ---------------------------------------------------------------------------
_SYNTHESIS_PROMPT = ChatPromptTemplate.from_template(
    """You are a professional company research analyst.
Using ONLY the web data provided below, write a detailed, structured research
report for **{company}**.

Focus areas requested: {focus_areas}

Web Data:
{web_data}

---

Format your output as a valid JSON object with the following keys:
{{
  "company": "<name>",
  "overview": "<2-3 sentences about what the company does>",
  "culture_and_values": "<summary of work culture, values, employee sentiment>",
  "compensation": "<salary ranges, equity, benefits info if available>",
  "interview_process": "<stages, difficulty, tips if available>",
  "tech_stack": "<languages, frameworks, tools if mentioned>",
  "recent_news": "<latest company news, funding, growth highlights>",
  "pros": ["<pro 1>", "<pro 2>", "<pro 3>"],
  "cons": ["<con 1>", "<con 2>"],
  "job_seeker_verdict": "<final 2-3 sentence recommendation for a job seeker>"
}}

Return ONLY the JSON object with no additional text or markdown."""
)


def _synthesise_report(company: str, focus_areas: list[str], web_data: str) -> dict:
    """Use Groq LLaMA to synthesise web data into a structured report."""
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not set — LLM synthesis unavailable."}

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=GROQ_API_KEY)
    chain = _SYNTHESIS_PROMPT | llm | StrOutputParser()

    focus_str = ", ".join(focus_areas) if focus_areas else "all areas"

    try:
        raw_output = chain.invoke({
            "company": company,
            "focus_areas": focus_str,
            "web_data": web_data[:8000],   # stay within context limits
        })
        # Clean potential markdown code fences
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        report = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM output was not valid JSON; returning raw text.")
        report = {"raw_report": raw_output}
    except Exception as exc:
        logger.error("LLM synthesis error: %s", exc)
        report = {"error": str(exc)}

    return report


# ---------------------------------------------------------------------------
# LangChain Tool
# ---------------------------------------------------------------------------
@tool(args_schema=CompanyResearchInput)
def company_research_tool(
    company_name: str,
    focus_areas: Optional[list[str]] = None,
    max_web_results: int = 6,
) -> str:
    """
    Research a company for job seekers.

    Performs multi-query Tavily web searches to gather real-time information
    about the company (culture, salaries, interviews, tech stack, news), then
    uses Groq LLaMA to synthesise the raw data into a clean, structured JSON
    research report.

    Returns a JSON-formatted company report.
    """
    logger.info("Starting research for company: %s", company_name)

    # Step 1 — Gather raw web data
    web_data = _gather_web_data(company_name, max_web_results)

    # Step 2 — Synthesise into structured report
    report = _synthesise_report(
        company=company_name,
        focus_areas=focus_areas or [],
        web_data=web_data,
    )

    return json.dumps(report, indent=2)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = company_research_tool.invoke({
        "company_name": "Google",
        "focus_areas": ["culture", "interview process", "salary"],
        "max_web_results": 4,
    })
    print(result)

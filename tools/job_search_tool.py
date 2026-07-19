"""
tools/job_search_tool.py
------------------------
Job Search Tool — searches live job listings via the Adzuna API,
with an automatic Tavily web-search fallback.

Exposed as a LangChain @tool so it can be plugged directly into any
LangGraph / LangChain agent.
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_API_KEY = os.getenv("ADZUNA_API_IKEY", "")   # note: "IKEY" in .env
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------
class JobSearchInput(BaseModel):
    title: str = Field(description="Job title or role to search for, e.g. 'Python Developer'")
    location: Optional[str] = Field(default=None, description="City, state or country")
    remote: Optional[bool] = Field(default=None, description="True to filter for remote jobs")
    min_salary: Optional[int] = Field(default=None, description="Minimum annual salary in USD/GBP")
    max_results: int = Field(default=5, description="Maximum number of results to return (1-20)")
    country: str = Field(default="in", description="Adzuna country code: 'in', 'us', 'gb', 'au', etc.")


# ---------------------------------------------------------------------------
# Adzuna helper
# ---------------------------------------------------------------------------
def _search_adzuna(params: JobSearchInput) -> list[dict]:
    """
    Call the Adzuna Jobs API and return a list of normalised job dicts.
    Returns an empty list if credentials are missing or the call fails.
    """
    if not ADZUNA_APP_ID or not ADZUNA_API_KEY:
        logger.warning("Adzuna credentials not found — skipping Adzuna search.")
        return []

    query_parts = [params.title]
    if params.remote:
        query_parts.append("remote")

    query_params: dict = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_API_KEY,
        "results_per_page": min(params.max_results, 20),
        "what": " ".join(query_parts),
        "content-type": "application/json",
    }

    if params.location:
        query_params["where"] = params.location
    if params.min_salary:
        query_params["salary_min"] = params.min_salary

    url = f"{ADZUNA_BASE_URL}/{params.country}/search/1"

    try:
        resp = requests.get(url, params=query_params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("Adzuna API error: %s", exc)
        return []

    results = []
    for job in data.get("results", []):
        results.append({
            "title":       job.get("title", "N/A"),
            "company":     job.get("company", {}).get("display_name", "N/A"),
            "location":    job.get("location", {}).get("display_name", "N/A"),
            "salary_min":  job.get("salary_min"),
            "salary_max":  job.get("salary_max"),
            "description": job.get("description", "")[:400],
            "url":         job.get("redirect_url", ""),
            "posted":      job.get("created", ""),
            "source":      "adzuna",
        })

    logger.info("Adzuna returned %d results.", len(results))
    return results


# ---------------------------------------------------------------------------
# Tavily fallback helper
# ---------------------------------------------------------------------------
def _search_tavily_jobs(params: JobSearchInput) -> list[dict]:
    """
    Build a targeted Tavily query and return normalised job-like dicts.
    """
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — skipping Tavily fallback.")
        return []

    query_parts = [f"{params.title} jobs"]
    if params.location:
        query_parts.append(f"in {params.location}")
    if params.remote:
        query_parts.append("remote")
    if params.min_salary:
        query_parts.append(f"salary {params.min_salary}+")

    query = " ".join(query_parts)

    tavily = TavilySearch(max_results=params.max_results)
    raw = tavily.invoke({"query": query})

    results_list = (
        raw.get("results", []) if isinstance(raw, dict)
        else (raw if isinstance(raw, list) else [])
    )

    results = []
    for r in results_list:
        if isinstance(r, dict):
            results.append({
                "title":       r.get("title", "N/A"),
                "company":     "See link",
                "location":    params.location or "Not specified",
                "salary_min":  None,
                "salary_max":  None,
                "description": r.get("content", "")[:400],
                "url":         r.get("url", ""),
                "posted":      "",
                "source":      "tavily",
            })

    logger.info("Tavily returned %d results.", len(results))
    return results


# ---------------------------------------------------------------------------
# LangChain Tool
# ---------------------------------------------------------------------------
@tool(args_schema=JobSearchInput)
def job_search_tool(
    title: str,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    min_salary: Optional[int] = None,
    max_results: int = 5,
    country: str = "in",
) -> str:
    """
    Search for live job listings.

    First queries the Adzuna Jobs API; if no results are found (or credentials
    are missing), automatically falls back to a Tavily web search.

    Returns a JSON-formatted string containing a list of job listings with
    title, company, location, salary range, description snippet, and apply URL.
    """
    params = JobSearchInput(
        title=title,
        location=location,
        remote=remote,
        min_salary=min_salary,
        max_results=max_results,
        country=country,
    )

    # Primary: Adzuna
    jobs = _search_adzuna(params)

    # Fallback: Tavily
    if not jobs:
        logger.info("No Adzuna results — falling back to Tavily.")
        jobs = _search_tavily_jobs(params)

    if not jobs:
        return json.dumps({
            "message": "No job listings found. Try different keywords or location.",
            "jobs": [],
        })

    return json.dumps({"total_found": len(jobs), "jobs": jobs}, indent=2)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = job_search_tool.invoke({
        "title": "Python Developer",
        "location": "Bangalore",
        "remote": False,
        "min_salary": None,
        "max_results": 3,
        "country": "in",
    })
    print(result)

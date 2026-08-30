"""
scraper.py — Adzuna job search with comprehensive error handling + monitoring.

Error handling:
  - Fail-fast credential validation at module load
  - Retry on transient network / 5xx errors (3 attempts, exponential back-off)
  - Typed RateLimitError on HTTP 429 with Retry-After support
  - AuthError on 401 / 403
  - Separate handling for connection errors vs. read timeouts
  - Safe JSON parsing with a fallback error message

Monitoring:
  - Every search outcome recorded via monitor.record_search()
  - Every HTTP round-trip recorded via monitor.record_api_call()
  - Latency measured with time.perf_counter() around _fetch_jobs()
"""

import os
import re
import time as _time
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, Timeout, RequestException
from dotenv import load_dotenv

from monitor import monitor as _monitor

from errors import (
    get_logger,
    handle_http_status,
    retry_with_backoff,
    require_env_vars,
    AuthError,
    RateLimitError,
    NetworkError,
    APIError,
)

load_dotenv()

logger = get_logger("scraper.adzuna")

# ── Credential validation (fail fast at import time) ──────────────────────────
try:
    _creds = require_env_vars("Adzuna", "ADZUNA_APP_ID", "ADZUNA_API_KEY")
    ADZUNA_APP_ID = _creds["ADZUNA_APP_ID"]
    ADZUNA_API_KEY = _creds["ADZUNA_API_KEY"]
    _CREDS_OK = True
except AuthError as _auth_err:
    logger.error("Adzuna credentials missing: %s", _auth_err)
    ADZUNA_APP_ID = ADZUNA_API_KEY = None
    _CREDS_OK = False

# ── Constants ──────────────────────────────────────────────────────────────────
CONNECT_TIMEOUT = 5   # seconds to establish TCP connection
READ_TIMEOUT    = 15  # seconds to wait for the server to respond


# ── Core HTTP fetch (decorated with retry) ─────────────────────────────────────

@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=(NetworkError, APIError),
    logger=logger,
)
def _fetch_jobs(url: str, params: dict) -> dict:
    """
    Make a single HTTP GET to Adzuna and return the parsed JSON body.

    Raises:
        NetworkError   on connection failure or timeout
        AuthError      on 401 / 403
        RateLimitError on 429
        APIError       on other non-2xx responses
    """
    logger.debug("GET %s params=%s", url, {k: v for k, v in params.items() if k != "app_key"})
    try:
        response = requests.get(url, params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    except Timeout:
        raise NetworkError("Adzuna", "Request timed out (connect=5s, read=15s).")
    except ReqConnectionError as exc:
        raise NetworkError("Adzuna", f"Connection refused or DNS failure: {exc}")
    except RequestException as exc:
        raise NetworkError("Adzuna", f"Unexpected request error: {exc}")

    # Raises typed exception for any non-2xx status
    handle_http_status(response, "Adzuna")

    # Safe JSON parse
    try:
        return response.json()
    except ValueError as exc:
        raise APIError("Adzuna", response.status_code, f"Invalid JSON in response: {exc}")


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _extract_notice_period_days(description: str | None) -> int | None:
    text = _normalize_text(description)
    if not text:
        return None

    if re.search(r"\b(immediate|immediately)\b", text):
        return 0

    match = re.search(r"(\d+)\s*(?:days?|d)\s*(?:notice|notice period|join|joining)", text)
    if match:
        return int(match.group(1))

    match = re.search(r"(\d+)\s*(?:month|months|mth|mths)\s*(?:notice|notice period|join|joining)", text)
    if match:
        return int(match.group(1)) * 30

    if "notice period" in text:
        match = re.search(r"(\d+)\s*(?:days?|months?|mth|mths)", text)
        if match:
            value = int(match.group(1))
            unit = re.search(r"(?:days?|d)\b|(?:month|months|mth|mths)\b", text)
            if unit and "month" in unit.group(0):
                return value * 30
            return value

    return None


def _matches_notice_period(job: dict, max_notice_days: int) -> bool:
    description = job.get("description") or ""
    notice_days = _extract_notice_period_days(description)
    if notice_days is None:
        return True
    return notice_days <= int(max_notice_days)


def _matches_remote(job: dict, require_remote: bool) -> bool:
    text = _normalize_text((job.get("description") or "") + " " + (job.get("title") or ""))
    remote_markers = {
        "remote", "work from home", "wfh", "work-from-home", "remote friendly", "hybrid",
        "distributed", "virtual"
    }
    has_remote_marker = any(marker in text for marker in remote_markers)
    if require_remote:
        return has_remote_marker
    return not has_remote_marker


def _matches_location(job: dict, preferred_locations: list[str]) -> bool:
    if not preferred_locations:
        return True

    location_text = _normalize_text(job.get("location", {}).get("display_name"))
    normalized = [loc.strip().lower() for loc in preferred_locations if str(loc).strip()]
    if not normalized:
        return True
    return any(city in location_text for city in normalized)


def filter_jobs_for_preferences(
    jobs: list[dict],
    notice_period_days: int | None = None,
    work_from_home: bool | None = None,
    preferred_locations: list[str] | None = None,
) -> list[dict]:
    """Return only jobs matching the user-side preference filters."""
    if not isinstance(jobs, list):
        return []

    normalized_locations = [str(loc).strip() for loc in (preferred_locations or []) if str(loc).strip()]
    filtered = []
    for job in jobs:
        if notice_period_days is not None and not _matches_notice_period(job, notice_period_days):
            continue
        if work_from_home is not None and not _matches_remote(job, work_from_home):
            continue
        if normalized_locations and not _matches_location(job, normalized_locations):
            continue
        filtered.append(job)
    return filtered


# ── Public interface ───────────────────────────────────────────────────────────

def job_scrape(
    job_title: str,
    location: str,
    country_code: str = "in",
    results_per_page: int = 5,
    notice_period_days: int | None = None,
    work_from_home: bool | None = None,
    preferred_locations: list[str] | None = None,
) -> str:
    """
    Search for jobs using the Adzuna API and apply the optional job-fit filters.
    """
    # Guard: credentials must be present
    if not _CREDS_OK:
        return (
            "Adzuna API credentials are missing. "
            "Set ADZUNA_APP_ID and ADZUNA_API_KEY in your .env file."
        )

    url = f"https://api.adzuna.com/v1/api/jobs/{country_code.lower()}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_API_KEY,
        "what": job_title,
        "where": location,
        "results_per_page": min(int(results_per_page), 50),
    }

    _t0 = _time.perf_counter()
    try:
        data = _fetch_jobs(url, params)
        _latency = (_time.perf_counter() - _t0) * 1000
    except AuthError as exc:
        _latency = (_time.perf_counter() - _t0) * 1000
        logger.error("Auth failure: %s", exc)
        _monitor.record_search(job_title, location, country_code, results_per_page,
                               0, 0, _latency, "error", type(exc).__name__)
        _monitor.record_api_call("adzuna", "job_search", _latency,
                                 status_code=401, success=False, error_type=type(exc).__name__)
        return f"Authentication error with Adzuna API. Check your credentials. ({exc})"
    except RateLimitError as exc:
        _latency = (_time.perf_counter() - _t0) * 1000
        wait_hint = f" Please wait {exc.retry_after:.0f}s before retrying." if exc.retry_after else ""
        logger.warning("Rate limit: %s", exc)
        _monitor.record_search(job_title, location, country_code, results_per_page,
                               0, 0, _latency, "error", "RateLimitError")
        _monitor.record_api_call("adzuna", "job_search", _latency,
                                 status_code=429, success=False, error_type="RateLimitError")
        return f"Adzuna rate limit reached.{wait_hint}"
    except NetworkError as exc:
        _latency = (_time.perf_counter() - _t0) * 1000
        logger.error("Network error after retries: %s", exc)
        _monitor.record_search(job_title, location, country_code, results_per_page,
                               0, 0, _latency, "error", "NetworkError")
        _monitor.record_api_call("adzuna", "job_search", _latency,
                                 status_code=0, success=False, error_type="NetworkError")
        return f"Could not reach Adzuna (network error). Check your internet connection. ({exc})"
    except APIError as exc:
        _latency = (_time.perf_counter() - _t0) * 1000
        logger.error("API error after retries: %s", exc)
        _monitor.record_search(job_title, location, country_code, results_per_page,
                               0, 0, _latency, "error", "APIError")
        _monitor.record_api_call("adzuna", "job_search", _latency,
                                 status_code=exc.status_code, success=False, error_type="APIError")
        return f"Adzuna API returned an error (HTTP {exc.status_code}). Try again later."
    except Exception as exc:
        _latency = (_time.perf_counter() - _t0) * 1000
        logger.exception("Unexpected error in job_scrape: %s", exc)
        _monitor.record_search(job_title, location, country_code, results_per_page,
                               0, 0, _latency, "error", type(exc).__name__)
        _monitor.record_api_call("adzuna", "job_search", _latency,
                                 status_code=0, success=False, error_type=type(exc).__name__)
        return f"An unexpected error occurred while searching for jobs: {exc}"

    raw_results = data.get("results", [])
    results = filter_jobs_for_preferences(
        raw_results,
        notice_period_days=notice_period_days,
        work_from_home=work_from_home,
        preferred_locations=preferred_locations,
    )
    total = data.get("count", len(raw_results))
    returned_cnt = len(results)

    if not results:
        _monitor.record_search(job_title, location, country_code, results_per_page,
                               0, 0, _latency, "no_results")
        _monitor.record_api_call("adzuna", "job_search", _latency,
                                 status_code=200, success=True)
        return (
            f"No jobs found for '{job_title}' in '{location}' matching the current filters. "
            "Try a broader search or remove notice period / remote / location constraints."
        )

    _monitor.record_search(job_title, location, country_code, results_per_page,
                           returned_cnt, total, _latency, "success")
    _monitor.record_api_call("adzuna", "job_search", _latency,
                             status_code=200, success=True)
    lines = [f"Found {returned_cnt} matching jobs for '{job_title}' in '{location}'.\n"]
    lines.append("=" * 60)

    for i, job in enumerate(results, start=1):
        title = job.get("title", "N/A")
        company = job.get("company", {}).get("display_name", "N/A")
        loc = job.get("location", {}).get("display_name", "N/A")
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        link = job.get("redirect_url", "N/A")
        description = (job.get("description") or "")[:200].strip()

        if salary_min and salary_max:
            salary = f"Rs.{salary_min:,.0f} - Rs.{salary_max:,.0f}"
        elif salary_min:
            salary = f"From Rs.{salary_min:,.0f}"
        else:
            salary = "Not specified"

        lines.append(f"[{i}] {title}")
        lines.append(f"    Company  : {company}")
        lines.append(f"    Location : {loc}")
        lines.append(f"    Salary   : {salary}")
        lines.append(f"    Summary  : {description}...")
        lines.append(f"    Link     : {link}")
        lines.append("-" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    print(job_scrape("Data Analyst", "Bangalore", notice_period_days=30, work_from_home=True))

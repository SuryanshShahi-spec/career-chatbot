"""
adzuna_scraper.py
=================
Scrapes job listings from the Adzuna API and stores the results in a
single CSV file containing:
  - Job Title
  - Job Description
  - Estimated Salary
  - Location
  - URL

Credentials are loaded from the project-root .env file:
  ADZUNA_APP_ID   = <your app id>
  ADZUNA_API_IKEY = <your api key>     (note: the key name uses "IKEY")

Usage
-----
  python Scraper/adzuna_scraper.py
  python Scraper/adzuna_scraper.py --what "data scientist" --where "India" --pages 3
  python Scraper/adzuna_scraper.py --country us --what "machine learning" --pages 5
"""

import os
import sys
import csv
import time
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

# ── Force UTF-8 stdout so emoji / special chars render on Windows ──────────────
sys.stdout.reconfigure(encoding="utf-8")

# ── Load .env from the project root (one level above this file's directory) ────
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path)

# ── Adzuna API base ────────────────────────────────────────────────────────────
BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

# ── CSV output path (project root) ────────────────────────────────────────────
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), "..")
CSV_FILENAME = "adzuna_jobs.csv"

# ── CSV column order ───────────────────────────────────────────────────────────
FIELDNAMES = [
    "job_title",
    "job_description",
    "estimated_salary",
    "location",
    "url",
    "company",
    "category",
    "contract_type",
    "scraped_at",
]

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_credentials():
    """Return (app_id, api_key) from environment variables."""
    app_id  = os.getenv("ADZUNA_APP_ID",   "").strip()
    api_key = os.getenv("ADZUNA_API_IKEY", "").strip()

    if not app_id or not api_key:
        print(
            "❌  Missing Adzuna credentials!\n"
            "    Make sure your .env file contains:\n"
            "      ADZUNA_APP_ID   = <your app id>\n"
            "      ADZUNA_API_IKEY = <your api key>"
        )
        sys.exit(1)

    return app_id, api_key


def _safe_salary(job):
    """
    Build a human-readable salary string.
    Adzuna returns 'salary_min' and 'salary_max' (floats, annual).
    Falls back gracefully when either field is absent.
    """
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")

    if salary_min is not None and salary_max is not None:
        return f"${int(salary_min):,} - ${int(salary_max):,} / year"
    if salary_min is not None:
        return f"${int(salary_min):,}+ / year"
    if salary_max is not None:
        return f"Up to ${int(salary_max):,} / year"
    return "Not specified"


def _safe_location(job):
    """
    Extract a readable location string.
    Adzuna nests location as:
      location.display_name  (e.g. "London, Greater London")
    """
    loc = job.get("location", {})
    if isinstance(loc, dict):
        return loc.get("display_name", "Not specified")
    return str(loc) if loc else "Not specified"


def parse_job(job):
    """Map a raw Adzuna result dict to the CSV row schema."""
    category  = job.get("category", {})
    cat_label = category.get("label", "") if isinstance(category, dict) else ""

    company   = job.get("company", {})
    comp_name = company.get("display_name", "") if isinstance(company, dict) else ""

    return {
        "job_title":        job.get("title", "").strip(),
        "job_description":  job.get("description", "").strip(),
        "estimated_salary": _safe_salary(job),
        "location":         _safe_location(job),
        "url":              job.get("redirect_url", ""),
        "company":          comp_name,
        "category":         cat_label,
        "contract_type":    job.get("contract_type", ""),
        "scraped_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API call
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_page(app_id, api_key, country, page, what, where, results_per_page=50):
    """
    Call the Adzuna search endpoint for one page and return the list of
    raw job dicts (empty list on error).
    """
    url = BASE_URL.format(country=country, page=page)
    params = {
        "app_id":           app_id,
        "app_key":          api_key,
        "results_per_page": results_per_page,
        "content-type":     "application/json",
    }
    if what.strip():
        params["what"] = what.strip()
    if where.strip():
        params["where"] = where.strip()

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.exceptions.HTTPError as exc:
        print(f"  ⚠️  HTTP error on page {page}: {exc}")
        return []
    except requests.exceptions.RequestException as exc:
        print(f"  ⚠️  Request failed on page {page}: {exc}")
        return []
    except ValueError:
        print(f"  ⚠️  JSON decode error on page {page}.")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# CSV writer
# ═══════════════════════════════════════════════════════════════════════════════

def save_to_csv(jobs, output_path):
    """Write all job rows to a single CSV file (overwrite if exists)."""
    if not jobs:
        print("\n⚠️  No jobs to save.")
        return

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)

    print(f"\n✅  Saved {len(jobs)} job(s) → {os.path.abspath(output_path)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Scrape jobs from the Adzuna API and export to a single CSV file."
    )
    parser.add_argument(
        "--what",
        default="",
        help='Job keywords / title (e.g. "python developer"). Default: all jobs.',
    )
    parser.add_argument(
        "--where",
        default="",
        help='Location filter (e.g. "London", "New York"). Default: everywhere.',
    )
    parser.add_argument(
        "--country",
        default="gb",
        help="Two-letter country code (e.g. gb, us, au, ca, in). Default: gb.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=2,
        help="Number of result pages to fetch (50 results/page). Default: 2.",
    )
    parser.add_argument(
        "--results-per-page",
        type=int,
        default=50,
        help="Results per page (max 50 per Adzuna limits). Default: 50.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(OUTPUT_DIR, CSV_FILENAME),
        help=f"Path for the output CSV. Default: <project-root>/{CSV_FILENAME}",
    )
    args = parser.parse_args()

    app_id, api_key = get_credentials()

    print("=" * 64)
    print("  🔍  Adzuna Job Scraper")
    print("=" * 64)
    print(f"  Search keywords  : {args.what or '(all)'}")
    print(f"  Location filter  : {args.where or '(anywhere)'}")
    print(f"  Country code     : {args.country}")
    print(f"  Pages to fetch   : {args.pages}  ({args.results_per_page} results/page)")
    print(f"  Output CSV       : {os.path.abspath(args.output)}")
    print("=" * 64)

    all_jobs = []
    last_page = 1

    for page in range(1, args.pages + 1):
        last_page = page
        print(f"\n  📄  Fetching page {page}/{args.pages} ...", end=" ", flush=True)

        raw_results = fetch_page(
            app_id=app_id,
            api_key=api_key,
            country=args.country,
            page=page,
            what=args.what,
            where=args.where,
            results_per_page=args.results_per_page,
        )

        if not raw_results:
            print("no results — stopping early.")
            break

        parsed = [parse_job(r) for r in raw_results]
        all_jobs.extend(parsed)
        print(f"got {len(parsed)} job(s)  |  total so far: {len(all_jobs)}")

        # Polite 1-second delay between pages to respect rate limits
        if page < args.pages:
            time.sleep(1)

    # ── Save to CSV ────────────────────────────────────────────────────────────
    save_to_csv(all_jobs, args.output)

    print("\n📊  Summary")
    print(f"   Pages fetched  : {last_page}")
    print(f"   Total jobs     : {len(all_jobs)}")
    print("=" * 64)


if __name__ == "__main__":
    main()

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_API_KEY = os.getenv("ADZUNA_API_KEY")


def job_scrape(job_title: str, location: str, country_code: str = "in", results_per_page: int = 5) -> str:
    """
    Search for jobs using the Adzuna API.

    Args:
        job_title: The job title or keyword to search for (e.g. 'Data Analyst').
        location: The city or region to search in (e.g. 'Bangalore').
        country_code: ISO country code, default is 'in' for India.
        results_per_page: How many results to return (max 50).

    Returns:
        A formatted string listing the jobs found, or an error message.
    """
    if not ADZUNA_APP_ID or not ADZUNA_API_KEY:
        return "❌ Error: Adzuna API credentials are missing from the .env file."

    page = 1
    url = f"https://api.adzuna.com/v1/api/jobs/{country_code.lower()}/search/{page}"

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_API_KEY,
        "what": job_title,
        "where": location,
        "results_per_page": results_per_page,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        return f"❌ Network error while contacting Adzuna: {e}"

    if response.status_code != 200:
        return f"❌ API Error {response.status_code}: {response.text}"

    data = response.json()
    results = data.get("results", [])

    if not results:
        return f"⚠️ No jobs found for '{job_title}' in '{location}'. Try a broader search."

    total = data.get("count", len(results))
    lines = [f"✅ Found {total} jobs for '{job_title}' in '{location}'. Showing top {len(results)}:\n"]
    lines.append("=" * 60)

    for i, job in enumerate(results, start=1):
        title = job.get("title", "N/A")
        company = job.get("company", {}).get("display_name", "N/A")
        loc = job.get("location", {}).get("display_name", "N/A")
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        link = job.get("redirect_url", "N/A")
        description = job.get("description", "")[:200].strip()

        if salary_min and salary_max:
            salary = f"₹{salary_min:,.0f} – ₹{salary_max:,.0f}"
        elif salary_min:
            salary = f"From ₹{salary_min:,.0f}"
        else:
            salary = "Not specified"

        lines.append(f"[{i}] {title}")
        lines.append(f"    🏢 Company  : {company}")
        lines.append(f"    📍 Location : {loc}")
        lines.append(f"    💰 Salary   : {salary}")
        lines.append(f"    📝 Summary  : {description}...")
        lines.append(f"    🔗 Link     : {link}")
        lines.append("-" * 60)

    return "\n".join(lines)

if __name__ == "__main__":
    job_scrape()

import time
import requests
import csv
from bs4 import BeautifulSoup
from selenium import webdriver

def find_job_cards_bs4():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    jobs = []  # collect job data here

    try:
        driver.get("https://in.indeed.com/q-jalgaon-jobs-jobs.html")
        print("Page title:", driver.title)

        # Wait for page to load and scroll
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Indeed job cards
        job_cards = soup.select("div.job_seen_beacon")
        print(f"Found {len(job_cards)} job cards.")

        for card in job_cards:
            title = card.select_one("h2.jobTitle span")
            company = card.select_one("span.companyName")
            location = card.select_one("div.companyLocation")
            link_tag = card.select_one("a")
            link = "https://in.indeed.com" + link_tag["href"] if link_tag else None

            jobs.append({
                "title": title.get_text(strip=True) if title else "",
                "company": company.get_text(strip=True) if company else "",
                "location": location.get_text(strip=True) if location else "",
                "link": link if link else ""
            })

    finally:
        driver.quit()

    return jobs

def extract_naukri():
    url = "https://www.naukri.com/fresher-jobs"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    jobs = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for card in soup.select("article.jobTuple"):
            title = card.select_one("a.title")
            company = card.select_one("a.subTitle")
            location = card.select_one("span.locWdth")
            link = title["href"] if title and title.has_attr("href") else ""
            jobs.append({
                "title": title.get_text(strip=True) if title else "",
                "company": company.get_text(strip=True) if company else "",
                "location": location.get_text(strip=True) if location else "",
                "link": link
            })
    return jobs

def save_to_csv(jobs, filename="jobs.csv"):
    if not jobs:
        print("No jobs scraped.")
        return
    fieldnames = ["title", "company", "location", "link"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)
    print(f"Saved {len(jobs)} jobs to {filename}")

if __name__ == "__main__":
    indeed_jobs = find_job_cards_bs4()
    naukri_jobs = extract_naukri()
    all_jobs = indeed_jobs + naukri_jobs
    save_to_csv(all_jobs, "jobs.csv")

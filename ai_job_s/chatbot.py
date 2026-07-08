import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random

# -------------------------------
# Utility Functions
# -------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

def rate_limit(min_delay=1, max_delay=3):
    time.sleep(random.uniform(min_delay, max_delay))

def scrape_naukri(pages=2):
    jobs = []
    base_url = "https://www.naukri.com/software-developer-jobs"

    for page in range(1, pages+1):
        url = f"{base_url}-{page}" if page > 1 else base_url
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("article", class_="jobTuple")

            for card in cards:
                try:
                    title_elem = card.find("a", class_="title")
                    company_elem = card.find("a", class_="subTitle")
                    location_elem = card.find("span", class_="locWdth")
                    
                    title = title_elem.text.strip() if title_elem else "N/A"
                    company = company_elem.text.strip() if company_elem else "N/A"
                    location = location_elem.text.strip() if location_elem else "N/A"
                    link = title_elem["href"] if title_elem else "#"

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "experience": "N/A",
                        "salary": "N/A",
                        "link": link,
                        "source": "Naukri"
                    })
                except Exception as e:
                    continue
            rate_limit()
        except Exception as e:
            continue
    return jobs

def scrape_indeed(pages=2):
    jobs = []
    base_url = "https://www.indeed.com/jobs?q=software+developer&start="

    for page in range(0, pages*10, 10):
        url = f"{base_url}{page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_="job_seen_beacon")

            for card in cards:
                try:
                    title_elem = card.find("h2")
                    company_elem = card.find("span", class_="companyName")
                    location_elem = card.find("div", class_="companyLocation")
                    link_elem = card.find("a")
                    
                    title = title_elem.text.strip() if title_elem else "N/A"
                    company = company_elem.text.strip() if company_elem else "N/A"
                    location = location_elem.text.strip() if location_elem else "N/A"
                    link = "https://www.indeed.com" + link_elem["href"] if link_elem else "#"

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "experience": "N/A",
                        "salary": "N/A",
                        "link": link,
                        "source": "Indeed"
                    })
                except Exception as e:
                    continue
            rate_limit()
        except Exception as e:
            continue
    return jobs

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("💼 Job Search Chatbot (India)")

st.sidebar.header("Filters")
location_filter = st.sidebar.text_input("Location")
experience_filter = st.sidebar.text_input("Experience (e.g., 2 years)")
salary_filter = st.sidebar.text_input("Salary (e.g., 5 LPA)")

if st.button("Fetch Jobs"):
    with st.spinner("Fetching jobs..."):
        naukri_jobs = scrape_naukri(pages=2)
        indeed_jobs = scrape_indeed(pages=2)
        all_jobs = naukri_jobs + indeed_jobs

    if not all_jobs:
        st.warning("No jobs found. Please try again later.")
    else:
        df = pd.DataFrame(all_jobs)
        
        # Check if dataframe has required columns
        if df.empty:
            st.warning("No jobs found. Please try again later.")
        else:
            # Display original data count
            st.info(f"Total jobs fetched: {len(df)}")
            
            # Apply filters
            if location_filter:
                try:
                    df = df[df["location"].str.contains(location_filter, case=False, na=False)]
                except KeyError:
                    st.error("Location column not found in data")
            
            if experience_filter and "experience" in df.columns:
                try:
                    df = df[df["experience"].str.contains(experience_filter, case=False, na=False)]
                except KeyError:
                    pass
            
            if salary_filter and "salary" in df.columns:
                try:
                    df = df[df["salary"].str.contains(salary_filter, case=False, na=False)]
                except KeyError:
                    pass

            st.write(f"Found {len(df)} jobs matching filters")
            
            if not df.empty:
                st.dataframe(df)
                
                # Chatbot-style interaction
                st.subheader("🤖 Chatbot")
                user_query = st.text_input("Ask about jobs (e.g., 'Show jobs in Pune')")
                if user_query:
                    try:
                        results = df[df["location"].str.contains(user_query, case=False, na=False)]
                        if not results.empty:
                            st.write(f"Found {len(results)} jobs matching your query:")
                            st.dataframe(results)
                        else:
                            st.write("No jobs found for your query.")
                    except KeyError:
                        st.error("Location column not found for filtering")
            else:
                st.warning("No jobs match your filters. Try adjusting your criteria.")

# Add a note about the API
st.sidebar.markdown("---")
st.sidebar.info(
    "**Note:** This app scrapes job listings from Naukri and Indeed. "
    "If no jobs appear, the websites may have changed their structure "
    "or blocked the request. Consider using official APIs for production use."
)
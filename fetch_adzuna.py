"""
SkillScope 2.0 - Multi-Domain Data Collection
Fetches job postings across multiple domains/roles and cities from Adzuna,
tagging each fetch with today's date for trend tracking.

Setup:
1. pip install requests python-dotenv
2. .env file must have ADZUNA_APP_ID and ADZUNA_APP_KEY
3. Run: python fetch_adzuna.py
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

if not APP_ID or not APP_KEY:
    raise SystemExit(
        "Missing ADZUNA_APP_ID or ADZUNA_APP_KEY. "
        "Create a .env file with both values before running."
    )

BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search"

# ---- Domains/roles to track ----
DOMAINS = [
    "Data Analyst",
    "Data Scientist",
    "Business Analyst",
    "Software Developer",
    "Full Stack Developer",
    "Data Engineer",
    "UI/UX Developer",
]

# ---- Cities (same for all domains) ----
CITIES = [
    "Bangalore",
    "Mumbai",
    "Delhi NCR",
    "Pune",
    "Hyderabad",
    "Remote",
]

RESULTS_PER_PAGE = 20
MAX_PAGES_PER_CITY = 3   # reduced from 5 -> keeps daily total ~126 calls, safe under 250/day limit
REQUEST_DELAY_SECONDS = 1

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

TODAY_STR = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fetch_page(domain: str, city: str, page: int) -> dict:
    """Fetch a single page of results for a given domain + city."""
    url = f"{BASE_URL}/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": domain,
        "where": city,
        "content-type": "application/json",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_domain_city(domain: str, city: str) -> list:
    """Fetch all pages for a domain+city combo."""
    all_results = []
    for page in range(1, MAX_PAGES_PER_CITY + 1):
        try:
            data = fetch_page(domain, city, page)
        except requests.exceptions.HTTPError as e:
            print(f"    HTTP error on {domain}/{city} page {page}: {e}")
            break
        except requests.exceptions.RequestException as e:
            print(f"    Network error on {domain}/{city} page {page}: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        all_results.extend(results)
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_results


def save_raw(domain: str, city: str, results: list):
    """Save raw results tagged with domain, city, and today's date."""
    safe_domain = domain.lower().replace(" ", "_").replace("/", "_")
    safe_city = city.lower().replace(" ", "_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = RAW_DIR / f"{safe_domain}__{safe_city}__{timestamp}.json"

    payload = {
        "domain": domain,
        "city_queried": city,
        "date_fetched": TODAY_STR,
        "fetched_at_utc": timestamp,
        "result_count": len(results),
        "results": results,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main():
    print(f"SkillScope 2.0 - Multi-domain collection for {TODAY_STR}")
    print(f"Domains: {len(DOMAINS)} | Cities: {len(CITIES)} | Max pages/city: {MAX_PAGES_PER_CITY}")
    est_calls = len(DOMAINS) * len(CITIES) * MAX_PAGES_PER_CITY
    print(f"Estimated max API calls today: {est_calls} (limit: 250/day)\n")

    summary = {}

    for domain in DOMAINS:
        print(f"Domain: {domain}")
        domain_total = 0
        for city in CITIES:
            results = fetch_domain_city(domain, city)
            save_raw(domain, city, results)
            domain_total += len(results)
            print(f"  {city}: {len(results)} postings")
        summary[domain] = domain_total
        print()

    print("=" * 50)
    print(f"Collection summary for {TODAY_STR}:")
    grand_total = 0
    for domain, count in summary.items():
        print(f"  {domain}: {count} postings")
        grand_total += count
    print(f"  TOTAL: {grand_total}")
    print("=" * 50)


if __name__ == "__main__":
    main()
"""
SkillScope - Step 1B: Adzuna Data Collection
Fetches Data Analyst job postings for major Indian cities and saves
raw, untouched JSON responses to data/raw/.

Setup:
1. pip install requests python-dotenv
2. Create a .env file in the same folder with:
     ADZUNA_APP_ID=your_app_id_here
     ADZUNA_APP_KEY=your_app_key_here
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

APP_ID = os.getenv("2aedd3a8")
APP_KEY = os.getenv("24dd10c13e99838c8c9c4d9943ee8a31")

if not APP_ID or not APP_KEY:
    raise SystemExit(
        "Missing ADZUNA_APP_ID or ADZUNA_APP_KEY. "
        "Create a .env file with both values before running."
    )

# Adzuna's country code for India is 'in'
BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search"

# Cities to query. Adzuna uses free-text location matching via 'where'.
CITIES = [
    "Bangalore",
    "Mumbai",
    "Delhi NCR",
    "Pune",
    "Hyderabad",
    "Remote",
]

SEARCH_TERM = "Data Analyst"
RESULTS_PER_PAGE = 20     # Adzuna's max per page
MAX_PAGES_PER_CITY = 5    # 5 pages x 20 = up to 100 postings per city (adjust later)
REQUEST_DELAY_SECONDS = 1  # be polite to the API, avoid rate-limit issues

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def fetch_page(city: str, page: int) -> dict:
    """Fetch a single page of results for a given city."""
    url = f"{BASE_URL}/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": SEARCH_TERM,
        "where": city,
        "content-type": "application/json",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_city(city: str) -> list:
    """Fetch all pages for a city until no more results or MAX_PAGES_PER_CITY hit."""
    all_results = []
    for page in range(1, MAX_PAGES_PER_CITY + 1):
        print(f"  Fetching {city} - page {page}...")
        try:
            data = fetch_page(city, page)
        except requests.exceptions.HTTPError as e:
            print(f"  HTTP error on {city} page {page}: {e}")
            break
        except requests.exceptions.RequestException as e:
            print(f"  Network error on {city} page {page}: {e}")
            break

        results = data.get("results", [])
        if not results:
            print(f"  No more results for {city} after page {page - 1}.")
            break

        all_results.extend(results)
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_results


def save_raw(city: str, results: list):
    """Save raw results for a city as timestamped JSON, untouched."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_city = city.lower().replace(" ", "_")
    filename = RAW_DIR / f"{safe_city}_{timestamp}.json"

    payload = {
        "city_queried": city,
        "search_term": SEARCH_TERM,
        "fetched_at_utc": timestamp,
        "result_count": len(results),
        "results": results,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  Saved {len(results)} postings -> {filename}")


def main():
    print(f"Starting SkillScope data collection: '{SEARCH_TERM}' across {len(CITIES)} cities\n")
    summary = {}

    for city in CITIES:
        print(f"City: {city}")
        results = fetch_city(city)
        save_raw(city, results)
        summary[city] = len(results)
        print()

    print("=" * 40)
    print("Collection summary:")
    total = 0
    for city, count in summary.items():
        print(f"  {city}: {count} postings")
        total += count
    print(f"  TOTAL: {total} postings")
    print("=" * 40)


if __name__ == "__main__":
    main()
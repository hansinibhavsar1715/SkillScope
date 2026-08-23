"""
SkillScope 2.0 - Load & Process Script (for automation)
Loads today's raw JSON into skillscope.db, extracts skills, and saves a
daily skill-demand snapshot for trend tracking.

Run with: python load_data.py
(Meant to run right after fetch_adzuna.py in the same pipeline)
"""

import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

DB_PATH = "skillscope.db"
RAW_DIR = Path("data/raw")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ---- Ensure schema exists (safe to run even on a fresh DB) ----
cursor.execute("""
CREATE TABLE IF NOT EXISTS postings (
    id TEXT PRIMARY KEY,
    title TEXT,
    company TEXT,
    city_queried TEXT,
    location_display_name TEXT,
    category_label TEXT,
    contract_time TEXT,
    salary_min REAL,
    salary_max REAL,
    salary_is_predicted TEXT,
    created_date TEXT,
    description TEXT,
    redirect_url TEXT,
    fetched_at_utc TEXT,
    domain TEXT,
    date_fetched TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS posting_skills (
    posting_id TEXT,
    skill TEXT,
    PRIMARY KEY (posting_id, skill)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_skill_snapshot (
    date_fetched TEXT,
    domain TEXT,
    skill TEXT,
    posting_count INTEGER,
    PRIMARY KEY (date_fetched, domain, skill)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS my_skills (
    skill TEXT PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS data_notes (
    note_key TEXT PRIMARY KEY,
    note_text TEXT
)
""")
conn.commit()

# ---- Skill patterns ----
SKILL_PATTERNS = {
    "SQL":            [r"\bsql\b"],
    "Python":         [r"\bpython\b"],
    "Java":           [r"\bjava\b(?!script)"],
    "JavaScript":     [r"\bjavascript\b", r"\bjs\b"],
    "React":          [r"\breact(\.?js)?\b"],
    "Node.js":        [r"\bnode(\.?js)?\b"],
    "Angular":        [r"\bangular\b"],
    "HTML/CSS":       [r"\bhtml\b", r"\bcss\b"],
    "Figma":          [r"\bfigma\b"],
    "Adobe XD":       [r"\badobe xd\b"],
    "UI/UX Design":   [r"\bui/?ux\b", r"\buser experience\b", r"\buser interface\b"],
    "R":              [r"\br programming\b", r"\br studio\b"],
    "Excel":          [r"\bexcel\b"],
    "Power BI":       [r"\bpower\s?bi\b"],
    "Tableau":        [r"\btableau\b"],
    "Looker":         [r"\blooker\b"],
    "SAS":            [r"\bsas\b"],
    "Statistics":     [r"\bstatistic(s|al)?\b"],
    "Machine Learning": [r"\bmachine learning\b", r"\bml\b"],
    "Deep Learning":  [r"\bdeep learning\b"],
    "AWS":            [r"\baws\b", r"\bamazon web services\b"],
    "Azure":          [r"\bazure\b"],
    "GCP":            [r"\bgcp\b", r"\bgoogle cloud\b"],
    "Docker":         [r"\bdocker\b"],
    "Kubernetes":     [r"\bkubernetes\b", r"\bk8s\b"],
    "ETL":            [r"\betl\b"],
    "Data Warehousing": [r"\bdata warehous\w*\b"],
    "Big Data":       [r"\bbig data\b", r"\bhadoop\b", r"\bspark\b"],
    "Power Query":    [r"\bpower query\b"],
    "VBA":            [r"\bvba\b"],
    "Git":            [r"\bgit\b(?!hub|lab)"],
    "REST API":       [r"\brest(ful)? api\b"],
    "MongoDB":        [r"\bmongodb\b"],
    "PostgreSQL":     [r"\bpostgres(ql)?\b"],
    "A/B Testing":    [r"\ba/b test\w*\b", r"\bab test\w*\b"],
    "Google Analytics": [r"\bgoogle analytics\b"],
    "Communication":  [r"\bcommunication skills\b"],
}
COMPILED_PATTERNS = {
    skill: [re.compile(p, re.IGNORECASE) for p in patterns]
    for skill, patterns in SKILL_PATTERNS.items()
}


def extract_skills(description: str) -> list:
    if not description:
        return []
    return [skill for skill, patterns in COMPILED_PATTERNS.items()
            if any(p.search(description) for p in patterns)]


def main():
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Find latest file per (domain, city) combo
    domain_city_files = {}
    for file in RAW_DIR.glob("*__*__*.json"):
        parts = file.stem.split("__")
        if len(parts) != 3:
            continue
        domain_key, city_key, _ = parts
        key = (domain_key, city_key)
        if key not in domain_city_files or file.name > domain_city_files[key].name:
            domain_city_files[key] = file

    print(f"Found {len(domain_city_files)} domain-city files to load.")

    rows_loaded = 0
    snapshot_counter = defaultdict(lambda: defaultdict(set))

    for (domain_key, city_key), file in domain_city_files.items():
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        domain = data.get("domain", domain_key)
        city_queried = data.get("city_queried", city_key)
        date_fetched = data.get("date_fetched", today_str)
        results = data.get("results", [])

        for job in results:
            job_id = job.get("id")
            title = job.get("title", "")
            company = (job.get("company") or {}).get("display_name", "")
            location_display = (job.get("location") or {}).get("display_name", "")
            category_label = (job.get("category") or {}).get("label", "")
            contract_time = job.get("contract_time", "")
            salary_min = job.get("salary_min")
            salary_max = job.get("salary_max")
            salary_is_predicted = job.get("salary_is_predicted", "")
            created_date = job.get("created", "")
            description = job.get("description", "")
            redirect_url = job.get("redirect_url", "")

            cursor.execute("""
                INSERT OR REPLACE INTO postings
                (id, title, company, city_queried, location_display_name, category_label,
                 contract_time, salary_min, salary_max, salary_is_predicted, created_date,
                 description, redirect_url, fetched_at_utc, domain, date_fetched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, title, company, city_queried, location_display, category_label,
                  contract_time, salary_min, salary_max, salary_is_predicted, created_date,
                  description, redirect_url, data.get("fetched_at_utc", ""), domain, date_fetched))

            skills_found = extract_skills(description)
            for skill in skills_found:
                cursor.execute(
                    "INSERT OR IGNORE INTO posting_skills (posting_id, skill) VALUES (?, ?)",
                    (job_id, skill)
                )
                snapshot_counter[domain][skill].add(job_id)

            rows_loaded += 1

    conn.commit()
    print(f"Loaded {rows_loaded} postings across {len(domain_city_files)} domain-city files.")

    snapshot_rows = 0
    for domain, skills in snapshot_counter.items():
        for skill, posting_ids in skills.items():
            cursor.execute("""
                INSERT OR REPLACE INTO daily_skill_snapshot
                (date_fetched, domain, skill, posting_count)
                VALUES (?, ?, ?, ?)
            """, (today_str, domain, skill, len(posting_ids)))
            snapshot_rows += 1
    conn.commit()
    print(f"Saved {snapshot_rows} skill-snapshot rows for {today_str}.")

    conn.close()


if __name__ == "__main__":
    main()

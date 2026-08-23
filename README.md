# 📊 SkillScope — Live Multi-Domain Job Market Intelligence & Skill-Gap Dashboard

**SkillScope** is a fully automated, end-to-end data analytics platform that collects **live job postings** from the Adzuna API across 7 tech domains and 6 major Indian cities, analyzes in-demand skills and salary trends, and lets users evaluate their own skill set against real-time market demand — all through an interactive dashboard that refreshes itself daily.

Unlike typical portfolio projects built on static Kaggle datasets, SkillScope is powered by a **live, self-updating data pipeline** — the same architecture pattern used in real production analytics systems.

🔗 **Live Dashboard:** [Local URL: http://localhost:8501]
🔗 **GitHub Repository:** https://github.com/hansinibhavsar1715/SkillScope

---

## 📌 Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Data Collection](#data-collection)
- [Database Design](#database-design)
- [Skill Extraction Methodology](#skill-extraction-methodology)
- [Salary Analysis](#salary-analysis)
- [Skill-Gap Evaluator](#skill-gap-evaluator)
- [Daily Automation (GitHub Actions)](#daily-automation-github-actions)
- [Trend Tracking](#trend-tracking)
- [Power BI Companion Dashboard](#power-bi-companion-dashboard)
- [Data Limitations & Quality Notes](#data-limitations--quality-notes)
- [Setup & Installation](#setup--installation)
- [Future Improvements](#future-improvements)
- [Author](#author)

---

## 🎯 Project Overview

**Objective:** Continuously analyze real, current job postings across multiple domains to answer:
1. Which skills are actually in demand right now, per domain?
2. How do skill combinations affect salary?
3. How does an individual's own skill set compare to live market demand?

**Approach:** A five-stage automated pipeline —
`Legally-sourced live data collection → SQL storage & querying → Statistical analysis → Personal skill-gap evaluation → Published interactive dashboard`

This project intentionally avoids scraping platforms like LinkedIn or Naukri (both prohibit scraping in their Terms of Service) and instead uses the **Adzuna Jobs API** — a free, legal, structured data source with genuine India job-market coverage.

---

## ✨ Key Features

- 🔄 **Fully automated daily data refresh** — no manual runs required, powered by GitHub Actions
- 🌐 **Multi-domain coverage** — Data Analyst, Data Scientist, Business Analyst, Software Developer, Full Stack Developer, Data Engineer, UI/UX Developer
- 🏙️ **City-wise analysis** across Bangalore, Mumbai, Delhi NCR, Pune, Hyderabad, and Remote
- 🔍 **Automated skill extraction** from job descriptions using regex-based keyword matching (35+ tracked skills)
- 💰 **Salary correlation analysis** — average salary by skill, with data-quality corrections applied
- 📈 **Historical trend tracking** — daily skill-demand snapshots build a time series for peak-detection
- 🎯 **Interactive skill-gap evaluator** — select a domain, check off your skills, and instantly see matched skills, priority gaps, and a readiness score
- 📊 **Dual dashboard delivery** — live Streamlit web app + companion Power BI dashboard
- 📝 **Transparent data-quality documentation** — every known limitation in the dataset is explicitly logged and surfaced in the dashboard, not hidden

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Data Collection | Python, `requests`, Adzuna Jobs API |
| Data Storage | SQLite |
| Data Processing | Python, `pandas`, `re` (regex) |
| Automation / Scheduling | GitHub Actions (cron-based) |
| Web Dashboard | Streamlit, Plotly |
| BI Dashboard | Power BI Desktop |
| Version Control | Git, GitHub |
| Deployment | Streamlit Community Cloud |

---

## 🏗️ System Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│   Adzuna API     │───▶ │ fetch_adzuna │───▶ │  Raw JSON      │
│ (7 domains ×     │     │    .py       │     │  (data/raw/)   │
│  6 cities)        │     └──────────────┘     └───────┬────────┘
└─────────────────┘                                   │
                                                        ▼
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│  Streamlit        │◀── │ skillscope.db│◀────│  load_data.py  │
│  Dashboard         │     │  (SQLite)    │     │ (skill extract,│
│  (live, interactive)│    └──────────────┘     │  daily snapshot)│
└─────────────────┘                            └───────────────┘
        ▲
        │
┌───────┴─────────┐
│ GitHub Actions    │  ← runs fetch + load daily, commits updated DB
│ (daily cron job)   │
└─────────────────┘

┌─────────────────┐
│  Power BI          │  ← CSV export of the same database, for a
│  Companion Dashboard│    business-intelligence-style view
└─────────────────┘
```

---

## 📁 Project Structure

```
skillscope/
├── .github/
│   └── workflows/
│       └── daily_update.yml       # GitHub Actions automation workflow
├── data/
│   └── raw/                       # Raw JSON responses per domain-city-day
├── powerbi_exports/                # CSV exports for Power BI
│   ├── postings.csv
│   ├── posting_skills.csv
│   ├── postings_flattened.csv
│   └── daily_skill_snapshot.csv
├── app.py                          # Streamlit dashboard
├── fetch_adzuna.py                 # Data collection script (multi-domain)
├── load_data.py                    # Loads raw JSON → SQLite, extracts skills
├── skillscope.db                   # SQLite database (auto-updated daily)
├── requirements.txt                # Python dependencies
├── .gitignore                      # Excludes .env, checkpoints, etc.
├── .env                             # API keys (NOT committed — see setup)
└── README.md
```

---

## 📥 Data Collection

**Source:** [Adzuna Jobs API](https://developer.adzuna.com/) — free developer tier, legal and structured.

**Scope:**
- **7 domains:** Data Analyst, Data Scientist, Business Analyst, Software Developer, Full Stack Developer, Data Engineer, UI/UX Developer
- **6 cities:** Bangalore, Mumbai, Delhi NCR, Pune, Hyderabad, Remote
- **Fields captured per posting:** title, company, location, category, contract type, salary (when disclosed), description snippet, posted date, and a unique job ID

**Rate-limit management:** Adzuna's free tier allows 250 API calls/day. With 7 domains × 6 cities × 3 pages, the pipeline uses a maximum of ~126 calls/day — well within the safe limit, leaving margin for retries.

**Current dataset size:** 2,000+ live postings, refreshed daily.

---

## 🗄️ Database Design

SQLite was chosen for simplicity — no server setup required, and easily portable.

**Core tables:**

| Table | Purpose |
|---|---|
| `postings` | One row per unique job posting (deduplicated by Adzuna job ID), tagged with `domain` and `date_fetched` |
| `posting_skills` | Many-to-many mapping between postings and detected skills |
| `daily_skill_snapshot` | Permanent daily record of skill-demand counts per domain, used for trend analysis (independent of the mutable `postings` table) |
| `my_skills` | User's own skill set, for the skill-gap comparison feature |
| `data_notes` | Documented data-quality limitations, surfaced transparently in the dashboard |

---

## 🔍 Skill Extraction Methodology

Skills are extracted from job description text using **regex-based keyword matching** across 35+ tracked skills spanning all 7 domains — including SQL, Python, Power BI, Tableau, React, Docker, Figma, AWS, Machine Learning, and more.

Each domain has a distinct skill footprint (e.g., UI/UX postings surface Figma and Adobe XD; Data Engineer postings surface ETL and Big Data tools), and skills are tracked per-domain rather than globally.

---

## 💰 Salary Analysis

- Only ~20–23% of postings disclose salary — typical for the Indian job market, and explicitly documented as a limitation rather than glossed over.
- A data-quality fix was applied for postings where Adzuna returns `salary_min = 0` (meaning only a maximum was specified by the employer) — these are treated as `salary_max`-only figures instead of being averaged with zero, which would have artificially deflated the numbers.
- Average salary by skill is only reported where at least 3 postings support the figure, to avoid misleading single-posting averages.

---

## 🎯 Skill-Gap Evaluator

An interactive feature within the Streamlit dashboard:

1. Select a domain from a dropdown
2. A checklist of all skills detected in that domain's market data appears (built dynamically from the database — not hardcoded)
3. Check the skills you currently have
4. Click **Evaluate** to instantly see:
   - ✅ **Matched skills** — what you have that the market wants
   - ⚠️ **Priority gaps** — high-demand skills you don't have yet, sorted by demand
   - 📊 **A readiness score** — the percentage of in-demand skills you currently cover

---

## ⚙️ Daily Automation (GitHub Actions)

The entire collection-and-load pipeline runs automatically every day via a scheduled GitHub Actions workflow (`.github/workflows/daily_update.yml`):

1. Checks out the repository
2. Sets up Python
3. Runs `fetch_adzuna.py` (using API keys stored securely as GitHub Secrets)
4. Runs `load_data.py` to update the database and record a new daily skill snapshot
5. Commits and pushes the updated `skillscope.db` back to the repository

This means the live dashboard reflects fresh market data every single day, with zero manual intervention.

---

## 📈 Trend Tracking

The `daily_skill_snapshot` table records skill-demand counts per domain **every day**, independent of the main `postings` table (which only reflects the current state). Over time, this builds a genuine time series that powers:

- Skill-demand trend line charts (per domain)
- Peak-demand day detection per skill

This is a feature that grows in value the longer the automation runs.

---

## 📊 Power BI Companion Dashboard

In addition to the live Streamlit web app, the same underlying data is exported to CSV (`powerbi_exports/`) and visualized in a companion **Power BI Desktop** dashboard, featuring:

- A domain slicer controlling all visuals
- A skill-demand bar chart
- A city-wise postings breakdown
- An average-salary-by-skill chart (filtered to skills with a minimum sample size for reliability)

This demonstrates the same insights through a business-intelligence tool widely used in industry reporting.

---

## ⚠️ Data Limitations & Quality Notes

In the spirit of honest, real-world analysis, the following limitations are documented directly in the dataset (`data_notes` table) and surfaced in the dashboard rather than hidden:

- **Description truncation:** Adzuna's free tier returns truncated job descriptions (~500 characters), not the full posting. Skill-keyword extraction is therefore an under-count, not an exhaustive requirement list.
- **Sparse salary disclosure:** Only ~20–23% of postings include salary data, typical for the Indian market — salary-based conclusions are directional, not statistically robust.
- **Zero-value salary handling:** Postings with `salary_min = 0` are treated as max-only figures to avoid deflating averages.
- **"Remote" as a city filter:** Adzuna does not treat "Remote" as a matchable location for India — this consistently returns 0 results and is a known platform limitation, not a bug in this pipeline.

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.9+
- A free [Adzuna API](https://developer.adzuna.com/) account (`app_id` and `app_key`)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/hansinibhavsar1715/SkillScope.git
cd SkillScope

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create a .env file in the root folder with:
#    ADZUNA_APP_ID=your_app_id
#    ADZUNA_APP_KEY=your_app_key

# 4. Fetch live data
python fetch_adzuna.py

# 5. Load data into the database
python load_data.py

# 6. Run the dashboard
streamlit run app.py
```

### Setting up your own daily automation
1. Add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` as **GitHub Secrets** (Settings → Secrets and variables → Actions)
2. Ensure **Workflow permissions** are set to "Read and write" (Settings → Actions → General)
3. The workflow in `.github/workflows/daily_update.yml` will run automatically on schedule, or can be triggered manually from the Actions tab

---

## 🔮 Future Improvements

- Fetch full job descriptions (not just truncated snippets) to improve skill-extraction accuracy
- Add more granular experience-level segmentation (entry-level vs. senior)
- Expand skill-gap evaluator with a "best-fit domain" recommendation across all tracked roles
- Add email/notification alerts when a tracked skill's demand crosses a threshold

---

## 👤 Author

**[Hansini Bbhavsar]**
Built as an end-to-end portfolio project demonstrating live data collection, SQL database design, automated pipelines, and interactive dashboard development.

📧 [hansinibhavsar@gmail.com] | 🔗 [www.linkedin.com/in/hansini-bhavsar-a07111253] | 💻 [https://github.com/hansinibhavsar1715]

---

*Data source: [Adzuna Jobs API](https://developer.adzuna.com/). This project is not affiliated with or endorsed by Adzuna.*

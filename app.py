"""
SkillScope Dashboard - Live Data Analyst Job Market Intelligence
Run with: streamlit run app.py
Requires: skillscope.db in the same folder (built via the earlier notebook steps)
"""

import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

# ---------------------------------------------------------
# Page config
# ---------------------------------------------------------
st.set_page_config(
    page_title="SkillScope - Data Analyst Market Intelligence",
    page_icon="📊",
    layout="wide",
)

DB_PATH = "skillscope.db"


@st.cache_data(ttl=3600)
def load_data():
    """Load all needed tables from SQLite into pandas DataFrames."""
    conn = sqlite3.connect(DB_PATH)

    postings = pd.read_sql_query("SELECT * FROM postings", conn)
    posting_skills = pd.read_sql_query("SELECT * FROM posting_skills", conn)

    try:
        my_skills = pd.read_sql_query("SELECT * FROM my_skills", conn)
    except Exception:
        my_skills = pd.DataFrame(columns=["skill"])

    try:
        notes = pd.read_sql_query("SELECT * FROM data_notes", conn)
    except Exception:
        notes = pd.DataFrame(columns=["note_key", "note_text"])

    conn.close()
    return postings, posting_skills, my_skills, notes


postings, posting_skills, my_skills, notes = load_data()

# Merge postings + skills for convenience
merged = posting_skills.merge(postings, left_on="posting_id", right_on="id", how="left")

# Corrected salary column (handle salary_min = 0 case, same logic as notebook)
merged["salary_avg"] = merged.apply(
    lambda row: row["salary_max"]
    if row["salary_min"] == 0
    else (row["salary_min"] + row["salary_max"]) / 2
    if pd.notnull(row["salary_min"]) and pd.notnull(row["salary_max"])
    else None,
    axis=1,
)
postings["salary_avg"] = postings.apply(
    lambda row: row["salary_max"]
    if row["salary_min"] == 0
    else (row["salary_min"] + row["salary_max"]) / 2
    if pd.notnull(row["salary_min"]) and pd.notnull(row["salary_max"])
    else None,
    axis=1,
)

my_skill_set = set(my_skills["skill"].tolist())

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.title("📊 SkillScope")
st.caption("Live Data Analyst Job Market Intelligence & Skill-Gap Dashboard — built on real Adzuna job posting data (India)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Postings", len(postings))
col2.metric("Cities Covered", postings["city_queried"].nunique())
col3.metric("Skills Tracked", posting_skills["skill"].nunique())
pct_with_salary = (postings["salary_avg"].notnull().sum() / len(postings) * 100) if len(postings) else 0
col4.metric("Postings w/ Salary Data", f"{pct_with_salary:.0f}%")

st.divider()

# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔥 Skill Demand",
    "🏙️ City Breakdown",
    "💰 Salary Insights",
    "🎯 My Skill Gap",
    "ℹ️ Data Notes",
])

# ---- TAB 1: Overall skill demand ----
with tab1:
    st.subheader("Most In-Demand Skills")

    skill_counts = (
        posting_skills.groupby("skill")["posting_id"]
        .nunique()
        .reset_index(name="postings_count")
        .sort_values("postings_count", ascending=False)
    )

    fig = px.bar(
        skill_counts,
        x="postings_count",
        y="skill",
        orientation="h",
        title="Number of Postings Mentioning Each Skill",
        labels={"postings_count": "Number of Postings", "skill": "Skill"},
        color="postings_count",
        color_continuous_scale="Blues",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Note: skills are extracted from job description snippets, which may be truncated. "
        "See the Data Notes tab for details."
    )

# ---- TAB 2: City-wise breakdown ----
with tab2:
    st.subheader("Skill Demand by City")

    city_options = sorted(postings["city_queried"].dropna().unique().tolist())
    selected_city = st.selectbox("Select a city", ["All Cities"] + city_options)

    if selected_city == "All Cities":
        city_skill_data = merged.copy()
    else:
        city_skill_data = merged[merged["city_queried"] == selected_city]

    city_skill_counts = (
        city_skill_data.groupby("skill")["posting_id"]
        .nunique()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
    )

    fig2 = px.bar(
        city_skill_counts,
        x="skill",
        y="count",
        title=f"Top Skills in {selected_city}",
        color="count",
        color_continuous_scale="Teal",
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Postings Count by City")
    city_totals = postings.groupby("city_queried").size().reset_index(name="total_postings")
    fig3 = px.pie(city_totals, names="city_queried", values="total_postings", title="Share of Postings by City")
    st.plotly_chart(fig3, use_container_width=True)

# ---- TAB 3: Salary insights ----
with tab3:
    st.subheader("Average Salary by Skill")
    st.caption(
        f"Based on {postings['salary_avg'].notnull().sum()} postings with disclosed salary "
        f"out of {len(postings)} total ({pct_with_salary:.0f}%). Treat as directional, not statistically robust."
    )

    salary_by_skill = (
        merged[merged["salary_avg"].notnull()]
        .groupby("skill")
        .agg(avg_salary=("salary_avg", "mean"), num_postings=("posting_id", "nunique"))
        .reset_index()
    )
    salary_by_skill = salary_by_skill[salary_by_skill["num_postings"] >= 3]
    salary_by_skill = salary_by_skill.sort_values("avg_salary", ascending=False)

    if len(salary_by_skill) > 0:
        fig4 = px.bar(
            salary_by_skill,
            x="avg_salary",
            y="skill",
            orientation="h",
            title="Average Salary by Skill (min. 3 postings)",
            labels={"avg_salary": "Average Salary (₹)", "skill": "Skill"},
            color="avg_salary",
            color_continuous_scale="Greens",
            hover_data=["num_postings"],
        )
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Not enough salary data to compute reliable per-skill averages.")

# ---- TAB 4: Personal skill gap ----
with tab4:
    st.subheader("Your Skill Gap Analysis")

    market_skills = set(posting_skills["skill"].unique().tolist())
    matched = my_skill_set & market_skills
    gaps = market_skills - my_skill_set
    extras = my_skill_set - market_skills

    demand_lookup = skill_counts.set_index("skill")["postings_count"].to_dict()

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### ✅ Matched Skills")
        if matched:
            matched_df = pd.DataFrame(
                [(s, demand_lookup.get(s, 0)) for s in matched],
                columns=["Skill", "Demand (postings)"],
            ).sort_values("Demand (postings)", ascending=False)
            st.dataframe(matched_df, use_container_width=True, hide_index=True)
        else:
            st.write("No matches found.")

    with colB:
        st.markdown("### ⚠️ Priority Gaps (learn these next)")
        if gaps:
            gaps_df = pd.DataFrame(
                [(s, demand_lookup.get(s, 0)) for s in gaps],
                columns=["Skill", "Demand (postings)"],
            ).sort_values("Demand (postings)", ascending=False)
            st.dataframe(gaps_df, use_container_width=True, hide_index=True)
        else:
            st.write("No gaps — you cover all detected market skills!")

    if extras:
        st.markdown("### 💡 Your Extra Skills (low signal in this dataset)")
        st.write(", ".join(extras))

    if market_skills:
        readiness = len(matched) / len(market_skills) * 100
        st.metric("Readiness Score", f"{readiness:.0f}%", help="Share of in-demand skills (from this dataset) that you currently have.")

# ---- TAB 5: Data notes / limitations ----
with tab5:
    st.subheader("Data Collection & Methodology Notes")
    st.write(
        "This dashboard is built on live job postings pulled from the Adzuna Jobs API "
        "for Data Analyst roles across major Indian cities. As with any real-world data "
        "project, the underlying data has some limitations — documented transparently below."
    )
    for _, row in notes.iterrows():
        with st.expander(row["note_key"].replace("_", " ").title()):
            st.write(row["note_text"])

    if len(notes) == 0:
        st.info("No data-quality notes recorded yet.")

st.divider()
st.caption("Built by [Hansini Bhavsar] · Data source: Adzuna Jobs API · Not affiliated with Adzuna")

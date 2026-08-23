"""
SkillScope 2.0 Dashboard - Multi-Domain Job Market Intelligence
Run with: streamlit run app.py
Requires: skillscope.db in the same folder
"""

import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="SkillScope - Multi-Domain Market Intelligence",
    page_icon="📊",
    layout="wide",
)

DB_PATH = "skillscope.db"


@st.cache_data(ttl=3600)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    postings = pd.read_sql_query("SELECT * FROM postings", conn)
    posting_skills = pd.read_sql_query("SELECT * FROM posting_skills", conn)

    try:
        daily_snapshot = pd.read_sql_query("SELECT * FROM daily_skill_snapshot", conn)
    except Exception:
        daily_snapshot = pd.DataFrame(columns=["date_fetched", "domain", "skill", "posting_count"])

    try:
        notes = pd.read_sql_query("SELECT * FROM data_notes", conn)
    except Exception:
        notes = pd.DataFrame(columns=["note_key", "note_text"])

    conn.close()
    return postings, posting_skills, daily_snapshot, notes


postings, posting_skills, daily_snapshot, notes = load_data()

merged = posting_skills.merge(postings, left_on="posting_id", right_on="id", how="left")

merged["salary_avg"] = merged.apply(
    lambda row: row["salary_max"]
    if row["salary_min"] == 0
    else (row["salary_min"] + row["salary_max"]) / 2
    if pd.notnull(row["salary_min"]) and pd.notnull(row["salary_max"])
    else None,
    axis=1,
)

ALL_DOMAINS = sorted(postings["domain"].dropna().unique().tolist())

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.title("📊 SkillScope")
st.caption("Live Multi-Domain Job Market Intelligence & Skill-Gap Dashboard — built on real Adzuna job posting data (India), auto-updated daily")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Postings", len(postings))
col2.metric("Domains Tracked", len(ALL_DOMAINS))
col3.metric("Cities Covered", postings["city_queried"].nunique())
col4.metric("Skills Tracked", posting_skills["skill"].nunique())

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔥 Skill Demand",
    "🏙️ City Breakdown",
    "📈 Trends Over Time",
    "🎯 Skill-Gap Evaluator",
    "ℹ️ Data Notes",
])

# ---- TAB 1: Skill demand (with domain filter) ----
with tab1:
    st.subheader("Most In-Demand Skills")

    domain_filter = st.selectbox("Filter by domain", ["All Domains"] + ALL_DOMAINS, key="tab1_domain")

    if domain_filter == "All Domains":
        filtered = merged.copy()
    else:
        filtered = merged[merged["domain"] == domain_filter]

    skill_counts = (
        filtered.groupby("skill")["posting_id"]
        .nunique()
        .reset_index(name="postings_count")
        .sort_values("postings_count", ascending=False)
        .head(20)
    )

    fig = px.bar(
        skill_counts, x="postings_count", y="skill", orientation="h",
        title=f"Top Skills — {domain_filter}",
        labels={"postings_count": "Number of Postings", "skill": "Skill"},
        color="postings_count", color_continuous_scale="Blues",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Postings Count by Domain")
    domain_totals = postings.groupby("domain").size().reset_index(name="total_postings").sort_values("total_postings", ascending=False)
    fig_d = px.bar(domain_totals, x="domain", y="total_postings", title="Total Postings per Domain", color="total_postings", color_continuous_scale="Purples")
    st.plotly_chart(fig_d, use_container_width=True)

# ---- TAB 2: City breakdown (with domain filter) ----
with tab2:
    st.subheader("Skill Demand by City")

    col_a, col_b = st.columns(2)
    with col_a:
        domain_sel = st.selectbox("Select domain", ALL_DOMAINS, key="tab2_domain")
    with col_b:
        city_options = sorted(postings["city_queried"].dropna().unique().tolist())
        city_sel = st.selectbox("Select city", ["All Cities"] + city_options, key="tab2_city")

    city_data = merged[merged["domain"] == domain_sel]
    if city_sel != "All Cities":
        city_data = city_data[city_data["city_queried"] == city_sel]

    city_skill_counts = (
        city_data.groupby("skill")["posting_id"].nunique()
        .reset_index(name="count").sort_values("count", ascending=False).head(10)
    )
    fig2 = px.bar(city_skill_counts, x="skill", y="count", title=f"Top Skills — {domain_sel} in {city_sel}", color="count", color_continuous_scale="Teal")
    st.plotly_chart(fig2, use_container_width=True)

    domain_city_totals = postings[postings["domain"] == domain_sel].groupby("city_queried").size().reset_index(name="total_postings")
    fig3 = px.pie(domain_city_totals, names="city_queried", values="total_postings", title=f"{domain_sel} — Share of Postings by City")
    st.plotly_chart(fig3, use_container_width=True)

# ---- TAB 3: Trends over time ----
with tab3:
    st.subheader("Skill Demand Trends Over Time")

    if daily_snapshot.empty or daily_snapshot["date_fetched"].nunique() < 2:
        st.info(
            "📅 Trend data builds up over time as the daily automation runs. "
            "Right now there's only one day of history — check back after a few days "
            "to see demand trends and peak-detection charts here."
        )
        if not daily_snapshot.empty:
            st.write(f"Data collected so far: {daily_snapshot['date_fetched'].nunique()} day(s)")
    else:
        trend_domain = st.selectbox("Select domain", ALL_DOMAINS, key="tab3_domain")
        domain_trend = daily_snapshot[daily_snapshot["domain"] == trend_domain]

        top_skills_overall = (
            domain_trend.groupby("skill")["posting_count"].sum()
            .reset_index().sort_values("posting_count", ascending=False)
            .head(8)["skill"].tolist()
        )
        trend_plot_data = domain_trend[domain_trend["skill"].isin(top_skills_overall)]

        fig_trend = px.line(
            trend_plot_data, x="date_fetched", y="posting_count", color="skill",
            title=f"{trend_domain} — Skill Demand Over Time (Top 8 Skills)",
            labels={"date_fetched": "Date", "posting_count": "Postings Mentioning Skill"},
            markers=True,
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Peak detection
        st.subheader("Peak Demand Days")
        peaks = (
            domain_trend.loc[domain_trend.groupby("skill")["posting_count"].idxmax()]
            [["skill", "date_fetched", "posting_count"]]
            .sort_values("posting_count", ascending=False)
        )
        st.dataframe(peaks.rename(columns={
            "skill": "Skill", "date_fetched": "Peak Date", "posting_count": "Peak Postings Count"
        }), use_container_width=True, hide_index=True)

# ---- TAB 4: Interactive skill-gap evaluator ----
with tab4:
    st.subheader("🎯 Skill-Gap Evaluator")
    st.write("Pick a domain, then select the skills you currently have. Click Evaluate to see your match.")

    eval_domain = st.selectbox("Choose a domain", ALL_DOMAINS, key="tab4_domain")

    domain_skill_data = merged[merged["domain"] == eval_domain]
    domain_skills_available = sorted(domain_skill_data["skill"].unique().tolist())

    if not domain_skills_available:
        st.warning("No skills detected for this domain yet.")
    else:
        st.markdown(f"**Skills detected in market for {eval_domain}** (check the ones you have):")

        # Render checkboxes in a grid of columns
        num_cols = 4
        cols = st.columns(num_cols)
        selected_skills = []
        for i, skill in enumerate(domain_skills_available):
            with cols[i % num_cols]:
                if st.checkbox(skill, key=f"skill_{eval_domain}_{skill}"):
                    selected_skills.append(skill)

        evaluate_clicked = st.button("Evaluate My Skills", type="primary")

        if evaluate_clicked:
            demand_lookup = (
                domain_skill_data.groupby("skill")["posting_id"].nunique().to_dict()
            )
            market_skill_set = set(domain_skills_available)
            my_set = set(selected_skills)

            matched = my_set & market_skill_set
            gaps = market_skill_set - my_set
            extras = my_set - market_skill_set  # will typically be empty since checkboxes come from market list

            st.divider()
            colA, colB = st.columns(2)

            with colA:
                st.markdown("### ✅ Matched Skills")
                if matched:
                    matched_df = pd.DataFrame(
                        [(s, demand_lookup.get(s, 0)) for s in matched],
                        columns=["Skill", "Demand (postings)"]
                    ).sort_values("Demand (postings)", ascending=False)
                    st.dataframe(matched_df, use_container_width=True, hide_index=True)
                else:
                    st.write("No skills selected yet.")

            with colB:
                st.markdown("### ⚠️ Priority Gaps")
                if gaps:
                    gaps_df = pd.DataFrame(
                        [(s, demand_lookup.get(s, 0)) for s in gaps],
                        columns=["Skill", "Demand (postings)"]
                    ).sort_values("Demand (postings)", ascending=False)
                    st.dataframe(gaps_df, use_container_width=True, hide_index=True)
                else:
                    st.write("You cover all detected skills for this domain!")

            if market_skill_set:
                readiness = len(matched) / len(market_skill_set) * 100
                st.metric(f"Readiness Score for {eval_domain}", f"{readiness:.0f}%")

# ---- TAB 5: Data notes ----
with tab5:
    st.subheader("Data Collection & Methodology Notes")
    st.write(
        "This dashboard pulls live job postings from the Adzuna Jobs API across 7 domains "
        "and 6 Indian cities, refreshed automatically once per day via GitHub Actions."
    )
    for _, row in notes.iterrows():
        with st.expander(row["note_key"].replace("_", " ").title()):
            st.write(row["note_text"])

    st.markdown("**Known limitation:** 'Remote' as a city filter consistently returns 0 results — "
                "Adzuna does not treat 'Remote' as a matchable location for India.")

    if len(notes) == 0:
        st.info("No additional data-quality notes recorded.")

st.divider()
st.caption("Built by [Hansini Bhavsar] · Data source: Adzuna Jobs API · Auto-updated daily via GitHub Actions · Not affiliated with Adzuna")
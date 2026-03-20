import streamlit as st
import plotly.express as px
from analytics import (
    load_data, cost_by_practice, daily_cost_trend,
    peak_usage_heatmap, tool_usage_stats, cost_by_level,
    terminal_distribution, event_type_distribution
)

st.set_page_config(page_title="Claude Code Analytics", layout="wide")
st.title("Claude Code Usage Analytics")
st.caption("Telemetry insights across developer sessions — 60-day window")


@st.cache_data
def get_data():
    return load_data()


df = get_data()

# ── Sidebar filters ───────────────────────────────────────────
st.sidebar.header("Filters")
practices = st.sidebar.multiselect(
    "Practice", df["practice"].dropna().unique(),
    default=list(df["practice"].dropna().unique()))
levels = st.sidebar.multiselect(
    "Level", sorted(df["level"].dropna().unique()),
    default=list(df["level"].dropna().unique()))
df = df[df["practice"].isin(practices) & df["level"].isin(levels)]

api = df[df["body"] == "claude_code.api_request"]

# ── KPI row ───────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total API calls",    f"{len(api):,}")
k2.metric("Unique users",       api["user_email"].nunique())
k3.metric("Total cost",         f"${api['cost_usd'].sum():.2f}")
k4.metric("Total output tokens", f"{api['output_tokens'].sum():,.0f}")
k5.metric("Unique sessions",    api["session_id"].nunique())

st.divider()

# ── Row 1 ─────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.subheader("Cost by engineering practice")
    fig = px.bar(cost_by_practice(df), x="practice", y="total_cost",
                 color="practice", labels={"total_cost": "USD"})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Event type distribution")
    evt_df = event_type_distribution(df)
    fig = px.pie(evt_df, names="body", values="count", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# ── Row 2 ─────────────────────────────────────────────────────
st.subheader("Daily cost trend")
fig = px.area(daily_cost_trend(df), x="date", y="total_cost",
              labels={"total_cost": "Cost (USD)"})
st.plotly_chart(fig, use_container_width=True)

# ── Row 3 ─────────────────────────────────────────────────────
col3, col4 = st.columns(2)
with col3:
    st.subheader("Peak usage — hour × day")
    heat = peak_usage_heatmap(df)
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    fig = px.density_heatmap(heat, x="hour", y="day", z="count",
                             category_orders={"day": day_order},
                             color_continuous_scale="Blues")
    st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("Tool usage & success rate")
    t = tool_usage_stats(df).head(10)
    fig = px.bar(t, x="tool_name", y="uses", color="success_rate",
                 color_continuous_scale="RdYlGn",
                 labels={"uses": "times used", "success_rate": "success rate"})
    st.plotly_chart(fig, use_container_width=True)

# ── Row 4 ─────────────────────────────────────────────────────
col5, col6 = st.columns(2)
with col5:
    st.subheader("Cost by seniority level")
    fig = px.bar(cost_by_level(df).sort_values("level"),
                 x="level", y="total_cost", color="level",
                 labels={"total_cost": "USD"})
    st.plotly_chart(fig, use_container_width=True)

with col6:
    st.subheader("Terminal type distribution")
    fig = px.pie(terminal_distribution(df), names="terminal_type",
                 values="count", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

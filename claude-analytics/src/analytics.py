import pandas as pd
try:
    from src.database import ENGINE
except ModuleNotFoundError:
    from database import ENGINE


def load_data():
    events = pd.read_sql(
        "SELECT * FROM events", ENGINE,
        parse_dates=["timestamp"])
    employees = pd.read_sql("SELECT * FROM employees", ENGINE)
    # Join on email so we get practice, level, location on every event
    df = events.merge(
        employees, left_on="user_email",
        right_on="email", how="left")
    return df

# ── API request events only ───────────────────────────────────


def api_df(df):
    return df[df["body"] == "claude_code.api_request"].copy()


def tool_df(df):
    return df[df["body"] == "claude_code.tool_result"].copy()


def cost_by_practice(df):
    """Which engineering practice spends the most?"""
    return (api_df(df).groupby("practice")["cost_usd"]
            .agg(total_cost="sum", avg_cost="mean", num_requests="count")
            .reset_index().sort_values("total_cost", ascending=False))


def token_by_model(df):
    """Token consumption breakdown by model."""
    return (api_df(df).groupby("model")
            .agg(input=("input_tokens", "sum"),
            output=("output_tokens", "sum"),
            cache_read=("cache_read_tokens", "sum"),
            requests=("cost_usd", "count"))
            .reset_index())


def daily_cost_trend(df):
    d = api_df(df).copy()
    d["date"] = d["timestamp"].dt.date
    return d.groupby("date")["cost_usd"].sum().reset_index(name="total_cost")


def peak_usage_heatmap(df):
    d = api_df(df).copy()
    d["hour"] = d["timestamp"].dt.hour
    d["day"] = d["timestamp"].dt.day_name()
    return d.groupby(["day", "hour"]).size().reset_index(name="count")


def tool_usage_stats(df):
    """Most used tools and their success rates."""
    t = tool_df(df)
    t = t.copy()
    t["success_bool"] = t["success"] == "true"
    return (t.groupby("tool_name")
            .agg(uses=("tool_name", "count"),
                 success_rate=("success_bool", "mean"),
                 avg_duration=("duration_ms", "mean"))
            .reset_index().sort_values("uses", ascending=False))


def cost_by_level(df):
    """Do senior engineers (L7+) use Claude differently than juniors?"""
    return (api_df(df).groupby("level")
            .agg(total_cost=("cost_usd", "sum"), avg_cost=("cost_usd", "mean"),
                 requests=("cost_usd", "count"))
            .reset_index())


def terminal_distribution(df):
    result = df[
        df[
            "body"
            ] == "claude_code.api_request"
            ]["terminal_type"].value_counts().reset_index()
    result.columns = ["terminal_type", "count"]
    return result


def event_type_distribution(df):
    result = df["body"].value_counts().reset_index()
    result.columns = ["body", "count"]
    return result


def error_rate_by_model(df):
    errors = df[df["body"] == "claude_code.api_error"].groupby("model").size()
    total = api_df(df).groupby("model").size()
    rate = (errors / total * 100).fillna(0).reset_index()
    rate.columns = ["model", "error_rate_pct"]
    return rate

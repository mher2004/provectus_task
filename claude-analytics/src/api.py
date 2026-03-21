from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
try:
    from src.analytics import (
        load_data, cost_by_practice,
        daily_cost_trend, tool_usage_stats,
    )
    from src.ml import forecast_cost, detect_anomalies
except ModuleNotFoundError:
    from analytics import (
        load_data, cost_by_practice,
        daily_cost_trend, tool_usage_stats,
    )
    from ml import forecast_cost, detect_anomalies


app = FastAPI(
    title="Claude Code Analytics API",
    description="Programmatic access to Claude Code telemetry insights",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_df():
    return load_data()

# ── Endpoints ──────────────────────────────────────────────────


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}


@app.get("/summary")
def summary():
    """High-level KPIs across all data."""
    df = get_df()
    api = df[df["body"] == "claude_code.api_request"]
    return {
        "total_api_calls":    int(len(api)),
        "unique_users":       int(api["user_email"].nunique()),
        "unique_sessions":    int(api["session_id"].nunique()),
        "total_cost_usd":     round(float(api["cost_usd"].sum()), 4),
        "total_output_tokens": int(api["output_tokens"].sum()),
        "total_input_tokens": int(api["input_tokens"].sum()),
    }


@app.get("/cost-by-practice")
def cost_by_practice_endpoint():
    """Total and average cost broken down by engineering practice."""
    df = get_df()
    result = cost_by_practice(df)
    return result.to_dict(orient="records")


@app.get("/tool-stats")
def tool_stats_endpoint(limit: int = Query(default=10, ge=1, le=50)):
    """Tool usage counts and success rates, sorted by usage."""
    df = get_df()
    result = tool_usage_stats(df).head(limit)
    result["avg_duration"] = result["avg_duration"].round(1)
    result["success_rate"] = result["success_rate"].round(3)
    return result.to_dict(orient="records")


@app.get("/daily-trend")
def daily_trend_endpoint():
    """Daily cost totals over the full date range."""
    df = get_df()
    result = daily_cost_trend(df)
    result["date"] = result["date"].astype(str)
    result["total_cost"] = result["total_cost"].round(4)
    return result.to_dict(orient="records")


@app.get("/forecast")
def forecast_endpoint(days: int = Query(default=7, ge=1, le=30)):
    """Linear regression cost forecast for the next N days."""
    df = get_df()
    result = forecast_cost(df, forecast_days=days)
    result["date"] = result["date"].astype(str)
    result["cost_usd"] = result["cost_usd"].round(4)
    result["lower"] = result["lower"].round(4)
    result["upper"] = result["upper"].round(4)
    return result.to_dict(orient="records")


@app.get("/anomalies")
def anomalies_endpoint():
    """Users flagged as anomalous by IsolationForest."""
    df = get_df()
    result = detect_anomalies(df)
    anomalous = result[result["anomaly"] == True][[
        "user_email", "full_name", "practice", "level",
        "total_cost", "request_count", "avg_duration", "anomaly_score"
    ]]
    anomalous = anomalous.round(4)
    return anomalous.to_dict(orient="records")

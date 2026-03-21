import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest
try:
    from src.database import ENGINE
except ModuleNotFoundError:
    from database import ENGINE


def get_api_events(df=None):
    if df is None:
        df = pd.read_sql(
            "SELECT * FROM events", ENGINE, parse_dates=["timestamp"]
            )
        emp = pd.read_sql("SELECT * FROM employees", ENGINE)
        df = df.merge(emp, left_on="user_email", right_on="email", how="left")
    return df[df["body"] == "claude_code.api_request"].copy()

# ── 1. 7-day cost forecast ─────────────────────────────────────


def daily_cost_series(df):
    api = get_api_events(df)
    api["date"] = api["timestamp"].dt.date
    daily = api.groupby("date")["cost_usd"].sum().reset_index()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    return daily


def forecast_cost(df, forecast_days=7):
    """
    Fit a linear regression on daily cost, forecast next N days.
    Returns a dataframe with historical + forecasted rows,
    and a 'is_forecast' boolean column.
    """
    daily = daily_cost_series(df)

    # Encode date as integer ordinal for regression
    daily["day_ord"] = (daily["date"] - daily["date"].min()).dt.days
    X = daily[["day_ord"]].values
    y = daily["cost_usd"].values

    model = LinearRegression()
    model.fit(X, y)

    # Generate future dates
    last_ord = daily["day_ord"].max()
    last_date = daily["date"].max()
    future_ords = np.arange(last_ord + 1, last_ord + forecast_days + 1)
    future_dates = [
        last_date + pd.Timedelta(days=i) for i in range(1, forecast_days + 1)
        ]
    future_costs = model.predict(future_ords.reshape(-1, 1))
    future_costs = np.clip(future_costs, 0, None)  # no negative costs

    historical = daily[["date", "cost_usd"]].copy()
    historical["is_forecast"] = False
    historical["lower"] = np.nan
    historical["upper"] = np.nan

    # Simple confidence band: ±1 std of residuals, growing with horizon
    residuals = y - model.predict(X)
    base_std = residuals.std()
    horizons = np.arange(1, forecast_days + 1)
    stds = base_std * np.sqrt(horizons)

    forecast_df = pd.DataFrame({
        "date": future_dates,
        "cost_usd": future_costs,
        "is_forecast": True,
        "lower": np.clip(future_costs - 1.96 * stds, 0, None),
        "upper": future_costs + 1.96 * stds,
    })

    return pd.concat([historical, forecast_df], ignore_index=True)

# ── 2. Anomaly detection ───────────────────────────────────────


def detect_anomalies(df):
    """
    Use IsolationForest to flag users whose usage patterns are anomalous.
    Features: total cost, total tokens, avg duration, request count.
    Returns a dataframe with one row per user, with an 'anomaly' boolean.
    """
    api = get_api_events(df)

    user_stats = api.groupby("user_email").agg(
        total_cost=("cost_usd", "sum"),
        total_input=("input_tokens", "sum"),
        total_output=("output_tokens", "sum"),
        avg_duration=("duration_ms", "mean"),
        request_count=("cost_usd", "count"),
    ).reset_index()

    # Need at least 10 users to make anomaly detection meaningful
    if len(user_stats) < 10:
        user_stats["anomaly"] = False
        user_stats["anomaly_score"] = 0.0
        return user_stats

    features = ["total_cost", "total_input", "total_output",
                "avg_duration", "request_count"]
    X = user_stats[features].fillna(0).values

    clf = IsolationForest(contamination=0.08, random_state=42)
    preds = clf.fit_predict(X)           # -1 = anomaly, 1 = normal
    scores = clf.decision_function(X)    # lower = more anomalous

    user_stats["anomaly"] = preds == -1
    user_stats["anomaly_score"] = -scores  # flip so higher = more anomalous

    # Normalize to non-negative values for visualization (marker size cannot be < 0)
    min_score = user_stats["anomaly_score"].min()
    if min_score < 0:
        user_stats["anomaly_score"] = user_stats["anomaly_score"] - min_score + 0.01

    # Merge back employee info
    emp = pd.read_sql("SELECT email, full_name, practice,\
 level FROM employees", ENGINE)
    user_stats = user_stats.merge(
        emp, left_on="user_email",
        right_on="email", how="left")

    return user_stats.sort_values("anomaly_score", ascending=False)

import json
import pandas as pd
from database import ENGINE, init_db


def parse_jsonl(path="data/raw/telemetry_logs.jsonl"):
    """Unwrap CloudWatch log batches → flat list of event dicts."""
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                batch = json.loads(line)
                for log_event in batch.get("logEvents", []):
                    msg = json.loads(log_event["message"])
                    event = {
                        "body": msg["body"],
                        **msg["attributes"],
                        "host_arch":     msg["resource"].get("host.arch"),
                        "os_type":       msg["resource"].get("os.type"),
                        "os_version":    msg["resource"].get("os.version"),
                        "user_practice": msg["resource"].get("user.practice"),
                        "scope_version": msg["scope"].get("version"),
                        # NOTE: do NOT re-add terminal_type or user.email here
                        #       they already come in via **msg["attributes"]
                    }
                    events.append(event)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Skipping malformed record: {e}")
    return events


def load_events():
    records = parse_jsonl()
    df = pd.DataFrame(records)

    # Rename dotted column names → snake_case
    df = df.rename(columns={
        "event.timestamp":  "timestamp",
        "event.name":       "event_name",
        "session.id":       "session_id",
        "user.id":          "user_id",
        "user.email":       "user_email",
        "organization.id":  "org_id",
        "terminal.type":    "terminal_type",
    })

    # Drop any fully duplicate columns that snuck in
    df = df.loc[:, ~df.columns.duplicated()]

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    for col in ["input_tokens", "output_tokens", "cache_read_tokens",
                "cache_creation_tokens", "duration_ms", "prompt_length"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["cost_usd"] = pd.to_numeric(df.get("cost_usd"), errors="coerce")

    df.to_sql("events", ENGINE, if_exists="replace", index=False)
    print(f"Loaded {len(df)} events ({df['body'].value_counts().to_dict()})")
    return df


def load_employees():
    df = pd.read_csv("data/raw/employees.csv")
    df.to_sql("employees", ENGINE, if_exists="replace", index=False)
    print(f"Loaded {len(df)} employees.")
    return df


def run_ingestion():
    init_db()
    employees = load_employees()
    events = load_events()
    return employees, events


if __name__ == "__main__":
    run_ingestion()

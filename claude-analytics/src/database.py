from sqlalchemy import create_engine, text

ENGINE = create_engine("sqlite:///data/analytics.db", echo=False)

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    email       TEXT PRIMARY KEY,
    full_name   TEXT,
    practice    TEXT,
    level       TEXT,
    location    TEXT
);

CREATE TABLE IF NOT EXISTS events (
    body            TEXT,
    timestamp       TEXT,
    event_name      TEXT,
    session_id      TEXT,
    user_id         TEXT,
    user_email      TEXT,
    org_id          TEXT,
    model           TEXT,
    input_tokens    REAL,
    output_tokens   REAL,
    cache_read_tokens    REAL,
    cache_creation_tokens REAL,
    cost_usd        REAL,
    duration_ms     REAL,
    tool_name       TEXT,
    decision        TEXT,
    success         TEXT,
    prompt_length   REAL,
    os_type         TEXT,
    terminal_type   TEXT,
    scope_version   TEXT,
    user_practice   TEXT
);
"""


def init_db():
    with ENGINE.connect() as conn:
        for stmt in SCHEMA.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        conn.commit()

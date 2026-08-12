from __future__ import annotations


VERSION = 3
NAME = "auth_abuse_protection"


SQL = """
CREATE TABLE IF NOT EXISTS auth_rate_limit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_hash TEXT NOT NULL,
    origin_hash TEXT,
    event_type TEXT NOT NULL,
    outcome TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auth_rate_identity_event_time
    ON auth_rate_limit_events (identity_hash, event_type, occurred_at);
CREATE INDEX IF NOT EXISTS idx_auth_rate_origin_event_time
    ON auth_rate_limit_events (origin_hash, event_type, occurred_at);
CREATE INDEX IF NOT EXISTS idx_auth_rate_event_time
    ON auth_rate_limit_events (event_type, occurred_at);
"""

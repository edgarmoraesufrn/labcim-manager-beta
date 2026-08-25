from __future__ import annotations


VERSION = 4
NAME = "supply_lifecycle"


COLUMN_ADDITIONS = (
    ("supplies", "inactive_reason", "TEXT"),
    ("supplies", "inactive_by_id", "INTEGER"),
    ("supplies", "inactive_at", "TEXT"),
)


NORMALIZATION_SQL = "UPDATE supplies SET active = 1 WHERE active IS NULL;"

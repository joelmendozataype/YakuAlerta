"""Utilidades de fecha/hora portátiles entre PostgreSQL y SQLite.

PostgreSQL (TIMESTAMPTZ) devuelve datetimes con zona horaria; SQLite los
devuelve "naive". Para poder restarlos con ``datetime.now(timezone.utc)`` los
normalizamos a UTC-aware.
"""
from datetime import datetime, timezone


def aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

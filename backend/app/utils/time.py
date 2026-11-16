from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC timestamp, matching how SQLite returns stored datetimes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

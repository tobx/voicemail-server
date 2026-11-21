from datetime import datetime, timezone


def utc(time: datetime | None = None) -> datetime:
    if time is None:
        time = datetime.now(timezone.utc)
    if time.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return time.astimezone(timezone.utc)

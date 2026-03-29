"""ID generators, timestamp helpers, weighted random utilities."""

import random
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NZ_TZ = ZoneInfo("Pacific/Auckland")
UTC = timezone.utc


def generate_user_pseudo_id() -> str:
    """GA4 client ID format: {10-digit}.{10-digit}"""
    part1 = random.randint(1_000_000_000, 9_999_999_999)
    part2 = random.randint(1_000_000_000, 9_999_999_999)
    return f"{part1}.{part2}"


def generate_ga_session_id() -> int:
    """Random large integer for ga_session_id."""
    return random.randint(1_000_000_000, 2_147_483_647)


def generate_transaction_id() -> str:
    """UUID-based transaction ID."""
    return str(uuid.uuid4()).replace("-", "")[:20].upper()


def generate_user_id() -> str:
    """Simulated logged-in user ID."""
    return f"U{random.randint(100000, 999999)}"


def nz_datetime_to_event_timestamp(dt: datetime) -> int:
    """Convert NZ-aware datetime to GA4 event_timestamp (microseconds UTC)."""
    utc_dt = dt.astimezone(UTC)
    return int(utc_dt.timestamp() * 1_000_000)


def event_date_from_nz(dt: datetime) -> str:
    """YYYYMMDD string from NZ-local datetime."""
    nz_dt = dt.astimezone(NZ_TZ)
    return nz_dt.strftime("%Y%m%d")


def random_time_of_day() -> timedelta:
    """Weighted random time-of-day with realistic EC patterns.

    Peaks at lunch (12-13h) and evening (20-22h).
    Low traffic 0-6am, moderate morning, dip in afternoon.
    """
    hour_weights = [
        1,   # 0
        1,   # 1
        0.5, # 2
        0.3, # 3
        0.2, # 4
        0.3, # 5
        1,   # 6
        3,   # 7
        6,   # 8
        8,   # 9
        9,   # 10
        9,   # 11
        12,  # 12 - lunch peak
        11,  # 13
        7,   # 14
        7,   # 15
        7,   # 16
        8,   # 17
        9,   # 18
        10,  # 19
        12,  # 20 - evening peak
        13,  # 21 - evening peak
        8,   # 22
        4,   # 23
    ]
    hour = random.choices(range(24), weights=hour_weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    micro = random.randint(0, 999_999)
    return timedelta(hours=hour, minutes=minute, seconds=second, microseconds=micro)


def weighted_choice(options: list, weights: list):
    """Weighted random selection."""
    return random.choices(options, weights=weights, k=1)[0]


def is_campaign_active(date_obj, campaigns: list[dict]) -> list[dict]:
    """Return list of active campaigns for a given date."""
    active = []
    if hasattr(date_obj, 'date') and callable(date_obj.date):
        d = date_obj.date()
    else:
        d = date_obj
    for c in campaigns:
        start = datetime.strptime(c["start"], "%Y-%m-%d").date() if isinstance(c["start"], str) else c["start"]
        end = datetime.strptime(c["end"], "%Y-%m-%d").date() if isinstance(c["end"], str) else c["end"]
        if start <= d <= end:
            active.append(c)
    return active

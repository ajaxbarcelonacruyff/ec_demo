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
    """Weighted random time-of-day (business hours peak in NZ)."""
    # Weight toward 8am-10pm NZ time
    hour_weights = (
        [1] * 6    # 0-5: low
        + [3] * 2  # 6-7: rising
        + [8] * 4  # 8-11: morning peak
        + [10] * 2 # 12-13: lunch peak
        + [7] * 4  # 14-17: afternoon
        + [9] * 3  # 18-20: evening peak
        + [5] * 2  # 21-22: winding down
        + [2] * 1  # 23: late
    )
    hour = random.choices(range(24), weights=hour_weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    micro = random.randint(0, 999_999)
    return timedelta(hours=hour, minutes=minute, seconds=second, microseconds=micro)


def weighted_choice(options: list, weights: list):
    """Weighted random selection."""
    return random.choices(options, weights=weights, k=1)[0]

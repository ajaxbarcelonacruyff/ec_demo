"""Traffic source generation for GA4 demo data."""

import random
from utils import weighted_choice

SOURCES = [
    {"source": "google", "medium": "organic", "campaign": "(organic)", "weight": 35},
    {"source": "(direct)", "medium": "(none)", "campaign": "(direct)", "weight": 25},
    {"source": "google", "medium": "cpc", "campaign": "spring_sale_2025", "weight": 8},
    {"source": "google", "medium": "cpc", "campaign": "brand_awareness", "weight": 7},
    {"source": "yahoo", "medium": "organic", "campaign": "(organic)", "weight": 5},
    {"source": "facebook", "medium": "referral", "campaign": "(referral)", "weight": 5},
    {"source": "instagram", "medium": "social", "campaign": "ig_promo", "weight": 3},
    {"source": "twitter", "medium": "social", "campaign": "(social)", "weight": 2},
    {"source": "newsletter", "medium": "email", "campaign": "weekly_digest", "weight": 5},
    {"source": "newsletter", "medium": "email", "campaign": "new_arrival", "weight": 3},
    {"source": "line", "medium": "social", "campaign": "line_message", "weight": 2},
]


def pick_traffic_source() -> dict:
    """Pick a traffic source for a session."""
    weights = [s["weight"] for s in SOURCES]
    src = weighted_choice(SOURCES, weights)
    result = {
        "source": src["source"],
        "medium": src["medium"],
        "campaign": src["campaign"],
    }
    # Add gclid for Google CPC
    if src["medium"] == "cpc" and src["source"] == "google":
        result["gclid"] = f"Cj0KCQj{random.randint(100000, 999999)}"
    return result


def build_traffic_source_record(src: dict) -> dict:
    """Build GA4 traffic_source (user-level first-touch) record."""
    return {
        "source": src["source"],
        "medium": src["medium"],
        "name": src["campaign"],
    }


def build_collected_traffic_source(src: dict) -> dict:
    """Build GA4 collected_traffic_source (event-level) record."""
    record = {
        "manual_source": src["source"],
        "manual_medium": src["medium"],
        "manual_campaign_name": src["campaign"],
    }
    if "gclid" in src:
        record["gclid"] = src["gclid"]
    return record

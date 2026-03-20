"""Traffic source generation for GA4 demo data."""

import random
from utils import weighted_choice

SOURCES = [
    {"source": "google", "medium": "organic", "campaign": "(organic)", "content": None, "weight": 35},
    {"source": "(direct)", "medium": "(none)", "campaign": "(direct)", "content": None, "weight": 25},
    {"source": "google", "medium": "cpc", "campaign": "spring_sale_2025", "content": "banner_top", "weight": 4},
    {"source": "google", "medium": "cpc", "campaign": "spring_sale_2025", "content": "sidebar_rect", "weight": 4},
    {"source": "google", "medium": "cpc", "campaign": "brand_awareness", "content": "text_ad_v1", "weight": 4},
    {"source": "google", "medium": "cpc", "campaign": "brand_awareness", "content": "text_ad_v2", "weight": 3},
    {"source": "yahoo", "medium": "organic", "campaign": "(organic)", "content": None, "weight": 5},
    {"source": "facebook", "medium": "referral", "campaign": "(referral)", "content": None, "weight": 3},
    {"source": "facebook", "medium": "social", "campaign": "fb_winter_sale", "content": "carousel_products", "weight": 2},
    {"source": "instagram", "medium": "social", "campaign": "ig_promo", "content": "story_ad", "weight": 2},
    {"source": "instagram", "medium": "social", "campaign": "ig_promo", "content": "feed_post", "weight": 1},
    {"source": "twitter", "medium": "social", "campaign": "(social)", "content": None, "weight": 2},
    {"source": "newsletter", "medium": "email", "campaign": "weekly_digest", "content": "header_cta", "weight": 3},
    {"source": "newsletter", "medium": "email", "campaign": "weekly_digest", "content": "product_grid", "weight": 2},
    {"source": "newsletter", "medium": "email", "campaign": "new_arrival", "content": "hero_banner", "weight": 3},
    {"source": "line", "medium": "social", "campaign": "line_message", "content": "rich_menu", "weight": 2},
]


def pick_traffic_source() -> dict:
    """Pick a traffic source for a session."""
    weights = [s["weight"] for s in SOURCES]
    src = weighted_choice(SOURCES, weights)
    result = {
        "source": src["source"],
        "medium": src["medium"],
        "campaign": src["campaign"],
        "content": src.get("content"),
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
    if src.get("content"):
        record["manual_content"] = src["content"]
    if "gclid" in src:
        record["gclid"] = src["gclid"]
    return record


def build_session_traffic_source_last_click(src: dict) -> dict:
    """Build GA4 session_traffic_source_last_click record.

    This reflects the last non-direct click source for the session,
    matching the GA4 BigQuery Export schema.
    """
    manual = {
        "source": src["source"],
        "medium": src["medium"],
        "campaign_name": src["campaign"],
    }
    if src.get("content"):
        manual["content"] = src["content"]
    record = {"manual_campaign": manual}
    if src.get("gclid"):
        record["google_ads_campaign"] = {
            "customer_id": "123-456-7890",
            "account_name": "Example EC Ads",
            "campaign_id": str(random.randint(10000000000, 99999999999)),
            "campaign_name": src["campaign"],
            "ad_group_id": str(random.randint(100000000000, 999999999999)),
            "ad_group_name": f"{src['campaign']}_adgroup",
        }
    return record

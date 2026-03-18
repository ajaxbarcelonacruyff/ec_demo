"""Device, browser, and geo data generation for GA4 demo data."""

import random
from utils import weighted_choice

DEVICE_PROFILES = [
    {
        "category": "mobile", "os": "Android", "os_version": "14",
        "brand": "Samsung", "model": "SM-S926B", "marketing_name": "Galaxy S24+",
        "browser": "Chrome", "browser_version": "122.0.6261.119",
        "weight": 15,
    },
    {
        "category": "mobile", "os": "Android", "os_version": "13",
        "brand": "Samsung", "model": "SM-A546B", "marketing_name": "Galaxy A54",
        "browser": "Chrome", "browser_version": "121.0.6167.178",
        "weight": 10,
    },
    {
        "category": "mobile", "os": "iOS", "os_version": "17.3",
        "brand": "Apple", "model": "iPhone15,3", "marketing_name": "iPhone 15 Pro Max",
        "browser": "Safari", "browser_version": "17.3",
        "weight": 15,
    },
    {
        "category": "mobile", "os": "iOS", "os_version": "17.2",
        "brand": "Apple", "model": "iPhone14,5", "marketing_name": "iPhone 13",
        "browser": "Safari", "browser_version": "17.2",
        "weight": 10,
    },
    {
        "category": "desktop", "os": "Windows", "os_version": "10",
        "brand": "", "model": "", "marketing_name": "",
        "browser": "Chrome", "browser_version": "122.0.6261.112",
        "weight": 15,
    },
    {
        "category": "desktop", "os": "Windows", "os_version": "11",
        "brand": "", "model": "", "marketing_name": "",
        "browser": "Edge", "browser_version": "122.0.2365.80",
        "weight": 8,
    },
    {
        "category": "desktop", "os": "Macintosh", "os_version": "14.3",
        "brand": "Apple", "model": "", "marketing_name": "",
        "browser": "Safari", "browser_version": "17.3",
        "weight": 10,
    },
    {
        "category": "desktop", "os": "Macintosh", "os_version": "14.3",
        "brand": "Apple", "model": "", "marketing_name": "",
        "browser": "Chrome", "browser_version": "122.0.6261.112",
        "weight": 7,
    },
    {
        "category": "tablet", "os": "iOS", "os_version": "17.3",
        "brand": "Apple", "model": "iPad14,1", "marketing_name": "iPad mini (6th gen)",
        "browser": "Safari", "browser_version": "17.3",
        "weight": 5,
    },
    {
        "category": "tablet", "os": "Android", "os_version": "14",
        "brand": "Samsung", "model": "SM-X810", "marketing_name": "Galaxy Tab S9+",
        "browser": "Chrome", "browser_version": "122.0.6261.119",
        "weight": 5,
    },
]

GEO_PROFILES = [
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Tokyo", "city": "Tokyo", "weight": 30},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Osaka", "city": "Osaka", "weight": 15},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Kanagawa", "city": "Yokohama", "weight": 8},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Aichi", "city": "Nagoya", "weight": 7},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Fukuoka", "city": "Fukuoka", "weight": 5},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Hokkaido", "city": "Sapporo", "weight": 5},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Hyogo", "city": "Kobe", "weight": 4},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Kyoto", "city": "Kyoto", "weight": 4},
    {"continent": "Americas", "sub_continent": "Northern America", "country": "United States", "region": "California", "city": "Los Angeles", "weight": 3},
    {"continent": "Asia", "sub_continent": "Eastern Asia", "country": "Japan", "region": "Miyagi", "city": "Sendai", "weight": 3},
]

LANGUAGES = ["ja", "ja-jp", "en-us", "en"]
LANGUAGE_WEIGHTS = [50, 30, 10, 10]


def pick_device() -> dict:
    """Pick a random device profile."""
    weights = [d["weight"] for d in DEVICE_PROFILES]
    return weighted_choice(DEVICE_PROFILES, weights)


def pick_geo() -> dict:
    """Pick a random geo profile."""
    weights = [g["weight"] for g in GEO_PROFILES]
    return weighted_choice(GEO_PROFILES, weights)


def build_device_record(profile: dict) -> dict:
    """Build GA4 device record from a device profile."""
    record = {
        "category": profile["category"],
        "operating_system": profile["os"],
        "operating_system_version": profile["os_version"],
        "language": weighted_choice(LANGUAGES, LANGUAGE_WEIGHTS),
        "web_info": {
            "browser": profile["browser"],
            "browser_version": profile["browser_version"],
            "hostname": "www.example-ec.jp",
        },
    }
    if profile["brand"]:
        record["mobile_brand_name"] = profile["brand"]
    if profile["model"]:
        record["mobile_model_name"] = profile["model"]
    if profile["marketing_name"]:
        record["mobile_marketing_name"] = profile["marketing_name"]
    if profile["category"] == "mobile":
        record["is_limited_ad_tracking"] = random.choice(["Yes", "No"])
    return record


def build_geo_record(profile: dict) -> dict:
    """Build GA4 geo record."""
    return {
        "continent": profile["continent"],
        "sub_continent": profile["sub_continent"],
        "country": profile["country"],
        "region": profile["region"],
        "city": profile["city"],
    }

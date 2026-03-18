"""User journey and session simulation for GA4 ecommerce demo data."""

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from utils import (
    generate_user_pseudo_id, generate_ga_session_id, generate_transaction_id,
    generate_user_id, nz_datetime_to_event_timestamp, event_date_from_nz,
    random_time_of_day, NZ_TZ,
)
from product_catalog import pick_products, pick_promotion
from traffic_sources import (
    pick_traffic_source, build_traffic_source_record,
    build_collected_traffic_source,
)
from device_geo import pick_device, pick_geo, build_device_record, build_geo_record
from ga4_schema import ep, up, build_event


SITE_PAGES = [
    {"path": "/", "title": "ホーム | Example EC"},
    {"path": "/category/electronics", "title": "家電・電子機器 | Example EC"},
    {"path": "/category/audio", "title": "オーディオ | Example EC"},
    {"path": "/category/accessories", "title": "アクセサリー | Example EC"},
    {"path": "/category/office", "title": "オフィス用品 | Example EC"},
    {"path": "/search", "title": "検索結果 | Example EC"},
    {"path": "/sale", "title": "セール | Example EC"},
    {"path": "/about", "title": "会社概要 | Example EC"},
    {"path": "/help", "title": "ヘルプ | Example EC"},
]

HOSTNAME = "www.example-ec.jp"


def create_user_pool(total_users: int, logged_in_ratio: float) -> list[dict]:
    """Create a pool of simulated users."""
    users = []
    for _ in range(total_users):
        device_profile = pick_device()
        geo_profile = pick_geo()
        first_touch_src = pick_traffic_source()
        user = {
            "user_pseudo_id": generate_user_pseudo_id(),
            "user_id": generate_user_id() if random.random() < logged_in_ratio else None,
            "device_profile": device_profile,
            "geo_profile": geo_profile,
            "first_touch_source": first_touch_src,
            "session_count": 0,
            "purchase_propensity": random.betavariate(2, 5),  # skewed toward lower
        }
        users.append(user)
    return users


def _page_url(path: str, query: str = None) -> str:
    url = f"https://{HOSTNAME}{path}"
    if query:
        url += f"?{query}"
    return url


def generate_session_events(
    user: dict,
    session_date: datetime,
    config: dict,
) -> list[dict]:
    """Generate all events for a single session."""
    user["session_count"] += 1
    session_id = generate_ga_session_id()
    session_number = user["session_count"]
    session_src = pick_traffic_source()

    device_record = build_device_record(user["device_profile"])
    geo_record = build_geo_record(user["geo_profile"])
    traffic_source_record = build_traffic_source_record(user["first_touch_source"])
    collected_ts = build_collected_traffic_source(session_src)

    first_touch_ts = nz_datetime_to_event_timestamp(
        session_date - timedelta(days=random.randint(0, 90))
    )

    stream_id = config.get("stream_id", "1234567890")
    currency = config.get("currency", "JPY")
    funnel = config.get("funnel", {})

    # Session start time
    current_time = session_date + random_time_of_day()
    events = []

    def _ts():
        return nz_datetime_to_event_timestamp(current_time)

    def _date():
        return event_date_from_nz(current_time)

    def _base_params():
        return [
            ep("ga_session_id", int_value=session_id),
            ep("ga_session_number", int_value=session_number),
            ep("session_engaged", int_value=1),
        ]

    def _user_props():
        props = []
        if user["user_id"]:
            props.append(up("user_id", string_value=user["user_id"]))
        return props

    def _make_event(name, extra_params=None, items=None, ecommerce=None):
        params = _base_params() + (extra_params or [])
        return build_event(
            event_name=name,
            event_timestamp=_ts(),
            event_date=_date(),
            user_pseudo_id=user["user_pseudo_id"],
            event_params=params,
            user_properties=_user_props(),
            device=device_record,
            geo=geo_record,
            traffic_source=traffic_source_record,
            collected_traffic_source=collected_ts,
            stream_id=stream_id,
            user_id=user["user_id"],
            user_first_touch_timestamp=first_touch_ts,
            items=items,
            ecommerce=ecommerce,
        )

    def _advance_time():
        nonlocal current_time
        current_time += timedelta(seconds=random.randint(2, 30))

    # 1. session_start
    events.append(_make_event("session_start", [ep("entrances", int_value=1)]))
    _advance_time()

    # 2. Landing page_view
    landing = random.choice(SITE_PAGES)
    landing_url = _page_url(landing["path"])
    events.append(_make_event("page_view", [
        ep("page_location", string_value=landing_url),
        ep("page_title", string_value=landing["title"]),
        ep("entrances", int_value=1),
    ]))
    _advance_time()

    # 3. Browse: 1-5 additional page_views
    browse_count = random.randint(1, 5)
    for _ in range(browse_count):
        page = random.choice(SITE_PAGES)
        events.append(_make_event("page_view", [
            ep("page_location", string_value=_page_url(page["path"])),
            ep("page_title", string_value=page["title"]),
            ep("page_referrer", string_value=landing_url),
        ]))
        _advance_time()

    # 4. select_promotion (optional)
    promo = None
    if random.random() < funnel.get("promotion_probability", 0.15):
        promo = pick_promotion()
        promo_items = pick_products(1)
        for item in promo_items:
            item["promotion_id"] = promo["promotion_id"]
            item["promotion_name"] = promo["promotion_name"]
            item["creative_name"] = promo["creative_name"]
            item["creative_slot"] = promo["creative_slot"]
        events.append(_make_event("select_promotion", [
            ep("promotion_id", string_value=promo["promotion_id"]),
            ep("promotion_name", string_value=promo["promotion_name"]),
            ep("creative_name", string_value=promo["creative_name"]),
            ep("creative_slot", string_value=promo["creative_slot"]),
        ], items=promo_items))
        _advance_time()

    # 5. view_item
    if random.random() < funnel.get("browse_to_view_item", 0.70):
        cart_items = pick_products(random.randint(1, 3))
        for item in cart_items:
            events.append(_make_event("view_item", [
                ep("page_location", string_value=_page_url(f"/product/{item['item_id']}")),
                ep("page_title", string_value=f"{item['item_name']} | Example EC"),
                ep("currency", string_value=currency),
                ep("value", float_value=item["price"]),
            ], items=[item]))
            _advance_time()

        # 6. add_to_cart
        if random.random() < funnel.get("view_item_to_add_to_cart", 0.30) + user["purchase_propensity"] * 0.2:
            added_items = cart_items[:random.randint(1, len(cart_items))]
            for item in added_items:
                events.append(_make_event("add_to_cart", [
                    ep("currency", string_value=currency),
                    ep("value", float_value=item["price"] * item["quantity"]),
                ], items=[item]))
                _advance_time()

            # 7. remove_from_cart (optional)
            if len(added_items) > 1 and random.random() < funnel.get("add_to_cart_to_remove", 0.10):
                removed = added_items.pop()
                events.append(_make_event("remove_from_cart", [
                    ep("currency", string_value=currency),
                    ep("value", float_value=removed["price"] * removed["quantity"]),
                ], items=[removed]))
                _advance_time()

            # 8. begin_checkout
            if random.random() < funnel.get("add_to_cart_to_checkout", 0.60):
                total_value = sum(i["price"] * i["quantity"] for i in added_items)
                events.append(_make_event("begin_checkout", [
                    ep("currency", string_value=currency),
                    ep("value", float_value=total_value),
                ], items=added_items))
                _advance_time()

                # 9. purchase
                if random.random() < funnel.get("checkout_to_purchase", 0.75):
                    txn_id = generate_transaction_id()
                    purchase_params = [
                        ep("currency", string_value=currency),
                        ep("value", float_value=total_value),
                        ep("transaction_id", string_value=txn_id),
                    ]
                    if promo:
                        purchase_params.append(ep("promotion_name", string_value=promo["promotion_name"]))

                    ecommerce_record = {
                        "transaction_id": txn_id,
                        "purchase_revenue": total_value,
                        "total_item_quantity": sum(i["quantity"] for i in added_items),
                        "unique_items": len(added_items),
                    }
                    events.append(_make_event(
                        "purchase", purchase_params,
                        items=added_items, ecommerce=ecommerce_record,
                    ))
                    _advance_time()

    # Add engagement_time_msec to all events
    for ev in events:
        ev["event_params"].append(
            ep("engagement_time_msec", int_value=random.randint(500, 30000))
        )

    return events


def generate_day_events(
    users: list[dict],
    target_date: datetime,
    config: dict,
) -> list[dict]:
    """Generate all events for a single day across all users."""
    daily_active_ratio = config.get("daily_active_ratio", 0.15)
    sessions_range = config.get("sessions_per_day_range", [1, 3])

    active_count = max(1, int(len(users) * daily_active_ratio))
    active_users = random.sample(users, active_count)

    all_events = []
    for user in active_users:
        num_sessions = random.randint(*sessions_range)
        for _ in range(num_sessions):
            session_events = generate_session_events(user, target_date, config)
            all_events.extend(session_events)

    # Sort by event_timestamp
    all_events.sort(key=lambda e: e["event_timestamp"])
    return all_events

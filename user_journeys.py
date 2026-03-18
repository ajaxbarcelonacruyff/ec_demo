"""User journey and session simulation for GA4 ecommerce demo data."""

import random
from datetime import datetime, timedelta

from utils import (
    generate_user_pseudo_id, generate_ga_session_id, generate_transaction_id,
    generate_user_id, nz_datetime_to_event_timestamp, event_date_from_nz,
    random_time_of_day, NZ_TZ,
)
from product_catalog import (
    pick_products, pick_product_list, pick_promotion,
    apply_coupon, COUPONS,
)
from traffic_sources import (
    pick_traffic_source, build_traffic_source_record,
    build_collected_traffic_source,
)
from device_geo import pick_device, pick_geo, build_device_record, build_geo_record
from ga4_schema import ep, up, build_event


HOSTNAME = "www.example-ec.jp"

SITE_PAGES = [
    {"path": "/",                       "title": "ホーム | Example EC"},
    {"path": "/category/electronics",   "title": "家電・電子機器 | Example EC",  "list_id": "category_electronics",  "list_name": "家電・電子機器"},
    {"path": "/category/audio",         "title": "オーディオ | Example EC",      "list_id": "category_audio",        "list_name": "オーディオ"},
    {"path": "/category/accessories",   "title": "アクセサリー | Example EC",    "list_id": "category_accessories",  "list_name": "アクセサリー"},
    {"path": "/category/office",        "title": "オフィス用品 | Example EC",    "list_id": "category_office",       "list_name": "オフィス用品"},
    {"path": "/category/smart-home",    "title": "スマートホーム | Example EC",  "list_id": "category_smart_home",   "list_name": "スマートホーム"},
    {"path": "/sale",                   "title": "セール | Example EC",          "list_id": "sale_items",            "list_name": "セール商品"},
    {"path": "/new-arrivals",           "title": "新着商品 | Example EC",        "list_id": "new_arrivals",          "list_name": "新着商品"},
    {"path": "/about",                  "title": "会社概要 | Example EC"},
    {"path": "/help",                   "title": "ヘルプ | Example EC"},
]

CATEGORY_PAGES = [p for p in SITE_PAGES if "list_id" in p]

SEARCH_TERMS = [
    "ワイヤレスヘッドホン", "スマートウォッチ", "キーボード", "マウス", "充電器",
    "モニター", "スピーカー", "イヤホン", "ウェブカメラ", "SSD", "バックパック",
    "LEDライト", "USBハブ", "ゲーミング", "ノイズキャンセリング", "Bluetooth",
    "充電ケーブル", "タブレットスタンド", "マイク", "スマートプラグ", "マウスパッド",
]

SHIPPING_OPTIONS = [
    {"tier": "standard", "fee": 550},
    {"tier": "express",  "fee": 1100},
]
FREE_SHIPPING_THRESHOLD = 5000

PAYMENT_TYPES   = ["credit_card", "debit_card", "convenience_store", "bank_transfer", "pay_later"]
PAYMENT_WEIGHTS = [50, 15, 20, 10, 5]

LOGIN_METHODS   = ["email", "google", "line", "yahoo"]
LOGIN_WEIGHTS   = [50, 30, 15, 5]

TAX_RATE = 0.10

# Referrer URLs by traffic source
_REFERRERS = {
    "google":    "https://www.google.com/",
    "yahoo":     "https://search.yahoo.co.jp/",
    "facebook":  "https://www.facebook.com/",
    "instagram": "https://www.instagram.com/",
    "twitter":   "https://t.co/",
    "line":      "https://line.me/",
    "newsletter":"",
    "(direct)":  "",
}


def _referrer_for_source(src: dict) -> str:
    return _REFERRERS.get(src.get("source", ""), "")


def create_user_pool(total_users: int, logged_in_ratio: float) -> list[dict]:
    """Create a pool of simulated users."""
    users = []
    for _ in range(total_users):
        users.append({
            "user_pseudo_id":       generate_user_pseudo_id(),
            "user_id":              generate_user_id() if random.random() < logged_in_ratio else None,
            "device_profile":       pick_device(),
            "geo_profile":          pick_geo(),
            "first_touch_source":   pick_traffic_source(),
            "session_count":        0,
            "purchase_propensity":  random.betavariate(2, 5),  # skewed low
        })
    return users


def _page_url(path: str, query: str = None) -> str:
    url = f"https://{HOSTNAME}{path}"
    if query:
        url += f"?{query}"
    return url


def _strip_list_fields(items: list[dict]) -> list[dict]:
    """Remove list-level fields from items for cart/checkout/purchase events."""
    remove = {"item_list_id", "item_list_name", "index"}
    return [{k: v for k, v in item.items() if k not in remove} for item in items]


def generate_refund_event(refund_info: dict, refund_date: datetime, stream_id: str) -> dict:
    """Build a refund event from stored purchase info."""
    refund_time = refund_date + random_time_of_day()
    ts    = nz_datetime_to_event_timestamp(refund_time)
    date  = event_date_from_nz(refund_time)

    items = refund_info["items"]
    # Partial refund (30% chance when multi-item order)
    if len(items) > 1 and random.random() < 0.3:
        items = items[:random.randint(1, len(items) - 1)]
    refund_value = sum(i["price"] * i["quantity"] for i in items)

    params = [
        ep("ga_session_id",       int_value=refund_info["session_id"]),
        ep("ga_session_number",   int_value=refund_info["session_number"]),
        ep("currency",            string_value=refund_info["currency"]),
        ep("value",               float_value=refund_value),
        ep("transaction_id",      string_value=refund_info["transaction_id"]),
        ep("engagement_time_msec",int_value=random.randint(500, 5000)),
    ]

    user_props = []
    if refund_info.get("user_id"):
        user_props.append(up("user_id", string_value=refund_info["user_id"]))

    return build_event(
        event_name="refund",
        event_timestamp=ts,
        event_date=date,
        user_pseudo_id=refund_info["user_pseudo_id"],
        event_params=params,
        user_properties=user_props,
        device=refund_info["device"],
        geo=refund_info["geo"],
        traffic_source=refund_info["traffic_source"],
        stream_id=stream_id,
        user_id=refund_info.get("user_id"),
        items=items,
    )


def generate_session_events(
    user: dict,
    session_date: datetime,
    config: dict,
) -> tuple[list[dict], dict | None]:
    """Generate all events for one session.

    Returns:
        (events, purchase_info)
        purchase_info is a dict with data needed to generate a future refund,
        or None if no purchase occurred.
    """
    is_first_session = (user["session_count"] == 0)
    user["session_count"] += 1

    session_id     = generate_ga_session_id()
    session_number = user["session_count"]
    session_src    = pick_traffic_source()

    device_record       = build_device_record(user["device_profile"])
    geo_record          = build_geo_record(user["geo_profile"])
    traffic_src_record  = build_traffic_source_record(user["first_touch_source"])
    collected_ts        = build_collected_traffic_source(session_src)

    first_touch_ts = nz_datetime_to_event_timestamp(
        session_date if is_first_session
        else session_date - timedelta(days=random.randint(1, 90))
    )

    stream_id = config.get("stream_id", "1234567890")
    currency  = config.get("currency", "JPY")
    funnel    = config.get("funnel", {})

    current_time = session_date + random_time_of_day()
    events: list[dict] = []
    purchase_info = None

    # ------------------------------------------------------------------ helpers
    def _ts():   return nz_datetime_to_event_timestamp(current_time)
    def _date(): return event_date_from_nz(current_time)

    def _base():
        return [
            ep("ga_session_id",     int_value=session_id),
            ep("ga_session_number", int_value=session_number),
            ep("session_engaged",   int_value=1),
        ]

    def _user_props():
        return [up("user_id", string_value=user["user_id"])] if user["user_id"] else []

    def _ev(name, extra=None, items=None, ecommerce=None):
        return build_event(
            event_name=name,
            event_timestamp=_ts(),
            event_date=_date(),
            user_pseudo_id=user["user_pseudo_id"],
            event_params=_base() + (extra or []),
            user_properties=_user_props(),
            device=device_record,
            geo=geo_record,
            traffic_source=traffic_src_record,
            collected_traffic_source=collected_ts,
            stream_id=stream_id,
            user_id=user["user_id"],
            user_first_touch_timestamp=first_touch_ts,
            items=items,
            ecommerce=ecommerce,
        )

    def _advance(lo=5, hi=60):
        nonlocal current_time
        current_time += timedelta(seconds=random.randint(lo, hi))

    # ------------------------------------------------------------------ session

    # 1. first_visit (auto-collected, only on the user's very first session)
    if is_first_session:
        events.append(_ev("first_visit"))
        _advance(1, 2)

    # 2. session_start
    events.append(_ev("session_start", [ep("entrances", int_value=1)]))
    _advance(1, 3)

    # 3. sign_up / login
    if user["user_id"]:
        method = random.choices(LOGIN_METHODS, LOGIN_WEIGHTS, k=1)[0]
        if is_first_session and random.random() < 0.70:
            events.append(_ev("sign_up", [ep("method", string_value=method)]))
            _advance(10, 60)
        elif not is_first_session and random.random() < 0.55:
            events.append(_ev("login", [ep("method", string_value=method)]))
            _advance(5, 20)

    # 4. Landing page_view
    landing      = random.choice(SITE_PAGES)
    landing_url  = _page_url(landing["path"])
    ext_referrer = _referrer_for_source(session_src)

    events.append(_ev("page_view", [
        ep("page_location", string_value=landing_url),
        ep("page_title",    string_value=landing["title"]),
        ep("page_referrer", string_value=ext_referrer),
        ep("entrances",     int_value=1),
    ]))
    _advance(10, 60)

    prev_url     = landing_url
    browsed_list = []   # items from the last view_item_list
    active_page  = None # the category page that produced browsed_list

    # 5. Site search (20 % of sessions)
    if random.random() < 0.20:
        term = random.choice(SEARCH_TERMS)
        search_url = _page_url("/search", f"q={term.replace(' ', '+')}")

        events.append(_ev("search", [ep("search_term", string_value=term)]))
        _advance(1, 3)

        events.append(_ev("page_view", [
            ep("page_location", string_value=search_url),
            ep("page_title",    string_value=f"「{term}」の検索結果 | Example EC"),
            ep("page_referrer", string_value=prev_url),
            ep("search_term",   string_value=term),
        ]))
        _advance(5, 20)

        list_items = pick_product_list(random.randint(8, 16),
                                       list_id="search_results", list_name="検索結果")
        events.append(_ev("view_item_list", [
            ep("item_list_id",   string_value="search_results"),
            ep("item_list_name", string_value="検索結果"),
            ep("search_term",    string_value=term),
        ], items=list_items))
        _advance(15, 90)

        browsed_list = list_items
        prev_url     = search_url

    # 6. Browse (1-5 more pages) + view_item_list on category pages
    for _ in range(random.randint(1, 5)):
        page     = random.choice(SITE_PAGES)
        page_url = _page_url(page["path"])

        events.append(_ev("page_view", [
            ep("page_location", string_value=page_url),
            ep("page_title",    string_value=page["title"]),
            ep("page_referrer", string_value=prev_url),
        ]))
        _advance(10, 90)
        prev_url = page_url

        if "list_id" in page:
            list_items = pick_product_list(random.randint(8, 16),
                                           list_id=page["list_id"], list_name=page["list_name"])
            events.append(_ev("view_item_list", [
                ep("item_list_id",   string_value=page["list_id"]),
                ep("item_list_name", string_value=page["list_name"]),
            ], items=list_items))
            _advance(15, 120)

            browsed_list = list_items
            active_page  = page

    # 7. view_promotion → select_promotion (optional)
    promo = None
    if random.random() < funnel.get("promotion_probability", 0.15):
        promo       = pick_promotion()
        promo_items = pick_product_list(3,
                                        list_id=promo["promotion_id"],
                                        list_name=promo["promotion_name"])
        for it in promo_items:
            it.update({
                "promotion_id":   promo["promotion_id"],
                "promotion_name": promo["promotion_name"],
                "creative_name":  promo["creative_name"],
                "creative_slot":  promo["creative_slot"],
            })

        promo_params = [
            ep("promotion_id",   string_value=promo["promotion_id"]),
            ep("promotion_name", string_value=promo["promotion_name"]),
            ep("creative_name",  string_value=promo["creative_name"]),
            ep("creative_slot",  string_value=promo["creative_slot"]),
        ]
        events.append(_ev("view_promotion", promo_params, items=promo_items))
        _advance(5, 30)

        # 60 % of viewers click the promotion
        if random.random() < 0.60:
            events.append(_ev("select_promotion", promo_params, items=promo_items))
            _advance(5, 20)

    # 8. select_item → view_item (and deeper funnel)
    if random.random() < funnel.get("browse_to_view_item", 0.70):

        # select_item: click a product from the last viewed list
        if browsed_list and active_page:
            clicked = random.choice(browsed_list[:min(8, len(browsed_list))])
            events.append(_ev("select_item", [
                ep("item_list_id",   string_value=active_page["list_id"]),
                ep("item_list_name", string_value=active_page["list_name"]),
            ], items=[clicked]))
            _advance(1, 5)
            # The detail items start with the clicked product
            detail_items = [clicked] + (
                pick_products(random.randint(0, 2)) if random.random() < 0.3 else []
            )
        else:
            detail_items = pick_products(random.randint(1, 3))

        # view_item for each product (each has its own product page)
        for it in detail_items:
            product_url = _page_url(f"/product/{it['item_id']}")
            events.append(_ev("page_view", [
                ep("page_location", string_value=product_url),
                ep("page_title",    string_value=f"{it['item_name']} | Example EC"),
                ep("page_referrer", string_value=prev_url),
            ]))
            _advance(2, 5)

            view_items = _strip_list_fields([it])
            events.append(_ev("view_item", [
                ep("page_location", string_value=product_url),
                ep("page_title",    string_value=f"{it['item_name']} | Example EC"),
                ep("currency",      string_value=currency),
                ep("value",         float_value=it["price"]),
            ], items=view_items))
            _advance(30, 180)
            prev_url = product_url

        # 9. add_to_cart
        add_prob = funnel.get("view_item_to_add_to_cart", 0.30) + user["purchase_propensity"] * 0.2
        if random.random() < add_prob:
            added = _strip_list_fields(detail_items[:random.randint(1, len(detail_items))])

            for it in added:
                events.append(_ev("add_to_cart", [
                    ep("currency", string_value=currency),
                    ep("value",    float_value=it["price"] * it["quantity"]),
                ], items=[it]))
                _advance(5, 30)

            # 10. remove_from_cart (optional, only if more than one item)
            if len(added) > 1 and random.random() < funnel.get("add_to_cart_to_remove", 0.10):
                removed = added.pop()
                events.append(_ev("remove_from_cart", [
                    ep("currency", string_value=currency),
                    ep("value",    float_value=removed["price"] * removed["quantity"]),
                ], items=[removed]))
                _advance(5, 20)

            cart_subtotal = sum(i["price"] * i["quantity"] for i in added)

            # 11. view_cart
            cart_url = _page_url("/cart")
            events.append(_ev("page_view", [
                ep("page_location", string_value=cart_url),
                ep("page_title",    string_value="カート | Example EC"),
                ep("page_referrer", string_value=prev_url),
            ]))
            _advance(2, 5)
            events.append(_ev("view_cart", [
                ep("currency", string_value=currency),
                ep("value",    float_value=cart_subtotal),
            ], items=added))
            _advance(30, 120)
            prev_url = cart_url

            # 12. begin_checkout
            if random.random() < funnel.get("add_to_cart_to_checkout", 0.60):
                order_coupon  = random.choice(COUPONS)
                checkout_url  = _page_url("/checkout")

                events.append(_ev("page_view", [
                    ep("page_location", string_value=checkout_url),
                    ep("page_title",    string_value="チェックアウト | Example EC"),
                    ep("page_referrer", string_value=prev_url),
                ]))
                _advance(2, 5)

                checkout_params = [
                    ep("currency", string_value=currency),
                    ep("value",    float_value=cart_subtotal),
                ]
                if order_coupon:
                    checkout_params.append(ep("coupon", string_value=order_coupon))
                events.append(_ev("begin_checkout", checkout_params, items=added))
                _advance(30, 120)

                # 13. add_shipping_info
                if random.random() < funnel.get("checkout_to_purchase", 0.75):
                    ship_opt    = random.choice(SHIPPING_OPTIONS)
                    ship_fee    = 0.0 if cart_subtotal >= FREE_SHIPPING_THRESHOLD else float(ship_opt["fee"])
                    ship_params = [
                        ep("currency",      string_value=currency),
                        ep("value",         float_value=cart_subtotal),
                        ep("shipping_tier", string_value=ship_opt["tier"]),
                        ep("shipping",      float_value=ship_fee),
                    ]
                    if order_coupon:
                        ship_params.append(ep("coupon", string_value=order_coupon))
                    events.append(_ev("add_shipping_info", ship_params, items=added))
                    _advance(30, 120)

                    # 14. add_payment_info
                    payment_type   = random.choices(PAYMENT_TYPES, PAYMENT_WEIGHTS, k=1)[0]
                    payment_params = [
                        ep("currency",     string_value=currency),
                        ep("value",        float_value=cart_subtotal),
                        ep("payment_type", string_value=payment_type),
                    ]
                    if order_coupon:
                        payment_params.append(ep("coupon", string_value=order_coupon))
                    events.append(_ev("add_payment_info", payment_params, items=added))
                    _advance(30, 120)

                    # 15. purchase
                    txn_id         = generate_transaction_id()
                    discount_total = apply_coupon(cart_subtotal, order_coupon) if order_coupon else 0.0
                    revenue        = cart_subtotal - discount_total + ship_fee
                    tax            = round(revenue * TAX_RATE)

                    purchase_params = [
                        ep("currency",       string_value=currency),
                        ep("value",          float_value=revenue),
                        ep("transaction_id", string_value=txn_id),
                        ep("shipping",       float_value=ship_fee),
                        ep("tax",            float_value=float(tax)),
                    ]
                    if order_coupon:
                        purchase_params.append(ep("coupon", string_value=order_coupon))
                    if promo:
                        purchase_params.append(ep("promotion_id",   string_value=promo["promotion_id"]))
                        purchase_params.append(ep("promotion_name", string_value=promo["promotion_name"]))

                    ecommerce = {
                        "transaction_id":     txn_id,
                        "purchase_revenue":   revenue,
                        "total_item_quantity":sum(i["quantity"] for i in added),
                        "unique_items":       len(added),
                        "shipping_value":     ship_fee,
                        "tax_value":          float(tax),
                    }
                    events.append(_ev("purchase", purchase_params, items=added, ecommerce=ecommerce))
                    _advance(5, 30)

                    purchase_info = {
                        "user_pseudo_id": user["user_pseudo_id"],
                        "user_id":        user["user_id"],
                        "transaction_id": txn_id,
                        "value":          revenue,
                        "items":          added,
                        "currency":       currency,
                        "session_id":     session_id,
                        "session_number": session_number,
                        "device":         device_record,
                        "geo":            geo_record,
                        "traffic_source": traffic_src_record,
                    }

    # Add engagement_time_msec to every event
    for ev in events:
        ev["event_params"].append(
            ep("engagement_time_msec", int_value=random.randint(500, 30000))
        )

    return events, purchase_info


def generate_day_events(
    users: list[dict],
    target_date: datetime,
    config: dict,
    due_refunds: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Generate all events for one day.

    Args:
        users:        Full user pool.
        target_date:  The day to simulate (tz-aware).
        config:       Generation config dict.
        due_refunds:  Refund infos whose refund_date <= target_date.

    Returns:
        (events, new_purchase_infos)
        new_purchase_infos: purchase records from today for future refund scheduling.
    """
    daily_active_ratio = config.get("daily_active_ratio", 0.15)
    sessions_range     = config.get("sessions_per_day_range", [1, 3])
    stream_id          = config.get("stream_id", "1234567890")

    active_count = max(1, int(len(users) * daily_active_ratio))
    active_users = random.sample(users, active_count)

    all_events:    list[dict] = []
    new_purchases: list[dict] = []

    for user in active_users:
        for _ in range(random.randint(*sessions_range)):
            session_events, p_info = generate_session_events(user, target_date, config)
            all_events.extend(session_events)
            if p_info:
                new_purchases.append(p_info)

    # Inject due refund events
    if due_refunds:
        for r_info in due_refunds:
            all_events.append(generate_refund_event(r_info, target_date, stream_id))

    all_events.sort(key=lambda e: e["event_timestamp"])
    return all_events, new_purchases

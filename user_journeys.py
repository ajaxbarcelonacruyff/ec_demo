"""User journey and session simulation for GA4 ecommerce demo data.

Improvements over v1:
- User segments (new vs returning) with different funnel rates
- Category affinity per user
- Device-based behavior differences
- Campaign-aware traffic source boosting
- Landing page ↔ traffic source correlation
- Data quality noise (null user_id, bot sessions, payment failures)
- Fixed event ordering (login after first page_view)
"""

import random
from datetime import datetime, timedelta

from utils import (
    generate_user_pseudo_id, generate_ga_session_id, generate_transaction_id,
    generate_user_id, nz_datetime_to_event_timestamp, event_date_from_nz,
    random_time_of_day, NZ_TZ, is_campaign_active,
)
from product_catalog import (
    pick_products, pick_product_list, pick_promotion,
    apply_coupon, COUPONS, CATEGORIES,
)
from tables import generate_customer_attrs
from traffic_sources import (
    pick_traffic_source, build_traffic_source_record,
    build_collected_traffic_source, build_session_traffic_source_last_click,
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
    {"path": "/category/bags",          "title": "バッグ | Example EC",          "list_id": "category_bags",         "list_name": "バッグ"},
    {"path": "/category/health",        "title": "ヘルス＆フィットネス | Example EC", "list_id": "category_health",  "list_name": "ヘルス＆フィットネス"},
    {"path": "/category/home",          "title": "ホーム＆リビング | Example EC", "list_id": "category_home",        "list_name": "ホーム＆リビング"},
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
    "ヨガマット", "デスクライト", "加湿器", "扇風機", "スマートスピーカー",
    "ロボット掃除機", "ドッキングステーション", "リュック", "ポーチ",
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

# Landing pages by traffic source type
_SOURCE_LANDING_PAGES = {
    "cpc":      ["/sale", "/new-arrivals", "/category/electronics"],
    "email":    ["/sale", "/new-arrivals", "/"],
    "organic":  ["/", "/category/electronics", "/category/audio", "/category/office"],
    "social":   ["/", "/sale", "/new-arrivals"],
    "(none)":   ["/", "/category/electronics"],
}

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

# Funnel adjustment by segment
_SEGMENT_FUNNEL_MULTIPLIERS = {
    # New users: lower conversion, more browsing
    "new": {
        "browse_to_view_item": 0.85,
        "view_item_to_add_to_cart": 0.65,
        "add_to_cart_to_checkout": 0.70,
        "checkout_to_purchase": 0.80,
    },
    # Returning users (2-5 sessions): moderate
    "returning": {
        "browse_to_view_item": 1.0,
        "view_item_to_add_to_cart": 1.0,
        "add_to_cart_to_checkout": 1.0,
        "checkout_to_purchase": 1.0,
    },
    # Loyal users (6+ sessions): higher conversion
    "loyal": {
        "browse_to_view_item": 1.1,
        "view_item_to_add_to_cart": 1.4,
        "add_to_cart_to_checkout": 1.3,
        "checkout_to_purchase": 1.15,
    },
}

# Device funnel adjustments (mobile users slightly lower conversion)
_DEVICE_FUNNEL_MULTIPLIERS = {
    "mobile":  {"view_item_to_add_to_cart": 0.85, "checkout_to_purchase": 0.90},
    "desktop": {"view_item_to_add_to_cart": 1.10, "checkout_to_purchase": 1.05},
    "tablet":  {"view_item_to_add_to_cart": 0.95, "checkout_to_purchase": 0.95},
}


def _referrer_for_source(src: dict) -> str:
    return _REFERRERS.get(src.get("source", ""), "")


def _get_user_segment(session_count: int) -> str:
    """Classify user based on historical session count."""
    if session_count <= 1:
        return "new"
    elif session_count <= 5:
        return "returning"
    else:
        return "loyal"


def _get_adjusted_funnel(base_funnel: dict, segment: str, device_category: str) -> dict:
    """Apply segment and device multipliers to base funnel rates."""
    result = dict(base_funnel)
    seg_mult = _SEGMENT_FUNNEL_MULTIPLIERS.get(segment, {})
    dev_mult = _DEVICE_FUNNEL_MULTIPLIERS.get(device_category, {})
    for key in result:
        val = result[key]
        if key in seg_mult:
            val *= seg_mult[key]
        if key in dev_mult:
            val *= dev_mult[key]
        result[key] = min(val, 0.99)  # cap at 99%
    return result


def _pick_landing_for_source(src: dict) -> dict:
    """Pick a landing page correlated with the traffic source medium."""
    medium = src.get("medium", "(none)")
    paths = _SOURCE_LANDING_PAGES.get(medium, _SOURCE_LANDING_PAGES["(none)"])
    target_path = random.choice(paths)
    for page in SITE_PAGES:
        if page["path"] == target_path:
            return page
    return SITE_PAGES[0]  # fallback to home


def create_user_pool(
    total_users: int,
    logged_in_ratio: float,
    sim_start: "date | None" = None,
) -> list[dict]:
    """Create a pool of simulated users with category affinity."""
    from datetime import date as _date
    if sim_start is None:
        sim_start = _date.today()

    users = []
    for _ in range(total_users):
        user_id = generate_user_id() if random.random() < logged_in_ratio else None

        # Category affinity: each user has 1-3 preferred categories
        n_affinity = random.choices([1, 2, 3], weights=[40, 40, 20], k=1)[0]
        affinity = random.sample(CATEGORIES, min(n_affinity, len(CATEGORIES)))

        user = {
            "user_pseudo_id":      generate_user_pseudo_id(),
            "user_id":             user_id,
            "device_profile":      pick_device(),
            "geo_profile":         pick_geo(),
            "first_touch_source":  pick_traffic_source(),
            "session_count":       0,
            "purchase_propensity": random.betavariate(2, 5),
            "affinity_categories": affinity,
        }
        if user_id:
            user.update(generate_customer_attrs(user_id, sim_start))
        users.append(user)
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


def generate_bot_session(user: dict, session_date: datetime, config: dict) -> list[dict]:
    """Generate a bot-like session: rapid page views, no engagement."""
    session_id = generate_ga_session_id()
    stream_id = config.get("stream_id", "1234567890")
    device_record = build_device_record(user["device_profile"])
    geo_record = build_geo_record(user["geo_profile"])
    traffic_src_record = build_traffic_source_record(user["first_touch_source"])

    current_time = session_date + random_time_of_day()
    events = []

    # session_start
    ts = nz_datetime_to_event_timestamp(current_time)
    date_str = event_date_from_nz(current_time)
    params = [
        ep("ga_session_id", int_value=session_id),
        ep("ga_session_number", int_value=1),
        ep("session_engaged", int_value=0),
        ep("entrances", int_value=1),
        ep("engagement_time_msec", int_value=random.randint(0, 100)),
    ]
    events.append(build_event(
        event_name="session_start", event_timestamp=ts, event_date=date_str,
        user_pseudo_id=user["user_pseudo_id"], event_params=params,
        user_properties=[], device=device_record, geo=geo_record,
        traffic_source=traffic_src_record, stream_id=stream_id,
        batch_page_id=0, batch_ordering_id=0, batch_event_index=0,
    ))

    # Rapid page views (5-20 pages in very short time)
    for i in range(random.randint(5, 20)):
        current_time += timedelta(milliseconds=random.randint(200, 2000))
        page = random.choice(SITE_PAGES)
        ts = nz_datetime_to_event_timestamp(current_time)
        params = [
            ep("ga_session_id", int_value=session_id),
            ep("ga_session_number", int_value=1),
            ep("session_engaged", int_value=0),
            ep("page_location", string_value=_page_url(page["path"])),
            ep("page_title", string_value=page["title"]),
            ep("engagement_time_msec", int_value=random.randint(0, 50)),
        ]
        events.append(build_event(
            event_name="page_view", event_timestamp=ts, event_date=date_str,
            user_pseudo_id=user["user_pseudo_id"], event_params=params,
            user_properties=[], device=device_record, geo=geo_record,
            traffic_source=traffic_src_record, stream_id=stream_id,
            batch_page_id=i + 1, batch_ordering_id=i + 1, batch_event_index=0,
        ))

    return events


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
    noise_cfg = config.get("noise", {})

    is_first_session = (user["session_count"] == 0)
    user["session_count"] += 1

    session_id     = generate_ga_session_id()
    session_number = user["session_count"]

    # Campaign-aware traffic source
    session_src = pick_traffic_source(
        active_campaigns=config.get("active_campaigns", []),
    )

    device_record       = build_device_record(user["device_profile"])
    geo_record          = build_geo_record(user["geo_profile"])
    traffic_src_record  = build_traffic_source_record(user["first_touch_source"])
    collected_ts        = build_collected_traffic_source(session_src)
    stslc               = build_session_traffic_source_last_click(session_src)

    # Segment-based funnel adjustment
    segment = _get_user_segment(session_number)
    device_category = user["device_profile"]["category"]
    base_funnel = config.get("funnel", {})
    funnel = _get_adjusted_funnel(base_funnel, segment, device_category)

    month = session_date.month
    affinity = user.get("affinity_categories", [])

    # Determine effective user_id (apply noise: sometimes null for logged-in users)
    effective_user_id = user["user_id"]
    if effective_user_id and random.random() < noise_cfg.get("null_user_id_rate", 0.0):
        effective_user_id = None  # simulate tracking gap

    # Batch tracking
    batch_state = {"page_id": 0, "ordering_id": 0, "event_index": 0}

    def _new_batch():
        batch_state["page_id"] += 1
        batch_state["ordering_id"] += 1
        batch_state["event_index"] = 0

    def _next_event_index():
        idx = batch_state["event_index"]
        batch_state["event_index"] += 1
        return idx

    first_touch_ts = nz_datetime_to_event_timestamp(
        session_date if is_first_session
        else session_date - timedelta(days=random.randint(1, 90))
    )

    stream_id = config.get("stream_id", "1234567890")
    currency  = config.get("currency", "JPY")

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
        return [up("user_id", string_value=effective_user_id)] if effective_user_id else []

    def _ev(name, extra=None, items=None, ecommerce=None, is_page_view=False):
        if is_page_view:
            _new_batch()
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
            user_id=effective_user_id,
            user_first_touch_timestamp=first_touch_ts,
            items=items,
            ecommerce=ecommerce,
            batch_page_id=batch_state["page_id"],
            batch_ordering_id=batch_state["ordering_id"],
            batch_event_index=_next_event_index(),
            session_traffic_source_last_click=stslc,
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

    # 3. Landing page_view (BEFORE login/signup to match real behavior)
    landing = _pick_landing_for_source(session_src)
    landing_url  = _page_url(landing["path"])
    ext_referrer = _referrer_for_source(session_src)

    events.append(_ev("page_view", [
        ep("page_location", string_value=landing_url),
        ep("page_title",    string_value=landing["title"]),
        ep("page_referrer", string_value=ext_referrer),
        ep("entrances",     int_value=1),
    ], is_page_view=True))
    _advance(5, 30)

    # 4. sign_up / login (AFTER landing page_view)
    if user["user_id"]:
        method = random.choices(LOGIN_METHODS, LOGIN_WEIGHTS, k=1)[0]
        if is_first_session and random.random() < 0.70:
            events.append(_ev("sign_up", [ep("method", string_value=method)]))
            _advance(10, 60)
        elif not is_first_session and random.random() < 0.55:
            events.append(_ev("login", [ep("method", string_value=method)]))
            _advance(5, 20)

    prev_url     = landing_url
    browsed_list = []
    active_page  = None

    # 5. Site search (20 % of sessions)
    if random.random() < 0.20:
        term = random.choice(SEARCH_TERMS)
        search_url = _page_url("/search", f"q={term.replace(' ', '+')}")

        events.append(_ev("page_view", [
            ep("page_location", string_value=search_url),
            ep("page_title",    string_value=f"「{term}」の検索結果 | Example EC"),
            ep("page_referrer", string_value=prev_url),
            ep("search_term",   string_value=term),
        ], is_page_view=True))
        _advance(1, 3)

        events.append(_ev("search", [ep("search_term", string_value=term)]))
        _advance(3, 10)

        list_items = pick_product_list(random.randint(8, 16),
                                       list_id="search_results", list_name="検索結果",
                                       month=month, affinity_categories=affinity)
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
        ], is_page_view=True))
        _advance(10, 90)
        prev_url = page_url

        if "list_id" in page:
            list_items = pick_product_list(random.randint(8, 16),
                                           list_id=page["list_id"], list_name=page["list_name"],
                                           month=month, affinity_categories=affinity)
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
        promo       = pick_promotion(month=month)
        promo_items = pick_product_list(3,
                                        list_id=promo["promotion_id"],
                                        list_name=promo["promotion_name"],
                                        month=month)
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

        if random.random() < 0.60:
            events.append(_ev("select_promotion", promo_params, items=promo_items))
            _advance(5, 20)

    # 8. select_item → view_item (and deeper funnel)
    if random.random() < funnel.get("browse_to_view_item", 0.70):

        if browsed_list and active_page:
            clicked = random.choice(browsed_list[:min(8, len(browsed_list))])
            events.append(_ev("select_item", [
                ep("item_list_id",   string_value=active_page["list_id"]),
                ep("item_list_name", string_value=active_page["list_name"]),
            ], items=[clicked]))
            _advance(1, 5)
            detail_items = [clicked] + (
                pick_products(random.randint(0, 2), month=month, affinity_categories=affinity)
                if random.random() < 0.3 else []
            )
        else:
            detail_items = pick_products(random.randint(1, 3), month=month,
                                         affinity_categories=affinity)

        # view_item for each product (each has its own product page)
        for it in detail_items:
            product_url = _page_url(f"/product/{it['item_id']}")
            events.append(_ev("page_view", [
                ep("page_location", string_value=product_url),
                ep("page_title",    string_value=f"{it['item_name']} | Example EC"),
                ep("page_referrer", string_value=prev_url),
            ], is_page_view=True))
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
            ], is_page_view=True))
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
                ], is_page_view=True))
                _advance(2, 5)

                checkout_params = [
                    ep("currency", string_value=currency),
                    ep("value",    float_value=cart_subtotal),
                ]
                if order_coupon:
                    checkout_params.append(ep("coupon", string_value=order_coupon))
                events.append(_ev("begin_checkout", checkout_params, items=added))
                _advance(30, 120)

                # 13. Payment failure → retry (noise)
                payment_failed = random.random() < noise_cfg.get("payment_failure_rate", 0.0)
                if payment_failed:
                    # Emit a page_view to error page, then return to checkout
                    error_url = _page_url("/checkout/error")
                    events.append(_ev("page_view", [
                        ep("page_location", string_value=error_url),
                        ep("page_title",    string_value="決済エラー | Example EC"),
                        ep("page_referrer", string_value=checkout_url),
                    ], is_page_view=True))
                    _advance(10, 60)

                    # Some users abandon after error (40%)
                    if random.random() < 0.40:
                        # Add engagement_time_msec to all events and return
                        for ev in events:
                            ev["event_params"].append(
                                ep("engagement_time_msec", int_value=random.randint(500, 30000))
                            )
                        return events, None

                    # Retry: back to checkout
                    events.append(_ev("page_view", [
                        ep("page_location", string_value=checkout_url),
                        ep("page_title",    string_value="チェックアウト | Example EC"),
                        ep("page_referrer", string_value=error_url),
                    ], is_page_view=True))
                    _advance(10, 30)
                    events.append(_ev("begin_checkout", checkout_params, items=added))
                    _advance(30, 90)

                # 14. add_shipping_info
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

                    # 15. add_payment_info
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

                    # 16. purchase
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
                    purchase_datetime = current_time  # capture before _advance
                    events.append(_ev("purchase", purchase_params, items=added, ecommerce=ecommerce))
                    _advance(5, 30)

                    purchase_info = {
                        "user_pseudo_id":  user["user_pseudo_id"],
                        "user_id":         user["user_id"],  # always use real user_id for orders
                        "transaction_id":  txn_id,
                        "order_datetime":  purchase_datetime,
                        "subtotal":        cart_subtotal,
                        "coupon_code":     order_coupon,
                        "discount_amount": discount_total,
                        "shipping_fee":    ship_fee,
                        "shipping_tier":   ship_opt["tier"],
                        "tax_amount":      float(tax),
                        "total_amount":    revenue,
                        "payment_type":    payment_type,
                        "currency":        currency,
                        "items":           added,
                        "session_id":      session_id,
                        "session_number":  session_number,
                        "device":          device_record,
                        "geo":             geo_record,
                        "traffic_source":  traffic_src_record,
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

    Applies day-of-week traffic variation and campaign awareness.
    """
    daily_active_ratio = config.get("daily_active_ratio", 0.15)
    sessions_range     = config.get("sessions_per_day_range", [1, 3])
    stream_id          = config.get("stream_id", "1234567890")
    noise_cfg          = config.get("noise", {})

    # Day-of-week traffic multiplier
    dow = target_date.weekday()  # Mon=0 .. Sun=6
    dow_weights = config.get("day_of_week_weights", {})
    dow_mult = dow_weights.get(dow, dow_weights.get(str(dow), 1.0))

    # Campaign awareness
    campaigns = config.get("campaigns", [])
    active_campaigns = is_campaign_active(target_date, campaigns)

    # Campaign boosts DAU slightly
    campaign_dau_boost = 1.0
    if active_campaigns:
        campaign_dau_boost = 1.15

    adjusted_ratio = daily_active_ratio * dow_mult * campaign_dau_boost
    active_count = max(1, int(len(users) * adjusted_ratio))
    active_users = random.sample(users, min(active_count, len(users)))

    # Pass campaign info into session config
    session_config = dict(config)
    session_config["active_campaigns"] = active_campaigns

    all_events:    list[dict] = []
    new_purchases: list[dict] = []

    for user in active_users:
        for _ in range(random.randint(*sessions_range)):
            # Bot session check
            if random.random() < noise_cfg.get("bot_session_rate", 0.0):
                bot_events = generate_bot_session(user, target_date, session_config)
                all_events.extend(bot_events)
                continue

            session_events, p_info = generate_session_events(user, target_date, session_config)
            all_events.extend(session_events)
            if p_info:
                new_purchases.append(p_info)

    # Inject due refund events
    if due_refunds:
        for r_info in due_refunds:
            all_events.append(generate_refund_event(r_info, target_date, stream_id))

    all_events.sort(key=lambda e: e["event_timestamp"])
    return all_events, new_purchases

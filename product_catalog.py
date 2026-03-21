"""EC product catalog for demo data generation.

~60 products with Pareto-distributed popularity weights.
Top 20% of products generate ~80% of sales.
"""

import random
import math

PRODUCTS = [
    # === Electronics > Audio (high popularity cluster) ===
    {"item_id": "SKU001", "item_name": "ワイヤレスヘッドホン",         "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Headphones",   "price": 12800.0, "weight": 50, "seasonal": None},
    {"item_id": "SKU002", "item_name": "Bluetooth スピーカー",        "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Speakers",     "price": 8500.0,  "weight": 40, "seasonal": None},
    {"item_id": "SKU010", "item_name": "ノイズキャンセリングイヤホン", "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Earbuds",      "price": 22800.0, "weight": 45, "seasonal": None},
    {"item_id": "SKU019", "item_name": "ワイヤレスイヤホン",           "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Earbuds",      "price": 5800.0,  "weight": 48, "seasonal": None},
    {"item_id": "SKU020", "item_name": "USB マイク",                   "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Microphones",  "price": 8800.0,  "weight": 25, "seasonal": None},
    {"item_id": "SKU041", "item_name": "コンデンサーマイク プロ",      "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Microphones",  "price": 18800.0, "weight": 12, "seasonal": None},
    {"item_id": "SKU042", "item_name": "ポータブルDACアンプ",          "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Amplifiers",   "price": 15800.0, "weight": 8,  "seasonal": None},
    {"item_id": "SKU043", "item_name": "骨伝導ヘッドホン",            "item_brand": "AudioTech",  "item_category": "Electronics", "item_category2": "Audio",       "item_category3": "Headphones",   "price": 16800.0, "weight": 15, "seasonal": "summer"},

    # === Electronics > Wearables ===
    {"item_id": "SKU003", "item_name": "スマートウォッチ Pro",         "item_brand": "TechWear",   "item_category": "Electronics", "item_category2": "Wearables",   "item_category3": "Watches",      "price": 34800.0, "weight": 35, "seasonal": None},
    {"item_id": "SKU004", "item_name": "フィットネスバンド",           "item_brand": "TechWear",   "item_category": "Electronics", "item_category2": "Wearables",   "item_category3": "Bands",        "price": 6800.0,  "weight": 30, "seasonal": None},
    {"item_id": "SKU044", "item_name": "スマートリング",               "item_brand": "TechWear",   "item_category": "Electronics", "item_category2": "Wearables",   "item_category3": "Rings",        "price": 28800.0, "weight": 10, "seasonal": None},
    {"item_id": "SKU045", "item_name": "GPS ランニングウォッチ",       "item_brand": "TechWear",   "item_category": "Electronics", "item_category2": "Wearables",   "item_category3": "Watches",      "price": 42800.0, "weight": 8,  "seasonal": "spring"},

    # === Electronics > Peripherals ===
    {"item_id": "SKU006", "item_name": "メカニカルキーボード",         "item_brand": "KeyMaster",  "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Keyboards",    "price": 15800.0, "weight": 30, "seasonal": None},
    {"item_id": "SKU007", "item_name": "ゲーミングマウス",             "item_brand": "KeyMaster",  "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Mice",         "price": 7800.0,  "weight": 35, "seasonal": None},
    {"item_id": "SKU012", "item_name": "Webカメラ 1080p",              "item_brand": "ViewMax",    "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Cameras",      "price": 5800.0,  "weight": 20, "seasonal": None},
    {"item_id": "SKU046", "item_name": "ゲーミングキーボード RGB",     "item_brand": "KeyMaster",  "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Keyboards",    "price": 12800.0, "weight": 18, "seasonal": None},
    {"item_id": "SKU047", "item_name": "トラックボールマウス",         "item_brand": "KeyMaster",  "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Mice",         "price": 6800.0,  "weight": 10, "seasonal": None},
    {"item_id": "SKU048", "item_name": "4K Webカメラ",                 "item_brand": "ViewMax",    "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Cameras",      "price": 12800.0, "weight": 7,  "seasonal": None},
    {"item_id": "SKU049", "item_name": "ゲーミングヘッドセット",       "item_brand": "KeyMaster",  "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Headsets",     "price": 9800.0,  "weight": 22, "seasonal": None},

    # === Electronics > Displays ===
    {"item_id": "SKU008", "item_name": "4K モニター 27インチ",         "item_brand": "ViewMax",    "item_category": "Electronics", "item_category2": "Displays",    "item_category3": "Monitors",     "price": 49800.0, "weight": 15, "seasonal": None},
    {"item_id": "SKU050", "item_name": "ウルトラワイドモニター 34インチ","item_brand": "ViewMax",   "item_category": "Electronics", "item_category2": "Displays",    "item_category3": "Monitors",     "price": 69800.0, "weight": 6,  "seasonal": None},
    {"item_id": "SKU051", "item_name": "モバイルモニター 15.6インチ",  "item_brand": "ViewMax",    "item_category": "Electronics", "item_category2": "Displays",    "item_category3": "Monitors",     "price": 24800.0, "weight": 12, "seasonal": None},

    # === Electronics > Accessories ===
    {"item_id": "SKU005", "item_name": "USB-C ハブ 7in1",              "item_brand": "ConnectPro", "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Hubs",         "price": 4500.0,  "weight": 25, "seasonal": None},
    {"item_id": "SKU009", "item_name": "ポータブル充電器 20000mAh",    "item_brand": "PowerUp",    "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Chargers",     "price": 3800.0,  "weight": 42, "seasonal": None},
    {"item_id": "SKU013", "item_name": "ワイヤレス充電パッド",         "item_brand": "PowerUp",    "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Chargers",     "price": 2500.0,  "weight": 28, "seasonal": None},
    {"item_id": "SKU052", "item_name": "USB-C ケーブル 3本セット",     "item_brand": "ConnectPro", "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Cables",       "price": 1800.0,  "weight": 38, "seasonal": None},
    {"item_id": "SKU053", "item_name": "ワイヤレス充電スタンド",       "item_brand": "PowerUp",    "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Chargers",     "price": 4800.0,  "weight": 15, "seasonal": None},
    {"item_id": "SKU054", "item_name": "USB-C ドッキングステーション", "item_brand": "ConnectPro", "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Docks",        "price": 18800.0, "weight": 8,  "seasonal": None},
    {"item_id": "SKU055", "item_name": "ケーブル収納ボックス",         "item_brand": "ConnectPro", "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Organizers",   "price": 2200.0,  "weight": 14, "seasonal": None},

    # === Electronics > Storage ===
    {"item_id": "SKU016", "item_name": "ポータブルSSD 1TB",            "item_brand": "DataVault",  "item_category": "Electronics", "item_category2": "Storage",     "item_category3": "SSD",          "price": 12800.0, "weight": 22, "seasonal": None},
    {"item_id": "SKU056", "item_name": "ポータブルSSD 2TB",            "item_brand": "DataVault",  "item_category": "Electronics", "item_category2": "Storage",     "item_category3": "SSD",          "price": 22800.0, "weight": 10, "seasonal": None},
    {"item_id": "SKU057", "item_name": "USBメモリ 128GB",              "item_brand": "DataVault",  "item_category": "Electronics", "item_category2": "Storage",     "item_category3": "USB Memory",   "price": 2800.0,  "weight": 18, "seasonal": None},

    # === Smart Home ===
    {"item_id": "SKU017", "item_name": "スマートプラグ 2個セット",     "item_brand": "HomeSmart",  "item_category": "Smart Home",  "item_category2": "Plugs",       "item_category3": "WiFi",         "price": 3200.0,  "weight": 16, "seasonal": None},
    {"item_id": "SKU058", "item_name": "スマートLED電球 4個セット",    "item_brand": "HomeSmart",  "item_category": "Smart Home",  "item_category2": "Lighting",    "item_category3": "Bulbs",        "price": 4800.0,  "weight": 14, "seasonal": None},
    {"item_id": "SKU059", "item_name": "スマートスピーカー",           "item_brand": "HomeSmart",  "item_category": "Smart Home",  "item_category2": "Speakers",    "item_category3": "Voice",        "price": 7800.0,  "weight": 20, "seasonal": None},
    {"item_id": "SKU060", "item_name": "スマートロック",               "item_brand": "HomeSmart",  "item_category": "Smart Home",  "item_category2": "Security",    "item_category3": "Locks",        "price": 18800.0, "weight": 6,  "seasonal": None},
    {"item_id": "SKU061", "item_name": "スマート温湿度計",             "item_brand": "HomeSmart",  "item_category": "Smart Home",  "item_category2": "Sensors",     "item_category3": "Climate",      "price": 3800.0,  "weight": 10, "seasonal": "winter"},
    {"item_id": "SKU062", "item_name": "ロボット掃除機",               "item_brand": "HomeSmart",  "item_category": "Smart Home",  "item_category2": "Cleaning",    "item_category3": "Vacuums",      "price": 39800.0, "weight": 12, "seasonal": None},

    # === Office > Accessories ===
    {"item_id": "SKU011", "item_name": "タブレットスタンド",           "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Accessories", "item_category3": "Stands",       "price": 2800.0,  "weight": 18, "seasonal": None},
    {"item_id": "SKU018", "item_name": "エルゴノミクスマウスパッド",   "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Accessories", "item_category3": "Mouse Pads",   "price": 1800.0,  "weight": 14, "seasonal": None},
    {"item_id": "SKU063", "item_name": "ノートPCスタンド",             "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Accessories", "item_category3": "Stands",       "price": 4800.0,  "weight": 20, "seasonal": None},
    {"item_id": "SKU064", "item_name": "デスクオーガナイザー",         "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Accessories", "item_category3": "Organizers",   "price": 3200.0,  "weight": 10, "seasonal": None},
    {"item_id": "SKU065", "item_name": "リストレスト キーボード用",    "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Accessories", "item_category3": "Ergonomics",   "price": 2400.0,  "weight": 12, "seasonal": None},

    # === Office > Lighting ===
    {"item_id": "SKU015", "item_name": "LEDデスクライト",              "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Lighting",    "item_category3": "Desk Lamps",   "price": 4200.0,  "weight": 20, "seasonal": None},
    {"item_id": "SKU066", "item_name": "モニターライトバー",           "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Lighting",    "item_category3": "Monitor Bars", "price": 5800.0,  "weight": 16, "seasonal": None},

    # === Office > Furniture ===
    {"item_id": "SKU067", "item_name": "昇降式デスク",                 "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Furniture",   "item_category3": "Desks",        "price": 49800.0, "weight": 4,  "seasonal": None},
    {"item_id": "SKU068", "item_name": "エルゴノミクスチェア",         "item_brand": "DeskPro",    "item_category": "Office",      "item_category2": "Furniture",   "item_category3": "Chairs",       "price": 39800.0, "weight": 5,  "seasonal": None},

    # === Bags ===
    {"item_id": "SKU014", "item_name": "防水バックパック",             "item_brand": "UrbanGear",  "item_category": "Bags",        "item_category2": "Backpacks",   "item_category3": "Waterproof",   "price": 9800.0,  "weight": 18, "seasonal": None},
    {"item_id": "SKU069", "item_name": "ビジネスリュック",             "item_brand": "UrbanGear",  "item_category": "Bags",        "item_category2": "Backpacks",   "item_category3": "Business",     "price": 12800.0, "weight": 15, "seasonal": None},
    {"item_id": "SKU070", "item_name": "ガジェットポーチ",             "item_brand": "UrbanGear",  "item_category": "Bags",        "item_category2": "Pouches",     "item_category3": "Gadget",       "price": 3200.0,  "weight": 22, "seasonal": None},
    {"item_id": "SKU071", "item_name": "PCインナーケース 14インチ",    "item_brand": "UrbanGear",  "item_category": "Bags",        "item_category2": "Cases",       "item_category3": "Laptop",       "price": 2800.0,  "weight": 16, "seasonal": None},
    {"item_id": "SKU072", "item_name": "トラベルオーガナイザー",       "item_brand": "UrbanGear",  "item_category": "Bags",        "item_category2": "Pouches",     "item_category3": "Travel",       "price": 2200.0,  "weight": 10, "seasonal": "summer"},

    # === Health & Fitness ===
    {"item_id": "SKU073", "item_name": "ヨガマット",                   "item_brand": "FitLife",    "item_category": "Health",      "item_category2": "Fitness",     "item_category3": "Mats",         "price": 3800.0,  "weight": 14, "seasonal": "spring"},
    {"item_id": "SKU074", "item_name": "フォームローラー",             "item_brand": "FitLife",    "item_category": "Health",      "item_category2": "Fitness",     "item_category3": "Recovery",     "price": 2800.0,  "weight": 10, "seasonal": None},
    {"item_id": "SKU075", "item_name": "プロテインシェイカー",         "item_brand": "FitLife",    "item_category": "Health",      "item_category2": "Fitness",     "item_category3": "Bottles",      "price": 1800.0,  "weight": 16, "seasonal": None},
    {"item_id": "SKU076", "item_name": "エクササイズバンド セット",    "item_brand": "FitLife",    "item_category": "Health",      "item_category2": "Fitness",     "item_category3": "Bands",        "price": 2200.0,  "weight": 12, "seasonal": "spring"},

    # === Seasonal / Climate ===
    {"item_id": "SKU077", "item_name": "卓上加湿器",                   "item_brand": "HomeSmart",  "item_category": "Home",        "item_category2": "Climate",     "item_category3": "Humidifiers",  "price": 4800.0,  "weight": 12, "seasonal": "winter"},
    {"item_id": "SKU078", "item_name": "USB扇風機",                    "item_brand": "HomeSmart",  "item_category": "Home",        "item_category2": "Climate",     "item_category3": "Fans",         "price": 2800.0,  "weight": 12, "seasonal": "summer"},
    {"item_id": "SKU079", "item_name": "電気ブランケット",             "item_brand": "HomeSmart",  "item_category": "Home",        "item_category2": "Climate",     "item_category3": "Heating",      "price": 5800.0,  "weight": 10, "seasonal": "winter"},
    {"item_id": "SKU080", "item_name": "ハンディファン",               "item_brand": "HomeSmart",  "item_category": "Home",        "item_category2": "Climate",     "item_category3": "Fans",         "price": 1800.0,  "weight": 14, "seasonal": "summer"},
]

# Category list for user affinity assignment
CATEGORIES = sorted(set(p["item_category"] for p in PRODUCTS))

# Map category -> product indices for affinity-based selection
_CATEGORY_PRODUCT_IDX = {}
for _i, _p in enumerate(PRODUCTS):
    _CATEGORY_PRODUCT_IDX.setdefault(_p["item_category"], []).append(_i)


PROMOTIONS = [
    {"promotion_id": "PROMO001", "promotion_name": "春のセール",           "creative_name": "spring_banner",  "creative_slot": "slot1_hero"},
    {"promotion_id": "PROMO002", "promotion_name": "新生活応援キャンペーン","creative_name": "new_life_banner", "creative_slot": "slot2_sidebar"},
    {"promotion_id": "PROMO003", "promotion_name": "ポイント2倍",          "creative_name": "points_double",  "creative_slot": "slot1_hero"},
    {"promotion_id": "PROMO004", "promotion_name": "タイムセール",          "creative_name": "time_sale_banner","creative_slot": "slot3_footer"},
    {"promotion_id": "PROMO005", "promotion_name": "送料無料キャンペーン",  "creative_name": "free_shipping",  "creative_slot": "slot2_sidebar"},
    {"promotion_id": "PROMO006", "promotion_name": "夏のクリアランス",      "creative_name": "summer_banner",  "creative_slot": "slot1_hero"},
    {"promotion_id": "PROMO007", "promotion_name": "冬のあったかセール",    "creative_name": "winter_banner",  "creative_slot": "slot1_hero"},
]

# Coupon codes: None entries increase no-coupon probability
COUPONS = ["WELCOME10", "SAVE20", "SPRING2025", "VIP500", "SUMMER15", None, None, None, None]

# Discount definition: percent (0.0-1.0) or flat yen amount
COUPON_DISCOUNTS = {
    "WELCOME10":  {"type": "percent", "value": 0.10},
    "SAVE20":     {"type": "percent", "value": 0.20},
    "SPRING2025": {"type": "percent", "value": 0.15},
    "VIP500":     {"type": "flat",    "value": 500.0},
    "SUMMER15":   {"type": "percent", "value": 0.15},
}

# Seasonal weight multipliers (applied on top of base weight)
_SEASON_MONTH_MAP = {
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "autumn": [9, 10, 11],
    "winter": [12, 1, 2],
}


def get_seasonal_weights(month: int) -> list[float]:
    """Get product weights adjusted for seasonality.

    In-season products get 3x weight; off-season get 0.3x.
    """
    weights = []
    for p in PRODUCTS:
        w = float(p["weight"])
        season = p.get("seasonal")
        if season:
            if month in _SEASON_MONTH_MAP.get(season, []):
                w *= 3.0   # in-season boost
            else:
                w *= 0.3   # off-season dampen
        weights.append(w)
    return weights


def apply_coupon(subtotal: float, coupon: str) -> float:
    """Return discount amount for a coupon applied to subtotal."""
    if not coupon or coupon not in COUPON_DISCOUNTS:
        return 0.0
    defn = COUPON_DISCOUNTS[coupon]
    if defn["type"] == "percent":
        return round(subtotal * defn["value"])
    else:
        return min(defn["value"], subtotal)


def _build_item(product: dict, index: int = 0, quantity: int = None,
                coupon: str = None, list_id: str = None, list_name: str = None) -> dict:
    """Build a GA4 item dict from a product record."""
    if quantity is None:
        quantity = random.choices([1, 2, 3], weights=[70, 20, 10], k=1)[0]
    discount = 0.0
    if coupon and coupon in COUPON_DISCOUNTS:
        discount = apply_coupon(product["price"], coupon)
    item = {
        "item_id": product["item_id"],
        "item_name": product["item_name"],
        "item_brand": product["item_brand"],
        "item_category": product["item_category"],
        "item_category2": product["item_category2"],
        "item_category3": product["item_category3"],
        "price": product["price"],
        "quantity": quantity,
        "index": index,
    }
    if discount:
        item["discount"] = discount
        item["coupon"] = coupon
    if list_id:
        item["item_list_id"] = list_id
        item["item_list_name"] = list_name or list_id
    return item


def pick_products(n: int = 1, coupon: str = None, month: int = 1,
                  affinity_categories: list[str] = None) -> list[dict]:
    """Pick n products weighted by popularity (for cart/checkout events).

    Args:
        affinity_categories: If provided, products in these categories get 2x weight.
        month: Current month for seasonal adjustment.
    """
    weights = get_seasonal_weights(month)

    # Apply category affinity boost
    if affinity_categories:
        for i, p in enumerate(PRODUCTS):
            if p["item_category"] in affinity_categories:
                weights[i] *= 2.0

    chosen = random.choices(PRODUCTS, weights=weights, k=n)
    items = []
    for i, p in enumerate(chosen):
        item_coupon = coupon or random.choice(COUPONS)
        items.append(_build_item(p, index=i, coupon=item_coupon))
    return items


def pick_product_list(n: int, list_id: str = "", list_name: str = "",
                      month: int = 1, affinity_categories: list[str] = None) -> list[dict]:
    """Pick n unique products for a list display (view_item_list / select_item).

    Uses sampling without replacement so no duplicate products appear in a list.
    Items have list metadata (item_list_id, item_list_name, index) but quantity=1
    and no coupon/discount (not yet decided at browse stage).
    """
    n = min(n, len(PRODUCTS))
    weights = get_seasonal_weights(month)

    if affinity_categories:
        for i, p in enumerate(PRODUCTS):
            if p["item_category"] in affinity_categories:
                weights[i] *= 2.0

    # Weighted sample without replacement via cumulative selection
    chosen = []
    pool = list(PRODUCTS)
    pool_weights = list(weights)
    for _ in range(n):
        total = sum(pool_weights)
        r = random.uniform(0, total)
        cumulative = 0
        for idx, w in enumerate(pool_weights):
            cumulative += w
            if r <= cumulative:
                chosen.append(pool[idx])
                pool.pop(idx)
                pool_weights.pop(idx)
                break
    return [_build_item(p, index=i + 1, quantity=1, list_id=list_id, list_name=list_name)
            for i, p in enumerate(chosen)]


def pick_promotion(month: int = 1) -> dict:
    """Pick a promotion, preferring seasonal ones when appropriate."""
    # Simple: random choice (seasonal promotions are always available)
    return random.choice(PROMOTIONS)

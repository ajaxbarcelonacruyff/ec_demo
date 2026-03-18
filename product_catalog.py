"""EC product catalog for demo data generation."""

import random

PRODUCTS = [
    {"item_id": "SKU001", "item_name": "ワイヤレスヘッドホン", "item_brand": "AudioTech", "item_category": "Electronics", "item_category2": "Audio", "item_category3": "Headphones", "price": 12800.0, "weight": 10},
    {"item_id": "SKU002", "item_name": "Bluetooth スピーカー", "item_brand": "AudioTech", "item_category": "Electronics", "item_category2": "Audio", "item_category3": "Speakers", "price": 8500.0, "weight": 8},
    {"item_id": "SKU003", "item_name": "スマートウォッチ Pro", "item_brand": "TechWear", "item_category": "Electronics", "item_category2": "Wearables", "item_category3": "Watches", "price": 34800.0, "weight": 7},
    {"item_id": "SKU004", "item_name": "フィットネスバンド", "item_brand": "TechWear", "item_category": "Electronics", "item_category2": "Wearables", "item_category3": "Bands", "price": 6800.0, "weight": 9},
    {"item_id": "SKU005", "item_name": "USB-C ハブ 7in1", "item_brand": "ConnectPro", "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Hubs", "price": 4500.0, "weight": 6},
    {"item_id": "SKU006", "item_name": "メカニカルキーボード", "item_brand": "KeyMaster", "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Keyboards", "price": 15800.0, "weight": 7},
    {"item_id": "SKU007", "item_name": "ゲーミングマウス", "item_brand": "KeyMaster", "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Mice", "price": 7800.0, "weight": 8},
    {"item_id": "SKU008", "item_name": "4K モニター 27インチ", "item_brand": "ViewMax", "item_category": "Electronics", "item_category2": "Displays", "item_category3": "Monitors", "price": 49800.0, "weight": 5},
    {"item_id": "SKU009", "item_name": "ポータブル充電器 20000mAh", "item_brand": "PowerUp", "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Chargers", "price": 3800.0, "weight": 10},
    {"item_id": "SKU010", "item_name": "ノイズキャンセリングイヤホン", "item_brand": "AudioTech", "item_category": "Electronics", "item_category2": "Audio", "item_category3": "Earbuds", "price": 22800.0, "weight": 9},
    {"item_id": "SKU011", "item_name": "タブレットスタンド", "item_brand": "DeskPro", "item_category": "Office", "item_category2": "Accessories", "item_category3": "Stands", "price": 2800.0, "weight": 6},
    {"item_id": "SKU012", "item_name": "Webカメラ 1080p", "item_brand": "ViewMax", "item_category": "Electronics", "item_category2": "Peripherals", "item_category3": "Cameras", "price": 5800.0, "weight": 7},
    {"item_id": "SKU013", "item_name": "ワイヤレス充電パッド", "item_brand": "PowerUp", "item_category": "Electronics", "item_category2": "Accessories", "item_category3": "Chargers", "price": 2500.0, "weight": 8},
    {"item_id": "SKU014", "item_name": "防水バックパック", "item_brand": "UrbanGear", "item_category": "Bags", "item_category2": "Backpacks", "item_category3": "Waterproof", "price": 9800.0, "weight": 6},
    {"item_id": "SKU015", "item_name": "LEDデスクライト", "item_brand": "DeskPro", "item_category": "Office", "item_category2": "Lighting", "item_category3": "Desk Lamps", "price": 4200.0, "weight": 7},
    {"item_id": "SKU016", "item_name": "ポータブルSSD 1TB", "item_brand": "DataVault", "item_category": "Electronics", "item_category2": "Storage", "item_category3": "SSD", "price": 12800.0, "weight": 8},
    {"item_id": "SKU017", "item_name": "スマートプラグ 2個セット", "item_brand": "HomeSmart", "item_category": "Smart Home", "item_category2": "Plugs", "item_category3": "WiFi", "price": 3200.0, "weight": 5},
    {"item_id": "SKU018", "item_name": "エルゴノミクスマウスパッド", "item_brand": "DeskPro", "item_category": "Office", "item_category2": "Accessories", "item_category3": "Mouse Pads", "price": 1800.0, "weight": 4},
    {"item_id": "SKU019", "item_name": "ワイヤレスイヤホン", "item_brand": "AudioTech", "item_category": "Electronics", "item_category2": "Audio", "item_category3": "Earbuds", "price": 5800.0, "weight": 10},
    {"item_id": "SKU020", "item_name": "USB マイク", "item_brand": "AudioTech", "item_category": "Electronics", "item_category2": "Audio", "item_category3": "Microphones", "price": 8800.0, "weight": 6},
]

PROMOTIONS = [
    {"promotion_id": "PROMO001", "promotion_name": "春のセール", "creative_name": "spring_banner", "creative_slot": "slot1_hero"},
    {"promotion_id": "PROMO002", "promotion_name": "新生活応援キャンペーン", "creative_name": "new_life_banner", "creative_slot": "slot2_sidebar"},
    {"promotion_id": "PROMO003", "promotion_name": "ポイント2倍", "creative_name": "points_double", "creative_slot": "slot1_hero"},
    {"promotion_id": "PROMO004", "promotion_name": "タイムセール", "creative_name": "time_sale_banner", "creative_slot": "slot3_footer"},
    {"promotion_id": "PROMO005", "promotion_name": "送料無料キャンペーン", "creative_name": "free_shipping", "creative_slot": "slot2_sidebar"},
]

# Coupon codes: None entries increase no-coupon probability
COUPONS = ["WELCOME10", "SAVE20", "SPRING2025", "VIP500", None, None, None]

# Discount definition: percent (0.0-1.0) or flat yen amount
COUPON_DISCOUNTS = {
    "WELCOME10": {"type": "percent", "value": 0.10},
    "SAVE20":    {"type": "percent", "value": 0.20},
    "SPRING2025":{"type": "percent", "value": 0.15},
    "VIP500":    {"type": "flat",    "value": 500.0},
}


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


def pick_products(n: int = 1, coupon: str = None) -> list[dict]:
    """Pick n products weighted by popularity (for cart/checkout events)."""
    weights = [p["weight"] for p in PRODUCTS]
    chosen = random.choices(PRODUCTS, weights=weights, k=n)
    items = []
    for i, p in enumerate(chosen):
        item_coupon = coupon or random.choice(COUPONS)
        items.append(_build_item(p, index=i, coupon=item_coupon))
    return items


def pick_product_list(n: int, list_id: str = "", list_name: str = "") -> list[dict]:
    """Pick n unique products for a list display (view_item_list / select_item).

    Uses sampling without replacement so no duplicate products appear in a list.
    Items have list metadata (item_list_id, item_list_name, index) but quantity=1
    and no coupon/discount (not yet decided at browse stage).
    """
    n = min(n, len(PRODUCTS))
    weights = [p["weight"] for p in PRODUCTS]
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


def pick_promotion() -> dict:
    """Pick a random promotion."""
    return random.choice(PROMOTIONS)

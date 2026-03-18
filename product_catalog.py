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

COUPONS = ["WELCOME10", "SAVE20", "SPRING2025", "VIP500", None, None, None]


def pick_products(n: int = 1) -> list[dict]:
    """Pick n products weighted by popularity."""
    weights = [p["weight"] for p in PRODUCTS]
    chosen = random.choices(PRODUCTS, weights=weights, k=n)
    items = []
    for i, p in enumerate(chosen):
        quantity = random.choices([1, 2, 3], weights=[70, 20, 10], k=1)[0]
        item = {
            "item_id": p["item_id"],
            "item_name": p["item_name"],
            "item_brand": p["item_brand"],
            "item_category": p["item_category"],
            "item_category2": p["item_category2"],
            "item_category3": p["item_category3"],
            "price": p["price"],
            "quantity": quantity,
            "item_list_index": str(i),
        }
        coupon = random.choice(COUPONS)
        if coupon:
            item["coupon"] = coupon
        items.append(item)
    return items


def pick_promotion() -> dict:
    """Pick a random promotion."""
    return random.choice(PROMOTIONS)

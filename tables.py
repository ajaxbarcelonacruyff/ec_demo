"""Relational table generation and CSV export for EC demo data.

Table consistency guarantees:
  customers.customer_id  == GA4 events user_id          == orders.customer_id
  products.product_id    == GA4 events items[].item_id  == order_items.product_id
  orders.order_id        == GA4 events transaction_id   == order_items.order_id
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from product_catalog import PRODUCTS

# ---------------------------------------------------------------------------
# Master data for customer generation
# ---------------------------------------------------------------------------

LAST_NAMES = [
    "佐藤", "鈴木", "高橋", "田中", "渡辺", "伊藤", "山本", "中村",
    "小林", "加藤", "吉田", "山田", "佐々木", "山口", "松本",
    "井上", "木村", "林", "斎藤", "清水",
]

FIRST_NAMES_MALE = [
    "太郎", "一郎", "健二", "翔", "颯太", "大輝", "蓮", "陸", "悠真", "拓海",
    "勇気", "和也", "直樹", "雄大", "航",
]

FIRST_NAMES_FEMALE = [
    "花子", "愛", "美咲", "さくら", "凛", "葵", "陽菜", "結衣", "莉子", "ひなた",
    "奈々", "真由", "理恵", "遥", "彩",
]

# Simple romanization lookup for email generation
_ROMAN = {
    "佐藤": "sato", "鈴木": "suzuki", "高橋": "takahashi", "田中": "tanaka",
    "渡辺": "watanabe", "伊藤": "ito", "山本": "yamamoto", "中村": "nakamura",
    "小林": "kobayashi", "加藤": "kato", "吉田": "yoshida", "山田": "yamada",
    "佐々木": "sasaki", "山口": "yamaguchi", "松本": "matsumoto",
    "井上": "inoue", "木村": "kimura", "林": "hayashi", "斎藤": "saito", "清水": "shimizu",
    "太郎": "taro", "一郎": "ichiro", "健二": "kenji", "翔": "sho", "颯太": "sota",
    "大輝": "daiki", "蓮": "ren", "陸": "riku", "悠真": "yuma", "拓海": "takumi",
    "勇気": "yuki", "和也": "kazuya", "直樹": "naoki", "雄大": "yudai", "航": "ko",
    "花子": "hanako", "愛": "ai", "美咲": "misaki", "さくら": "sakura", "凛": "rin",
    "葵": "aoi", "陽菜": "hina", "結衣": "yui", "莉子": "riko", "ひなた": "hinata",
    "奈々": "nana", "真由": "mayu", "理恵": "rie", "遥": "haruka", "彩": "aya",
}

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.co.jp", "icloud.com",
    "docomo.ne.jp", "ezweb.ne.jp", "outlook.com",
]

PREFECTURES = [
    "東京都", "大阪府", "神奈川県", "愛知県", "福岡県",
    "北海道", "兵庫県", "京都府", "宮城県", "広島県",
]

MEMBERSHIP_RANKS   = ["regular", "silver", "gold"]
MEMBERSHIP_WEIGHTS = [70, 20, 10]


def _roman(name: str) -> str:
    return _ROMAN.get(name, name)


def generate_customer_attrs(user_id: str, sim_start: date) -> dict:
    """Generate supplementary customer attributes for a logged-in user.

    Returns a dict that is merged into the user dict in create_user_pool.
    The customer_id is the same as user_id to ensure cross-table consistency.
    """
    gender    = random.choice(["male", "female"])
    last      = random.choice(LAST_NAMES)
    first     = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
    full_name = f"{last} {first}"

    local_part = f"{_roman(last)}.{_roman(first)}{random.randint(1, 99)}"
    email      = f"{local_part}@{random.choice(EMAIL_DOMAINS)}"

    # Registration 30–1095 days before simulation start
    reg_date = sim_start - timedelta(days=random.randint(30, 1095))

    return {
        "customer_id":       user_id,          # == user_id in GA4 events
        "name":              full_name,
        "email":             email,
        "gender":            gender,
        "age":               random.randint(18, 65),
        "prefecture":        random.choice(PREFECTURES),
        "registration_date": reg_date.isoformat(),
        "membership_rank":   random.choices(MEMBERSHIP_RANKS, MEMBERSHIP_WEIGHTS, k=1)[0],
    }


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def write_customers_csv(users: list[dict], path: Path) -> int:
    """Write customers.csv from the user pool (logged-in users only).

    customer_id == user_id in GA4 events.
    """
    FIELDS = [
        "customer_id", "name", "email", "gender", "age",
        "prefecture", "registration_date", "membership_rank",
    ]
    rows = [u for u in users if u.get("customer_id")]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def write_products_csv(path: Path) -> int:
    """Write products.csv from the product catalog.

    product_id == item_id in GA4 events items[].
    """
    FIELDS = [
        "product_id", "product_name", "brand",
        "category", "category2", "category3",
        "price", "tax_rate", "stock_quantity",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for p in PRODUCTS:
            w.writerow({
                "product_id":     p["item_id"],
                "product_name":   p["item_name"],
                "brand":          p["item_brand"],
                "category":       p["item_category"],
                "category2":      p["item_category2"],
                "category3":      p["item_category3"],
                "price":          int(p["price"]),
                "tax_rate":       0.10,
                "stock_quantity": random.randint(0, 500),
            })
    return len(PRODUCTS)


def write_orders_csv(
    purchases: list[dict],
    refunded_ids: set[str],
    path: Path,
) -> int:
    """Write orders.csv from collected purchase events.

    order_id       == transaction_id in GA4 purchase/refund events.
    customer_id    == user_id in GA4 events (NULL for guest purchases).
    """
    FIELDS = [
        "order_id", "customer_id", "order_date", "order_datetime",
        "status", "subtotal", "coupon_code", "discount_amount",
        "shipping_fee", "shipping_tier", "tax_amount", "total_amount",
        "payment_type", "currency",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for p in purchases:
            status = "refunded" if p["transaction_id"] in refunded_ids else "completed"
            w.writerow({
                "order_id":        p["transaction_id"],
                "customer_id":     p.get("user_id") or "",   # blank = guest
                "order_date":      p["order_datetime"].strftime("%Y-%m-%d"),
                "order_datetime":  p["order_datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                "status":          status,
                "subtotal":        int(p["subtotal"]),
                "coupon_code":     p.get("coupon_code") or "",
                "discount_amount": int(p.get("discount_amount", 0)),
                "shipping_fee":    int(p["shipping_fee"]),
                "shipping_tier":   p["shipping_tier"],
                "tax_amount":      int(p["tax_amount"]),
                "total_amount":    int(p["total_amount"]),
                "payment_type":    p["payment_type"],
                "currency":        p["currency"],
            })
    return len(purchases)


def write_order_items_csv(purchases: list[dict], path: Path) -> int:
    """Write order_items.csv from collected purchase events.

    order_id   == orders.order_id.
    product_id == products.product_id == GA4 items[].item_id.
    """
    FIELDS = [
        "order_item_id", "order_id", "product_id", "product_name",
        "unit_price", "quantity", "discount_amount", "line_total",
    ]
    row_count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for p in purchases:
            for seq, item in enumerate(p["items"], start=1):
                unit_price = int(item["price"])
                qty        = item["quantity"]
                discount   = int(item.get("discount", 0))
                line_total = unit_price * qty - discount
                w.writerow({
                    "order_item_id":  f"{p['transaction_id']}-{seq:02d}",
                    "order_id":       p["transaction_id"],
                    "product_id":     item["item_id"],   # == products.product_id
                    "product_name":   item["item_name"],
                    "unit_price":     unit_price,
                    "quantity":       qty,
                    "discount_amount":discount,
                    "line_total":     line_total,
                })
                row_count += 1
    return row_count

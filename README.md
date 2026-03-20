# ec_demo

> **[日本語版 README はこちら (README_ja.md)](README_ja.md)**

GA4 (Google Analytics 4) ecommerce demo data generator for BigQuery.

## Overview

Generates realistic GA4 BigQuery Export-format ecommerce event data along with relational tables (customers, products, orders, order_items). Designed for development, testing, and demo environments where production data is not available — ideal for validating GA4 data pipelines and prototyping BI dashboards.

## Generated Tables

| Table | File | Format | Columns | Rows (approx.) |
|---|---|---|---|---|
| GA4 events | `output/events_YYYYMMDD.jsonl` | JSONL (daily) | 20 (70+ leaf) | ~3,600/day |
| customers | `output/customers.csv` | CSV | 8 | users x login rate |
| products | `output/products.csv` | CSV | 9 | 20 (fixed) |
| orders | `output/orders.csv` | CSV | 14 | = GA4 purchase events |
| order_items | `output/order_items.csv` | CSV | 8 | orders x avg items |

> Default settings (1,000 users, 31 days): events 113,689 / customers 301 / orders 1,059 / order_items 1,262

### Join Keys

```
customers.customer_id  <->  GA4 events.user_id
                        <->  orders.customer_id

products.product_id    <->  GA4 events.items[].item_id
                        <->  order_items.product_id

orders.order_id        <->  GA4 events.transaction_id (purchase events)
                        <->  order_items.order_id
```

- Events without `user_id` represent anonymous (guest) users — this is expected
- Customers with no events (non-visiting members) are expected
- Customers with no orders (non-purchasing members) are expected

---

## Schema Details

### GA4 events (JSONL, BigQuery Export format)

#### Top-level columns (20)

| Column | Type | NULLABLE | Description |
|---|---|---|---|
| `event_date` | STRING | NO | YYYYMMDD |
| `event_timestamp` | INTEGER | NO | Microseconds UTC |
| `event_name` | STRING | NO | Event name (19 types below) |
| `user_pseudo_id` | STRING | NO | GA4 client ID |
| `user_id` | STRING | YES | Logged-in user ID (null if anonymous) |
| `platform` | STRING | NO | "WEB" (fixed) |
| `stream_id` | STRING | NO | GA4 stream ID |
| `user_first_touch_timestamp` | INTEGER | YES | Microseconds UTC |
| `event_params` | RECORD REPEATED | NO | Event parameters (24 keys below) |
| `user_properties` | RECORD REPEATED | NO | User properties |
| `device` | RECORD | NO | Device information |
| `geo` | RECORD | NO | Geographic information |
| `traffic_source` | RECORD | NO | User first-touch traffic source |
| `collected_traffic_source` | RECORD | YES | Session-level traffic source |
| `session_traffic_source_last_click` | RECORD | YES | Session last-click traffic source |
| `items` | RECORD REPEATED | YES | Product info (ecommerce events only) |
| `ecommerce` | RECORD | YES | Purchase events only |
| `batch_page_id` | INTEGER | YES | Increments per page transition |
| `batch_ordering_id` | INTEGER | YES | Increments per batch |
| `batch_event_index` | INTEGER | YES | Event sequence within a batch |

#### Event Types (19)

| Event Name | Category | Description |
|---|---|---|
| `first_visit` | Auto-collected | User's first visit |
| `session_start` | Auto-collected | Session start |
| `page_view` | Auto-collected | Page view |
| `sign_up` | Recommended | User registration |
| `login` | Recommended | Login |
| `search` | Recommended | Site search |
| `view_promotion` | EC Recommended | Promotion impression |
| `select_promotion` | EC Recommended | Promotion click |
| `view_item_list` | EC Recommended | Product list view |
| `select_item` | EC Recommended | Product list click |
| `view_item` | EC Recommended | Product detail view |
| `add_to_cart` | EC Recommended | Add to cart |
| `remove_from_cart` | EC Recommended | Remove from cart |
| `view_cart` | EC Recommended | Cart view |
| `begin_checkout` | EC Recommended | Checkout start |
| `add_shipping_info` | EC Recommended | Shipping method selection |
| `add_payment_info` | EC Recommended | Payment method selection |
| `purchase` | EC Recommended | Purchase complete |
| `refund` | EC Recommended | Refund (~5% of purchases, 3-14 days later) |

#### event_params Keys (24)

| Key | Value Type | Primary Events |
|---|---|---|
| `ga_session_id` | int | All events |
| `ga_session_number` | int | All events |
| `session_engaged` | int | All events |
| `engagement_time_msec` | int | All events |
| `entrances` | int | session_start, landing page_view |
| `page_location` | string | page_view, view_item |
| `page_title` | string | page_view, view_item |
| `page_referrer` | string | page_view |
| `search_term` | string | search, view_item_list (search results) |
| `item_list_id` | string | view_item_list, select_item |
| `item_list_name` | string | view_item_list, select_item |
| `currency` | string | All ecommerce events |
| `value` | float | All ecommerce events |
| `coupon` | string | begin_checkout through purchase |
| `shipping` | float | add_shipping_info, purchase |
| `shipping_tier` | string | add_shipping_info (standard / express) |
| `tax` | float | purchase |
| `transaction_id` | string | purchase, refund |
| `payment_type` | string | add_payment_info |
| `promotion_id` | string | view_promotion, select_promotion |
| `promotion_name` | string | view_promotion, select_promotion, purchase |
| `creative_name` | string | view_promotion, select_promotion |
| `creative_slot` | string | view_promotion, select_promotion |
| `method` | string | sign_up, login |

#### items columns (17)

| Column | Type | NULLABLE | Notes |
|---|---|---|---|
| `item_id` | STRING | NO | SKU001-SKU020 |
| `item_name` | STRING | NO | |
| `item_brand` | STRING | NO | |
| `item_category` | STRING | NO | |
| `item_category2` | STRING | NO | |
| `item_category3` | STRING | NO | |
| `price` | FLOAT | NO | |
| `quantity` | INTEGER | NO | |
| `index` | INTEGER | YES | Position in list |
| `coupon` | STRING | YES | |
| `discount` | FLOAT | YES | Coupon discount amount |
| `item_list_id` | STRING | YES | view_item_list / select_item only |
| `item_list_name` | STRING | YES | view_item_list / select_item only |
| `promotion_id` | STRING | YES | |
| `promotion_name` | STRING | YES | |
| `creative_name` | STRING | YES | |
| `creative_slot` | STRING | YES | |

#### ecommerce columns (6, purchase events only)

| Column | Type | Description |
|---|---|---|
| `transaction_id` | STRING | |
| `purchase_revenue` | FLOAT | After coupon discount, including shipping |
| `total_item_quantity` | INTEGER | |
| `unique_items` | INTEGER | |
| `shipping_value` | FLOAT | |
| `tax_value` | FLOAT | |

#### device columns (11)

| Column | Type | NULLABLE |
|---|---|---|
| `category` | STRING | NO | mobile / desktop / tablet |
| `operating_system` | STRING | NO | |
| `operating_system_version` | STRING | NO | |
| `language` | STRING | NO | |
| `mobile_brand_name` | STRING | YES | |
| `mobile_model_name` | STRING | YES | |
| `mobile_marketing_name` | STRING | YES | |
| `is_limited_ad_tracking` | STRING | YES | Mobile only |
| `web_info.browser` | STRING | NO | |
| `web_info.browser_version` | STRING | NO | |
| `web_info.hostname` | STRING | NO | |

#### geo columns (5)

`continent` / `sub_continent` / `country` / `region` / `city`

#### traffic_source columns (3, user first-touch)

`source` / `medium` / `name`

#### collected_traffic_source columns (5, session-level)

`manual_source` / `manual_medium` / `manual_campaign_name` / `manual_content` (nullable) / `gclid` (nullable)

#### session_traffic_source_last_click columns (session last-click source)

```
session_traffic_source_last_click
├── manual_campaign
│   ├── source
│   ├── medium
│   ├── campaign_name
│   └── content (nullable)
└── google_ads_campaign (Google CPC only)
    ├── customer_id
    ├── account_name
    ├── campaign_id / campaign_name
    └── ad_group_id / ad_group_name
```

#### batch columns (3, for determining event order)

| Column | Type | Description |
|---|---|---|
| `batch_page_id` | INTEGER | Increments per page transition; events on the same page share the same value |
| `batch_ordering_id` | INTEGER | Increments per batch |
| `batch_event_index` | INTEGER | Event sequence within a batch (0-based) |

> `event_timestamp` is the arrival time at the GA4 server, and multiple events can arrive simultaneously. To determine the correct event order, use `event_timestamp, batch_page_id, batch_ordering_id, batch_event_index` in that priority.

---

### customers (8 columns)

| Column | Type | NULLABLE | Description |
|---|---|---|---|
| `customer_id` | STRING | NO | **= GA4 `user_id`** / **= orders.customer_id** |
| `name` | STRING | NO | Full name (Japanese) |
| `email` | STRING | NO | |
| `gender` | STRING | NO | male / female |
| `age` | INTEGER | NO | 18-65 |
| `prefecture` | STRING | NO | Prefecture |
| `registration_date` | DATE | NO | 30-1,095 days before simulation start |
| `membership_rank` | STRING | NO | regular (70%) / silver (20%) / gold (10%) |

---

### products (9 columns)

| Column | Type | NULLABLE | Description |
|---|---|---|---|
| `product_id` | STRING | NO | **= GA4 `items[].item_id`** / **= order_items.product_id** |
| `product_name` | STRING | NO | |
| `brand` | STRING | NO | |
| `category` | STRING | NO | |
| `category2` | STRING | NO | |
| `category3` | STRING | NO | |
| `price` | INTEGER | NO | JPY (tax-exclusive) |
| `tax_rate` | FLOAT | NO | 0.10 (fixed) |
| `stock_quantity` | INTEGER | NO | 0-500 |

---

### orders (14 columns)

| Column | Type | NULLABLE | Description |
|---|---|---|---|
| `order_id` | STRING | NO | **= GA4 `transaction_id`** / **= order_items.order_id** |
| `customer_id` | STRING | YES | **= customers.customer_id** (blank for guest purchases) |
| `order_date` | DATE | NO | |
| `order_datetime` | TIMESTAMP | NO | |
| `status` | STRING | NO | completed / refunded |
| `subtotal` | INTEGER | NO | Before coupon, excluding shipping |
| `coupon_code` | STRING | YES | |
| `discount_amount` | INTEGER | NO | Coupon discount amount |
| `shipping_fee` | INTEGER | NO | Free for orders >= 5,000 JPY |
| `shipping_tier` | STRING | NO | standard / express |
| `tax_amount` | INTEGER | NO | 10% consumption tax |
| `total_amount` | INTEGER | NO | After discount, including shipping and tax |
| `payment_type` | STRING | NO | credit_card / debit_card / convenience_store / bank_transfer / pay_later |
| `currency` | STRING | NO | JPY (fixed) |

---

### order_items (8 columns)

| Column | Type | NULLABLE | Description |
|---|---|---|---|
| `order_item_id` | STRING | NO | `{order_id}-{sequence}` |
| `order_id` | STRING | NO | **= orders.order_id** |
| `product_id` | STRING | NO | **= products.product_id** |
| `product_name` | STRING | NO | |
| `unit_price` | INTEGER | NO | Tax-exclusive unit price |
| `quantity` | INTEGER | NO | |
| `discount_amount` | INTEGER | NO | Discount for this line item |
| `line_total` | INTEGER | NO | `unit_price * quantity - discount_amount` |

---

## Data Mart Views

View definitions for data marts are stored under `sql/mart/`.

### v_events_flat (Event Flattening View)

A base view that flattens the nested GA4 BigQuery Export structure and enriches each event row with session-level attributes. Downstream marts (session, funnel, revenue, user) should query from this view.

**Key transformations:**

1. Pivots each `event_params` key into individual columns (24 keys)
2. Flattens `device`, `geo`, `traffic_source`, `collected_traffic_source`, `session_traffic_source_last_click`
3. Normalizes NULL-equivalent values (`(not set)`, `(none)`, `(not provided)`, empty string) to NULL — `(direct)` is preserved as-is
4. Assigns `event_sequence_number` within each session using `event_timestamp, batch_page_id, batch_ordering_id, batch_event_index`
5. Attaches session-level attributes to every event row:
   - `session_traffic_source/medium/campaign/content`: latest non-NULL values from `collected_traffic_source`, fetched from the same event row to guarantee cross-field consistency
   - `session_landing_page`: `page_location` where `entrances=1`
   - `session_duration_sec`, `session_has_purchase`, etc.

**File:** `sql/mart/v_events_flat.sql`

---

## Setup and Usage

### 1. Create Virtual Environment and Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate Demo Data

```bash
python generate.py
```

Override period, user count, or seed via command-line options:

```bash
python generate.py --start 2025-01-01 --end 2025-03-31 --users 5000 --seed 123
```

| Option | Default | Description |
|---|---|---|
| `-c`, `--config` | `config.yaml` | Config file path |
| `--start` | config `date_range.start` | Start date (YYYY-MM-DD) |
| `--end` | config `date_range.end` | End date (YYYY-MM-DD) |
| `--users` | config `users.total` | Total user count |
| `--seed` | config `settings.seed` | Random seed |

Generated files:

```
output/
├── events_20250101.jsonl   # GA4 events (daily JSONL)
├── events_20250102.jsonl
├── ...
├── customers.csv
├── products.csv
├── orders.csv
└── order_items.csv
```

### 3. Load into BigQuery

#### Prerequisites

| Item | Description | Example |
|---|---|---|
| GCP Project ID | Project with BigQuery enabled | `my-project-123` |
| Dataset name | Dataset to create (auto-created if missing) | `ec_demo` |
| Location | Dataset region | `asia-northeast1` (Tokyo) / `US` / `EU` |
| Authentication | One of the methods below | - |

#### Authentication

**Option A: gcloud CLI (recommended for local use)**

```bash
# Install gcloud CLI if not already installed
# https://cloud.google.com/sdk/docs/install

gcloud auth application-default login
```

**Option B: Service account key**

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

Required IAM roles for the service account:
- `BigQuery Data Editor` (create/write datasets and tables)
- `BigQuery Job User` (run load jobs)

#### Run the Loader

```bash
python bigquery_load.py \
  --project YOUR_PROJECT_ID \
  --dataset ec_demo \
  --location asia-northeast1
```

With an explicit service account key:

```bash
python bigquery_load.py \
  --project YOUR_PROJECT_ID \
  --dataset ec_demo \
  --location asia-northeast1 \
  --key-file /path/to/service-account-key.json
```

| Option | Default | Description |
|---|---|---|
| `--project` | (required) | GCP project ID |
| `--dataset` | (required) | BigQuery dataset name |
| `--location` | `asia-northeast1` | Dataset location |
| `--output-dir` | `./output` | Directory containing generated files |
| `--key-file` | None (uses ADC) | Path to service account key JSON |

#### Table Layout After Loading

GA4 events are created as date-sharded tables, matching the real GA4 BigQuery Export format.

```
{dataset}/
├── events_20250101     # GA4 events (daily tables)
├── events_20250102
├── ...
├── customers
├── products
├── orders
└── order_items
```

### 4. Create Data Mart Views

After loading tables into BigQuery, create the data mart views.

```bash
# Replace PROJECT_ID.DATASET with your actual values
sed 's/PROJECT_ID\.DATASET/YOUR_PROJECT_ID.ec_demo/g' sql/mart/v_events_flat.sql \
  | bq query --use_legacy_sql=false
```

Alternatively, paste the contents of `sql/mart/v_events_flat.sql` into the BigQuery console and replace `PROJECT_ID.DATASET` manually.

#### Dataset Layout After View Creation

```
{dataset}/
├── events_20250101     # GA4 events (daily tables)
├── events_20250102
├── ...
├── customers
├── products
├── orders
├── order_items
└── v_events_flat       # Event flattening view
```

Verify in the BigQuery console:
`https://console.cloud.google.com/bigquery?project=YOUR_PROJECT_ID`

## Configuration (config.yaml)

```yaml
date_range:
  start: "2025-01-01"
  end: "2025-01-31"

users:
  total: 1000               # Total user pool size
  logged_in_ratio: 0.3      # Ratio of logged-in users
  daily_active_ratio: 0.15  # Daily active user rate
  sessions_per_day_range: [1, 3]

funnel:
  browse_to_view_item: 0.70
  view_item_to_add_to_cart: 0.30
  add_to_cart_to_remove: 0.10
  add_to_cart_to_checkout: 0.60
  checkout_to_purchase: 0.75
  promotion_probability: 0.15

output:
  directory: "./output"

settings:
  stream_id: "1234567890"
  currency: "JPY"
  seed: 42
```

## File Structure

| File | Description |
|---|---|
| `generate.py` | Main entry point |
| `user_journeys.py` | Session and event generation logic |
| `product_catalog.py` | Product master and coupon definitions |
| `tables.py` | CSV table generation (customers / products / orders / order_items) |
| `ga4_schema.py` | GA4 BigQuery Export schema builder |
| `traffic_sources.py` | Traffic source data |
| `device_geo.py` | Device and geographic data |
| `utils.py` | ID generation and timestamp utilities |
| `config.yaml` | Generation parameter settings |
| `bigquery_load.py` | BigQuery loader |
| `sql/mart/v_events_flat.sql` | Event flattening view definition |

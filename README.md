# ec_demo

> **[日本語版 README はこちら (README_ja.md)](README_ja.md)**

Statistically realistic GA4 BigQuery export data — generated, not fabricated.

## Table of Contents

[Why This Exists](#why-this-exists) | [What It Generates](#what-it-generates) | [Realism Features](#realism-features) | [Quick Start](#quick-start) | [Configuration](#configuration-configyaml) | [Schema Reference](#schema-reference) | [File Structure](#file-structure)

---

## Why This Exists

GA4's BigQuery export format is deeply nested and statistically structured. Most synthetic data generators produce flat, uniformly distributed records that look nothing like real ecommerce traffic. The problems that causes are practical:

- **Funnel queries break** when every session has the same conversion probability, because your SQL assumes realistic drop-off rates between stages.
- **Dashboard prototypes mislead** when traffic sources, device types, and purchase amounts are uniformly distributed — every chart looks like a straight line.
- **Schema validation fails** when test data omits the nested fields that real GA4 exports always include (`session_traffic_source_last_click`, `batch_*` columns, `collected_traffic_source`).
- **Event ordering logic is untestable** when events lack the `batch_page_id / batch_ordering_id / batch_event_index` triplet that GA4 uses to sequence simultaneous arrivals.

ec_demo generates synthetic ecommerce events with real behavioral patterns: Pareto-distributed product popularity, user-segment-specific conversion rates, correlated traffic source and landing page assignments, payment failures with retry sequences, and purchase propensity drawn from a Beta distribution rather than a coin flip. The relational tables (customers, products, orders, order_items) join cleanly to the GA4 events via shared keys, so you can test cross-dataset queries without massaging the data first.

The output is JSONL in GA4 BigQuery Export format, loadable with the included `bigquery_load.py` script. It is designed for development, testing, and demo environments where production data is not available.

---

## What It Generates

| Table | File | Format | Columns | Rows (approx.) |
|---|---|---|---|---|
| GA4 events | `output/events_YYYYMMDD.jsonl` | JSONL (daily) | 25 (100+ leaf) | ~4,300/day |
| customers | `output/customers.csv` | CSV | 8 | users x login rate |
| products | `output/products.csv` | CSV | 9 | 80 (fixed) |
| orders | `output/orders.csv` | CSV | 14 | = GA4 purchase events |
| order_items | `output/order_items.csv` | CSV | 8 | orders x avg items |

> Default settings (1,000 users, 31 days): events ~133,000 / customers ~285 / orders ~1,600 / order_items ~1,800

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

## Realism Features

- **User segments** — New / returning / loyal users have different conversion rates
- **Category affinity** — Each user has 1-3 preferred product categories
- **Device-based behavior** — Mobile users have slightly lower conversion rates
- **Day-of-week variation** — Weekend traffic is 20-25% higher than weekdays
- **Hourly distribution** — Peaks at lunch (12h) and evening (20-21h)
- **Campaign spikes** — Configurable campaign periods boost CPC/email traffic
- **Pareto product popularity** — Top 20% of products generate ~80% of views/sales
- **Seasonal products** — Some products are boosted/dampened by month (e.g., fans in summer)
- **Traffic source to landing page correlation** — CPC → sale/LP pages, organic → top page
- **Data quality noise** — 5% null user_id, 2% bot sessions, 8% payment failures with retry
- **Payment failure retry** — Failed checkout attempts generate a realistic `add_payment_info` → failure → retry → `purchase` sequence before the order is recorded
- **Purchase propensity via Beta distribution** — Each user's baseline conversion probability is drawn from Beta(2,5) rather than a fixed rate, producing the long-tail of low-converting users seen in real stores
- **Config validation on startup** — `generate.py` validates `config.yaml` at launch: checks file paths exist and that numeric values are within legal ranges, failing fast with a descriptive error rather than producing invalid data silently
- **EC order to GA4 purchase consistency** — Timestamps, amounts, and items match exactly
- **Realistic identity model** — Multi-device users, shared devices, login-gated `user_id`, and GA4 tracking loss with order preservation. See [docs/IDENTITY_MODEL.md](docs/IDENTITY_MODEL.md) for full specification.

---

## Quick Start

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

Verify in the BigQuery console:
`https://console.cloud.google.com/bigquery?project=YOUR_PROJECT_ID`

---

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
  browse_to_view_item: 0.70       # Base rates (adjusted per segment)
  view_item_to_add_to_cart: 0.30
  add_to_cart_to_remove: 0.10
  add_to_cart_to_checkout: 0.60
  checkout_to_purchase: 0.75
  promotion_probability: 0.15

# Day-of-week traffic multipliers (Mon=0 .. Sun=6)
day_of_week_weights:
  0: 0.90   # Monday
  1: 0.95   # Tuesday
  2: 1.00   # Wednesday
  3: 1.00   # Thursday
  4: 1.10   # Friday
  5: 1.25   # Saturday
  6: 1.20   # Sunday

# Campaign periods: CPC/email traffic boosted during these windows
campaigns:
  - name: "new_year_sale"
    start: "2025-01-01"
    end: "2025-01-03"
    cpc_multiplier: 2.5
    email_multiplier: 1.8

# Data quality noise settings
noise:
  null_user_id_rate: 0.05      # 5% of logged-in user events have null user_id
  bot_session_rate: 0.02       # 2% of sessions are bot-like
  payment_failure_rate: 0.08   # 8% of checkout attempts fail, then retry

output:
  directory: "./output"

settings:
  stream_id: "1234567890"
  currency: "JPY"
  seed: 42
```

---

## Schema Reference

### GA4 events (JSONL, BigQuery Export format)

<details>
<summary>Top-level columns (25)</summary>

| Column | Type | NULLABLE | Description |
|---|---|---|---|
| `event_date` | STRING | NO | YYYYMMDD |
| `event_timestamp` | INTEGER | NO | Microseconds UTC |
| `event_name` | STRING | NO | Event name (19 types below) |
| `event_value_in_usd` | FLOAT | YES | Event value converted to USD |
| `event_bundle_sequence_id` | INTEGER | YES | Bundle sequence ID |
| `event_server_timestamp_offset` | INTEGER | YES | Server timestamp offset (microseconds) |
| `user_pseudo_id` | STRING | NO | GA4 client ID |
| `user_id` | STRING | YES | Logged-in user ID (null if anonymous) |
| `is_active_user` | BOOLEAN | YES | Whether the user was active |
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
| `privacy_info` | RECORD | YES | Consent mode status |
| `batch_page_id` | INTEGER | YES | Increments per page transition |
| `batch_ordering_id` | INTEGER | YES | Increments per batch |
| `batch_event_index` | INTEGER | YES | Event sequence within a batch |

</details>

<details>
<summary>Event Types (19)</summary>

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

</details>

<details>
<summary>event_params Keys (24)</summary>

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

</details>

<details>
<summary>items columns (25)</summary>

| Column | Type | NULLABLE | Notes |
|---|---|---|---|
| `item_id` | STRING | NO | SKU001-SKU080 |
| `item_name` | STRING | NO | |
| `item_brand` | STRING | NO | |
| `item_variant` | STRING | YES | |
| `item_category` | STRING | NO | |
| `item_category2` | STRING | NO | |
| `item_category3` | STRING | NO | |
| `item_category4` | STRING | YES | |
| `item_category5` | STRING | YES | |
| `price` | FLOAT | NO | |
| `price_in_usd` | FLOAT | YES | USD-converted price |
| `quantity` | INTEGER | NO | |
| `item_revenue` | FLOAT | YES | Revenue for purchase events |
| `item_revenue_in_usd` | FLOAT | YES | USD-converted item revenue |
| `index` | INTEGER | YES | Position in list |
| `coupon` | STRING | YES | |
| `discount` | FLOAT | YES | Coupon discount amount |
| `item_list_id` | STRING | YES | view_item_list / select_item only |
| `item_list_name` | STRING | YES | view_item_list / select_item only |
| `promotion_id` | STRING | YES | |
| `promotion_name` | STRING | YES | |
| `creative_name` | STRING | YES | |
| `creative_slot` | STRING | YES | |
| `location_id` | STRING | YES | |
| `item_params` | RECORD REPEATED | YES | Custom item parameters |

</details>

<details>
<summary>ecommerce columns (9, purchase events only)</summary>

| Column | Type | Description |
|---|---|---|
| `transaction_id` | STRING | |
| `purchase_revenue` | FLOAT | After coupon discount, including shipping |
| `purchase_revenue_in_usd` | FLOAT | USD-converted purchase revenue |
| `refund_value` | FLOAT | Refund amount (refund events only) |
| `refund_value_in_usd` | FLOAT | USD-converted refund value |
| `shipping_value` | FLOAT | |
| `tax_value` | FLOAT | |
| `total_item_quantity` | INTEGER | |
| `unique_items` | INTEGER | |

</details>

<details>
<summary>device columns (12)</summary>

| Column | Type | NULLABLE | Notes |
|---|---|---|---|
| `category` | STRING | NO | mobile / desktop / tablet |
| `operating_system` | STRING | NO | |
| `operating_system_version` | STRING | NO | |
| `language` | STRING | NO | |
| `mobile_brand_name` | STRING | YES | |
| `mobile_model_name` | STRING | YES | |
| `mobile_marketing_name` | STRING | YES | |
| `is_limited_ad_tracking` | STRING | YES | Mobile only |
| `advertising_id` | STRING | YES | |
| `web_info.browser` | STRING | NO | |
| `web_info.browser_version` | STRING | NO | |
| `web_info.hostname` | STRING | NO | |

</details>

<details>
<summary>geo, traffic_source, collected_traffic_source columns</summary>

**geo columns (6)**

`continent` / `sub_continent` / `country` / `region` / `city` / `metro`

**traffic_source columns (3, user first-touch)**

`source` / `medium` / `name`

**collected_traffic_source columns (11, session-level)**

`manual_source` / `manual_medium` / `manual_campaign_name` / `manual_content` (nullable) / `manual_term` (nullable) / `gclid` (nullable) / `dclid` (nullable) / `srsltid` (nullable) / `manual_source_platform` (nullable) / `manual_creative_format` (nullable) / `manual_marketing_tactic` (nullable)

</details>

<details>
<summary>session_traffic_source_last_click (session last-click source)</summary>

```
session_traffic_source_last_click
├── manual_campaign
│   ├── source
│   ├── medium
│   ├── campaign_name
│   ├── content (nullable)
│   ├── term (nullable)
│   ├── source_platform (nullable)
│   ├── creative_format (nullable)
│   └── marketing_tactic (nullable)
├── google_ads_campaign (Google CPC only)
│   ├── customer_id / account_name
│   ├── campaign_id / campaign_name
│   └── ad_group_id / ad_group_name
├── cross_channel_campaign (nullable)
│   ├── campaign_name / source / medium
│   └── source_platform
├── sa360_campaign (nullable)
│   ├── campaign_id / campaign_name
│   ├── ad_group_id / ad_group_name
│   ├── keyword_text
│   └── engine_account_name / engine_account_type / manager_account_name
├── cm360_campaign (nullable)
│   ├── campaign_id / campaign_name
│   ├── account_id / account_name
│   ├── advertiser_id / advertiser_name
│   ├── placement_id / placement_name
│   └── site_id / source_type
└── dv360_campaign (nullable)
    ├── campaign_id / campaign_name
    ├── advertiser_id / advertiser_name
    ├── creative_id / creative_name
    ├── exchange_id / exchange_name
    ├── insertion_order_id / insertion_order_name
    ├── line_item_id / line_item_name
    ├── partner_id / partner_name
    └── site_id
```

</details>

<details>
<summary>privacy_info and batch columns</summary>

**privacy_info columns (3)**

| Column | Type | Description |
|---|---|---|
| `ads_storage` | STRING | Consent status for ad storage (Yes/No) |
| `analytics_storage` | STRING | Consent status for analytics storage (Yes/No) |
| `uses_transient_token` | STRING | Whether transient token is used (Yes/No) |

**batch columns (3, for determining event order)**

| Column | Type | Description |
|---|---|---|
| `batch_page_id` | INTEGER | Increments per page transition; events on the same page share the same value |
| `batch_ordering_id` | INTEGER | Increments per batch |
| `batch_event_index` | INTEGER | Event sequence within a batch (0-based) |

> `event_timestamp` is the arrival time at the GA4 server, and multiple events can arrive simultaneously. To determine the correct event order, use `event_timestamp, batch_page_id, batch_ordering_id, batch_event_index` in that priority.

</details>

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

## File Structure

```
ec_demo/
├── generate.py                      # Entry point (wrapper)
├── bigquery_load.py                 # BigQuery loader (wrapper)
├── config.yaml                      # Generation parameters
├── requirements.txt
├── README.md / README_ja.md
│
├── src/                             # Python source modules
│   ├── generate.py                  # Main generation logic
│   ├── identity.py                  # Person-Device model, SessionIdentity
│   ├── user_journeys.py             # Session and event simulation
│   ├── product_catalog.py           # Product master and coupons
│   ├── tables.py                    # CSV table generation
│   ├── ga4_schema.py                # GA4 BigQuery Export schema builder
│   ├── traffic_sources.py           # Traffic source data
│   ├── device_geo.py                # Device and geographic data
│   ├── utils.py                     # ID generation, timestamp utilities
│   └── bigquery_load.py             # BigQuery loader implementation
│
├── tests/                           # Unit and integration tests (pytest)
│   ├── test_identity.py             # Identity module tests
│   └── test_invariants.py           # 5 invariants + noise + consistency
│
├── docs/                            # Documentation
│   ├── IDENTITY_MODEL.md            # Identity model spec (EN)
│   ├── IDENTITY_MODEL_ja.md         # Identity model spec (JA)
│   └── schema_ga4_latest.json       # GA4 schema reference
```

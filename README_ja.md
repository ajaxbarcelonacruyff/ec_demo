# ec_demo

> **[English README is here (README.md)](README.md)**

GA4（Google Analytics 4）の EC（eコマース）デモデータを生成するプロジェクトです。

## プロジェクトの目的・概要

BigQuery 上の GA4 eコマースイベントデータを模したデモデータを生成します。開発・テスト・デモ環境で、本番データを使わずに GA4 データパイプラインの検証や BI ダッシュボードのプロトタイピングを行うことを目的としています。

## 生成されるテーブル一覧

| テーブル | ファイル | 形式 | カラム数 | レコード数（目安）|
|---|---|---|---|---|
| GA4 events | `output/events_YYYYMMDD.jsonl` | JSONL（日別） | 20列（リーフ展開70列超） | 約3,600行/日 |
| customers | `output/customers.csv` | CSV | 8列 | ユーザー数 × ログイン率 |
| products | `output/products.csv` | CSV | 9列 | 20行（固定） |
| orders | `output/orders.csv` | CSV | 14列 | GA4 purchase イベント数と一致 |
| order_items | `output/order_items.csv` | CSV | 8列 | 注文数 × 平均購入点数 |

> デフォルト設定（1,000ユーザー・31日間）の実行例：events 113,689行 / customers 301行 / orders 1,059行 / order_items 1,262行

### テーブル間の結合キー

```
customers.customer_id  <->  GA4 events.user_id
                        <->  orders.customer_id

products.product_id    <->  GA4 events.items[].item_id
                        <->  order_items.product_id

orders.order_id        <->  GA4 events.transaction_id（purchaseイベント）
                        <->  order_items.order_id
```

- GA4 events に `user_id` がない行は匿名ユーザー（ゲスト）によるアクセスで正常
- customers に登録はあるが GA4 events に現れないユーザー（未訪問会員）も正常
- customers に登録はあるが orders に現れないユーザー（未購入会員）も正常

---

## スキーマ詳細

### GA4 events（JSONL・BigQuery Export 形式）

#### トップレベル列（20列）

| カラム | 型 | NULLABLE | 説明 |
|---|---|---|---|
| `event_date` | STRING | NO | YYYYMMDD |
| `event_timestamp` | INTEGER | NO | マイクロ秒 UTC |
| `event_name` | STRING | NO | イベント名（下記19種） |
| `user_pseudo_id` | STRING | NO | GA4 クライアントID |
| `user_id` | STRING | YES | ログインユーザーID（未ログインは null） |
| `platform` | STRING | NO | "WEB" 固定 |
| `stream_id` | STRING | NO | GA4 ストリームID |
| `user_first_touch_timestamp` | INTEGER | YES | マイクロ秒 UTC |
| `event_params` | RECORD REPEATED | NO | イベントパラメータ（下記24種） |
| `user_properties` | RECORD REPEATED | NO | ユーザープロパティ |
| `device` | RECORD | NO | デバイス情報 |
| `geo` | RECORD | NO | 地理情報 |
| `traffic_source` | RECORD | NO | ユーザー初回流入元 |
| `collected_traffic_source` | RECORD | YES | セッション単位の流入元 |
| `session_traffic_source_last_click` | RECORD | YES | セッションのラストクリック流入元 |
| `items` | RECORD REPEATED | YES | 商品情報（ecommerce イベントのみ） |
| `ecommerce` | RECORD | YES | purchase イベントのみ |
| `batch_page_id` | INTEGER | YES | ページ遷移ごとにインクリメント |
| `batch_ordering_id` | INTEGER | YES | バッチごとにインクリメント |
| `batch_event_index` | INTEGER | YES | バッチ内のイベント連番 |

#### イベント種別（19種）

| イベント名 | 分類 | 説明 |
|---|---|---|
| `first_visit` | 自動収集 | ユーザーの初回訪問 |
| `session_start` | 自動収集 | セッション開始 |
| `page_view` | 自動収集 | ページ表示 |
| `sign_up` | 推奨 | 会員登録 |
| `login` | 推奨 | ログイン |
| `search` | 推奨 | サイト内検索 |
| `view_promotion` | EC推奨 | プロモーション表示 |
| `select_promotion` | EC推奨 | プロモーションクリック |
| `view_item_list` | EC推奨 | 商品一覧表示 |
| `select_item` | EC推奨 | 商品一覧からクリック |
| `view_item` | EC推奨 | 商品詳細表示 |
| `add_to_cart` | EC推奨 | カートに追加 |
| `remove_from_cart` | EC推奨 | カートから削除 |
| `view_cart` | EC推奨 | カート表示 |
| `begin_checkout` | EC推奨 | チェックアウト開始 |
| `add_shipping_info` | EC推奨 | 配送方法選択 |
| `add_payment_info` | EC推奨 | 支払方法選択 |
| `purchase` | EC推奨 | 購入完了 |
| `refund` | EC推奨 | 返金（購入の約5%が3〜14日後） |

#### event_params キー（24種）

| key | value型 | 主な対象イベント |
|---|---|---|
| `ga_session_id` | int | 全イベント |
| `ga_session_number` | int | 全イベント |
| `session_engaged` | int | 全イベント |
| `engagement_time_msec` | int | 全イベント |
| `entrances` | int | session_start、ランディング page_view |
| `page_location` | string | page_view、view_item |
| `page_title` | string | page_view、view_item |
| `page_referrer` | string | page_view |
| `search_term` | string | search、view_item_list（検索結果） |
| `item_list_id` | string | view_item_list、select_item |
| `item_list_name` | string | view_item_list、select_item |
| `currency` | string | ecommerce イベント全般 |
| `value` | float | ecommerce イベント全般 |
| `coupon` | string | begin_checkout〜purchase |
| `shipping` | float | add_shipping_info、purchase |
| `shipping_tier` | string | add_shipping_info（standard / express） |
| `tax` | float | purchase |
| `transaction_id` | string | purchase、refund |
| `payment_type` | string | add_payment_info |
| `promotion_id` | string | view_promotion、select_promotion |
| `promotion_name` | string | view_promotion、select_promotion、purchase |
| `creative_name` | string | view_promotion、select_promotion |
| `creative_slot` | string | view_promotion、select_promotion |
| `method` | string | sign_up、login |

#### items 列（17列）

| カラム | 型 | NULLABLE | 備考 |
|---|---|---|---|
| `item_id` | STRING | NO | SKU001〜SKU020 |
| `item_name` | STRING | NO | |
| `item_brand` | STRING | NO | |
| `item_category` | STRING | NO | |
| `item_category2` | STRING | NO | |
| `item_category3` | STRING | NO | |
| `price` | FLOAT | NO | |
| `quantity` | INTEGER | NO | |
| `index` | INTEGER | YES | リスト内表示順 |
| `coupon` | STRING | YES | |
| `discount` | FLOAT | YES | クーポン割引額 |
| `item_list_id` | STRING | YES | view_item_list / select_item のみ |
| `item_list_name` | STRING | YES | view_item_list / select_item のみ |
| `promotion_id` | STRING | YES | |
| `promotion_name` | STRING | YES | |
| `creative_name` | STRING | YES | |
| `creative_slot` | STRING | YES | |

#### ecommerce 列（6列、purchase イベントのみ）

| カラム | 型 | 説明 |
|---|---|---|
| `transaction_id` | STRING | |
| `purchase_revenue` | FLOAT | クーポン割引後・送料込み |
| `total_item_quantity` | INTEGER | |
| `unique_items` | INTEGER | |
| `shipping_value` | FLOAT | |
| `tax_value` | FLOAT | |

#### device 列（11列）

| カラム | 型 | NULLABLE |
|---|---|---|
| `category` | STRING | NO | mobile / desktop / tablet |
| `operating_system` | STRING | NO | |
| `operating_system_version` | STRING | NO | |
| `language` | STRING | NO | |
| `mobile_brand_name` | STRING | YES | |
| `mobile_model_name` | STRING | YES | |
| `mobile_marketing_name` | STRING | YES | |
| `is_limited_ad_tracking` | STRING | YES | モバイルのみ |
| `web_info.browser` | STRING | NO | |
| `web_info.browser_version` | STRING | NO | |
| `web_info.hostname` | STRING | NO | |

#### geo 列（5列）

`continent` / `sub_continent` / `country` / `region` / `city`

#### traffic_source 列（3列、ユーザー初回流入）

`source` / `medium` / `name`

#### collected_traffic_source 列（5列、セッション単位）

`manual_source` / `manual_medium` / `manual_campaign_name` / `manual_content`（nullable）/ `gclid`（nullable）

#### session_traffic_source_last_click 列（セッションのラストクリック流入元）

```
session_traffic_source_last_click
├── manual_campaign
│   ├── source
│   ├── medium
│   ├── campaign_name
│   └── content（nullable）
└── google_ads_campaign（Google CPC の場合のみ）
    ├── customer_id
    ├── account_name
    ├── campaign_id / campaign_name
    └── ad_group_id / ad_group_name
```

#### batch 列（3列、イベント発生順の判定に使用）

| カラム | 型 | 説明 |
|---|---|---|
| `batch_page_id` | INTEGER | ページ遷移ごとにインクリメント。同一ページ内のイベントは同じ値 |
| `batch_ordering_id` | INTEGER | バッチごとにインクリメント |
| `batch_event_index` | INTEGER | バッチ内のイベント連番（0始まり） |

> `event_timestamp` はGA4サーバーへの到達時刻であり、同時到着するケースがあるため、イベントの発生順の判定には `event_timestamp, batch_page_id, batch_ordering_id, batch_event_index` の順で使用する。

---

### customers（8列）

| カラム | 型 | NULLABLE | 説明 |
|---|---|---|---|
| `customer_id` | STRING | NO | **= GA4 `user_id`** / **= orders.customer_id** |
| `name` | STRING | NO | 氏名（日本語） |
| `email` | STRING | NO | |
| `gender` | STRING | NO | male / female |
| `age` | INTEGER | NO | 18〜65 |
| `prefecture` | STRING | NO | 都道府県 |
| `registration_date` | DATE | NO | シミュレーション開始の30〜1095日前 |
| `membership_rank` | STRING | NO | regular（70%）/ silver（20%）/ gold（10%） |

---

### products（9列）

| カラム | 型 | NULLABLE | 説明 |
|---|---|---|---|
| `product_id` | STRING | NO | **= GA4 `items[].item_id`** / **= order_items.product_id** |
| `product_name` | STRING | NO | |
| `brand` | STRING | NO | |
| `category` | STRING | NO | |
| `category2` | STRING | NO | |
| `category3` | STRING | NO | |
| `price` | INTEGER | NO | 円（税抜） |
| `tax_rate` | FLOAT | NO | 0.10 固定 |
| `stock_quantity` | INTEGER | NO | 0〜500 |

---

### orders（14列）

| カラム | 型 | NULLABLE | 説明 |
|---|---|---|---|
| `order_id` | STRING | NO | **= GA4 `transaction_id`** / **= order_items.order_id** |
| `customer_id` | STRING | YES | **= customers.customer_id**（ゲスト購入は空白） |
| `order_date` | DATE | NO | |
| `order_datetime` | TIMESTAMP | NO | |
| `status` | STRING | NO | completed / refunded |
| `subtotal` | INTEGER | NO | クーポン適用前・送料除く |
| `coupon_code` | STRING | YES | |
| `discount_amount` | INTEGER | NO | クーポン割引額 |
| `shipping_fee` | INTEGER | NO | 5,000円以上で0円 |
| `shipping_tier` | STRING | NO | standard / express |
| `tax_amount` | INTEGER | NO | 消費税10% |
| `total_amount` | INTEGER | NO | 割引後・送料・税込み |
| `payment_type` | STRING | NO | credit_card / debit_card / convenience_store / bank_transfer / pay_later |
| `currency` | STRING | NO | JPY 固定 |

---

### order_items（8列）

| カラム | 型 | NULLABLE | 説明 |
|---|---|---|---|
| `order_item_id` | STRING | NO | `{order_id}-{連番}` |
| `order_id` | STRING | NO | **= orders.order_id** |
| `product_id` | STRING | NO | **= products.product_id** |
| `product_name` | STRING | NO | |
| `unit_price` | INTEGER | NO | 税抜単価 |
| `quantity` | INTEGER | NO | |
| `discount_amount` | INTEGER | NO | 当該明細の割引額 |
| `line_total` | INTEGER | NO | `unit_price * quantity - discount_amount` |

---

## データマートビュー

`sql/mart/` 配下にデータマート用のビュー定義SQLを格納しています。

### v_events_flat（イベントフラット化ビュー）

GA4 BigQuery Export のネスト構造をフラット化し、セッション単位の情報を付与した基盤ビューです。後続のセッションマート・ファネルマート・売上マート等はこのビューを `FROM` して作成します。

**主な処理:**

1. `event_params` の各キーを個別カラムに展開（24キー）
2. `device`, `geo`, `traffic_source`, `collected_traffic_source`, `session_traffic_source_last_click` をフラット化
3. NULL同等値（`(not set)`, `(none)`, `(not provided)`, 空文字列）を NULL に正規化（`(direct)` はそのまま保持）
4. セッション内イベント発生順（`event_sequence_number`）を `event_timestamp, batch_page_id, batch_ordering_id, batch_event_index` で判定
5. セッションレベル属性を全イベント行に付与:
   - `session_traffic_source/medium/campaign/content`: `collected_traffic_source` の直近の非NULL値（source/medium/campaign/content を同一イベントから取得し整合性を保証）
   - `session_landing_page`: `entrances=1` の `page_location`
   - `session_duration_sec`, `session_has_purchase` 等

**ファイル:** `sql/mart/v_events_flat.sql`

---

## セットアップと実行

### 1. 仮想環境の作成・依存ライブラリのインストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. デモデータの生成

```bash
python generate.py
```

オプションで期間・ユーザー数・シードを上書きできます。

```bash
python generate.py --start 2025-01-01 --end 2025-03-31 --users 5000 --seed 123
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `-c`, `--config` | `config.yaml` | 設定ファイルパス |
| `--start` | config の `date_range.start` | 開始日（YYYY-MM-DD） |
| `--end` | config の `date_range.end` | 終了日（YYYY-MM-DD） |
| `--users` | config の `users.total` | ユーザー総数 |
| `--seed` | config の `settings.seed` | 乱数シード |

実行後に以下のファイルが生成されます。

```
output/
├── events_20250101.jsonl   # GA4 events（日別 JSONL）
├── events_20250102.jsonl
├── ...
├── customers.csv
├── products.csv
├── orders.csv
└── order_items.csv
```

### 3. BigQuery へのロード

#### 必要なもの

| 項目 | 説明 | 例 |
|---|---|---|
| GCP プロジェクト ID | BigQuery を利用するプロジェクト | `my-project-123` |
| データセット名 | 作成するデータセット（存在しない場合は自動作成） | `ec_demo` |
| ロケーション | データセットのリージョン | `asia-northeast1`（東京）/ `US` / `EU` |
| 認証 | 下記のいずれか | - |

#### 認証の設定

**方法 A: gcloud CLI（ローカル実行推奨）**

```bash
# gcloud CLI のインストールがまだの場合
# https://cloud.google.com/sdk/docs/install

gcloud auth application-default login
```

**方法 B: サービスアカウントキー**

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

サービスアカウントに必要な IAM ロール：
- `BigQuery Data Editor`（データセット・テーブルの作成・書き込み）
- `BigQuery Job User`（ロードジョブの実行）

#### ロード実行

```bash
python bigquery_load.py \
  --project YOUR_PROJECT_ID \
  --dataset ec_demo \
  --location asia-northeast1
```

サービスアカウントキーを明示する場合：

```bash
python bigquery_load.py \
  --project YOUR_PROJECT_ID \
  --dataset ec_demo \
  --location asia-northeast1 \
  --key-file /path/to/service-account-key.json
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--project` | （必須） | GCP プロジェクト ID |
| `--dataset` | （必須） | BigQuery データセット名 |
| `--location` | `asia-northeast1` | データセットのロケーション |
| `--output-dir` | `./output` | 生成ファイルのディレクトリ |
| `--key-file` | なし（ADC使用） | サービスアカウントキーのパス |

#### ロード後のテーブル構成

GA4 events は実際の GA4 BigQuery Export と同じ日付シャーディング形式で作成されます。

```
{dataset}/
├── events_20250101     # GA4 events（日別テーブル）
├── events_20250102
├── ...
├── customers
├── products
├── orders
└── order_items
```

### 4. データマートビューの作成

BigQuery にテーブルをロードした後、データマートビューを作成します。

```bash
# PROJECT_ID.DATASET を実際の値に置換して実行
sed 's/PROJECT_ID\.DATASET/YOUR_PROJECT_ID.ec_demo/g' sql/mart/v_events_flat.sql \
  | bq query --use_legacy_sql=false
```

または BigQuery コンソールで `sql/mart/v_events_flat.sql` の内容を貼り付け、`PROJECT_ID.DATASET` を置換して実行してください。

#### ビュー作成後のデータセット構成

```
{dataset}/
├── events_20250101     # GA4 events（日別テーブル）
├── events_20250102
├── ...
├── customers
├── products
├── orders
├── order_items
└── v_events_flat       # イベントフラット化ビュー
```

BigQuery コンソールで確認：
`https://console.cloud.google.com/bigquery?project=YOUR_PROJECT_ID`

## 設定ファイル（config.yaml）

```yaml
date_range:
  start: "2025-01-01"
  end: "2025-01-31"

users:
  total: 1000               # ユーザープール総数
  logged_in_ratio: 0.3      # ログインユーザーの割合
  daily_active_ratio: 0.15  # 1日あたりのアクティブユーザー率
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

## ファイル構成

| ファイル | 説明 |
|---|---|
| `generate.py` | メインエントリーポイント |
| `user_journeys.py` | セッション・イベント生成ロジック |
| `product_catalog.py` | 商品マスタ・クーポン定義 |
| `tables.py` | CSV テーブル生成（customers / products / orders / order_items） |
| `ga4_schema.py` | GA4 BigQuery Export スキーマのビルダー |
| `traffic_sources.py` | 流入元データ |
| `device_geo.py` | デバイス・地理データ |
| `utils.py` | ID生成・タイムスタンプ変換ユーティリティ |
| `config.yaml` | 生成パラメータ設定 |
| `bigquery_load.py` | BigQuery ローダー |
| `sql/mart/v_events_flat.sql` | イベントフラット化ビュー定義 |

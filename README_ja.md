# ec_demo

> **[English version here](README.md)**

統計的にリアルな GA4 BigQuery エクスポートデータを生成するプロジェクト。作為的なデータではなく、実際の行動パターンに基づいて生成します。

## 目次

[このプロジェクトが必要な理由](#このプロジェクトが必要な理由) | [生成されるデータ](#生成されるデータ) | [リアリズム機能](#リアリズム機能) | [クイックスタート](#クイックスタート) | [設定ファイル (config.yaml)](#設定ファイル-configyaml) | [スキーマ詳細](#スキーマ詳細) | [データマートビュー](#データマートビュー) | [ファイル構成](#ファイル構成)

---

## このプロジェクトが必要な理由

GA4 の BigQuery エクスポート形式は、深くネストされた構造を持ち、統計的な特性が実際のトラフィックパターンに基づいています。一般的なダミーデータ生成ツールが出力するフラットで均一なレコードは、実際の EC サイトのデータとはかけ離れています。その弊害は実務上の問題として現れます。

- **ファネルクエリが壊れる** — セッションごとのコンバージョン率が一定だと、実際のドロップオフ率を前提とした SQL がまったく機能しません。
- **ダッシュボードプロトタイプが実態を反映しない** — トラフィックソース・デバイス種別・購入金額が均一分布だと、あらゆるグラフが単調な直線になります。
- **スキーマバリデーションが失敗する** — 実際の GA4 エクスポートに常に含まれるネストフィールド（`session_traffic_source_last_click`、`batch_*` 列、`collected_traffic_source`）がないと、テストが通りません。
- **イベント順序のロジックがテストできない** — GA4 が同時到着イベントの順序付けに使用する `batch_page_id / batch_ordering_id / batch_event_index` のトリプレットがないと、検証不可能です。

ec_demo は、実際の行動パターンに基づいた合成 EC イベントを生成します。パレート分布に従う商品人気度、ユーザーセグメント別のコンバージョン率、流入元とランディングページの相関、決済失敗とリトライシーケンス、コインフリップではなくベータ分布から引いた購買傾向、などがその例です。リレーショナルテーブル（customers、products、orders、order_items）は共通キーで GA4 イベントと結合できるため、データを加工せずにクロスデータセットクエリをテストできます。

出力は GA4 BigQuery Export 形式の JSONL ファイルで、付属の `bigquery_load.py` スクリプトで読み込めます。本番データが使えない開発・テスト・デモ環境向けに設計されています。

---

## 生成されるデータ

| テーブル | ファイル | 形式 | カラム数 | レコード数（目安） |
|---|---|---|---|---|
| GA4 events | `output/events_YYYYMMDD.jsonl` | JSONL（日別） | 25列（リーフ展開100列超） | 約4,300行/日 |
| customers | `output/customers.csv` | CSV | 8列 | ユーザー数 x ログイン率 |
| products | `output/products.csv` | CSV | 9列 | 80行（固定） |
| orders | `output/orders.csv` | CSV | 14列 | GA4 purchase イベント数と一致 |
| order_items | `output/order_items.csv` | CSV | 8列 | 注文数 x 平均購入点数 |

> デフォルト設定（1,000ユーザー・31日間）の実行例：events 約133,000行 / customers 約285行 / orders 約1,600行 / order_items 約1,800行

### テーブル間の結合キー

```
customers.customer_id  <->  GA4 events.user_id
                        <->  orders.customer_id

products.product_id    <->  GA4 events.items[].item_id
                        <->  order_items.product_id

orders.order_id        <->  GA4 events.transaction_id (purchase events)
                        <->  order_items.order_id
```

- `user_id` がない GA4 イベント行は匿名（ゲスト）ユーザーによるアクセスで正常です
- customers に登録はあるが GA4 events に現れないユーザー（未訪問会員）も正常です
- customers に登録はあるが orders に現れないユーザー（未購入会員）も正常です

---

## リアリズム機能

- **ユーザーセグメント** — 新規 / リピーター / ロイヤルユーザーでコンバージョン率が異なる
- **カテゴリ親和性** — ユーザーごとに1〜3個の好みカテゴリを保持
- **デバイス別行動差** — モバイルユーザーはコンバージョン率がやや低い
- **曜日変動** — 週末はトラフィックが20〜25%増加
- **時間帯分布** — 昼休み（12時台）と夜間（20〜21時台）にピーク
- **キャンペーンスパイク** — 設定期間中に CPC / メール流入が急増
- **パレート分布の商品人気** — 上位20%の商品が閲覧・売上の約80%を占める
- **季節商品** — 月に応じた商品ウェイト変動（夏に扇風機、冬に加湿器など）
- **流入元とランディングページの相関** — CPC はセール/LP、organic はトップページへ
- **データ品質ノイズ** — 5%の user_id 欠損、2%の bot 的セッション、8%の決済エラー→リトライ
- **決済失敗リトライ** — チェックアウト失敗時に `add_payment_info` → 失敗 → リトライ → `purchase` の現実的なシーケンスを生成し、注文として記録
- **ベータ分布による購買傾向** — ユーザーの基本コンバージョン確率は固定レートではなく Beta(2,5) から引かれ、実際のストアで見られる低コンバージョンユーザーのロングテールを再現
- **起動時の設定バリデーション** — `generate.py` は起動時に `config.yaml` を検証。ファイルパスの存在確認と数値の範囲チェックを行い、不正なデータをサイレントに生成する代わりに明確なエラーメッセージで即時終了
- **EC 受注データと GA4 purchase の完全一致** — タイムスタンプ・金額・商品が完全に一致

---

## クイックスタート

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

コマンドラインオプションで期間・ユーザー数・シードを上書きできます。

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

### 3. スキーマの移行（任意）

古いスキーマで生成した既存の出力がある場合、`migrate_schema.py` を使って再生成せずに新しい GA4 フィールドを追加できます。

```bash
python migrate_schema.py --input-dir output --output-dir output_v2
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--input-dir` | `output` | 既存の JSONL ファイルが含まれるディレクトリ |
| `--output-dir` | `output_v2` | 移行後のファイルを出力するディレクトリ |

データ損失を防ぐため、入力ディレクトリと出力ディレクトリは異なる場所を指定してください。同一ディレクトリへの上書きは拒否されます。

セッション内のイベント順序が正しくない場合（タイムスタンプが同一のイベントがある場合）は、`fix_event_order.py` を使用してください。

```bash
python fix_event_order.py --input-dir output --output-dir output_fixed
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--input-dir` | `output` | 既存の JSONL ファイルが含まれるディレクトリ |
| `--output-dir` | `output_fixed` | 並び替え後のファイルを出力するディレクトリ |

入力ディレクトリと出力ディレクトリは異なる場所を指定してください。

### 4. BigQuery へのロード

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
| `--key-file` | なし（ADC 使用） | サービスアカウントキーのパス |

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

### 5. データマートビューの作成

BigQuery にテーブルをロードした後、データマートビューを作成します。

```bash
# PROJECT_ID.DATASET を実際の値に置換して実行
sed 's/PROJECT_ID\.DATASET/YOUR_PROJECT_ID.ec_demo/g' sql/mart/v_events_flat.sql \
  | bq query --use_legacy_sql=false
```

または BigQuery コンソールで `sql/mart/v_events_flat.sql` の内容を貼り付け、`PROJECT_ID.DATASET` を手動で置換して実行してください。

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

---

## 設定ファイル (config.yaml)

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
  browse_to_view_item: 0.70       # 基本ファネル率（セグメントで自動調整）
  view_item_to_add_to_cart: 0.30
  add_to_cart_to_remove: 0.10
  add_to_cart_to_checkout: 0.60
  checkout_to_purchase: 0.75
  promotion_probability: 0.15

# 曜日別トラフィック係数（月=0 .. 日=6）
day_of_week_weights:
  0: 0.90   # 月曜
  1: 0.95   # 火曜
  2: 1.00   # 水曜
  3: 1.00   # 木曜
  4: 1.10   # 金曜
  5: 1.25   # 土曜
  6: 1.20   # 日曜

# キャンペーン期間：CPC/メール流入が増加
campaigns:
  - name: "new_year_sale"
    start: "2025-01-01"
    end: "2025-01-03"
    cpc_multiplier: 2.5
    email_multiplier: 1.8

# データ品質ノイズ設定
noise:
  null_user_id_rate: 0.05      # ログインユーザーの5%で user_id が null
  bot_session_rate: 0.02       # 2%のセッションがbot的挙動
  payment_failure_rate: 0.08   # 8%のチェックアウトで決済エラー→リトライ

output:
  directory: "./output"

settings:
  stream_id: "1234567890"
  currency: "JPY"
  seed: 42
```

---

## スキーマ詳細

### GA4 events（JSONL・BigQuery Export 形式）

<details>
<summary>トップレベル列（25列）</summary>

| カラム | 型 | NULLABLE | 説明 |
|---|---|---|---|
| `event_date` | STRING | NO | YYYYMMDD |
| `event_timestamp` | INTEGER | NO | マイクロ秒 UTC |
| `event_name` | STRING | NO | イベント名（下記19種） |
| `event_value_in_usd` | FLOAT | YES | イベント値（USD換算） |
| `event_bundle_sequence_id` | INTEGER | YES | バンドルシーケンス ID |
| `event_server_timestamp_offset` | INTEGER | YES | サーバータイムスタンプオフセット（マイクロ秒） |
| `user_pseudo_id` | STRING | NO | GA4 クライアント ID |
| `user_id` | STRING | YES | ログインユーザー ID（未ログインは null） |
| `is_active_user` | BOOLEAN | YES | アクティブユーザーフラグ |
| `platform` | STRING | NO | "WEB" 固定 |
| `stream_id` | STRING | NO | GA4 ストリーム ID |
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
| `privacy_info` | RECORD | YES | 同意モードのステータス |
| `batch_page_id` | INTEGER | YES | ページ遷移ごとにインクリメント |
| `batch_ordering_id` | INTEGER | YES | バッチごとにインクリメント |
| `batch_event_index` | INTEGER | YES | バッチ内のイベント連番 |

</details>

<details>
<summary>イベント種別（19種）</summary>

| イベント名 | 分類 | 説明 |
|---|---|---|
| `first_visit` | 自動収集 | ユーザーの初回訪問 |
| `session_start` | 自動収集 | セッション開始 |
| `page_view` | 自動収集 | ページ表示 |
| `sign_up` | 推奨 | 会員登録 |
| `login` | 推奨 | ログイン |
| `search` | 推奨 | サイト内検索 |
| `view_promotion` | EC 推奨 | プロモーション表示 |
| `select_promotion` | EC 推奨 | プロモーションクリック |
| `view_item_list` | EC 推奨 | 商品一覧表示 |
| `select_item` | EC 推奨 | 商品一覧からクリック |
| `view_item` | EC 推奨 | 商品詳細表示 |
| `add_to_cart` | EC 推奨 | カートに追加 |
| `remove_from_cart` | EC 推奨 | カートから削除 |
| `view_cart` | EC 推奨 | カート表示 |
| `begin_checkout` | EC 推奨 | チェックアウト開始 |
| `add_shipping_info` | EC 推奨 | 配送方法選択 |
| `add_payment_info` | EC 推奨 | 支払方法選択 |
| `purchase` | EC 推奨 | 購入完了 |
| `refund` | EC 推奨 | 返金（購入の約5%が3〜14日後） |

</details>

<details>
<summary>event_params キー（24種）</summary>

| key | value 型 | 主な対象イベント |
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

</details>

<details>
<summary>items 列（25列）</summary>

| カラム | 型 | NULLABLE | 備考 |
|---|---|---|---|
| `item_id` | STRING | NO | SKU001〜SKU080 |
| `item_name` | STRING | NO | |
| `item_brand` | STRING | NO | |
| `item_variant` | STRING | YES | |
| `item_category` | STRING | NO | |
| `item_category2` | STRING | NO | |
| `item_category3` | STRING | NO | |
| `item_category4` | STRING | YES | |
| `item_category5` | STRING | YES | |
| `price` | FLOAT | NO | |
| `price_in_usd` | FLOAT | YES | USD 換算価格 |
| `quantity` | INTEGER | NO | |
| `item_revenue` | FLOAT | YES | purchase イベントの売上 |
| `item_revenue_in_usd` | FLOAT | YES | USD 換算アイテム売上 |
| `index` | INTEGER | YES | リスト内表示順 |
| `coupon` | STRING | YES | |
| `discount` | FLOAT | YES | クーポン割引額 |
| `item_list_id` | STRING | YES | view_item_list / select_item のみ |
| `item_list_name` | STRING | YES | view_item_list / select_item のみ |
| `promotion_id` | STRING | YES | |
| `promotion_name` | STRING | YES | |
| `creative_name` | STRING | YES | |
| `creative_slot` | STRING | YES | |
| `location_id` | STRING | YES | |
| `item_params` | RECORD REPEATED | YES | カスタムアイテムパラメータ |

</details>

<details>
<summary>ecommerce 列（9列、purchase イベントのみ）</summary>

| カラム | 型 | 説明 |
|---|---|---|
| `transaction_id` | STRING | |
| `purchase_revenue` | FLOAT | クーポン割引後・送料込み |
| `purchase_revenue_in_usd` | FLOAT | USD 換算購入売上 |
| `refund_value` | FLOAT | 返金額（refund イベントのみ） |
| `refund_value_in_usd` | FLOAT | USD 換算返金額 |
| `shipping_value` | FLOAT | |
| `tax_value` | FLOAT | |
| `total_item_quantity` | INTEGER | |
| `unique_items` | INTEGER | |

</details>

<details>
<summary>device 列（12列）</summary>

| カラム | 型 | NULLABLE | 備考 |
|---|---|---|---|
| `category` | STRING | NO | mobile / desktop / tablet |
| `operating_system` | STRING | NO | |
| `operating_system_version` | STRING | NO | |
| `language` | STRING | NO | |
| `mobile_brand_name` | STRING | YES | |
| `mobile_model_name` | STRING | YES | |
| `mobile_marketing_name` | STRING | YES | |
| `is_limited_ad_tracking` | STRING | YES | モバイルのみ |
| `advertising_id` | STRING | YES | |
| `web_info.browser` | STRING | NO | |
| `web_info.browser_version` | STRING | NO | |
| `web_info.hostname` | STRING | NO | |

</details>

<details>
<summary>geo、traffic_source、collected_traffic_source 列</summary>

**geo 列（6列）**

`continent` / `sub_continent` / `country` / `region` / `city` / `metro`

**traffic_source 列（3列、ユーザー初回流入）**

`source` / `medium` / `name`

**collected_traffic_source 列（11列、セッション単位）**

`manual_source` / `manual_medium` / `manual_campaign_name` / `manual_content`（nullable）/ `manual_term`（nullable）/ `gclid`（nullable）/ `dclid`（nullable）/ `srsltid`（nullable）/ `manual_source_platform`（nullable）/ `manual_creative_format`（nullable）/ `manual_marketing_tactic`（nullable）

</details>

<details>
<summary>session_traffic_source_last_click（セッションのラストクリック流入元）</summary>

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
<summary>privacy_info 列と batch 列</summary>

**privacy_info 列（3列）**

| カラム | 型 | 説明 |
|---|---|---|
| `ads_storage` | STRING | 広告ストレージの同意ステータス（Yes/No） |
| `analytics_storage` | STRING | アナリティクスストレージの同意ステータス（Yes/No） |
| `uses_transient_token` | STRING | 一時トークン使用の有無（Yes/No） |

**batch 列（3列、イベント発生順の判定に使用）**

| カラム | 型 | 説明 |
|---|---|---|
| `batch_page_id` | INTEGER | ページ遷移ごとにインクリメント。同一ページ内のイベントは同じ値 |
| `batch_ordering_id` | INTEGER | バッチごとにインクリメント |
| `batch_event_index` | INTEGER | バッチ内のイベント連番（0始まり） |

> `event_timestamp` は GA4 サーバーへの到達時刻であり、複数のイベントが同時に到着するケースがあります。イベントの発生順を正確に判定するには、`event_timestamp, batch_page_id, batch_ordering_id, batch_event_index` の順で使用してください。

</details>

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
| `registration_date` | DATE | NO | シミュレーション開始の30〜1,095日前 |
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

`sql/mart/` 配下にデータマート用のビュー定義 SQL を格納しています。

### v_events_flat（イベントフラット化ビュー）

GA4 BigQuery Export のネスト構造をフラット化し、セッション単位の情報を付与した基盤ビューです。後続のセッションマート・ファネルマート・売上マート・ユーザーマートはこのビューを `FROM` して作成します。

**主な処理:**

1. `event_params` の各キーを個別カラムに展開（24キー）
2. `device`、`geo`、`traffic_source`、`collected_traffic_source`、`session_traffic_source_last_click` をフラット化
3. NULL 同等値（`(not set)`、`(none)`、`(not provided)`、空文字列）を NULL に正規化（`(direct)` はそのまま保持）
4. セッション内イベント発生順（`event_sequence_number`）を `event_timestamp, batch_page_id, batch_ordering_id, batch_event_index` で判定
5. セッションレベル属性を全イベント行に付与:
   - `session_traffic_source/medium/campaign/content`: `collected_traffic_source` の直近の非 NULL 値（source/medium/campaign/content を同一イベントから取得し整合性を保証）
   - `session_landing_page`: `entrances=1` の `page_location`
   - `session_duration_sec`、`session_has_purchase` など

**ファイル:** `sql/mart/v_events_flat.sql`

---

## ファイル構成

| ファイル | 説明 |
|---|---|
| `generate.py` | メインエントリーポイント。起動時に設定をバリデーション |
| `user_journeys.py` | セッション・イベント生成ロジック |
| `product_catalog.py` | 商品マスタ・クーポン定義 |
| `tables.py` | CSV テーブル生成（customers / products / orders / order_items） |
| `ga4_schema.py` | GA4 BigQuery Export スキーマのビルダー |
| `traffic_sources.py` | 流入元データ |
| `device_geo.py` | デバイス・地理データ |
| `utils.py` | ID 生成・タイムスタンプ変換ユーティリティ |
| `config.yaml` | 生成パラメータ設定 |
| `bigquery_load.py` | BigQuery ローダー |
| `schema_ga4_latest.json` | 最新 GA4 BigQuery Export スキーマ定義 |
| `migrate_schema.py` | 既存 JSONL 出力に新 GA4 スキーマフィールドを追加（`--input-dir` / `--output-dir`） |
| `fix_event_order.py` | セッション内イベント順序の修正（`--input-dir` / `--output-dir`） |
| `sql/mart/v_events_flat.sql` | イベントフラット化ビュー定義 |

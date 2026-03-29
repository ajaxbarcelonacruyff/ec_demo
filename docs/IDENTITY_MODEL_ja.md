# アイデンティティモデル: user_id と user_pseudo_id

> **[English version](IDENTITY_MODEL.md)**

このドキュメントは、ec_demo が生成するデータにおける `user_id` と `user_pseudo_id` の振る舞い、および GA4 イベントとリレーショナルテーブル（orders, customers）間の整合性ルールを定義します。

---

## 用語定義

| 用語 | 説明 |
|------|------|
| **Person（人物）** | 複数のデバイスを所有する可能性がある実際の人間。登録済み（ログインユーザー）なら `user_id` を持ち、未登録（ゲスト）なら `user_id` なし。 |
| **Device（デバイス）** | `user_pseudo_id`（GA4 クライアント ID）で識別されるブラウザ/アプリのインスタンス。物理的なハードウェアに紐づく。 |
| **Session（セッション）** | 1回の訪問。`user_pseudo_id` + `ga_session_id` で識別される。 |
| **ログイン状態** | セッション内でユーザーが認証済みかどうか。イベントに `user_id` が付与されるかを制御する。 |

---

## Person と Device の関係

実際の GA4 データでは、`user_id` と `user_pseudo_id` の関係は**多対多**です：

```
Person (user_id)          Device (user_pseudo_id)
================          ======================
    U-001  ──────────────── DPID-AAA  (PC)
       \                 /
        \──────────────── DPID-BBB  (スマートフォン)
                         /
    U-002  ─────────────── DPID-BBB  (共有デバイス)
        \
         \────────────────  DPID-CCC  (タブレット)
```

### マルチデバイスユーザー

1人の人物が複数のデバイスを使用します。同じ `user_id` が異なる `user_pseudo_id` で異なるセッションに出現します。

| シナリオ | 例 |
|----------|-----|
| 職場で PC、自宅でスマホ | `user_id=U-001` が `user_pseudo_id=AAA`（PC）と `user_pseudo_id=BBB`（スマホ）で出現 |
| スマホ + タブレット | `user_id=U-002` が `user_pseudo_id=CCC`（スマホ）と `user_pseudo_id=DDD`（タブレット）で出現 |

**設定：**

```yaml
identity:
  multi_device_ratio: 0.25     # ログインユーザーの25%が2台以上のデバイスを所有
  max_devices_per_user: 3      # 1人あたりの最大デバイス数
```

### 共有デバイス

1台のデバイスを複数の人物が使用します。同じ `user_pseudo_id` に異なる `user_id` が異なるセッションで出現します。

| シナリオ | 例 |
|----------|-----|
| 家族で自宅 PC を共有 | `user_pseudo_id=AAA` に `user_id=U-001`（月曜）と `user_id=U-002`（火曜）が出現 |

**設定：**

```yaml
identity:
  shared_device_ratio: 0.05      # デバイスの5%が共有
  max_users_per_device: 3        # 1台あたりの最大ユーザー数
```

**注意：** `user_id` は1つのセッション内で変わることはありません。共有デバイスでのユーザー切り替えは、別々のセッション間でのみ発生します。

### デバイスプロパティ

`device_profile`（OS、ブラウザ、画面サイズ）と `geo_profile`（国、地域、都市）は **Person ではなく Device に紐づきます**。Person B が Person A のデバイスを使用する場合、デバイスプロパティは変わりません（家庭内共有モデル）。

---

## セッション内アイデンティティ状態マシン

すべてのセッションは、厳格なログインゲート型アイデンティティモデルに従います。GA4 イベントの `user_id` は、`login` イベントと `logout` イベントの境界によってのみ制御されます。

### 状態遷移

```
セッション開始
  │
  │  user_id = NULL（すべてのセッションは匿名で開始）
  │
  ▼
  ┌─── 匿名ブラウジング ────┐
  │  page_view (user_id=NULL) │
  │  search    (user_id=NULL) │
  └──────────┬───────────────┘
             │
             ▼
     ┌── LOGIN イベント ──┐
     │  user_id = U-xxx    │
     └───────┬────────────┘
             │
             │  以降すべてのイベントに user_id = U-xxx
             │
             ▼
  ┌─── 認証済みブラウジング + eコマース ──┐
  │  add_to_cart      (user_id=U-xxx)      │
  │  begin_checkout   (user_id=U-xxx)      │
  │  purchase         (user_id=U-xxx)      │
  └──────────┬────────────────────────────┘
             │
             ▼（オプション）
     ┌── LOGOUT イベント ──┐
     │  user_id = NULL      │
     └───────┬─────────────┘
             │
             │  以降すべてのイベントに user_id = NULL
             │
             ▼
  ┌─── 匿名ブラウジング ────┐
  │  page_view (user_id=NULL) │
  └──────────────────────────┘
             │
             ▼
         セッション終了
```

### 不変条件（必ず守られるルール）

| # | ルール | 説明 |
|---|--------|------|
| 1 | **purchase には必ず user_id** | すべての `purchase` イベントに非 NULL の `user_id` が存在する。 |
| 2 | **login が eコマースより先** | 同一セッション内で、`login` または `sign_up` イベントが eコマースイベント（`add_to_cart`、`begin_checkout`、`purchase` 等）より先に発生する。 |
| 3 | **login 後は user_id が固定** | `login`/`sign_up` から `logout` またはセッション終了まで、すべてのイベントに同じ `user_id` が付与される。 |
| 4 | **logout 後は user_id = NULL** | `logout` イベント以降、次の `login` まですべてのイベントの `user_id` は NULL。 |
| 5 | **非 NULL 間の変更なし** | `user_id` が非 NULL 値から別の非 NULL 値に変わることはない。遷移は `NULL -> U-xxx`（ログイン）または `U-xxx -> NULL`（ログアウト）のみ。 |

### ログインタイミング

`user_id` を持つ Person のセッションでは、ログインは以下の3つのタイミングのいずれかで発火します：

| タイミング | デフォルト率 | 説明 |
|-----------|------------|------|
| **早期ログイン** | 60% | 初期ブラウジング中、ランディングページ直後にログイン |
| **遅延ログイン** | 25% | eコマースイベント直前（add_to_cart の手前）にログイン |
| **ログインなし** | 15% | 完全に匿名のセッション。eコマースなし。購入なし。 |

初回セッションでは `login` の代わりに `sign_up` が発火します（アイデンティティのセマンティクスは同じ）。

**設定：**

```yaml
identity:
  early_login_rate: 0.60
  late_login_rate: 0.25
  mid_session_logout_rate: 0.05
```

### チェックアウト時の強制再ログイン

ユーザーがセッション途中でログアウトした後にチェックアウトフローに到達した場合、`begin_checkout` の前に `login` イベントが挿入されます。これは日本の EC サイトでチェックアウト時に認証を要求する一般的な挙動をモデル化しています。

---

## 正規イベントシーケンス

### A. リピーター、早期ログイン、購入あり

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)    ← ランディングページ
login               (user_id=U-001)   ← アイデンティティ設定
page_view /category (user_id=U-001)
view_item_list      (user_id=U-001)
select_item         (user_id=U-001)
page_view /product  (user_id=U-001)
view_item           (user_id=U-001)
add_to_cart         (user_id=U-001)
view_cart           (user_id=U-001)
begin_checkout      (user_id=U-001)
add_shipping_info   (user_id=U-001)
add_payment_info    (user_id=U-001)
purchase            (user_id=U-001)   ← user_id は必ず非 NULL
```

### B. リピーター、遅延ログイン、購入あり

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
page_view /category (user_id=NULL)
view_item_list      (user_id=NULL)
view_item           (user_id=NULL)
login               (user_id=U-001)   ← eコマース直前にログイン
add_to_cart         (user_id=U-001)
begin_checkout      (user_id=U-001)
purchase            (user_id=U-001)
```

### C. ログインユーザーだが今回はログインなし（匿名ブラウジング）

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
page_view /category (user_id=NULL)
view_item           (user_id=NULL)
                    ← ログインなし、eコマースなし、購入なし
```

### D. 初回ユーザー、sign_up、購入あり

```
first_visit         (user_id=NULL)
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
sign_up             (user_id=U-002)   ← login の代わりに sign_up
page_view /product  (user_id=U-002)
add_to_cart         (user_id=U-002)
purchase            (user_id=U-002)
```

### E. ログイン、購入、その後ログアウトして匿名ブラウジング

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
login               (user_id=U-001)
add_to_cart         (user_id=U-001)
purchase            (user_id=U-001)
logout              (user_id=NULL)    ← アイデンティティクリア
page_view /sale     (user_id=NULL)
page_view /product  (user_id=NULL)
```

### F. noise セッション（GA4 トラッキング欠損、注文は記録）

```
GA4 イベント：
  session_start     (user_id=NULL)
  page_view /       (user_id=NULL)
  page_view /browse (user_id=NULL)
  ← GA4 にはログイン・eコマースイベントなし

orders.csv：
  order_id=TXN-xxx, customer_id=U-001, total_amount=12345
  ← リレーショナルテーブルには注文が記録される
```

### G. ゲストユーザー（アカウントなし）

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
page_view /category (user_id=NULL)
view_item           (user_id=NULL)
                    ← ログイン不可、購入なし
```

---

## GA4 イベントと注文データの整合性

### ルール

| 方向 | ルール |
|------|--------|
| **GA4 purchase -> orders** | GA4 `purchase` イベントの `user_id`、`transaction_id`、金額、商品は、対応する `orders` / `order_items` レコードと**完全に一致しなければならない**。 |
| **orders -> GA4 purchase** | `orders` レコードに対応する GA4 `purchase` イベントが**存在しなくてもよい**。これはトラッキング欠損（広告ブロッカー、同意拒否、ネットワークエラー）を表す。 |

### 単一の真実の源（Single Source of Truth）

GA4 `purchase` イベントと `orders`/`order_items` レコードは、共に1つの `purchase_info` ディクショナリから生成されます。これによりフィールドレベルの整合性が保証されます：

```
purchase_info（単一の真実の源）
    │
    ├──→ GA4 purchase イベント（noise セッションでない場合に送信）
    │     transaction_id  ← purchase_info["transaction_id"]
    │     user_id         ← purchase_info["user_id"]
    │     value           ← purchase_info["total_amount"]
    │     items           ← purchase_info["items"]
    │
    └──→ orders.csv + order_items.csv（常に書き込み）
          order_id        ← purchase_info["transaction_id"]
          customer_id     ← purchase_info["user_id"]
          total_amount    ← purchase_info["total_amount"]
          items           ← purchase_info["items"]
```

### 整合性対象フィールド

| フィールド | GA4 purchase イベント | orders.csv | 一致必須 |
|-----------|---------------------|------------|---------|
| トランザクションID | `event_params.transaction_id` | `order_id` | 完全一致 |
| ユーザーID | `user_id` | `customer_id` | 完全一致 |
| 売上金額 | `event_params.value` | `total_amount` | 完全一致 |
| 税額 | `event_params.tax` | `tax_amount` | 完全一致 |
| 送料 | `event_params.shipping` | `shipping_fee` | 完全一致 |
| 商品 | `items[].item_id`, `quantity` | `order_items.product_id`, `quantity` | 完全一致 |

---

## ノイズモデル

### セッションレベルのトラッキング欠損（`null_user_id_rate`）

GA4 トラッキングがブロックされるシナリオ（広告ブロッカー、同意拒否等）をシミュレートします。

| 項目 | 動作 |
|------|------|
| GA4 イベント | 匿名の page_view のみ送信（login なし、eコマースイベントなし） |
| 注文データ | 購入は**そのまま記録**される（real user_id 付きで orders/order_items に記録） |
| 効果 | 「GA4 アトリビューションなしの注文」が生成される — 現実的なデータギャップ |

**設定：**

```yaml
noise:
  null_user_id_rate: 0.05    # ログインユーザーのセッションの5%
```

### 個別イベント欠損（`ga4_event_loss_rate`）

個別のイベントが転送中に失われるシナリオ（ネットワークエラー、サンプリング）をシミュレートします。

| 項目 | 動作 |
|------|------|
| GA4 イベント | ランダムにイベントがドロップされる（`session_start` を除く） |
| 注文データ | 影響なし |
| 効果 | イベントシーケンスにギャップが生じる（例：`add_to_cart` はあるが `view_item` がない） |

**設定：**

```yaml
noise:
  ga4_event_loss_rate: 0.03   # 個別イベントの3%
```

---

## アイデンティティ解決（Identity Resolution）

### 課題

セッションは匿名で開始し、ログインはセッション途中で発生するため、クロスデバイスアトリビューションのために `user_pseudo_id` を `user_id` に紐づける必要があります。

### SQL アプローチ

付属の `v_identity_resolution.sql` ビューは、各 `user_pseudo_id` を最も頻繁に関連付けられた `user_id` に解決します：

```sql
-- 各デバイス（user_pseudo_id）について、
-- ログインセッションで最も頻繁に出現した user_id を見つける。
SELECT
  user_pseudo_id,
  user_id AS resolved_user_id,
  session_count AS logged_in_sessions
FROM (
  SELECT
    user_pseudo_id,
    user_id,
    COUNT(DISTINCT ga_session_id) AS session_count,
    ROW_NUMBER() OVER (
      PARTITION BY user_pseudo_id
      ORDER BY COUNT(DISTINCT ga_session_id) DESC
    ) AS rn
  FROM events
  WHERE user_id IS NOT NULL
  GROUP BY user_pseudo_id, user_id
)
WHERE rn = 1
```

### 既知の制限事項

| シナリオ | 動作 |
|----------|------|
| **共有デバイスで同等のアクティビティ** | 2人のユーザーが1台のデバイスで同等にアクティブな場合、解決は任意に選択される。 |
| **共有デバイス上のゲスト** | ゲストセッションはプライマリユーザーに誤帰属される。これは意図的なもので、実際のアイデンティティ解決の限界を反映している。 |
| **Cookie リセット** | このモデルは `user_pseudo_id` をデバイスに永続的に紐づけるものとして扱う。実際の GA4 では Cookie クリアやアプリ再インストールで `user_pseudo_id` がリセットされる。 |

---

## 設定リファレンス

アイデンティティ関連のすべての設定：

```yaml
users:
  logged_in_ratio: 0.30         # user_id を持つ Person の割合

identity:
  multi_device_ratio: 0.25      # ログインユーザーの2台以上デバイス所有率
  max_devices_per_user: 3
  shared_device_ratio: 0.05     # デバイスの共有率
  max_users_per_device: 3
  early_login_rate: 0.60        # 初期ブラウジング中のログイン
  late_login_rate: 0.25         # カート/チェックアウト時のログイン
  mid_session_logout_rate: 0.05 # 購入後のログアウト

noise:
  null_user_id_rate: 0.05       # セッションレベルの GA4 トラッキング欠損
  ga4_event_loss_rate: 0.03     # 個別イベント欠損
```

**ヒント：** アトリビューション分析デモには `logged_in_ratio >= 0.50` を推奨します。クロスデバイスシグナルのボリュームが増加します。

---

## 分析への影響

| 分析タイプ | このモデルで可能になること |
|-----------|-------------------------|
| **クロスデバイスアトリビューション** | 同じ `user_id` が複数の `user_pseudo_id` にまたがる。タッチポイントが PC とモバイルに跨る。 |
| **アイデンティティスティッチング** | 匿名セッション（ログイン前）を `user_pseudo_id` 経由で既知のユーザーに紐づけ可能。 |
| **データ品質評価** | GA4 イベントのない注文がトラッキングギャップを明らかにする。 |
| **ファネル分析** | ログインタイミング（早期/遅延）が、ユーザーが計測ファネルに入る位置に影響する。 |
| **共有デバイス検出** | 1つの `user_pseudo_id` に複数の `user_id` が出現すると共有デバイスを示す。 |

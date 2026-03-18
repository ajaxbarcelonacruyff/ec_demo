# ec_demo

GA4（Google Analytics 4）の EC（eコマース）デモデータを生成するプロジェクトです。

## プロジェクトの目的・概要

BigQuery 上の GA4 eコマースイベントデータを模したデモデータを生成します。開発・テスト・デモ環境で、本番データを使わずに GA4 データパイプラインの検証やBIダッシュボードのプロトタイピングを行うことを目的としています。

## 対象データ

GA4 BigQuery Export スキーマに準拠した eコマース関連イベントデータを生成します。

### 主要フィールド

| フィールド | 説明 |
|---|---|
| `event_name` | GA4 イベント名（`view_item`, `add_to_cart`, `purchase` など） |
| `event_date` | イベント日付（`YYYYMMDD` 形式の STRING） |
| `event_timestamp` | イベントタイムスタンプ（マイクロ秒、UTC） |
| `user_pseudo_id` | GA4 が付与する匿名ユーザーID |
| `event_params` | イベントパラメータ（REPEATED RECORD） |
| `user_properties` | ユーザープロパティ（REPEATED RECORD） |
| `items` | eコマース商品情報（REPEATED RECORD） |

### 主要 eコマースイベント

- `view_item` — 商品閲覧
- `add_to_cart` — カートに追加
- `remove_from_cart` — カートから削除
- `begin_checkout` — 決済開始
- `purchase` — 購入完了
- `select_promotion` — プロモーション選択

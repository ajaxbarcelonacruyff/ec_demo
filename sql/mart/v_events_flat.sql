-- =============================================================================
-- v_events_flat: GA4 イベントフラット化ビュー
-- =============================================================================
-- 目的:
--   GA4 BigQuery Export のネスト構造（event_params, items 等）をフラット化し、
--   セッション単位の情報（参照元、ランディングページ）とイベント発生順を付与する。
--   後続のセッションマート・ファネルマート・売上マート等の基盤テーブルとなる。
--
-- 使い方:
--   CREATE OR REPLACE VIEW `PROJECT_ID.ec_demo.v_events_flat` AS ( ... )
-- =============================================================================

CREATE OR REPLACE VIEW `PROJECT_ID.DATASET.v_events_flat` AS

WITH

-- -------------------------------------------------------
-- 0. NULL同等値を NULL に正規化するヘルパー関数
--    対象: (not set), (none), (direct), (not provided), 空文字列
-- -------------------------------------------------------

-- -------------------------------------------------------
-- 1. event_params をピボット（キーごとにカラム化）
--    文字列カラムは NULL 同等値を NULL に変換
-- -------------------------------------------------------
events_with_params AS (
  SELECT
    -- === 基本カラム ===
    event_date,
    PARSE_DATE('%Y%m%d', event_date)                           AS event_date_parsed,
    event_timestamp,
    TIMESTAMP_MICROS(event_timestamp)                          AS event_timestamp_jst,
    event_name,
    user_pseudo_id,
    user_id,
    platform,
    stream_id,
    user_first_touch_timestamp,
    TIMESTAMP_MICROS(user_first_touch_timestamp)               AS user_first_touch_timestamp_jst,

    -- === バッチ順序（イベント発生順の正確な判定に使用） ===
    batch_page_id,
    batch_ordering_id,
    batch_event_index,

    -- === event_params フラット化 ===
    (SELECT ep.value.int_value    FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id')          AS ga_session_id,
    (SELECT ep.value.int_value    FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_number')      AS ga_session_number,
    (SELECT ep.value.int_value    FROM UNNEST(event_params) ep WHERE ep.key = 'session_engaged')        AS session_engaged,
    (SELECT ep.value.int_value    FROM UNNEST(event_params) ep WHERE ep.key = 'engagement_time_msec')   AS engagement_time_msec,
    (SELECT ep.value.int_value    FROM UNNEST(event_params) ep WHERE ep.key = 'entrances')              AS entrances,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'page_location'), '')          AS page_location,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'page_title'), '')             AS page_title,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'page_referrer'), '')          AS page_referrer,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'search_term'), '')            AS search_term,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'item_list_id'), '')           AS item_list_id,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'item_list_name'), '')         AS item_list_name,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'currency'), '')               AS currency,
    (SELECT ep.value.float_value  FROM UNNEST(event_params) ep WHERE ep.key = 'value')                  AS event_value,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'coupon'), '')                 AS coupon,
    (SELECT ep.value.float_value  FROM UNNEST(event_params) ep WHERE ep.key = 'shipping')               AS shipping,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'shipping_tier'), '')          AS shipping_tier,
    (SELECT ep.value.float_value  FROM UNNEST(event_params) ep WHERE ep.key = 'tax')                    AS tax,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'transaction_id'), '')         AS transaction_id,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'payment_type'), '')           AS payment_type,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'promotion_id'), '')           AS promotion_id,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'promotion_name'), '')         AS promotion_name,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'creative_name'), '')          AS creative_name,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'creative_slot'), '')          AS creative_slot,
    NULLIF((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key = 'method'), '')                 AS method,

    -- === デバイス ===
    NULLIF(device.category, '(not set)')                       AS device_category,
    NULLIF(device.operating_system, '(not set)')               AS device_os,
    NULLIF(device.operating_system_version, '(not set)')       AS device_os_version,
    NULLIF(device.language, '(not set)')                       AS device_language,
    NULLIF(device.mobile_brand_name, '(not set)')              AS mobile_brand_name,
    NULLIF(device.mobile_model_name, '(not set)')              AS mobile_model_name,
    NULLIF(device.web_info.browser, '(not set)')               AS browser,
    NULLIF(device.web_info.browser_version, '(not set)')       AS browser_version,

    -- === 地理 ===
    NULLIF(geo.continent, '(not set)')     AS continent,
    NULLIF(geo.sub_continent, '(not set)') AS sub_continent,
    NULLIF(geo.country, '(not set)')       AS country,
    NULLIF(geo.region, '(not set)')        AS region,
    NULLIF(geo.city, '(not set)')          AS city,

    -- === トラフィックソース（ユーザー初回流入） ===
    -- (none), (not set), (not provided), 空文字列 → NULL（(direct) はそのまま保持）
    IF(traffic_source.source IN ('(none)', '(not set)', ''), NULL, traffic_source.source)  AS user_source,
    IF(traffic_source.medium IN ('(none)', '(not set)', ''), NULL, traffic_source.medium)  AS user_medium,
    IF(traffic_source.name   IN ('(none)', '(not set)', '(not provided)', ''), NULL, traffic_source.name) AS user_campaign,

    -- === セッション単位の流入元（collected_traffic_source） ===
    IF(collected_traffic_source.manual_source        IN ('(none)', '(not set)', ''), NULL, collected_traffic_source.manual_source)        AS session_source,
    IF(collected_traffic_source.manual_medium         IN ('(none)', '(not set)', ''), NULL, collected_traffic_source.manual_medium)        AS session_medium,
    IF(collected_traffic_source.manual_campaign_name  IN ('(none)', '(not set)', '(not provided)', ''), NULL, collected_traffic_source.manual_campaign_name) AS session_campaign,
    NULLIF(collected_traffic_source.manual_content, '') AS session_content,
    NULLIF(collected_traffic_source.gclid, '')         AS gclid,

    -- === セッション単位の流入元（session_traffic_source_last_click：カラム保持のみ） ===
    IF(session_traffic_source_last_click.manual_campaign.source IN ('(none)', '(not set)', ''), NULL, session_traffic_source_last_click.manual_campaign.source)               AS stslc_source,
    IF(session_traffic_source_last_click.manual_campaign.medium IN ('(none)', '(not set)', ''), NULL, session_traffic_source_last_click.manual_campaign.medium)               AS stslc_medium,
    IF(session_traffic_source_last_click.manual_campaign.campaign_name IN ('(none)', '(not set)', '(not provided)', ''), NULL, session_traffic_source_last_click.manual_campaign.campaign_name) AS stslc_campaign,
    NULLIF(session_traffic_source_last_click.manual_campaign.content, '') AS stslc_content,
    session_traffic_source_last_click.google_ads_campaign.customer_id   AS stslc_gads_customer_id,
    session_traffic_source_last_click.google_ads_campaign.account_name  AS stslc_gads_account_name,
    session_traffic_source_last_click.google_ads_campaign.campaign_id   AS stslc_gads_campaign_id,
    session_traffic_source_last_click.google_ads_campaign.campaign_name AS stslc_gads_campaign_name,
    session_traffic_source_last_click.google_ads_campaign.ad_group_id   AS stslc_gads_ad_group_id,
    session_traffic_source_last_click.google_ads_campaign.ad_group_name AS stslc_gads_ad_group_name,

    -- === ecommerce（purchase イベントのみ） ===
    ecommerce.transaction_id               AS ecom_transaction_id,
    ecommerce.purchase_revenue,
    ecommerce.total_item_quantity,
    ecommerce.unique_items,
    ecommerce.shipping_value,
    ecommerce.tax_value,

    -- === items 配列（後続で UNNEST 可能なようにそのまま保持） ===
    items

  FROM
    `PROJECT_ID.DATASET.events_*`
),

-- -------------------------------------------------------
-- 2. セッション識別キー生成 + セッション内イベント連番
--    ※ batch_event_index, batch_page_id, batch_ordering_id で
--      イベントの実際の発生順を判定（event_timestamp はGA4到達時刻のため不正確）
-- -------------------------------------------------------
events_with_sequence AS (
  SELECT
    *,
    -- セッション識別キー（user_pseudo_id × ga_session_id）
    CONCAT(user_pseudo_id, '.', CAST(ga_session_id AS STRING)) AS session_key,

    -- セッション内イベント発生順（batch フィールドで正確に判定、event_timestamp でフォールバック）
    ROW_NUMBER() OVER (
      PARTITION BY user_pseudo_id, ga_session_id
      ORDER BY event_timestamp, batch_page_id, batch_ordering_id, batch_event_index
    ) AS event_sequence_number,

    -- セッション内イベント総数
    COUNT(*) OVER (
      PARTITION BY user_pseudo_id, ga_session_id
    ) AS session_event_count

  FROM events_with_params
),

-- -------------------------------------------------------
-- 3a. セッション参照元（source/medium/campaign/content を同一イベントから取得）
--     session_source が非NULLの直近イベントからまとめて取得し、
--     フィールド間の不整合を防ぐ
-- -------------------------------------------------------
session_last_traffic AS (
  SELECT
    user_pseudo_id,
    ga_session_id,
    session_source,
    session_medium,
    session_campaign,
    session_content,
    ROW_NUMBER() OVER (
      PARTITION BY user_pseudo_id, ga_session_id
      ORDER BY event_timestamp DESC, batch_page_id DESC, batch_ordering_id DESC, batch_event_index DESC
    ) AS rn
  FROM events_with_params
  WHERE session_source IS NOT NULL
),

-- -------------------------------------------------------
-- 3b. セッションレベル情報（参照元・ランディングページ）を取得
-- -------------------------------------------------------
session_attributes AS (
  SELECT
    e.user_pseudo_id,
    e.ga_session_id,

    -- セッションの参照元: session_last_traffic から取得（同一イベント由来で整合性を保証）
    t.session_source   AS session_traffic_source,
    t.session_medium   AS session_traffic_medium,
    t.session_campaign AS session_traffic_campaign,
    t.session_content  AS session_traffic_content,

    -- ランディングページ: セッション内で entrances=1 の page_location
    MAX(IF(e.entrances = 1, e.page_location, NULL)) AS session_landing_page,
    MAX(IF(e.entrances = 1, e.page_title, NULL))    AS session_landing_page_title,
    MAX(IF(e.entrances = 1, e.page_referrer, NULL)) AS session_referrer,

    -- セッション開始・終了タイムスタンプ
    MIN(e.event_timestamp) AS session_start_timestamp,
    MAX(e.event_timestamp) AS session_end_timestamp,

    -- セッションの合計エンゲージメント時間（ミリ秒）
    SUM(e.engagement_time_msec) AS session_total_engagement_time_msec,

    -- セッション内の購入有無
    MAX(IF(e.event_name = 'purchase', 1, 0)) AS session_has_purchase,

    -- セッション内の購入回数
    COUNTIF(e.event_name = 'purchase') AS session_purchase_count

  FROM events_with_params e
  LEFT JOIN session_last_traffic t
    ON  e.user_pseudo_id = t.user_pseudo_id
    AND e.ga_session_id  = t.ga_session_id
    AND t.rn = 1
  GROUP BY
    e.user_pseudo_id,
    e.ga_session_id,
    t.session_source,
    t.session_medium,
    t.session_campaign,
    t.session_content
)

-- -------------------------------------------------------
-- 4. 最終結合: イベント行 × セッション属性
-- -------------------------------------------------------
SELECT
  -- === イベント識別 ===
  e.event_date,
  e.event_date_parsed,
  e.event_timestamp,
  e.event_timestamp_jst,
  e.event_name,
  e.session_key,
  e.event_sequence_number,
  e.session_event_count,

  -- === バッチ順序 ===
  e.batch_page_id,
  e.batch_ordering_id,
  e.batch_event_index,

  -- === ユーザー識別 ===
  e.user_pseudo_id,
  e.user_id,
  e.user_first_touch_timestamp,
  e.user_first_touch_timestamp_jst,

  -- === セッション情報 ===
  e.ga_session_id,
  e.ga_session_number,
  e.session_engaged,
  e.engagement_time_msec,

  -- === セッションレベル属性（全イベント行に付与） ===
  s.session_traffic_source,
  s.session_traffic_medium,
  s.session_traffic_campaign,
  s.session_traffic_content,
  s.session_landing_page,
  s.session_landing_page_title,
  s.session_referrer,
  TIMESTAMP_MICROS(s.session_start_timestamp)          AS session_start_timestamp_jst,
  TIMESTAMP_MICROS(s.session_end_timestamp)            AS session_end_timestamp_jst,
  (s.session_end_timestamp - s.session_start_timestamp) / 1000000 AS session_duration_sec,
  s.session_total_engagement_time_msec,
  s.session_has_purchase,
  s.session_purchase_count,

  -- === ページ情報 ===
  e.page_location,
  e.page_title,
  e.page_referrer,
  e.entrances,

  -- === 検索 ===
  e.search_term,

  -- === 商品リスト ===
  e.item_list_id,
  e.item_list_name,

  -- === EC トランザクション ===
  e.currency,
  e.event_value,
  e.coupon,
  e.shipping,
  e.shipping_tier,
  e.tax,
  e.transaction_id,
  e.payment_type,

  -- === プロモーション ===
  e.promotion_id,
  e.promotion_name,
  e.creative_name,
  e.creative_slot,

  -- === 認証 ===
  e.method,

  -- === ecommerce 集計（purchase のみ） ===
  e.ecom_transaction_id,
  e.purchase_revenue,
  e.total_item_quantity,
  e.unique_items,
  e.shipping_value,
  e.tax_value,

  -- === デバイス ===
  e.device_category,
  e.device_os,
  e.device_os_version,
  e.device_language,
  e.mobile_brand_name,
  e.mobile_model_name,
  e.browser,
  e.browser_version,

  -- === 地理 ===
  e.continent,
  e.sub_continent,
  e.country,
  e.region,
  e.city,

  -- === ユーザー初回流入元 ===
  e.user_source,
  e.user_medium,
  e.user_campaign,

  -- === セッション流入元（イベント行レベル・生値） ===
  e.session_source,
  e.session_medium,
  e.session_campaign,
  e.session_content,
  e.gclid,

  -- === session_traffic_source_last_click（フラット化） ===
  e.stslc_source,
  e.stslc_medium,
  e.stslc_campaign,
  e.stslc_content,
  e.stslc_gads_customer_id,
  e.stslc_gads_account_name,
  e.stslc_gads_campaign_id,
  e.stslc_gads_campaign_name,
  e.stslc_gads_ad_group_id,
  e.stslc_gads_ad_group_name,

  -- === items 配列（UNNEST 用に保持） ===
  e.items,

  -- === メタ ===
  e.platform,
  e.stream_id

FROM events_with_sequence e
LEFT JOIN session_attributes s
  ON  e.user_pseudo_id = s.user_pseudo_id
  AND e.ga_session_id  = s.ga_session_id
;

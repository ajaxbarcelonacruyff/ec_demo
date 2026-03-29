-- Identity Resolution View
-- Maps user_pseudo_id to resolved_user_id using the most frequent
-- non-NULL user_id observed in logged-in sessions on that device.
--
-- Known limitations:
-- - Shared devices: when two users are equally active, resolution picks arbitrarily
-- - Guest sessions on shared devices are misattributed to the primary user
-- - user_pseudo_id is treated as permanently bound to a device (no cookie reset)
--
-- Usage:
--   SELECT e.*, ir.resolved_user_id
--   FROM `PROJECT_ID.DATASET.v_events_flat` e
--   LEFT JOIN `PROJECT_ID.DATASET.v_identity_resolution` ir
--     ON e.user_pseudo_id = ir.user_pseudo_id

CREATE OR REPLACE VIEW `PROJECT_ID.DATASET.v_identity_resolution` AS

WITH device_user_sessions AS (
  SELECT
    user_pseudo_id,
    user_id,
    COUNT(DISTINCT
      CONCAT(user_pseudo_id, '.', CAST(
        (SELECT ep.value.int_value FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id')
        AS STRING
      ))
    ) AS session_count
  FROM `PROJECT_ID.DATASET.events_*`
  WHERE user_id IS NOT NULL
  GROUP BY user_pseudo_id, user_id
),

ranked AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY user_pseudo_id
      ORDER BY session_count DESC, user_id ASC
    ) AS rn
  FROM device_user_sessions
)

SELECT
  user_pseudo_id,
  user_id AS resolved_user_id,
  session_count AS logged_in_sessions
FROM ranked
WHERE rn = 1

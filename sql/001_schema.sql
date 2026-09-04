SELECT game_id, title
FROM analytics.stg_library
WHERE status IS NULL
   OR BTRIM(status::text) = '';
-- Duplicate game IDs: should return zero rows.
SELECT
    game_id,
    COUNT(*) AS duplicate_count
FROM analytics.dim_game
GROUP BY game_id
HAVING COUNT(*) > 1;


-- Duplicate ownership records: should return zero rows.
SELECT
    game_key,
    platform_key,
    storefront_key,
    COUNT(*) AS duplicate_count
FROM analytics.fact_library
GROUP BY
    game_key,
    platform_key,
    storefront_key
HAVING COUNT(*) > 1;


-- Compare staging and curated row counts.
SELECT
    (
        SELECT COUNT(*)
        FROM analytics.stg_library
    ) AS staging_rows,

    (
        SELECT COUNT(*)
        FROM analytics.fact_library
    ) AS curated_rows;


-- Profile missing optional information.
SELECT
    COUNT(*) AS games,
    COUNT(*) FILTER (
        WHERE personal_rating IS NULL
    ) AS missing_rating,
    COUNT(*) FILTER (
        WHERE playtime_hours IS NULL
    ) AS missing_playtime,
    COUNT(*) FILTER (
        WHERE purchase_price_aud IS NULL
    ) AS missing_price,
    COUNT(*) FILTER (
        WHERE last_played IS NULL
    ) AS missing_last_played
FROM analytics.vw_library_analysis;


-- Display the analysis-ready data.
SELECT *
FROM analytics.vw_library_analysis
ORDER BY title;
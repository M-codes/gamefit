
BEGIN;

-- This replaces only the derived view.
-- It does not delete any table data.
DROP VIEW IF EXISTS analytics.vw_library_analysis;

CREATE VIEW analytics.vw_library_analysis AS
SELECT
    fact.library_key,
    game.game_key,
    platform.platform_key,
    storefront.storefront_key,

    game.game_id,
    game.steam_app_id,
    game.rawg_id,
    game.title,

    platform.platform_name,
    storefront.storefront_name,

    fact.status,
    fact.personal_rating,
    fact.purchase_price_aud,
    fact.purchase_date,
    fact.playtime_hours,
    fact.achievement_pct,
    fact.last_played,
    fact.reason_stopped,
    fact.would_recommend,
    fact.play_context,

    game.release_date,
    EXTRACT(YEAR FROM game.release_date)::INTEGER AS release_year,
    game.typical_playtime_hours,
    game.metacritic_score,
    game.rawg_rating,
    game.rawg_ratings_count,
    game.rawg_url,

    COALESCE(genre_summary.genres, '') AS genres,
    genre_summary.genre_count,

    CASE
        WHEN fact.status = 'completed' THEN 1
        WHEN fact.status = 'abandoned' THEN 0
        ELSE NULL
    END AS completed_label,

    CASE
        WHEN fact.playtime_hours > 0
         AND fact.purchase_price_aud IS NOT NULL
        THEN ROUND(
            fact.purchase_price_aud / fact.playtime_hours,
            2
        )
        ELSE NULL
    END AS cost_per_played_hour_aud,

    CASE
        WHEN game.typical_playtime_hours > 0
         AND fact.playtime_hours IS NOT NULL
        THEN ROUND(
            fact.playtime_hours / game.typical_playtime_hours,
            2
        )
        ELSE NULL
    END AS playtime_vs_typical_ratio,

    CASE
        WHEN fact.personal_rating IS NOT NULL
         AND game.rawg_rating IS NOT NULL
        THEN ROUND(
            fact.personal_rating - (game.rawg_rating * 2),
            2
        )
        ELSE NULL
    END AS personal_vs_rawg_rating_gap,

    fact.source,
    fact.updated_at

FROM analytics.fact_library AS fact

JOIN analytics.dim_game AS game
    ON game.game_key = fact.game_key

JOIN analytics.dim_platform AS platform
    ON platform.platform_key = fact.platform_key

JOIN analytics.dim_storefront AS storefront
    ON storefront.storefront_key = fact.storefront_key

LEFT JOIN LATERAL (
    SELECT
        STRING_AGG(
            genre.genre_name,
            ', '
            ORDER BY genre.genre_name
        ) AS genres,

        COUNT(genre.genre_key)::INTEGER AS genre_count

    FROM analytics.bridge_game_genre AS bridge

    JOIN analytics.dim_genre AS genre
        ON genre.genre_key = bridge.genre_key

    WHERE bridge.game_key = game.game_key
) AS genre_summary
    ON TRUE;

COMMIT;
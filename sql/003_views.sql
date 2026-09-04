SET ROLE gamefit;


CREATE OR REPLACE VIEW analytics.vw_library_analysis AS
SELECT
    fact.library_key,
    game.game_id,
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
    fact.source,
    fact.updated_at,
    game.release_date,
    game.typical_playtime_hours,
    game.metacritic_score,

    CASE
        WHEN fact.status = 'completed' THEN 1
        WHEN fact.status = 'abandoned' THEN 0
        ELSE NULL
    END AS completed_label

FROM analytics.fact_library AS fact

JOIN analytics.dim_game AS game
    ON game.game_key = fact.game_key

JOIN analytics.dim_platform AS platform
    ON platform.platform_key = fact.platform_key

JOIN analytics.dim_storefront AS storefront
    ON storefront.storefront_key =
       fact.storefront_key;


RESET ROLE;
BEGIN;

SET LOCAL ROLE gamefit;


DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM analytics.stg_library
        WHERE game_id IS NULL
           OR BTRIM(game_id::text) = ''
           OR title IS NULL
           OR BTRIM(title::text) = ''
           OR platform IS NULL
           OR BTRIM(platform::text) = ''
           OR storefront IS NULL
           OR BTRIM(storefront::text) = ''
           OR status IS NULL
           OR BTRIM(status::text) = ''
    ) THEN
        RAISE EXCEPTION
            'Required staging values cannot be blank';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM analytics.stg_library
        WHERE LOWER(BTRIM(status::text)) NOT IN (
            'backlog',
            'playing',
            'completed',
            'abandoned',
            'paused'
        )
    ) THEN
        RAISE EXCEPTION
            'Invalid status found in staging data';
    END IF;
END
$$;


INSERT INTO analytics.dim_game (
    game_id,
    title
)
SELECT DISTINCT
    BTRIM(game_id::text),
    BTRIM(title::text)
FROM analytics.stg_library
ON CONFLICT (game_id)
DO UPDATE SET
    title = EXCLUDED.title;


INSERT INTO analytics.dim_platform (
    platform_name
)
SELECT DISTINCT
    BTRIM(platform::text)
FROM analytics.stg_library
ON CONFLICT (platform_name)
DO NOTHING;


INSERT INTO analytics.dim_storefront (
    storefront_name
)
SELECT DISTINCT
    BTRIM(storefront::text)
FROM analytics.stg_library
ON CONFLICT (storefront_name)
DO NOTHING;


INSERT INTO analytics.fact_library (
    game_key,
    platform_key,
    storefront_key,
    status,
    personal_rating,
    purchase_price_aud,
    purchase_date,
    playtime_hours,
    last_played,
    reason_stopped,
    would_recommend,
    play_context,
    source,
    updated_at
)
SELECT
    game.game_key,
    platform.platform_key,
    storefront.storefront_key,
    LOWER(BTRIM(staging.status::text)),

    NULLIF(
        BTRIM(staging.personal_rating::text),
        ''
    )::NUMERIC(3, 1),

    NULLIF(
        BTRIM(staging.purchase_price_aud::text),
        ''
    )::NUMERIC(10, 2),

    staging.purchase_date::DATE,

    NULLIF(
        BTRIM(staging.playtime_hours::text),
        ''
    )::NUMERIC(10, 2),

    staging.last_played::DATE,

    NULLIF(
        BTRIM(staging.reason_stopped::text),
        ''
    ),

    CASE LOWER(
        BTRIM(staging.would_recommend::text)
    )
        WHEN 'true' THEN TRUE
        WHEN 't' THEN TRUE
        WHEN '1' THEN TRUE
        WHEN 'yes' THEN TRUE
        WHEN 'false' THEN FALSE
        WHEN 'f' THEN FALSE
        WHEN '0' THEN FALSE
        WHEN 'no' THEN FALSE
        ELSE NULL
    END,

    NULLIF(
        BTRIM(staging.play_context::text),
        ''
    ),

    'manual',
    NOW()

FROM analytics.stg_library AS staging

JOIN analytics.dim_game AS game
    ON game.game_id =
       BTRIM(staging.game_id::text)

JOIN analytics.dim_platform AS platform
    ON platform.platform_name =
       BTRIM(staging.platform::text)

JOIN analytics.dim_storefront AS storefront
    ON storefront.storefront_name =
       BTRIM(staging.storefront::text)

ON CONFLICT (
    game_key,
    platform_key,
    storefront_key
)
DO UPDATE SET
    status = EXCLUDED.status,
    personal_rating = EXCLUDED.personal_rating,
    purchase_price_aud = EXCLUDED.purchase_price_aud,
    purchase_date = EXCLUDED.purchase_date,
    playtime_hours = EXCLUDED.playtime_hours,
    last_played = EXCLUDED.last_played,
    reason_stopped = EXCLUDED.reason_stopped,
    would_recommend = EXCLUDED.would_recommend,
    play_context = EXCLUDED.play_context,
    source = EXCLUDED.source,
    updated_at = NOW();


COMMIT;
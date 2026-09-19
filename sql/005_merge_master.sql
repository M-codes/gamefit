BEGIN;

-- Stop if the staging dataset is incomplete.
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM analytics.stg_library) <> 30 THEN
        RAISE EXCEPTION 'Expected exactly 30 staging rows';
    END IF;

    IF EXISTS (
        SELECT game_id
        FROM analytics.stg_library
        GROUP BY game_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate game_id values exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM analytics.stg_library
        WHERE rawg_id IS NULL
    ) THEN
        RAISE EXCEPTION 'At least one RAWG ID is missing';
    END IF;
END
$$;


-- Add useful RAWG fields to dim_game.
ALTER TABLE analytics.dim_game
    ADD COLUMN IF NOT EXISTS rawg_rating NUMERIC(4,2)
        CHECK (rawg_rating BETWEEN 0 AND 5);

ALTER TABLE analytics.dim_game
    ADD COLUMN IF NOT EXISTS rawg_ratings_count INTEGER
        CHECK (rawg_ratings_count >= 0);

ALTER TABLE analytics.dim_game
    ADD COLUMN IF NOT EXISTS rawg_url TEXT;


-- Insert new games or update existing games.
INSERT INTO analytics.dim_game (
    game_id,
    steam_app_id,
    rawg_id,
    title,
    release_date,
    typical_playtime_hours,
    metacritic_score,
    rawg_rating,
    rawg_ratings_count,
    rawg_url
)
SELECT
    s.game_id::TEXT,
    NULLIF(s.steam_app_id::TEXT, '')::NUMERIC::INTEGER,
    NULLIF(s.rawg_id::TEXT, '')::NUMERIC::INTEGER,
    s.title::TEXT,
    NULLIF(NULLIF(s.released::TEXT, ''), 'NaT')::DATE,
    NULLIF(NULLIF(s.typical_playtime_hours::TEXT, ''), 'NaN')::NUMERIC,
    NULLIF(NULLIF(s.metacritic_score::TEXT, ''), 'NaN')::NUMERIC::SMALLINT,
    NULLIF(NULLIF(s.rawg_rating::TEXT, ''), 'NaN')::NUMERIC,
    NULLIF(NULLIF(s.rawg_ratings_count::TEXT, ''), 'NaN')::NUMERIC::INTEGER,
    NULLIF(s.rawg_url::TEXT, '')
FROM analytics.stg_library AS s
ON CONFLICT (game_id)
DO UPDATE SET
    steam_app_id = EXCLUDED.steam_app_id,
    rawg_id = EXCLUDED.rawg_id,
    title = EXCLUDED.title,
    release_date = EXCLUDED.release_date,
    typical_playtime_hours = EXCLUDED.typical_playtime_hours,
    metacritic_score = EXCLUDED.metacritic_score,
    rawg_rating = EXCLUDED.rawg_rating,
    rawg_ratings_count = EXCLUDED.rawg_ratings_count,
    rawg_url = EXCLUDED.rawg_url;


-- Insert platforms.
INSERT INTO analytics.dim_platform (platform_name)
SELECT DISTINCT TRIM(s.platform::TEXT)
FROM analytics.stg_library AS s
WHERE NULLIF(TRIM(s.platform::TEXT), '') IS NOT NULL
ON CONFLICT (platform_name) DO NOTHING;

-- Insert storefronts such as Steam and Epic Games.
INSERT INTO analytics.dim_storefront (storefront_name)
SELECT DISTINCT TRIM(s.storefront::TEXT)
FROM analytics.stg_library AS s
WHERE NULLIF(TRIM(s.storefront::TEXT), '') IS NOT NULL
ON CONFLICT (storefront_name) DO NOTHING;


-- Split comma-separated RAWG genres into individual genres.
INSERT INTO analytics.dim_genre (genre_name)
SELECT DISTINCT TRIM(split_genre.genre_name)
FROM analytics.stg_library AS s
CROSS JOIN LATERAL regexp_split_to_table(
    COALESCE(s.genres::TEXT, ''),
    '[[:space:]]*,[[:space:]]*'
) AS split_genre(genre_name)
WHERE TRIM(split_genre.genre_name) <> ''
ON CONFLICT (genre_name) DO NOTHING;


-- Rebuild genre links only for the 30 staged games.
DELETE FROM analytics.bridge_game_genre AS bridge
USING
    analytics.dim_game AS game,
    analytics.stg_library AS staging
WHERE bridge.game_key = game.game_key
  AND game.game_id = staging.game_id::TEXT;


INSERT INTO analytics.bridge_game_genre (
    game_key,
    genre_key
)
SELECT DISTINCT
    game.game_key,
    genre.genre_key
FROM analytics.stg_library AS staging
JOIN analytics.dim_game AS game
    ON game.game_id = staging.game_id::TEXT
CROSS JOIN LATERAL regexp_split_to_table(
    COALESCE(staging.genres::TEXT, ''),
    '[[:space:]]*,[[:space:]]*'
) AS split_genre(genre_name)
JOIN analytics.dim_genre AS genre
    ON genre.genre_name = TRIM(split_genre.genre_name)
WHERE TRIM(split_genre.genre_name) <> ''
ON CONFLICT (game_key, genre_key) DO NOTHING;


-- Insert or update your personal library facts.
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
    staging.status::TEXT,
    NULLIF(
        NULLIF(staging.personal_rating::TEXT, ''),
        'NaN'
    )::NUMERIC,
    NULLIF(
        NULLIF(staging.purchase_price_aud::TEXT, ''),
        'NaN'
    )::NUMERIC,
    NULLIF(
        NULLIF(staging.purchase_date::TEXT, ''),
        'NaT'
    )::DATE,
    NULLIF(
        NULLIF(staging.playtime_hours::TEXT, ''),
        'NaN'
    )::NUMERIC,
    NULLIF(
        NULLIF(staging.last_played::TEXT, ''),
        'NaT'
    )::TIMESTAMPTZ::DATE,
    NULLIF(staging.reason_stopped::TEXT, ''),
    NULLIF(staging.would_recommend::TEXT, '')::BOOLEAN,
    NULLIF(staging.play_context::TEXT, ''),
    'manual+steam+rawg',
    NOW()
FROM analytics.stg_library AS staging
JOIN analytics.dim_game AS game
    ON game.game_id = staging.game_id::TEXT
JOIN analytics.dim_platform AS platform
    ON platform.platform_name = TRIM(staging.platform::TEXT)
JOIN analytics.dim_storefront AS storefront
    ON storefront.storefront_name = TRIM(staging.storefront::TEXT)
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
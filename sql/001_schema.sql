SET ROLE gamefit;

CREATE SCHEMA IF NOT EXISTS analytics AUTHORIZATION gamefit;


CREATE TABLE IF NOT EXISTS analytics.dim_game (
    game_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id TEXT NOT NULL UNIQUE,
    steam_app_id INTEGER UNIQUE,
    rawg_id INTEGER UNIQUE,
    title TEXT NOT NULL,
    release_date DATE,
    developer TEXT,
    publisher TEXT,
    typical_playtime_hours NUMERIC(8, 2)
        CHECK (typical_playtime_hours >= 0),
    metacritic_score SMALLINT
        CHECK (metacritic_score BETWEEN 0 AND 100)
);


CREATE TABLE IF NOT EXISTS analytics.dim_platform (
    platform_key SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform_name TEXT NOT NULL UNIQUE
);


CREATE TABLE IF NOT EXISTS analytics.dim_storefront (
    storefront_key SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    storefront_name TEXT NOT NULL UNIQUE
);


CREATE TABLE IF NOT EXISTS analytics.dim_genre (
    genre_key SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    genre_name TEXT NOT NULL UNIQUE
);


CREATE TABLE IF NOT EXISTS analytics.bridge_game_genre (
    game_key BIGINT NOT NULL
        REFERENCES analytics.dim_game(game_key)
        ON DELETE CASCADE,

    genre_key SMALLINT NOT NULL
        REFERENCES analytics.dim_genre(genre_key)
        ON DELETE CASCADE,

    PRIMARY KEY (game_key, genre_key)
);


CREATE TABLE IF NOT EXISTS analytics.fact_library (
    library_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    game_key BIGINT NOT NULL
        REFERENCES analytics.dim_game(game_key),

    platform_key SMALLINT NOT NULL
        REFERENCES analytics.dim_platform(platform_key),

    storefront_key SMALLINT NOT NULL
        REFERENCES analytics.dim_storefront(storefront_key),

    status TEXT NOT NULL
        CHECK (
            status IN (
                'backlog',
                'playing',
                'completed',
                'abandoned',
                'paused'
            )
        ),

    personal_rating NUMERIC(3, 1)
        CHECK (personal_rating BETWEEN 1 AND 10),

    purchase_price_aud NUMERIC(10, 2)
        CHECK (purchase_price_aud >= 0),

    purchase_date DATE,

    playtime_hours NUMERIC(10, 2)
        CHECK (playtime_hours >= 0),

    achievement_pct NUMERIC(5, 2)
        CHECK (achievement_pct BETWEEN 0 AND 100),

    last_played DATE,

    reason_stopped TEXT,

    would_recommend BOOLEAN,

    play_context TEXT,

    source TEXT NOT NULL DEFAULT 'manual',

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (
        game_key,
        platform_key,
        storefront_key
    )
);


CREATE INDEX IF NOT EXISTS idx_fact_library_status
    ON analytics.fact_library(status);


CREATE INDEX IF NOT EXISTS idx_fact_library_last_played
    ON analytics.fact_library(last_played);


RESET ROLE;
SELECT
    (SELECT COUNT(*) FROM analytics.dim_game) AS games,
    (SELECT COUNT(*) FROM analytics.fact_library) AS library_rows,
    (SELECT COUNT(*) FROM analytics.dim_genre) AS genres,
    (SELECT COUNT(*) FROM analytics.bridge_game_genre) AS game_genre_links,
    (SELECT COUNT(*) FROM analytics.dim_storefront) AS storefronts;
from pathlib import Path

import pandas as pd


ALLOWED_STATUS = {
    "backlog",
    "playing",
    "completed",
    "abandoned",
    "paused",
}


def load_manual(path: Path) -> pd.DataFrame:
    """Load, clean and validate the manually maintained game library."""

    df = pd.read_csv(path)

    df.columns = [
        column.strip().lower()
        for column in df.columns
    ]

    required = {
        "game_id",
        "title",
        "platform",
        "storefront",
        "status",
        "personal_rating",
        "purchase_price_aud",
        "purchase_date",
        "playtime_hours",
        "last_played",
        "reason_stopped",
        "would_recommend",
        "play_context",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    text_columns = [
        "game_id",
        "title",
        "platform",
        "storefront",
        "status",
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    df["status"] = df["status"].str.lower()

    invalid_statuses = (
        set(df["status"].dropna())
        - ALLOWED_STATUS
    )

    if invalid_statuses:
        raise ValueError(
            f"Invalid status values: {sorted(invalid_statuses)}"
        )

    if df["game_id"].duplicated().any():
        raise ValueError("game_id must be unique")

    date_columns = [
        "purchase_date",
        "last_played",
    ]

    for column in date_columns:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce",
        )

    number_columns = [
        "personal_rating",
        "purchase_price_aud",
        "playtime_hours",
    ]

    for column in number_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    ratings = df["personal_rating"].dropna()

    if not ratings.between(1, 10).all():
        raise ValueError(
            "personal_rating must be between 1 and 10"
        )

    return df
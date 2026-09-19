import json
from datetime import datetime, timezone

import pandas as pd
import requests

from gamefit.config import ROOT, Settings


# These three matches were manually verified on RAWG.
VERIFIED_SLUGS = {
    "manual-002": "final-fantasy-ix",
    "manual-006": "street-fighter-v",
    "manual-022": "geometry-dash",
}

REVIEW_CSV = ROOT / "data" / "processed" / "rawg_match_review.csv"
REVIEW_PARQUET = ROOT / "data" / "processed" / "rawg_match_review.parquet"


def get_rawg_game(slug: str, api_key: str) -> dict:
    url = f"https://api.rawg.io/api/games/{slug}"

    try:
        response = requests.get(
            url,
            params={"key": api_key},
            timeout=30,
        )
    except requests.RequestException:
        raise RuntimeError(f"RAWG request failed for {slug}") from None

    if response.status_code != 200:
        raise RuntimeError(
            f"RAWG returned HTTP {response.status_code} for {slug}"
        )

    return response.json()


def extract_names(items: list[dict], nested_key: str | None = None) -> str:
    names = []

    for item in items:
        value = item.get(nested_key, {}) if nested_key else item
        name = value.get("name")

        if name:
            names.append(name)

    return ", ".join(names)


def main() -> None:
    api_key = Settings().rawg_api_key

    if not api_key:
        raise RuntimeError("RAWG_API_KEY is missing from .env")

    if not REVIEW_CSV.exists():
        raise FileNotFoundError(f"Cannot find {REVIEW_CSV}")

    df = pd.read_csv(REVIEW_CSV)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_directory = ROOT / "data" / "raw" / "rawg" / f"resolved_{timestamp}"
    raw_directory.mkdir(parents=True, exist_ok=True)

    for game_id, slug in VERIFIED_SLUGS.items():
        mask = df["game_id"].eq(game_id)

        if not mask.any():
            raise ValueError(f"{game_id} is missing from the review CSV")

        game = get_rawg_game(slug, api_key)

        # Keep the raw API response for traceability.
        raw_path = raw_directory / f"{game_id}_{slug}.json"

        with raw_path.open("w", encoding="utf-8") as file:
            json.dump(game, file, indent=2, ensure_ascii=False)

        values = {
            "rawg_id": game.get("id"),
            "rawg_title": game.get("name"),
            "released": game.get("released"),
            "genres": extract_names(game.get("genres", [])),
            "rawg_rating": game.get("rating"),
            "rawg_ratings_count": game.get("ratings_count"),
            "metacritic_score": game.get("metacritic"),
            "typical_playtime_hours": game.get("playtime"),
            "rawg_platforms": extract_names(
                game.get("platforms", []),
                nested_key="platform",
            ),
            "rawg_url": f"https://rawg.io/games/{game.get('slug')}",
            "match_status": "matched",
            "match_note": "manually_verified_slug",
            "candidate_count": 1,
            "candidate_titles": game.get("name"),
        }

        for column, value in values.items():
            df.loc[mask, column] = value

        print(
            f"Resolved {game_id}: "
            f"{game.get('name')} (RAWG ID {game.get('id')})"
        )

    integer_columns = [
        "rawg_id",
        "rawg_ratings_count",
        "metacritic_score",
        "typical_playtime_hours",
        "candidate_count",
    ]

    for column in integer_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).astype("Int64")

    duplicate_ids = df["rawg_id"].dropna().duplicated()

    if duplicate_ids.any():
        raise ValueError("Duplicate RAWG IDs remain after resolution")

    df.to_csv(REVIEW_CSV, index=False)
    df.to_parquet(REVIEW_PARQUET, index=False)

    unresolved = df[df["match_status"] != "matched"]

    print(f"\nMatched: {len(df) - len(unresolved)}/{len(df)}")
    print(f"Still requiring review: {len(unresolved)}")

    if not unresolved.empty:
        print(unresolved[["game_id", "source_title", "match_status"]])


if __name__ == "__main__":
    main()
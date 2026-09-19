import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from gamefit.config import ROOT, Settings


RAWG_GAMES_URL = "https://api.rawg.io/api/games"

SOURCE_FILE = (
    ROOT / "data" / "processed" / "library_enriched.parquet"
)
REVIEW_CSV = (
    ROOT / "data" / "processed" / "rawg_match_review.csv"
)
REVIEW_PARQUET = (
    ROOT / "data" / "processed" / "rawg_match_review.parquet"
)


def normalize_title(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value)
    text = re.sub(r"[™®©]", "", text)
    text = unicodedata.normalize("NFKD", text).casefold()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


def fetch_candidates(
    title: str,
    api_key: str,
) -> dict:
    parameters = {
        "key": api_key,
        "search": title,
        "search_exact": "true",
        "page_size": 5,
    }

    try:
        response = requests.get(
            RAWG_GAMES_URL,
            params=parameters,
            headers={
                "User-Agent": (
                    "GameFit/0.1 personal analytics project"
                )
            },
            timeout=30,
        )
    except requests.RequestException:
        raise RuntimeError(
            "RAWG request failed because of a network error."
        ) from None

    if response.status_code in {401, 403}:
        raise RuntimeError(
            "RAWG rejected the API key."
        )

    if response.status_code == 429:
        raise RuntimeError(
            "RAWG rate limit reached. Wait before retrying."
        )

    if response.status_code >= 500:
        raise RuntimeError(
            f"RAWG server error: {response.status_code}"
        )

    if not response.ok:
        raise RuntimeError(
            f"RAWG request failed: {response.status_code}"
        )

    try:
        return response.json()
    except ValueError:
        raise RuntimeError(
            "RAWG returned invalid JSON."
        ) from None


def choose_candidate(
    source_title: str,
    results: list[dict],
) -> tuple[dict | None, str, str]:
    if not results:
        return None, "unmatched", "no_results"

    normalized_source = normalize_title(source_title)

    exact_matches = [
        result
        for result in results
        if normalize_title(result.get("name")) == normalized_source
    ]

    if len(exact_matches) == 1:
        return exact_matches[0], "matched", "exact_title"

    if len(exact_matches) > 1:
        return (
            exact_matches[0],
            "review",
            "multiple_exact_titles",
        )

    return (
        results[0],
        "review",
        "top_title_differs",
    )


def extract_genres(candidate: dict) -> str:
    return ", ".join(
        genre["name"]
        for genre in candidate.get("genres", [])
        if genre.get("name")
    )


def extract_platforms(candidate: dict) -> str:
    names = []

    for item in candidate.get("platforms", []):
        platform = item.get("platform", {})
        name = platform.get("name")

        if name:
            names.append(name)

    return ", ".join(names)


def build_review_record(
    game_id: str,
    source_title: str,
    results: list[dict],
) -> dict:
    candidate, match_status, match_note = choose_candidate(
        source_title,
        results,
    )

    candidate_titles = " | ".join(
        str(result.get("name", ""))
        for result in results
    )

    record = {
        "game_id": game_id,
        "source_title": source_title,
        "rawg_id": None,
        "rawg_title": None,
        "released": None,
        "genres": None,
        "rawg_rating": None,
        "rawg_ratings_count": None,
        "metacritic_score": None,
        "typical_playtime_hours": None,
        "rawg_platforms": None,
        "rawg_url": None,
        "match_status": match_status,
        "match_note": match_note,
        "candidate_count": len(results),
        "candidate_titles": candidate_titles,
    }

    if candidate is None:
        return record

    slug = candidate.get("slug")

    record.update(
        {
            "rawg_id": candidate.get("id"),
            "rawg_title": candidate.get("name"),
            "released": candidate.get("released"),
            "genres": extract_genres(candidate),
            "rawg_rating": candidate.get("rating"),
            "rawg_ratings_count": candidate.get(
                "ratings_count"
            ),
            "metacritic_score": candidate.get("metacritic"),
            "typical_playtime_hours": candidate.get(
                "playtime"
            ),
            "rawg_platforms": extract_platforms(candidate),
            "rawg_url": (
                f"https://rawg.io/games/{slug}"
                if slug
                else None
            ),
        }
    )

    return record


def main() -> None:
    settings = Settings()

    if not settings.rawg_api_key:
        raise ValueError("RAWG_API_KEY is missing from .env")

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            "library_enriched.parquet is missing. "
            "Run the GameFit pipeline first."
        )

    library = pd.read_parquet(SOURCE_FILE)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    raw_directory = (
        ROOT
        / "data"
        / "raw"
        / "rawg"
        / f"batch_{timestamp}"
    )
    raw_directory.mkdir(parents=True, exist_ok=True)

    review_records = []

    for number, game in enumerate(
        library.itertuples(index=False),
        start=1,
    ):
        print(
            f"[{number:02}/{len(library)}] "
            f"Searching: {game.title}"
        )

        data = fetch_candidates(
            game.title,
            settings.rawg_api_key,
        )

        raw_path = raw_directory / f"{game.game_id}.json"

        with raw_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

        results = data.get("results", [])

        record = build_review_record(
            game.game_id,
            game.title,
            results,
        )
        review_records.append(record)

        print(
            f"         Candidate: "
            f"{record['rawg_title']} "
            f"[{record['match_status']}]"
        )

        if number < len(library):
            time.sleep(0.25)

    review = pd.DataFrame(review_records)

    review["rawg_id"] = review["rawg_id"].astype("Int64")
    review["metacritic_score"] = review[
        "metacritic_score"
    ].astype("Int64")

    review.to_csv(REVIEW_CSV, index=False)
    review.to_parquet(REVIEW_PARQUET, index=False)

    counts = review["match_status"].value_counts()

    print("\nRAWG extraction complete.")
    print(f"Matched: {counts.get('matched', 0)}")
    print(f"Needs review: {counts.get('review', 0)}")
    print(f"Unmatched: {counts.get('unmatched', 0)}")
    print(f"Review file: {REVIEW_CSV}")
    print(f"Raw responses: {raw_directory}")


if __name__ == "__main__":
    main()
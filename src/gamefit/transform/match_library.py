import re
import unicodedata
from difflib import get_close_matches
from pathlib import Path

import pandas as pd

from gamefit.config import ROOT


MANUAL_FILE = ROOT / "data" / "processed" / "library.parquet"
STEAM_FILE = ROOT / "data" / "processed" / "steam_library.parquet"

OUTPUT_PARQUET = (
    ROOT / "data" / "processed" / "library_enriched.parquet"
)
OUTPUT_CSV = (
    ROOT / "data" / "processed" / "library_enriched.csv"
)


def normalize_title(value: object) -> str:
    """Create a simplified title used only for matching."""
    if pd.isna(value):
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = text.casefold()
    text = text.replace("&", "and")
    text = re.sub(r"[™®©]", "", text)
    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not MANUAL_FILE.exists():
        raise FileNotFoundError(
            "library.parquet is missing. Run "
            "'python -m gamefit.pipeline' first."
        )

    if not STEAM_FILE.exists():
        raise FileNotFoundError(
            "steam_library.parquet is missing. Run "
            "'python -m gamefit.transform.steam' first."
        )

    return (
        pd.read_parquet(MANUAL_FILE),
        pd.read_parquet(STEAM_FILE),
    )


def match_libraries() -> pd.DataFrame:
    manual, steam = load_inputs()

    required_manual = {
        "game_id",
        "title",
        "storefront",
        "playtime_hours",
        "last_played",
    }
    required_steam = {
        "steam_app_id",
        "title",
        "playtime_hours",
    }

    missing_manual = required_manual - set(manual.columns)
    missing_steam = required_steam - set(steam.columns)

    if missing_manual:
        raise ValueError(
            f"Manual data is missing: {sorted(missing_manual)}"
        )

    if missing_steam:
        raise ValueError(
            f"Steam data is missing: {sorted(missing_steam)}"
        )

    if "last_played" not in steam.columns:
        steam["last_played"] = pd.NaT

    manual["_match_title"] = manual["title"].map(normalize_title)
    steam["_match_title"] = steam["title"].map(normalize_title)

    # Do not automatically match ambiguous duplicate Steam titles.
    duplicated_keys = set(
        steam.loc[
            steam["_match_title"].duplicated(keep=False),
            "_match_title",
        ]
    )

    steam_lookup = steam[
        ~steam["_match_title"].isin(duplicated_keys)
    ].rename(
        columns={
            "title": "steam_title",
            "playtime_hours": "steam_playtime_hours",
            "last_played": "steam_last_played",
        }
    )

    steam_lookup = steam_lookup[
        [
            "_match_title",
            "steam_app_id",
            "steam_title",
            "steam_playtime_hours",
            "steam_last_played",
        ]
    ]

    combined = manual.merge(
        steam_lookup,
        on="_match_title",
        how="left",
        validate="many_to_one",
    )

    is_steam = (
        combined["storefront"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .eq("steam")
        .fillna(False)
    )

    steam_fields = [
        "steam_app_id",
        "steam_title",
        "steam_playtime_hours",
        "steam_last_played",
    ]

    # Prevent non-Steam purchases from receiving Steam information.
    combined.loc[~is_steam, steam_fields] = pd.NA

    combined["steam_match_status"] = "not_applicable"
    combined.loc[is_steam, "steam_match_status"] = "unmatched"
    combined.loc[
        is_steam & combined["steam_app_id"].notna(),
        "steam_match_status",
    ] = "matched"

    # Steam values replace blank/manual factual values.
    combined["playtime_hours"] = (
        combined["steam_playtime_hours"]
        .combine_first(combined["playtime_hours"])
    )

    combined["last_played"] = (
        combined["steam_last_played"]
        .combine_first(combined["last_played"])
    )

    combined["steam_app_id"] = (
        combined["steam_app_id"].astype("Int64")
    )

    return combined.drop(
        columns=[
            "_match_title",
            "steam_playtime_hours",
            "steam_last_played",
        ]
    )


def main() -> None:
    combined = match_libraries()

    combined.to_parquet(OUTPUT_PARQUET, index=False)
    combined.to_csv(OUTPUT_CSV, index=False)

    steam_games = combined[
        combined["storefront"]
        .astype("string")
        .str.casefold()
        .eq("steam")
    ]

    matched = steam_games[
        steam_games["steam_match_status"] == "matched"
    ]
    unmatched = steam_games[
        steam_games["steam_match_status"] == "unmatched"
    ]

    print(
        f"Matched {len(matched)} of "
        f"{len(steam_games)} manually labelled Steam games."
    )
    print(f"Saved: {OUTPUT_PARQUET}")
    print(f"Review copy: {OUTPUT_CSV}")

    if not unmatched.empty:
        steam = pd.read_parquet(STEAM_FILE)
        title_lookup = {
            normalize_title(title): title
            for title in steam["title"].dropna()
        }

        print("\nUnmatched titles:")

        for title in unmatched["title"]:
            suggestions = get_close_matches(
                normalize_title(title),
                title_lookup.keys(),
                n=3,
                cutoff=0.5,
            )
            suggested_titles = [
                title_lookup[key] for key in suggestions
            ]

            print(f"- {title}")
            if suggested_titles:
                print(
                    "  Possible Steam matches: "
                    + ", ".join(suggested_titles)
                )


if __name__ == "__main__":
    main()
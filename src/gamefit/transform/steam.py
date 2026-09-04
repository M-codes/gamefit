import json
from pathlib import Path

import pandas as pd

from gamefit.config import ROOT


RAW_STEAM_DIRECTORY = ROOT / "data" / "raw" / "steam"
PROCESSED_STEAM_FILE = ROOT / "data" / "processed" / "steam_library.parquet"


def find_latest_steam_file() -> Path:
    files = sorted(
        RAW_STEAM_DIRECTORY.glob("owned_games_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError(
            "No Steam JSON files found. Run the Steam extractor first."
        )

    return files[0]


def transform_steam_library(source: Path | None = None) -> pd.DataFrame:
    source = source or find_latest_steam_file()

    with source.open("r", encoding="utf-8") as file:
        data = json.load(file)

    games = data.get("response", {}).get("games", [])

    if not games:
        raise ValueError("The Steam response contains no games.")

    dataframe = pd.DataFrame(games)

    required_columns = {
        "appid",
        "name",
        "playtime_forever",
    }

    missing = required_columns - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Steam data is missing columns: {sorted(missing)}"
        )

    dataframe = dataframe.rename(
        columns={
            "appid": "steam_app_id",
            "name": "title",
            "playtime_forever": "playtime_minutes",
            "rtime_last_played": "last_played_timestamp",
        }
    )

    dataframe["steam_app_id"] = pd.to_numeric(
        dataframe["steam_app_id"],
        errors="raise",
    ).astype("int64")

    dataframe["title"] = dataframe["title"].astype("string").str.strip()

    dataframe["playtime_minutes"] = pd.to_numeric(
        dataframe["playtime_minutes"],
        errors="coerce",
    ).fillna(0)

    dataframe["playtime_hours"] = (
        dataframe["playtime_minutes"] / 60
    ).round(2)

    if "playtime_2weeks" in dataframe.columns:
        dataframe["playtime_2weeks_hours"] = (
            pd.to_numeric(
                dataframe["playtime_2weeks"],
                errors="coerce",
            ).fillna(0)
            / 60
        ).round(2)

    if "last_played_timestamp" in dataframe.columns:
        dataframe["last_played"] = pd.to_datetime(
            dataframe["last_played_timestamp"],
            unit="s",
            errors="coerce",
            utc=True,
        )

    dataframe["platform"] = "PC"
    dataframe["storefront"] = "Steam"

    if dataframe["steam_app_id"].duplicated().any():
        raise ValueError("Steam app IDs must be unique.")

    dataframe = dataframe.sort_values(
        by=["playtime_hours", "title"],
        ascending=[False, True],
    ).reset_index(drop=True)

    return dataframe


def main() -> None:
    dataframe = transform_steam_library()

    PROCESSED_STEAM_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        PROCESSED_STEAM_FILE,
        index=False,
    )

    print(f"Processed {len(dataframe)} Steam games.")
    print(f"Saved to: {PROCESSED_STEAM_FILE}")
    print("\nFive most-played games:")
    print(
        dataframe[
            ["steam_app_id", "title", "playtime_hours"]
        ].head()
    )


if __name__ == "__main__":
    main()
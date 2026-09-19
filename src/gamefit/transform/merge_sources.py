import pandas as pd

from gamefit.config import ROOT


LIBRARY_FILE = ROOT / "data" / "processed" / "library_enriched.csv"
RAWG_FILE = ROOT / "data" / "processed" / "rawg_match_review.csv"

MASTER_CSV = ROOT / "data" / "processed" / "gamefit_master.csv"
MASTER_PARQUET = ROOT / "data" / "processed" / "gamefit_master.parquet"

RAWG_COLUMNS = [
    "game_id",
    "rawg_id",
    "rawg_title",
    "released",
    "genres",
    "rawg_rating",
    "rawg_ratings_count",
    "metacritic_score",
    "typical_playtime_hours",
    "rawg_platforms",
    "rawg_url",
    "match_status",
    "match_note",
]


def require_unique_game_ids(df: pd.DataFrame, name: str) -> None:
    if df["game_id"].isna().any():
        raise ValueError(f"{name} contains a blank game_id")

    duplicates = df.loc[
        df["game_id"].duplicated(),
        "game_id",
    ].tolist()

    if duplicates:
        raise ValueError(
            f"{name} contains duplicate game_id values: {duplicates}"
        )


def main() -> None:
    if not LIBRARY_FILE.exists():
        raise FileNotFoundError(f"Cannot find {LIBRARY_FILE}")

    if not RAWG_FILE.exists():
        raise FileNotFoundError(f"Cannot find {RAWG_FILE}")

    library = pd.read_csv(LIBRARY_FILE)
    rawg = pd.read_csv(RAWG_FILE)

    require_unique_game_ids(library, "library_enriched.csv")
    require_unique_game_ids(rawg, "rawg_match_review.csv")

    if len(library) != 30 or len(rawg) != 30:
        raise ValueError(
            f"Expected 30 rows from each source, got "
            f"{len(library)} library rows and "
            f"{len(rawg)} RAWG rows"
        )

    if not rawg["match_status"].eq("matched").all():
        unresolved = rawg.loc[
            rawg["match_status"] != "matched",
            ["game_id", "source_title", "match_status"],
        ]

        raise ValueError(
            f"Unresolved RAWG matches remain:\n{unresolved}"
        )

    rawg_for_merge = rawg[RAWG_COLUMNS].rename(
        columns={
            "match_status": "rawg_match_status",
            "match_note": "rawg_match_note",
        }
    )

    master = library.merge(
        rawg_for_merge,
        on="game_id",
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    incomplete = master[master["_merge"] != "both"]

    if not incomplete.empty:
        raise ValueError(
            "Some rows did not exist in both sources:\n"
            f"{incomplete[['game_id', '_merge']]}"
        )

    master = master.drop(columns="_merge")
    master = master.sort_values("game_id").reset_index(drop=True)

    integer_columns = [
        "steam_app_id",
        "rawg_id",
        "rawg_ratings_count",
        "metacritic_score",
        "typical_playtime_hours",
    ]

    for column in integer_columns:
        master[column] = pd.to_numeric(
            master[column],
            errors="coerce",
        ).astype("Int64")

    if master["rawg_id"].isna().any():
        raise ValueError("At least one game is missing a RAWG ID")

    if not master["rawg_id"].is_unique:
        raise ValueError("Duplicate RAWG IDs exist in the master dataset")

    MASTER_CSV.parent.mkdir(parents=True, exist_ok=True)

    master.to_csv(MASTER_CSV, index=False)
    master.to_parquet(MASTER_PARQUET, index=False)

    print(f"Created master dataset with {len(master)} rows")
    print(f"Columns: {len(master.columns)}")
    print(f"CSV: {MASTER_CSV}")
    print(f"Parquet: {MASTER_PARQUET}")


if __name__ == "__main__":
    main()
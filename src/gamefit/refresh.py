import pandas as pd

from gamefit.load.postgres import load_staging
from gamefit.transform.merge_sources import MASTER_PARQUET

from gamefit.load.postgres import load_staging, merge_master

from gamefit.extract.steam import fetch_owned_games
from gamefit.transform.steam import (
    PROCESSED_STEAM_FILE,
    transform_steam_library,
)
from gamefit.config import ROOT
from gamefit.transform.library import load_manual
from gamefit.transform.match_library import (
    MANUAL_FILE,
    OUTPUT_CSV,
    OUTPUT_PARQUET,
    match_libraries,
)
from gamefit.transform.merge_sources import main as build_master


def main() -> None:
    print("Step 1: Fetching current Steam data...")
    _, source_path = fetch_owned_games()

    print("Step 2: Processing the fresh download...")
    steam_df = transform_steam_library(source_path)

    PROCESSED_STEAM_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    steam_df.to_parquet(
        PROCESSED_STEAM_FILE,
        index=False,
    )

    print(f"Refreshed {len(steam_df)} Steam games.")
    
    print("Step 3: Validating manual labels...")
    manual_df = load_manual(
        ROOT / "data" / "manual" / "library.csv"
    )
    manual_df.to_parquet(MANUAL_FILE, index=False)

    print("Step 4: Matching fresh Steam data...")
    enriched_df = match_libraries()

    unmatched = enriched_df.loc[
        enriched_df["steam_match_status"].eq("unmatched"),
        "title",
    ]
    if not unmatched.empty:
        raise ValueError(
            f"Unmatched Steam games: {unmatched.tolist()}"
        )

    enriched_df.to_parquet(OUTPUT_PARQUET, index=False)
    enriched_df.to_csv(OUTPUT_CSV, index=False)

    print("Step 5: Combining reviewed RAWG metadata...")
    build_master()

    print("Step 6: Loading master data into PostgreSQL staging...")
    master_df = pd.read_parquet(MASTER_PARQUET)
    load_staging(master_df)

    print(f"Loaded {len(master_df)} rows into analytics.stg_library.")
    
    print("Step 7: Merging into the main database tables...")
    merge_master()
    print("Database merge completed.")

if __name__ == "__main__":
    main()
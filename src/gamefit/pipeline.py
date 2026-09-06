from gamefit.config import ROOT
from gamefit.load.postgres import load_staging
from gamefit.transform.library import load_manual
from gamefit.transform.match_library import (
    OUTPUT_CSV,
    OUTPUT_PARQUET,
    match_libraries,
)


def main() -> None:
    manual_source = ROOT / "data" / "manual" / "library.csv"
    manual_target = ROOT / "data" / "processed" / "library.parquet"

    manual_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Validate and process the manually labelled CSV.
    manual_df = load_manual(manual_source)
    manual_df.to_parquet(manual_target, index=False)

    # Match manual labels with factual Steam information.
    enriched_df = match_libraries()
    enriched_df.to_parquet(OUTPUT_PARQUET, index=False)
    enriched_df.to_csv(OUTPUT_CSV, index=False)

    unmatched = enriched_df[
        enriched_df["steam_match_status"] == "unmatched"
    ]

    if not unmatched.empty:
        titles = unmatched["title"].tolist()
        raise ValueError(
            f"Cannot load unmatched Steam games: {titles}"
        )

    # Replace only the temporary staging table.
    load_staging(enriched_df)

    matched = (
        enriched_df["steam_match_status"] == "matched"
    ).sum()

    print(f"Validated {len(manual_df)} manual games.")
    print(f"Matched {matched} Steam games.")
    print(f"Saved enriched data to: {OUTPUT_PARQUET}")
    print(
        f"Loaded {len(enriched_df)} rows into "
        "analytics.stg_library."
    )


if __name__ == "__main__":
    main()
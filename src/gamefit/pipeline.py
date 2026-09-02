from gamefit.config import ROOT
from gamefit.load.postgres import load_staging
from gamefit.transform.library import load_manual


def main() -> None:
    source = ROOT / "data" / "manual" / "library.csv"
    target = ROOT / "data" / "processed" / "library.parquet"

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = load_manual(source)

    df.to_parquet(
        target,
        index=False,
    )

    load_staging(df)

    print(f"Wrote {len(df)} rows to {target}")
    print("Loaded rows into analytics.stg_library")


if __name__ == "__main__":
    main()
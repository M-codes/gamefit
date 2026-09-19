import pandas as pd
from sqlalchemy import create_engine, text

from gamefit.config import ROOT, Settings
from gamefit.load.postgres import load_staging


MASTER_FILE = ROOT / "data" / "processed" / "gamefit_master.parquet"


def main() -> None:
    if not MASTER_FILE.exists():
        raise FileNotFoundError(f"Cannot find {MASTER_FILE}")

    df = pd.read_parquet(MASTER_FILE)

    if len(df) != 30:
        raise ValueError(f"Expected 30 games, found {len(df)}")

    if df["game_id"].duplicated().any():
        raise ValueError("Duplicate game_id values found")

    if df["rawg_id"].isna().any():
        raise ValueError("Some games are missing RAWG IDs")

    # Uses your existing postgres.py function.
    load_staging(df)

    engine = create_engine(
        Settings().database_url,
        pool_pre_ping=True,
    )

    with engine.connect() as connection:
        database_count = connection.execute(
            text("SELECT COUNT(*) FROM analytics.stg_library")
        ).scalar_one()

    if database_count != len(df):
        raise ValueError(
            f"Loaded {len(df)} rows but PostgreSQL contains "
            f"{database_count} rows"
        )

    print(f"Loaded {len(df)} master rows into analytics.stg_library")
    print(f"Database row count confirmed: {database_count}")


if __name__ == "__main__":
    main()
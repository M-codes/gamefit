from pandas import DataFrame
from sqlalchemy import create_engine

from gamefit.config import Settings


def load_staging(df: DataFrame) -> None:
    database_url = Settings().database_url

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing from the .env file"
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    try:
        with engine.begin() as connection:
            df.to_sql(
                "stg_library",
                connection,
                schema="analytics",
                if_exists="replace",
                index=False,
                method="multi",
            )
    finally:
        engine.dispose()
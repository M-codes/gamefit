from pandas import DataFrame
from sqlalchemy import create_engine

from gamefit.config import Settings

from gamefit.config import ROOT

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

def merge_master() -> None:
    database_url = Settings().database_url
    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env")

    sql = (ROOT / "sql" / "005_merge_master.sql").read_text(
        encoding="utf-8-sig"
    )

    # The SQL file manages its own BEGIN / COMMIT transaction.
    engine = create_engine(
        database_url,
        isolation_level="AUTOCOMMIT",
    )

    try:
        connection = engine.raw_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                while cursor.nextset():
                    pass
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
    finally:
        engine.dispose()
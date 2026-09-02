import os 
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    steam_api_key: str = os.getenv("STEAM_API_KEY", "")
    steam_id64: str = os.getenv("STEAM_ID64", "")
    rawg_api_key: str = os.getenv("RAWG_API_KEY", "")
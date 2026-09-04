import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from gamefit.config import ROOT, Settings


STEAM_OWNED_GAMES_URL = (
    "https://api.steampowered.com/"
    "IPlayerService/GetOwnedGames/v0001/"
)


def fetch_owned_games() -> tuple[dict, Path]:
    settings = Settings()

    if not settings.steam_api_key:
        raise ValueError("STEAM_API_KEY is missing from .env")

    if not settings.steam_id64:
        raise ValueError("STEAM_ID64 is missing from .env")

    parameters = {
        "key": settings.steam_api_key,
        "steamid": settings.steam_id64,
        "include_appinfo": True,
        "include_played_free_games": True,
        "format": "json",
    }

    response = requests.get(
        STEAM_OWNED_GAMES_URL,
        params=parameters,
        timeout=30,
    )

    if response.status_code == 401:
        raise RuntimeError("Steam rejected the API key.")

    if response.status_code == 403:
        raise RuntimeError(
            "Steam denied access. Check your API key and "
            "Steam Game details privacy setting."
        )

    if response.status_code == 429:
        raise RuntimeError(
            "Steam rate limit reached. Wait before trying again."
        )

    response.raise_for_status()

    data = response.json()
    games = data.get("response", {}).get("games", [])

    output_directory = ROOT / "data" / "raw" / "steam"
    output_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_directory / f"owned_games_{timestamp}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print(f"Downloaded {len(games)} Steam games.")
    print(f"Saved raw response to: {output_path}")

    return data, output_path


def main() -> None:
    fetch_owned_games()


if __name__ == "__main__":
    main()
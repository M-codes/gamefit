from pathlib import Path

import pandas as pd


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    input_path = project_root / "data" / "manual" / "Gamelist.csv"
    output_path = project_root / "data" / "manual" / "library.csv"

    games = pd.read_csv(
        input_path,
        header=None,
        names=["title"],
        dtype="string",
        encoding="utf-8-sig",
    )

    games["title"] = games["title"].str.strip()
    games = games.dropna(subset=["title"])
    games = games[games["title"] != ""]
    games = games.drop_duplicates().reset_index(drop=True)

    library = pd.DataFrame(
        {
            "game_id": [
                f"manual-{number:03d}"
                for number in range(1, len(games) + 1)
            ],
            "title": games["title"],
            "platform": "PC",
            "storefront": "Steam",
        }
    )

    empty_columns = [
        "status",
        "personal_rating",
        "purchase_price_aud",
        "purchase_date",
        "playtime_hours",
        "last_played",
        "reason_stopped",
        "would_recommend",
        "play_context",
    ]

    for column in empty_columns:
        library[column] = ""

    library.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Created {len(library)} game rows")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
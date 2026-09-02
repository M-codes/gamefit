import pandas as pd
import pytest

from gamefit.transform.library import load_manual


def test_rejects_invalid_status(tmp_path) -> None:
    path = tmp_path / "library.csv"

    test_data = [
        {
            "game_id": "test-001",
            "title": "Test Game",
            "platform": "PC",
            "storefront": "Steam",
            "status": "forgotten",
            "personal_rating": None,
            "purchase_price_aud": None,
            "purchase_date": None,
            "playtime_hours": None,
            "last_played": None,
            "reason_stopped": None,
            "would_recommend": None,
            "play_context": None,
        }
    ]

    pd.DataFrame(test_data).to_csv(
        path,
        index=False,
    )

    with pytest.raises(
        ValueError,
        match="Invalid status",
    ):
        load_manual(path)
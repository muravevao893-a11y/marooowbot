from datetime import datetime, timezone

from app.texts import auto_drop_text, manual_post_text


def test_manual_text_contains_counter():
    text = manual_post_text("drop", "gift", 1, datetime.now(timezone.utc), 42)
    assert "drop" in text
    assert "42" in text
    assert "gift" in text


def test_auto_text_contains_chance():
    text = auto_drop_text("drop", "gift", datetime.now(timezone.utc), 1, 3)
    assert "3%" in text
    assert "gift" in text

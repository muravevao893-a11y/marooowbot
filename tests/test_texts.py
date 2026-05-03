from datetime import datetime, timezone

from app.texts import manual_giveaway_text, auto_drop_text


def test_manual_text_contains_counter():
    text = manual_giveaway_text("РОЗЫГРЫШ", "тест", "мишка", 3, datetime.now(timezone.utc), 42)
    assert "РОЗЫГРЫШ" in text
    assert "42" in text
    assert "мишка" in text


def test_auto_text_contains_chance():
    text = auto_drop_text("Кто хочет мишку?", "мишка", datetime.now(timezone.utc), 1, 3)
    assert "3%" in text
    assert "мишка" in text
    assert "Забрать мишку" in text

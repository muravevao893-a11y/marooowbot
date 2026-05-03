from app.utils.time import human_left


def test_human_left_seconds():
    assert human_left(5) == "5с"


def test_human_left_minutes():
    assert human_left(125) == "2м"


def test_human_left_hours():
    assert human_left(3700) == "1ч 1м"

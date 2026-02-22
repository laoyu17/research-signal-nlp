from research_signal_nlp.utils.text import normalize_text


def test_normalize_text_keeps_words_and_numbers() -> None:
    text = "  上调评级!!! EPS +20%  "
    out = normalize_text(text)
    assert "上调评级" in out
    assert "eps" in out
    assert "%" not in out

import pandas as pd

from research_signal_nlp.core.config import EventPatternConfig, LexiconConfig
from research_signal_nlp.signals.events import EventExtractor
from research_signal_nlp.signals.lexicon import LexiconSentimentExtractor


def test_lexicon_score_positive_greater_than_negative() -> None:
    extractor = LexiconSentimentExtractor.from_config(LexiconConfig())
    pos = extractor.score_text("公司业绩预增 上调 买入")
    neg = extractor.score_text("公司亏损 下调 风险")
    assert pos > neg


def test_event_extractor_detects_patterns() -> None:
    extractor = EventExtractor.from_config(EventPatternConfig())
    df = pd.DataFrame(
        {
            "text": ["券商上调公司评级并提高目标价，预计业绩预增"],
            "asset": ["000001.SZ"],
            "trade_date": ["2025-01-01"],
        }
    )
    transformed = extractor.transform(df)
    assert transformed.loc[0, "rating_upgrade"] == 1
    assert transformed.loc[0, "target_up"] == 1
    assert transformed.loc[0, "earnings_positive"] == 1

    events = extractor.extract_events(df)
    assert len(events) == 3


def test_event_extractor_deduplicates_same_asset_date_event_type() -> None:
    extractor = EventExtractor.from_config(EventPatternConfig())
    df = pd.DataFrame(
        {
            "text": ["上调公司评级", "再次上调公司评级"],
            "asset": ["000001.SZ", "000001.SZ"],
            "trade_date": ["2025-01-01", "2025-01-01"],
        }
    )
    events = extractor.extract_events(df)
    rating_row = events.loc[events["event_type"] == "rating_upgrade"].iloc[0]
    assert len(events) == 1
    assert rating_row["event_strength"] == 2.0

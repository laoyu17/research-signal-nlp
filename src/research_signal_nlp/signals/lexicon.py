"""Dictionary-based sentiment scoring."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from research_signal_nlp.core.config import LexiconConfig
from research_signal_nlp.signals.base import BaseExtractor
from research_signal_nlp.utils.text import normalize_text

DEFAULT_POSITIVE_WORDS = [
    "上调",
    "增持",
    "买入",
    "超预期",
    "改善",
    "增长",
    "新高",
    "利好",
    "提价",
    "盈利",
]

DEFAULT_NEGATIVE_WORDS = [
    "下调",
    "减持",
    "卖出",
    "低于预期",
    "恶化",
    "下降",
    "亏损",
    "利空",
    "处罚",
    "风险",
]


@dataclass(slots=True)
class LexiconSentimentExtractor(BaseExtractor):
    positive_words: list[str]
    negative_words: list[str]

    @classmethod
    def from_config(cls, config: LexiconConfig) -> LexiconSentimentExtractor:
        positives = config.positive_words or DEFAULT_POSITIVE_WORDS
        negatives = config.negative_words or DEFAULT_NEGATIVE_WORDS
        return cls(positive_words=positives, negative_words=negatives)

    def score_text(self, text: str) -> float:
        normalized = normalize_text(text)
        pos_hits = sum(normalized.count(w.lower()) for w in self.positive_words)
        neg_hits = sum(normalized.count(w.lower()) for w in self.negative_words)
        denom = pos_hits + neg_hits + 1.0
        return (pos_hits - neg_hits) / denom

    def transform(self, df: pd.DataFrame, text_col: str = "text") -> pd.Series:
        return df[text_col].fillna("").map(self.score_text).astype(float)

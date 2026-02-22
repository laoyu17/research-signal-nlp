"""Regex-based financial event extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from research_signal_nlp.core.config import EventPatternConfig
from research_signal_nlp.signals.base import BaseExtractor


@dataclass(slots=True)
class EventExtractor(BaseExtractor):
    rating_upgrade_patterns: list[re.Pattern[str]]
    target_up_patterns: list[re.Pattern[str]]
    earnings_positive_patterns: list[re.Pattern[str]]

    @classmethod
    def from_config(cls, config: EventPatternConfig) -> EventExtractor:
        return cls(
            rating_upgrade_patterns=[re.compile(p) for p in config.rating_upgrade_patterns],
            target_up_patterns=[re.compile(p) for p in config.target_up_patterns],
            earnings_positive_patterns=[re.compile(p) for p in config.earnings_positive_patterns],
        )

    @staticmethod
    def _contains_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
        return any(pattern.search(text) for pattern in patterns)

    def _extract_flags(self, text: str) -> dict[str, int]:
        return {
            "rating_upgrade": int(self._contains_any(text, self.rating_upgrade_patterns)),
            "target_up": int(self._contains_any(text, self.target_up_patterns)),
            "earnings_positive": int(self._contains_any(text, self.earnings_positive_patterns)),
        }

    def transform(self, df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
        rows = []
        for text in df[text_col].fillna(""):
            flags = self._extract_flags(text)
            event_score = float(sum(flags.values()) / 3.0)
            event_types = [k for k, v in flags.items() if v == 1]
            rows.append(
                {
                    **flags,
                    "event_score": event_score,
                    "event_types": ";".join(event_types),
                }
            )
        return pd.DataFrame(rows)

    def extract_events(
        self,
        df: pd.DataFrame,
        text_col: str = "text",
        asset_col: str = "asset",
        date_col: str = "trade_date",
    ) -> pd.DataFrame:
        event_rows: list[dict] = []
        for _, row in df.iterrows():
            flags = self._extract_flags(str(row.get(text_col, "")))
            for event_type, flag in flags.items():
                if flag:
                    event_rows.append(
                        {
                            "asset": row[asset_col],
                            "event_date": row[date_col],
                            "event_type": event_type,
                            "event_strength": 1.0,
                        }
                    )
        if not event_rows:
            return pd.DataFrame(columns=["asset", "event_date", "event_type", "event_strength"])
        events = pd.DataFrame(event_rows)
        return (
            events.groupby(["asset", "event_date", "event_type"], as_index=False, observed=True)[
                "event_strength"
            ]
            .sum()
            .sort_values(["event_date", "asset", "event_type"])
            .reset_index(drop=True)
        )

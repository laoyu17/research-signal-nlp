"""Base interfaces for signal extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseExtractor(ABC):
    @abstractmethod
    def transform(self, df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame | pd.Series:
        """Transform input dataframe into signal features."""

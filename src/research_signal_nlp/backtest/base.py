"""Base interface for backtest adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseBacktestAdapter(ABC):
    @abstractmethod
    def evaluate(self, *frames: pd.DataFrame) -> dict:
        """Return metrics dictionary from one or more dataframes."""

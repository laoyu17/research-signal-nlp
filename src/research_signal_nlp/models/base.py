"""Base interface for model plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class BaseModel(ABC):
    @abstractmethod
    def fit(self, texts: pd.Series, y: pd.Series) -> BaseModel:
        """Fit model from text and labels."""

    @abstractmethod
    def predict(self, texts: pd.Series) -> np.ndarray:
        """Predict numeric scores."""

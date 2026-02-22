"""TF-IDF + linear baseline model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge

from research_signal_nlp.core.config import ModelConfig
from research_signal_nlp.models.base import BaseModel


@dataclass(slots=True)
class TfidfLinearBaseline(BaseModel):
    model_type: str = "ridge"
    min_df: int = 2
    max_features: int = 5000

    def __post_init__(self) -> None:
        self.vectorizer = TfidfVectorizer(min_df=self.min_df, max_features=self.max_features)
        if self.model_type == "logistic":
            self.model = LogisticRegression(max_iter=1000)
        else:
            self.model = Ridge(alpha=1.0)
        self._fitted = False

    @classmethod
    def from_config(cls, config: ModelConfig) -> TfidfLinearBaseline:
        return cls(
            model_type=config.model_type,
            min_df=config.min_df,
            max_features=config.max_features,
        )

    def fit(self, texts: pd.Series, y: pd.Series) -> TfidfLinearBaseline:
        matrix = self.vectorizer.fit_transform(texts.fillna(""))
        self.model.fit(matrix, y)
        self._fitted = True
        return self

    def predict(self, texts: pd.Series) -> np.ndarray:
        if not self._fitted:
            # fallback when labels are unavailable: length-based weak prior
            values = texts.fillna("").str.len().to_numpy(dtype=float)
            std = values.std()
            return (values - values.mean()) / (std if std > 0 else 1.0)

        matrix = self.vectorizer.transform(texts.fillna(""))
        if self.model_type == "logistic":
            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(matrix)
                if probs.shape[1] == 1:
                    return probs[:, 0]
                return probs[:, -1]
            return self.model.decision_function(matrix)

        preds = self.model.predict(matrix)
        return np.asarray(preds, dtype=float)

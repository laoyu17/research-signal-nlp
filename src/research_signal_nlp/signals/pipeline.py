"""Signal construction pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from research_signal_nlp.core.config import SignalBuildConfig
from research_signal_nlp.data.ingest import ingest_text_data
from research_signal_nlp.models.tfidf_linear import TfidfLinearBaseline
from research_signal_nlp.signals.events import EventExtractor
from research_signal_nlp.signals.lexicon import LexiconSentimentExtractor
from research_signal_nlp.utils.io import read_table


@dataclass(slots=True)
class SignalBuildResult:
    scores: pd.DataFrame
    events: pd.DataFrame
    debug_frame: pd.DataFrame


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - series.mean()) / std


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(v, 0.0) for v in weights.values())
    if total <= 0:
        return {k: 1.0 / len(weights) for k in weights}
    return {k: max(v, 0.0) / total for k, v in weights.items()}


def _load_labels(path: str) -> pd.DataFrame:
    ext = Path(path).suffix.lower()
    fmt = "parquet" if ext == ".parquet" else "csv"
    labels = read_table(path, fmt)
    expected = {"id", "label"}
    missing = expected - set(labels.columns)
    if missing:
        raise ValueError(f"Label file missing required columns: {sorted(missing)}")
    return labels[["id", "label"]]


def _table_format_from_path(path: str) -> str:
    return "parquet" if Path(path).suffix.lower() == ".parquet" else "csv"


def _load_ingested_records(path: str) -> pd.DataFrame:
    records = read_table(path, _table_format_from_path(path))
    required = {"id", "asset", "source", "title", "body"}
    missing = required - set(records.columns)
    if missing:
        raise ValueError(f"Ingested records missing required columns: {sorted(missing)}")

    frame = records.copy()
    if "trade_date" in frame.columns:
        parsed_trade_date = pd.to_datetime(frame["trade_date"], errors="coerce")
    else:
        if "publish_time" not in frame.columns:
            raise ValueError(
                "Ingested records require trade_date, or publish_time for fallback conversion."
            )
        parsed_trade_date = pd.to_datetime(frame["publish_time"], errors="coerce")

    missing_trade_dates = int(parsed_trade_date.isna().sum())
    if missing_trade_dates > 0:
        raise ValueError(
            "Ingested records contain invalid or missing trade_date values "
            f"(count={missing_trade_dates})."
        )
    frame["trade_date"] = parsed_trade_date.dt.strftime("%Y-%m-%d")
    return frame


def _load_input_frame(config: SignalBuildConfig) -> pd.DataFrame:
    if config.ingested_records_path:
        ingested_path = Path(config.ingested_records_path)
        if ingested_path.exists():
            return _load_ingested_records(str(ingested_path))
        if not config.data_source:
            raise FileNotFoundError(
                f"Ingested records not found: {config.ingested_records_path}"
            )

    if not config.data_source:
        raise ValueError(
            "Signal build requires data_source when ingested_records_path is unavailable."
        )
    return ingest_text_data(config.data_source).data.copy()


def build_signal_scores(config: SignalBuildConfig) -> SignalBuildResult:
    df = _load_input_frame(config)
    if df.empty:
        raise ValueError("Signal input dataframe is empty after loading.")

    text_cols = [c for c in config.text_concat_fields if c in df.columns]
    if not text_cols:
        text_cols = ["title", "body"]
    df["text"] = df[text_cols].fillna("").agg(" ".join, axis=1)

    lexicon = LexiconSentimentExtractor.from_config(config.lexicon)
    event_extractor = EventExtractor.from_config(config.event_patterns)
    model = TfidfLinearBaseline.from_config(config.model)

    df["lexicon_score"] = lexicon.transform(df, text_col="text")
    event_df = event_extractor.transform(df, text_col="text")
    df = pd.concat([df, event_df], axis=1)

    if config.model.enabled:
        if config.train_label_path:
            labels = _load_labels(config.train_label_path)
            train_df = df.merge(labels, on="id", how="left")
            fit_df = train_df.dropna(subset=["label"])
            if len(fit_df) >= 10:
                try:
                    model.fit(fit_df["text"], fit_df["label"])
                except ValueError:
                    # Keep unfitted state and fallback to weak-prior prediction.
                    pass
            df["model_score"] = model.predict(df["text"])
        else:
            df["model_score"] = model.predict(df["text"])
    else:
        df["model_score"] = 0.0

    weights = _normalize_weights(
        {
            "lexicon_score": config.weights.lexicon,
            "event_score": config.weights.event,
            "model_score": config.weights.model,
        }
    )

    df["raw_score"] = (
        weights["lexicon_score"] * df["lexicon_score"]
        + weights["event_score"] * df["event_score"]
        + weights["model_score"] * df["model_score"]
    )

    df["score"] = df.groupby("trade_date", group_keys=False)["raw_score"].apply(_zscore)

    scores = df[
        [
            "asset",
            "trade_date",
            "score",
            "lexicon_score",
            "event_score",
            "model_score",
            "id",
            "source",
            "title",
        ]
    ].rename(columns={"id": "text_id"})
    scores["signal_name"] = config.signal_name
    scores["version"] = config.signal_version

    events = event_extractor.extract_events(
        df,
        text_col="text",
        asset_col="asset",
        date_col="trade_date",
    )

    return SignalBuildResult(scores=scores, events=events, debug_frame=df)

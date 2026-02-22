"""Data ingest and standardization."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from research_signal_nlp.core.config import DataSourceConfig
from research_signal_nlp.utils.io import read_table


@dataclass(slots=True)
class IngestResult:
    data: pd.DataFrame
    records_before: int
    records_after: int


def _normalize_publish_time(value: object, timezone: str) -> pd.Timestamp:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    if not isinstance(ts, pd.Timestamp):
        ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        return ts.tz_localize(timezone, ambiguous="NaT", nonexistent="NaT")
    return ts.tz_convert(timezone)


def ingest_text_data(config: DataSourceConfig) -> IngestResult:
    """Load data from source and normalize to project schema."""

    df = read_table(config.path, config.format)
    before = len(df)

    mapping = config.mapping
    rename_map = {
        mapping.id_field: "id",
        mapping.asset_field: "asset",
        mapping.publish_time_field: "publish_time",
        mapping.source_field: "source",
        mapping.title_field: "title",
        mapping.body_field: "body",
    }
    df = df.rename(columns=rename_map)

    required = ["id", "asset", "publish_time", "source", "title", "body"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns after mapping: {missing}")

    df = df[required].copy()
    df["publish_time"] = df["publish_time"].map(
        lambda value: _normalize_publish_time(value, config.timezone)
    )
    df = df.dropna(subset=["publish_time", "asset", "title", "body"])

    # Use mapped keys if user provided source names; fallback to standardized names.
    dedup_cols = []
    for col in config.deduplicate_by:
        dedup_cols.append(rename_map.get(col, col))
    dedup_cols = [c for c in dedup_cols if c in df.columns]
    if dedup_cols:
        df = df.drop_duplicates(subset=dedup_cols, keep="last")

    df["trade_date"] = df["publish_time"].dt.strftime("%Y-%m-%d")
    after = len(df)
    return IngestResult(data=df.reset_index(drop=True), records_before=before, records_after=after)

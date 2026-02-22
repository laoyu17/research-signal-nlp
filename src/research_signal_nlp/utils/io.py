"""I/O helpers for dataframes and json."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def read_table(path: str | Path, fmt: str) -> pd.DataFrame:
    if fmt == "csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent(path)
    target = Path(path)
    if target.suffix == ".csv":
        df.to_csv(target, index=False)
    else:
        df.to_parquet(target, index=False)


def write_json(payload: dict, path: str | Path) -> None:
    ensure_parent(path)
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)

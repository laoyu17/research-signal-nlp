from pathlib import Path

import pandas as pd
import pytest

from research_signal_nlp.utils.io import read_table


def test_read_table_supports_csv_case_insensitive(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    pd.DataFrame({"asset": ["A"], "value": [1]}).to_csv(path, index=False)

    loaded = read_table(path, "CSV")
    assert loaded.to_dict(orient="records") == [{"asset": "A", "value": 1}]


def test_read_table_rejects_unsupported_format_with_readable_error() -> None:
    with pytest.raises(ValueError, match="Unsupported table format 'json'"):
        read_table("artifacts/does-not-matter", "json", source="run_cs_backtest")

    with pytest.raises(ValueError, match="from run_cs_backtest"):
        read_table("artifacts/does-not-matter", "json", source="run_cs_backtest")

    with pytest.raises(ValueError, match="allowed values: csv, parquet"):
        read_table("artifacts/does-not-matter", "json", source="run_cs_backtest")

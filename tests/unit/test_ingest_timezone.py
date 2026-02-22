from pathlib import Path

import pandas as pd
import pytest

from research_signal_nlp.core.config import DataSourceConfig
from research_signal_nlp.data.ingest import ingest_text_data


def test_ingest_uses_timezone_for_trade_date(tmp_path: Path) -> None:
    source = tmp_path / "text.csv"
    pd.DataFrame(
        {
            "id": ["naive", "aware"],
            "asset": ["000001.SZ", "000002.SZ"],
            "publish_time": ["2025-01-01 09:00:00", "2025-01-01T16:30:00Z"],
            "source": ["news", "news"],
            "title": ["a", "b"],
            "body": ["x", "y"],
        }
    ).to_csv(source, index=False)

    cfg = DataSourceConfig(path=str(source), format="csv", timezone="Asia/Shanghai")
    result = ingest_text_data(cfg).data

    trade_dates = dict(zip(result["id"], result["trade_date"], strict=False))
    assert trade_dates["naive"] == "2025-01-01"
    assert trade_dates["aware"] == "2025-01-02"


def test_data_source_config_rejects_invalid_timezone(tmp_path: Path) -> None:
    source = tmp_path / "text.csv"
    pd.DataFrame(
        {
            "id": ["x"],
            "asset": ["000001.SZ"],
            "publish_time": ["2025-01-01 09:00:00"],
            "source": ["news"],
            "title": ["a"],
            "body": ["b"],
        }
    ).to_csv(source, index=False)

    with pytest.raises(ValueError, match="Invalid timezone"):
        DataSourceConfig(path=str(source), format="csv", timezone="Invalid/Timezone")

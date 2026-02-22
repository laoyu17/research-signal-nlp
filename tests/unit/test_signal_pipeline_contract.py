from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research_signal_nlp.core.config import SignalBuildConfig
from research_signal_nlp.signals.pipeline import build_signal_scores


def test_signal_pipeline_adds_contract_columns_and_handles_small_label_set(tmp_path: Path) -> None:
    text_path = tmp_path / "text.csv"
    label_path = tmp_path / "label.csv"

    pd.DataFrame(
        {
            "id": [f"id_{i}" for i in range(6)],
            "asset": ["A", "B", "C", "A", "B", "C"],
            "publish_time": [
                "2025-01-01 09:00:00",
                "2025-01-01 09:10:00",
                "2025-01-01 09:20:00",
                "2025-01-02 09:00:00",
                "2025-01-02 09:10:00",
                "2025-01-02 09:20:00",
            ],
            "source": ["news"] * 6,
            "title": ["上调评级", "维持买入", "风险提示", "业绩预增", "目标价上调", "卖出建议"],
            "body": [
                "公司增长稳健",
                "盈利改善",
                "下调预期",
                "净利润同比增长",
                "提高目标价",
                "存在亏损风险",
            ],
        }
    ).to_csv(text_path, index=False)

    # Intentionally keep labels < 10 so model falls back to weak prior prediction.
    pd.DataFrame({"id": ["id_0", "id_1", "id_2"], "label": [1, 1, 0]}).to_csv(
        label_path, index=False
    )

    cfg = SignalBuildConfig.model_validate(
        {
            "data_source": {"path": str(text_path), "format": "csv"},
            "train_label_path": str(label_path),
            "model": {"enabled": True, "model_type": "logistic", "min_df": 1},
            "signal_name": "test_signal",
            "signal_version": "0.9.0",
        }
    )
    result = build_signal_scores(cfg)

    score_df = result.scores
    assert {"signal_name", "version"} <= set(score_df.columns)
    assert score_df["signal_name"].nunique() == 1
    assert score_df["version"].nunique() == 1
    assert np.isfinite(score_df["model_score"]).all()


def test_signal_pipeline_fallbacks_when_logistic_labels_have_single_class(tmp_path: Path) -> None:
    text_path = tmp_path / "text.csv"
    label_path = tmp_path / "label.csv"

    rows = 12
    pd.DataFrame(
        {
            "id": [f"id_{i}" for i in range(rows)],
            "asset": [f"S{i % 4}" for i in range(rows)],
            "publish_time": [
                f"2025-01-{(i // 4) + 1:02d} 09:0{i % 6}:00" for i in range(rows)
            ],
            "source": ["news"] * rows,
            "title": ["上调评级"] * rows,
            "body": ["公司增长稳健"] * rows,
        }
    ).to_csv(text_path, index=False)

    # Keep >=10 labels but only one class to trigger logistic training fallback.
    pd.DataFrame({"id": [f"id_{i}" for i in range(rows)], "label": [1] * rows}).to_csv(
        label_path, index=False
    )

    cfg = SignalBuildConfig.model_validate(
        {
            "data_source": {"path": str(text_path), "format": "csv"},
            "train_label_path": str(label_path),
            "model": {"enabled": True, "model_type": "logistic", "min_df": 1},
        }
    )
    result = build_signal_scores(cfg)

    assert np.isfinite(result.scores["model_score"]).all()


def test_signal_pipeline_rejects_ingested_records_with_invalid_trade_date(tmp_path: Path) -> None:
    ingested_path = tmp_path / "records.csv"
    pd.DataFrame(
        {
            "id": ["id_1"],
            "asset": ["A"],
            "source": ["news"],
            "title": ["上调评级"],
            "body": ["公司增长稳健"],
            "publish_time": ["not-a-time"],
        }
    ).to_csv(ingested_path, index=False)

    cfg = SignalBuildConfig.model_validate(
        {
            "ingested_records_path": str(ingested_path),
            "model": {"enabled": False},
        }
    )

    with pytest.raises(ValueError, match="invalid or missing trade_date"):
        build_signal_scores(cfg)


def test_signal_pipeline_rejects_existing_trade_date_with_invalid_value(tmp_path: Path) -> None:
    ingested_path = tmp_path / "records.csv"
    pd.DataFrame(
        {
            "id": ["id_1", "id_2"],
            "asset": ["A", "B"],
            "source": ["news", "news"],
            "title": ["上调评级", "风险提示"],
            "body": ["公司增长稳健", "存在亏损风险"],
            "trade_date": ["2025-01-01", "bad-date"],
        }
    ).to_csv(ingested_path, index=False)

    cfg = SignalBuildConfig.model_validate(
        {
            "ingested_records_path": str(ingested_path),
            "model": {"enabled": False},
        }
    )

    with pytest.raises(ValueError, match="invalid or missing trade_date"):
        build_signal_scores(cfg)

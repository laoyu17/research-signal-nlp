from pathlib import Path

import pandas as pd
import pytest
import yaml

import research_signal_nlp.core.services as services


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_run_ingest_service_writes_output(tmp_path: Path) -> None:
    source_path = tmp_path / "source.csv"
    output_path = tmp_path / "ingested.parquet"
    config_path = tmp_path / "ingest.yaml"

    pd.DataFrame(
        {
            "id": ["a1", "a2"],
            "asset": ["000001.SZ", "000002.SZ"],
            "publish_time": ["2025-01-01 09:00:00", "2025-01-01 09:30:00"],
            "source": ["news", "news"],
            "title": ["t1", "t2"],
            "body": ["b1", "b2"],
        }
    ).to_csv(source_path, index=False)

    _write_yaml(
        config_path,
        {
            "path": str(source_path),
            "format": "csv",
            "mapping": {
                "id_field": "id",
                "asset_field": "asset",
                "publish_time_field": "publish_time",
                "source_field": "source",
                "title_field": "title",
                "body_field": "body",
            },
            "timezone": "Asia/Shanghai",
            "deduplicate_by": ["id"],
        },
    )

    result = services.run_ingest(str(config_path), str(output_path))
    assert result["records_after"] == 2
    assert Path(result["output_path"]).exists()


def test_run_regression_check_service_returns_dict_payload(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text('{"metrics":{"ic_mean":0.10,"ls_return_mean":0.02}}', encoding="utf-8")
    current.write_text('{"metrics":{"ic_mean":0.11,"ls_return_mean":0.024}}', encoding="utf-8")

    result = services.run_regression_check(
        str(baseline),
        str(current),
        ic_threshold=0.02,
        ls_threshold=0.01,
    )
    assert result["passed"] is True
    assert "delta_ic" in result
    assert "delta_ls" in result


def test_run_cs_backtest_rejects_invalid_payload_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    score_path = tmp_path / "scores.csv"
    returns_path = tmp_path / "returns.csv"
    config_path = tmp_path / "cs.yaml"

    pd.DataFrame(
        {
            "asset": ["A", "B"],
            "trade_date": ["2025-01-01", "2025-01-01"],
            "score": [0.3, -0.2],
        }
    ).to_csv(score_path, index=False)
    pd.DataFrame(
        {
            "asset": ["A", "B"],
            "trade_date": ["2025-01-01", "2025-01-01"],
            "fwd_return": [0.01, -0.005],
        }
    ).to_csv(returns_path, index=False)

    _write_yaml(
        config_path,
        {
            "score_path": str(score_path),
            "returns_path": str(returns_path),
            "returns_format": "csv",
            "output_path": str(tmp_path / "cs_metrics.json"),
            "quantiles": 2,
        },
    )

    monkeypatch.setattr(
        services.CrossSectionEvaluator,
        "evaluate",
        lambda self, *args, **kwargs: {"metrics": {"ic_mean": "bad"}},
    )

    with pytest.raises(ValueError, match="Invalid cs payload schema"):
        services.run_cs_backtest(str(config_path))


def test_run_event_backtest_rejects_invalid_payload_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events_path = tmp_path / "events.csv"
    returns_path = tmp_path / "returns.csv"
    config_path = tmp_path / "event.yaml"

    pd.DataFrame(
        {
            "asset": ["A"],
            "event_date": ["2025-01-01"],
            "event_type": ["rating_upgrade"],
            "event_strength": [1.0],
        }
    ).to_csv(events_path, index=False)
    pd.DataFrame(
        {
            "asset": ["A"],
            "trade_date": ["2025-01-02"],
            "return": [0.01],
            "benchmark_return": [0.0],
        }
    ).to_csv(returns_path, index=False)

    _write_yaml(
        config_path,
        {
            "events_path": str(events_path),
            "returns_path": str(returns_path),
            "returns_format": "csv",
            "output_path": str(tmp_path / "event_metrics.json"),
            "windows": [1],
        },
    )

    monkeypatch.setattr(
        services.EventStudyEvaluator,
        "evaluate",
        lambda self, *args, **kwargs: {
            "metrics": [{"event_type": "rating_upgrade", "window": "bad"}]
        },
    )

    with pytest.raises(ValueError, match="Invalid event payload schema"):
        services.run_event_backtest(str(config_path))

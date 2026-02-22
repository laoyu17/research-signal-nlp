from pathlib import Path

import yaml

from research_signal_nlp.core.config import DataSourceConfig
from research_signal_nlp.core.services import (
    run_cs_backtest,
    run_event_backtest,
    run_report,
    run_signal_build,
)
from research_signal_nlp.data.ingest import ingest_text_data
from research_signal_nlp.utils.io import read_json, read_table, write_table


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_full_pipeline_services(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    text_path = repo_root / "examples" / "data" / "text_sample.csv"
    label_path = repo_root / "examples" / "data" / "label_sample.csv"
    returns_path = repo_root / "examples" / "data" / "returns_sample.csv"
    ingested_path = tmp_path / "text_records.parquet"

    ingest_cfg = DataSourceConfig(path=str(text_path), format="csv")
    ingest_result = ingest_text_data(ingest_cfg)
    write_table(ingest_result.data, ingested_path)

    signal_cfg = {
        "ingested_records_path": str(ingested_path),
        "output_path": str(tmp_path / "signal_scores.parquet"),
        "events_output_path": str(tmp_path / "custom_events.parquet"),
        "debug_output_path": str(tmp_path / "custom_signal_debug.parquet"),
        "train_label_path": str(label_path),
        "model": {"enabled": True, "model_type": "logistic", "min_df": 1},
        "weights": {"lexicon": 0.4, "event": 0.3, "model": 0.3},
    }
    signal_cfg_path = tmp_path / "signal.yaml"
    _write_yaml(signal_cfg_path, signal_cfg)

    build_result = run_signal_build(str(signal_cfg_path))
    assert Path(build_result["score_path"]).exists()
    assert Path(build_result["event_path"]).exists()
    assert Path(build_result["debug_path"]).exists()
    assert build_result["event_path"] == str(tmp_path / "custom_events.parquet")
    assert build_result["debug_path"] == str(tmp_path / "custom_signal_debug.parquet")
    score_df = read_table(build_result["score_path"], "parquet")
    assert {"signal_name", "version"} <= set(score_df.columns)

    cs_cfg = {
        "score_path": build_result["score_path"],
        "returns_path": str(returns_path),
        "returns_format": "csv",
        "output_path": str(tmp_path / "cs_metrics.json"),
        "quantiles": 5,
    }
    cs_cfg_path = tmp_path / "cs.yaml"
    _write_yaml(cs_cfg_path, cs_cfg)
    cs_result = run_cs_backtest(str(cs_cfg_path))
    assert Path(cs_result["output_path"]).exists()

    event_cfg = {
        "events_path": build_result["event_path"],
        "returns_path": str(returns_path),
        "returns_format": "csv",
        "output_path": str(tmp_path / "event_metrics.json"),
        "windows": [1, 3],
    }
    event_cfg_path = tmp_path / "event.yaml"
    _write_yaml(event_cfg_path, event_cfg)
    event_result = run_event_backtest(str(event_cfg_path))
    assert Path(event_result["output_path"]).exists()
    event_payload = read_json(tmp_path / "event_metrics.json")
    assert "diagnostics" in event_payload

    report_cfg = {
        "run_name": "integration",
        "output_path": str(tmp_path / "report.html"),
        "cs_metrics_path": str(tmp_path / "cs_metrics.json"),
        "event_metrics_path": str(tmp_path / "event_metrics.json"),
    }
    report_cfg_path = tmp_path / "report.yaml"
    _write_yaml(report_cfg_path, report_cfg)
    report_result = run_report(str(report_cfg_path))
    assert Path(report_result["report_path"]).exists()

    cs_metrics = read_json(tmp_path / "cs_metrics.json")
    assert cs_metrics["metrics"]["ic_mean"] > -0.2

from pathlib import Path

import yaml
from typer.testing import CliRunner

from research_signal_nlp.cli import app

runner = CliRunner()


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_cli_end_to_end(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    text_path = repo_root / "examples" / "data" / "text_sample.csv"
    label_path = repo_root / "examples" / "data" / "label_sample.csv"
    returns_path = repo_root / "examples" / "data" / "returns_sample.csv"
    ingested_path = tmp_path / "text_records.parquet"

    ingest_cfg_path = tmp_path / "ingest.yaml"
    _write_yaml(
        ingest_cfg_path,
        {
            "path": str(text_path),
            "format": "csv",
            "mapping": {
                "id_field": "id",
                "asset_field": "asset",
                "publish_time_field": "publish_time",
                "source_field": "source",
                "title_field": "title",
                "body_field": "body",
            },
            "deduplicate_by": ["id"],
        },
    )

    signal_cfg_path = tmp_path / "signal.yaml"
    _write_yaml(
        signal_cfg_path,
        {
            "ingested_records_path": str(ingested_path),
            "output_path": str(tmp_path / "signal_scores.parquet"),
            "train_label_path": str(label_path),
            "model": {"enabled": True, "model_type": "logistic", "min_df": 1},
        },
    )

    cs_cfg_path = tmp_path / "cs.yaml"
    _write_yaml(
        cs_cfg_path,
        {
            "score_path": str(tmp_path / "signal_scores.parquet"),
            "returns_path": str(returns_path),
            "returns_format": "csv",
            "output_path": str(tmp_path / "cs_metrics.json"),
            "quantiles": 5,
        },
    )

    event_cfg_path = tmp_path / "event.yaml"
    _write_yaml(
        event_cfg_path,
        {
            "events_path": str(tmp_path / "events.parquet"),
            "returns_path": str(returns_path),
            "returns_format": "csv",
            "output_path": str(tmp_path / "event_metrics.json"),
            "windows": [1, 3],
        },
    )

    report_cfg_path = tmp_path / "report.yaml"
    _write_yaml(
        report_cfg_path,
        {
            "run_name": "e2e",
            "output_path": str(tmp_path / "report.html"),
            "cs_metrics_path": str(tmp_path / "cs_metrics.json"),
            "event_metrics_path": str(tmp_path / "event_metrics.json"),
        },
    )

    r0 = runner.invoke(
        app,
        ["ingest", "-c", str(ingest_cfg_path), "-o", str(ingested_path)],
    )
    assert r0.exit_code == 0, r0.stdout

    r1 = runner.invoke(app, ["build-signal", "-c", str(signal_cfg_path)])
    assert r1.exit_code == 0, r1.stdout

    r2 = runner.invoke(app, ["backtest", "cs", "-c", str(cs_cfg_path)])
    assert r2.exit_code == 0, r2.stdout

    r3 = runner.invoke(app, ["backtest", "event", "-c", str(event_cfg_path)])
    assert r3.exit_code == 0, r3.stdout

    r4 = runner.invoke(app, ["report", "-c", str(report_cfg_path)])
    assert r4.exit_code == 0, r4.stdout

    baseline_path = tmp_path / "baseline_cs.json"
    baseline_payload = (tmp_path / "cs_metrics.json").read_text(encoding="utf-8")
    baseline_path.write_text(baseline_payload, encoding="utf-8")
    r5 = runner.invoke(
        app,
        [
            "check-regression",
            "-b",
            str(baseline_path),
            "-c",
            str(tmp_path / "cs_metrics.json"),
        ],
    )
    assert r5.exit_code == 0, r5.stdout

    assert (tmp_path / "report.html").exists()

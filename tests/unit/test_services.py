from pathlib import Path

import pandas as pd
import yaml

from research_signal_nlp.core.services import run_ingest, run_regression_check


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

    result = run_ingest(str(config_path), str(output_path))
    assert result["records_after"] == 2
    assert Path(result["output_path"]).exists()


def test_run_regression_check_service_returns_dict_payload(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text('{"metrics":{"ic_mean":0.10,"ls_return_mean":0.02}}', encoding="utf-8")
    current.write_text('{"metrics":{"ic_mean":0.11,"ls_return_mean":0.024}}', encoding="utf-8")

    result = run_regression_check(str(baseline), str(current), ic_threshold=0.02, ls_threshold=0.01)
    assert result["passed"] is True
    assert "delta_ic" in result
    assert "delta_ls" in result

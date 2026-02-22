import json
from pathlib import Path

import pytest

from research_signal_nlp.core.config import ReportConfig
from research_signal_nlp.reporting.report import build_html_report


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_html_report_allows_missing_files_in_compat_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "report.html"
    cfg = ReportConfig(
        run_name="compat",
        output_path=str(output_path),
        cs_metrics_path=str(tmp_path / "missing_cs.json"),
        event_metrics_path=str(tmp_path / "missing_event.json"),
        strict_inputs=False,
    )

    report_path = build_html_report(cfg)
    assert Path(report_path).exists()
    html = Path(report_path).read_text(encoding="utf-8")
    assert "无横截面结果" in html
    assert "无事件研究结果" in html


def test_build_html_report_rejects_missing_file_in_strict_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "report.html"
    cfg = ReportConfig(
        run_name="strict",
        output_path=str(output_path),
        cs_metrics_path=str(tmp_path / "missing_cs.json"),
        event_metrics_path=str(tmp_path / "missing_event.json"),
        strict_inputs=True,
    )

    with pytest.raises(FileNotFoundError, match="cs_metrics file not found"):
        build_html_report(cfg)


def test_build_html_report_rejects_missing_metrics_field_in_strict_mode(tmp_path: Path) -> None:
    cs_path = tmp_path / "cs_metrics.json"
    event_path = tmp_path / "event_metrics.json"
    _write_json(cs_path, {"daily_ic": [], "daily_ls": []})
    _write_json(event_path, {"metrics": []})

    cfg = ReportConfig(
        run_name="strict",
        output_path=str(tmp_path / "report.html"),
        cs_metrics_path=str(cs_path),
        event_metrics_path=str(event_path),
        strict_inputs=True,
    )

    with pytest.raises(ValueError, match="CS metrics payload"):
        build_html_report(cfg)


def test_build_html_report_succeeds_with_valid_files_in_strict_mode(tmp_path: Path) -> None:
    cs_path = tmp_path / "cs_metrics.json"
    event_path = tmp_path / "event_metrics.json"
    _write_json(
        cs_path,
        {
            "metrics": {
                "ic_mean": 0.1,
                "ic_ir": 1.0,
                "rank_ic_mean": 0.08,
                "ls_return_mean": 0.02,
                "turnover_mean": 0.3,
            },
            "daily_ic": [],
            "daily_ls": [],
        },
    )
    _write_json(event_path, {"metrics": []})

    cfg = ReportConfig(
        run_name="strict",
        output_path=str(tmp_path / "report.html"),
        cs_metrics_path=str(cs_path),
        event_metrics_path=str(event_path),
        strict_inputs=True,
    )

    report_path = build_html_report(cfg)
    assert Path(report_path).exists()

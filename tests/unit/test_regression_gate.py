import json
from pathlib import Path

import pytest

from research_signal_nlp.core.regression import check_cs_regression


def _write_metrics(path: Path, ic_mean: float, ls_mean: float) -> None:
    payload = {"metrics": {"ic_mean": ic_mean, "ls_return_mean": ls_mean}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_check_cs_regression_passes_within_threshold(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_metrics(baseline, ic_mean=0.2, ls_mean=0.03)
    _write_metrics(current, ic_mean=0.205, ls_mean=0.034)

    result = check_cs_regression(
        baseline_path=baseline,
        current_path=current,
        ic_threshold=0.01,
        ls_threshold=0.005,
    )
    assert result.passed is True


def test_check_cs_regression_fails_when_delta_exceeds_threshold(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_metrics(baseline, ic_mean=0.2, ls_mean=0.03)
    _write_metrics(current, ic_mean=0.25, ls_mean=0.04)

    result = check_cs_regression(
        baseline_path=baseline,
        current_path=current,
        ic_threshold=0.01,
        ls_threshold=0.005,
    )
    assert result.passed is False
    assert result.delta_ic == pytest.approx(0.05)

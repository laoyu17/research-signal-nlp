"""Regression gate helpers for cross-sectional metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from research_signal_nlp.utils.io import read_json


@dataclass(slots=True)
class RegressionCheckResult:
    delta_ic: float
    delta_ls: float
    ic_threshold: float
    ls_threshold: float
    passed: bool


def _read_metric(path: str | Path, metric_name: str) -> float:
    payload = read_json(path)
    metrics = payload.get("metrics", {})
    if metric_name not in metrics:
        raise ValueError(f"Metric '{metric_name}' not found in {path}")
    return float(metrics[metric_name])


def check_cs_regression(
    baseline_path: str | Path,
    current_path: str | Path,
    ic_threshold: float = 0.01,
    ls_threshold: float = 0.005,
) -> RegressionCheckResult:
    baseline_ic = _read_metric(baseline_path, "ic_mean")
    current_ic = _read_metric(current_path, "ic_mean")
    baseline_ls = _read_metric(baseline_path, "ls_return_mean")
    current_ls = _read_metric(current_path, "ls_return_mean")

    delta_ic = current_ic - baseline_ic
    delta_ls = current_ls - baseline_ls
    passed = abs(delta_ic) <= ic_threshold and abs(delta_ls) <= ls_threshold

    return RegressionCheckResult(
        delta_ic=delta_ic,
        delta_ls=delta_ls,
        ic_threshold=ic_threshold,
        ls_threshold=ls_threshold,
        passed=passed,
    )

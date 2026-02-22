"""Application services used by CLI and GUI."""

from __future__ import annotations

from pathlib import Path

from research_signal_nlp.backtest.cross_section import CrossSectionEvaluator
from research_signal_nlp.backtest.event_study import EventStudyEvaluator
from research_signal_nlp.core.config import (
    CrossSectionBacktestConfig,
    DataSourceConfig,
    EventBacktestConfig,
    ReportConfig,
    SignalBuildConfig,
    load_config,
)
from research_signal_nlp.core.regression import check_cs_regression
from research_signal_nlp.data.ingest import ingest_text_data
from research_signal_nlp.reporting.report import build_html_report
from research_signal_nlp.signals.pipeline import build_signal_scores
from research_signal_nlp.utils.io import read_table, write_json, write_table


def run_ingest(
    config_path: str,
    output_path: str = "artifacts/text_records.parquet",
) -> dict:
    cfg = load_config(config_path, DataSourceConfig)
    result = ingest_text_data(cfg)
    write_table(result.data, output_path)
    return {
        "output_path": output_path,
        "records_before": result.records_before,
        "records_after": result.records_after,
    }


def run_signal_build(config_path: str) -> dict:
    cfg = load_config(config_path, SignalBuildConfig)
    result = build_signal_scores(cfg)

    write_table(result.scores, cfg.output_path)

    event_path = cfg.events_output_path or str(
        Path(cfg.output_path).with_name("events.parquet")
    )
    debug_path = cfg.debug_output_path or str(
        Path(cfg.output_path).with_name("signal_debug.parquet")
    )
    write_table(result.events, event_path)
    write_table(result.debug_frame, debug_path)

    return {
        "score_path": cfg.output_path,
        "event_path": event_path,
        "debug_path": debug_path,
        "rows": len(result.scores),
    }


def run_cs_backtest(config_path: str) -> dict:
    cfg = load_config(config_path, CrossSectionBacktestConfig)
    score_fmt = "parquet" if str(cfg.score_path).endswith(".parquet") else "csv"
    score_df = read_table(cfg.score_path, score_fmt)
    returns_df = read_table(cfg.returns_path, cfg.returns_format)

    evaluator = CrossSectionEvaluator(quantiles=cfg.quantiles)
    payload = evaluator.evaluate(score_df, returns_df)
    write_json(payload, cfg.output_path)
    return {"output_path": cfg.output_path, "metrics": payload.get("metrics", {})}


def run_event_backtest(config_path: str) -> dict:
    cfg = load_config(config_path, EventBacktestConfig)
    events_fmt = "parquet" if str(cfg.events_path).endswith(".parquet") else "csv"
    events_df = read_table(cfg.events_path, events_fmt)
    returns_df = read_table(cfg.returns_path, cfg.returns_format)

    evaluator = EventStudyEvaluator(windows=cfg.windows)
    payload = evaluator.evaluate(events_df, returns_df)
    write_json(payload, cfg.output_path)
    return {"output_path": cfg.output_path, "metric_rows": len(payload.get("metrics", []))}


def run_report(config_path: str) -> dict:
    cfg = load_config(config_path, ReportConfig)
    report_path = build_html_report(cfg)
    return {"report_path": report_path}


def run_regression_check(
    baseline_path: str,
    current_path: str,
    ic_threshold: float = 0.01,
    ls_threshold: float = 0.005,
) -> dict:
    result = check_cs_regression(
        baseline_path=baseline_path,
        current_path=current_path,
        ic_threshold=ic_threshold,
        ls_threshold=ls_threshold,
    )
    return {
        "passed": result.passed,
        "delta_ic": result.delta_ic,
        "delta_ls": result.delta_ls,
        "ic_threshold": result.ic_threshold,
        "ls_threshold": result.ls_threshold,
    }

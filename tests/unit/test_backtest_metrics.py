import pandas as pd
import pytest

from research_signal_nlp.backtest.cross_section import CrossSectionEvaluator
from research_signal_nlp.backtest.event_study import EventStudyEvaluator


def test_cross_section_evaluator_outputs_metrics() -> None:
    score_df = pd.DataFrame(
        {
            "asset": ["A", "B", "C", "A", "B", "C"],
            "trade_date": ["2025-01-01"] * 3 + ["2025-01-02"] * 3,
            "score": [0.9, 0.2, -0.3, 0.8, 0.1, -0.2],
        }
    )
    returns_df = pd.DataFrame(
        {
            "asset": ["A", "B", "C", "A", "B", "C"],
            "trade_date": ["2025-01-01"] * 3 + ["2025-01-02"] * 3,
            "fwd_return": [0.02, 0.00, -0.01, 0.015, 0.002, -0.005],
        }
    )

    payload = CrossSectionEvaluator(quantiles=3).evaluate(score_df, returns_df)
    assert "metrics" in payload
    assert payload["metrics"]["ic_mean"] > 0


def test_event_study_evaluator_outputs_metrics() -> None:
    events_df = pd.DataFrame(
        {
            "asset": ["A", "A"],
            "event_date": ["2025-01-01", "2025-01-03"],
            "event_type": ["rating_upgrade", "target_up"],
        }
    )
    returns_df = pd.DataFrame(
        {
            "asset": ["A"] * 6,
            "trade_date": [
                "2025-01-01",
                "2025-01-02",
                "2025-01-03",
                "2025-01-06",
                "2025-01-07",
                "2025-01-08",
            ],
            "return": [0.0, 0.01, 0.0, 0.02, -0.01, 0.01],
            "benchmark_return": [0.0, 0.001, 0.0, 0.001, 0.001, 0.001],
        }
    )

    payload = EventStudyEvaluator(windows=[1, 2]).evaluate(events_df, returns_df)
    assert len(payload["metrics"]) >= 1


def test_event_study_window_excludes_event_day_return() -> None:
    events_df = pd.DataFrame(
        {
            "asset": ["A"],
            "event_date": ["2025-01-01"],
            "event_type": ["rating_upgrade"],
        }
    )
    returns_df = pd.DataFrame(
        {
            "asset": ["A", "A", "A"],
            "trade_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "return": [0.5, 0.01, 0.02],
            "benchmark_return": [0.0, 0.0, 0.0],
        }
    )

    payload = EventStudyEvaluator(windows=[1]).evaluate(events_df, returns_df)
    assert payload["event_details"][0]["car"] == pytest.approx(0.01)
    assert payload["diagnostics"]["event_type_count"] == 1
    assert payload["diagnostics"]["full_overlap_event_types"] is False


def test_event_study_reports_full_overlap_event_types() -> None:
    events_df = pd.DataFrame(
        {
            "asset": ["A", "A"],
            "event_date": ["2025-01-01", "2025-01-01"],
            "event_type": ["rating_upgrade", "target_up"],
        }
    )
    returns_df = pd.DataFrame(
        {
            "asset": ["A", "A"],
            "trade_date": ["2025-01-02", "2025-01-03"],
            "return": [0.01, 0.02],
            "benchmark_return": [0.0, 0.0],
        }
    )

    payload = EventStudyEvaluator(windows=[1]).evaluate(events_df, returns_df)
    assert payload["diagnostics"]["event_type_count"] == 2
    assert payload["diagnostics"]["full_overlap_event_types"] is True


def test_cross_section_evaluator_reports_missing_columns() -> None:
    score_df = pd.DataFrame({"asset": ["A"], "trade_date": ["2025-01-01"]})
    returns_df = pd.DataFrame(
        {"asset": ["A"], "trade_date": ["2025-01-01"], "fwd_return": [0.01]}
    )

    with pytest.raises(ValueError, match="score_df missing required columns"):
        CrossSectionEvaluator(quantiles=3).evaluate(score_df, returns_df)


def test_event_study_reports_missing_columns() -> None:
    events_df = pd.DataFrame({"asset": ["A"], "event_date": ["2025-01-01"]})
    returns_df = pd.DataFrame(
        {
            "asset": ["A"],
            "trade_date": ["2025-01-02"],
            "return": [0.01],
        }
    )

    with pytest.raises(ValueError, match="events_df missing required columns"):
        EventStudyEvaluator(windows=[1]).evaluate(events_df, returns_df)


def test_event_study_reports_invalid_event_date_values() -> None:
    events_df = pd.DataFrame(
        {
            "asset": ["A"],
            "event_date": ["bad-date"],
            "event_type": ["rating_upgrade"],
        }
    )
    returns_df = pd.DataFrame(
        {
            "asset": ["A", "A"],
            "trade_date": ["2025-01-02", "2025-01-03"],
            "return": [0.01, 0.02],
        }
    )

    with pytest.raises(ValueError, match="invalid event_date"):
        EventStudyEvaluator(windows=[1]).evaluate(events_df, returns_df)


def test_cross_section_rejects_quantiles_less_than_two() -> None:
    score_df = pd.DataFrame(
        {"asset": ["A", "B"], "trade_date": ["2025-01-01", "2025-01-01"], "score": [0.1, -0.1]}
    )
    returns_df = pd.DataFrame(
        {
            "asset": ["A", "B"],
            "trade_date": ["2025-01-01", "2025-01-01"],
            "fwd_return": [0.01, -0.01],
        }
    )

    with pytest.raises(ValueError, match="quantiles must be >="):
        CrossSectionEvaluator(quantiles=1).evaluate(score_df, returns_df)

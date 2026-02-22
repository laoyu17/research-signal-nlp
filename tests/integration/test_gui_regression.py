import os
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from research_signal_nlp.gui import app as gui_app

_APP = QApplication.instance() or QApplication([])


class _ImmediateSignal:
    def __init__(self, payload: Any | None = None) -> None:
        self._payload = payload

    def connect(self, callback: Any) -> None:
        callback(self._payload)


class _NoopSignal:
    def connect(self, callback: Any) -> None:
        _ = callback


class _ImmediateSignals:
    def __init__(self, payload: Any) -> None:
        self.finished = _ImmediateSignal(payload)
        self.failed = _NoopSignal()


class _ImmediateTaskRunner:
    def __init__(self, fn: Any) -> None:
        self._fn = fn

    def run(self, *args: Any, **kwargs: Any) -> tuple[object, _ImmediateSignals]:
        result = self._fn(*args, **kwargs)
        return object(), _ImmediateSignals(result)


def _ensure_app() -> QApplication:
    return _APP


def test_data_manager_tab_runs_ingest_and_updates_preview_path(monkeypatch: Any) -> None:
    _ensure_app()
    monkeypatch.setattr(gui_app, "TaskRunner", _ImmediateTaskRunner)
    monkeypatch.setattr(
        gui_app,
        "run_ingest",
        lambda config, output: {
            "output_path": output,
            "records_before": 12,
            "records_after": 10,
        },
    )

    tab = gui_app.DataManagerTab()
    load_calls: list[str] = []
    done_calls: list[str] = []
    monkeypatch.setattr(tab, "_load", lambda: load_calls.append("ok"))
    monkeypatch.setattr(tab, "_handle_done", lambda message: done_calls.append(message))

    tab.ingest_config_input.setText("configs/data_source.yaml")
    tab.ingest_output_input.setText("artifacts/from_gui.parquet")
    tab._run_ingest()

    assert tab.file_input.text() == "artifacts/from_gui.parquet"
    assert load_calls == ["ok"]
    assert done_calls
    assert "[DONE]" in tab.ingest_log.toPlainText()


def test_evaluation_board_tab_runs_regression_gate(monkeypatch: Any) -> None:
    _ensure_app()
    monkeypatch.setattr(gui_app, "TaskRunner", _ImmediateTaskRunner)
    monkeypatch.setattr(
        gui_app,
        "run_regression_check",
        lambda baseline, current, ic, ls: {
            "passed": True,
            "delta_ic": 0.001,
            "delta_ls": -0.002,
            "ic_threshold": ic,
            "ls_threshold": ls,
        },
    )

    tab = gui_app.EvaluationBoardTab()
    tab.baseline_input.setText("tests/baseline/cs_metrics_baseline.json")
    tab.current_input.setText("artifacts/cs_metrics.json")
    tab.ic_threshold_input.setText("0.01")
    tab.ls_threshold_input.setText("0.005")
    tab._run_regression_gate()

    assert "PASS" in tab.gate_result.text()
    assert "ΔIC=0.001000" in tab.gate_result.text()


def test_evaluation_board_tab_validates_threshold_input(monkeypatch: Any) -> None:
    _ensure_app()
    tab = gui_app.EvaluationBoardTab()
    errors: list[str] = []
    monkeypatch.setattr(tab, "_handle_error", lambda message: errors.append(message))

    tab.baseline_input.setText("tests/baseline/cs_metrics_baseline.json")
    tab.current_input.setText("artifacts/cs_metrics.json")
    tab.ic_threshold_input.setText("not-a-number")
    tab._run_regression_gate()

    assert errors == ["阈值必须是数字"]

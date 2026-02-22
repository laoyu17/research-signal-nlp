import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEventLoop, QThread, QTimer
from PyQt6.QtWidgets import QApplication

from research_signal_nlp.gui.worker import TaskRunner, WorkerSignals

_APP = QApplication.instance() or QApplication([])


def _ensure_app() -> QApplication:
    return _APP


def _wait_for_task_result(
    thread: QThread,
    signals: WorkerSignals,
    timeout_ms: int = 3000,
) -> dict[str, object]:
    _ensure_app()
    loop = QEventLoop()
    state: dict[str, object] = {}
    timed_out = {"value": False}

    def on_finished(payload: object) -> None:
        state["payload"] = payload
        loop.quit()

    def on_failed(error: str) -> None:
        state["error"] = error
        loop.quit()

    def on_timeout() -> None:
        timed_out["value"] = True
        loop.quit()

    signals.finished.connect(on_finished)
    signals.failed.connect(on_failed)
    QTimer.singleShot(timeout_ms, on_timeout)
    loop.exec()
    assert not timed_out["value"], "TaskRunner timed out before emitting signals."

    deadline = time.monotonic() + 1.0
    while thread.isRunning() and time.monotonic() < deadline:
        _APP.processEvents()
        time.sleep(0.01)

    assert not thread.isRunning()
    return state


def _wait_for_cleanup(runner: TaskRunner, timeout_sec: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_sec
    while runner._active_jobs and time.monotonic() < deadline:
        _APP.processEvents()
        time.sleep(0.01)


def test_task_runner_emits_finished_and_cleans_up_job_refs() -> None:
    _ensure_app()
    runner = TaskRunner(lambda value: value + 1)
    thread, signals = runner.run(41)
    state = _wait_for_task_result(thread, signals)
    _wait_for_cleanup(runner)

    assert state["payload"] == 42
    assert "error" not in state
    assert runner._active_jobs == []


def test_task_runner_emits_failed_and_cleans_up_job_refs() -> None:
    _ensure_app()

    def _raise_runtime_error() -> None:
        raise RuntimeError("boom")

    runner = TaskRunner(_raise_runtime_error)
    thread, signals = runner.run()
    state = _wait_for_task_result(thread, signals)
    _wait_for_cleanup(runner)

    assert "payload" not in state
    assert "boom" in str(state["error"])
    assert runner._active_jobs == []

"""Background worker for long-running tasks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


@dataclass
class TaskRunner:
    fn: Callable[..., Any]
    # Keep strong references to thread/task pairs until thread finishes.
    _active_jobs: list[tuple[QThread, QObject]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def run(self, *args: Any, **kwargs: Any) -> tuple[QThread, WorkerSignals]:
        signals = WorkerSignals()
        thread = QThread()

        class _Task(QObject):
            def start(self) -> None:
                try:
                    result = self._fn(*self._args, **self._kwargs)
                    signals.finished.emit(result)
                except Exception as exc:  # pragma: no cover - GUI runtime path
                    signals.failed.emit(str(exc))
                finally:
                    thread.quit()

            def __init__(
                self,
                fn: Callable[..., Any],
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
            ) -> None:
                super().__init__()
                self._fn = fn
                self._args = args
                self._kwargs = kwargs

        task = _Task(self.fn, args, kwargs)
        task.moveToThread(thread)

        self._active_jobs.append((thread, task))

        def _cleanup() -> None:
            for i, (active_thread, _) in enumerate(self._active_jobs):
                if active_thread is thread:
                    self._active_jobs.pop(i)
                    break
            task.deleteLater()
            thread.deleteLater()

        thread.finished.connect(_cleanup)
        thread.started.connect(task.start)
        thread.start()
        return thread, signals

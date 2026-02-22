"""PyQt6 research workstation UI."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from research_signal_nlp.core.services import (
    run_cs_backtest,
    run_event_backtest,
    run_ingest,
    run_regression_check,
    run_report,
    run_signal_build,
)
from research_signal_nlp.utils.io import read_json

from .worker import TaskRunner


class BaseTaskTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._active_runners: list[TaskRunner] = []

    def _handle_done(self, message: str) -> None:
        QMessageBox.information(self, "任务完成", message)

    def _handle_error(self, error: str) -> None:
        QMessageBox.critical(self, "任务失败", error)

    def _start_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        runner = TaskRunner(fn)
        thread, signals = runner.run(*args, **kwargs)
        self._active_runners.append(runner)

        def _cleanup_runner() -> None:
            self._active_runners = [
                active for active in self._active_runners if active is not runner
            ]

        finished_signal = getattr(thread, "finished", None)
        if finished_signal is not None and hasattr(finished_signal, "connect"):
            finished_signal.connect(_cleanup_runner)
        else:
            _cleanup_runner()
        return signals


class DataManagerTab(BaseTaskTab):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        ingest_group = QGroupBox("数据标准化（ingest）")
        ingest_grid = QGridLayout(ingest_group)

        self.ingest_config_input = QLineEdit("configs/data_source.yaml")
        self.ingest_output_input = QLineEdit("artifacts/text_records.parquet")
        ingest_browse_btn = QPushButton("配置文件")
        ingest_output_btn = QPushButton("输出路径")
        ingest_run_btn = QPushButton("运行 ingest")
        self.ingest_progress = QProgressBar()
        self.ingest_progress.setVisible(False)
        self.ingest_log = QTextEdit()
        self.ingest_log.setReadOnly(True)

        ingest_browse_btn.clicked.connect(self._browse_ingest_config)
        ingest_output_btn.clicked.connect(self._browse_ingest_output)
        ingest_run_btn.clicked.connect(self._run_ingest)

        ingest_grid.addWidget(QLabel("Config"), 0, 0)
        ingest_grid.addWidget(self.ingest_config_input, 0, 1)
        ingest_grid.addWidget(ingest_browse_btn, 0, 2)
        ingest_grid.addWidget(QLabel("Output"), 1, 0)
        ingest_grid.addWidget(self.ingest_output_input, 1, 1)
        ingest_grid.addWidget(ingest_output_btn, 1, 2)
        ingest_grid.addWidget(ingest_run_btn, 2, 1)
        ingest_grid.addWidget(self.ingest_progress, 3, 0, 1, 3)

        file_bar = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("选择文本数据文件（csv/parquet）")
        browse_btn = QPushButton("浏览")
        load_btn = QPushButton("加载预览")

        browse_btn.clicked.connect(self._browse)
        load_btn.clicked.connect(self._load)

        file_bar.addWidget(self.file_input)
        file_bar.addWidget(browse_btn)
        file_bar.addWidget(load_btn)

        self.summary_label = QLabel("尚未加载数据")
        self.summary_label.setObjectName("muted")

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)

        layout.addWidget(ingest_group)
        layout.addWidget(self.ingest_log)
        layout.addLayout(file_bar)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)

    def _browse_ingest_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 ingest 配置", "", "YAML (*.yaml *.yml)")
        if path:
            self.ingest_config_input.setText(path)

    def _browse_ingest_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "选择 ingest 输出路径",
            self.ingest_output_input.text().strip() or "artifacts/text_records.parquet",
            "Parquet (*.parquet);;CSV (*.csv)",
        )
        if path:
            self.ingest_output_input.setText(path)

    def _run_ingest(self) -> None:
        config = self.ingest_config_input.text().strip()
        output = self.ingest_output_input.text().strip()
        if not config or not output:
            self._handle_error("ingest 配置与输出路径不能为空")
            return

        self.ingest_progress.setRange(0, 0)
        self.ingest_progress.setVisible(True)
        self.ingest_log.append(f"[RUN] ingest with config={config} output={output}")

        signals = self._start_task(run_ingest, config, output)

        def finished(result: Any) -> None:
            self.ingest_progress.setVisible(False)
            self.ingest_log.append(f"[DONE] {result}")
            self.file_input.setText(str(result["output_path"]))
            self._load()
            self._handle_done(
                f"ingest 完成\nrows={result['records_after']} output={result['output_path']}"
            )

        def failed(error: str) -> None:
            self.ingest_progress.setVisible(False)
            self.ingest_log.append(f"[ERROR] {error}")
            self._handle_error(error)

        signals.finished.connect(finished)
        signals.failed.connect(failed)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择数据文件", "", "Data (*.csv *.parquet)")
        if path:
            self.file_input.setText(path)

    def _load(self) -> None:
        path = self.file_input.text().strip()
        if not path:
            return
        target = Path(path)
        if not target.exists():
            self._handle_error(f"文件不存在: {path}")
            return

        if target.suffix.lower() == ".parquet":
            df = pd.read_parquet(target)
        else:
            df = pd.read_csv(target)

        preview = df.head(30)
        self.table.setColumnCount(len(preview.columns))
        self.table.setRowCount(len(preview))
        self.table.setHorizontalHeaderLabels([str(c) for c in preview.columns])

        for i, (_, row) in enumerate(preview.iterrows()):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))

        self.summary_label.setText(
            f"总行数: {len(df)} | 列数: {len(df.columns)} | 预览: {len(preview)} 行"
        )


class SignalWorkshopTab(BaseTaskTab):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        group = QGroupBox("信号构建配置")
        grid = QGridLayout(group)

        self.config_input = QLineEdit("configs/signal_build.yaml")
        browse_btn = QPushButton("浏览")
        run_btn = QPushButton("运行信号构建")
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        browse_btn.clicked.connect(self._browse)
        run_btn.clicked.connect(self._run)

        grid.addWidget(QLabel("Config"), 0, 0)
        grid.addWidget(self.config_input, 0, 1)
        grid.addWidget(browse_btn, 0, 2)
        grid.addWidget(run_btn, 1, 1)
        grid.addWidget(self.progress, 2, 0, 1, 3)

        layout.addWidget(group)
        layout.addWidget(self.log)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择配置", "", "YAML (*.yaml *.yml)")
        if path:
            self.config_input.setText(path)

    def _run(self) -> None:
        config = self.config_input.text().strip()
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.log.append(f"[RUN] build-signal with {config}")

        signals = self._start_task(run_signal_build, config)

        def finished(result: Any) -> None:
            self.progress.setVisible(False)
            self.log.append(f"[DONE] {result}")
            self._handle_done(f"信号构建完成\n{result}")

        def failed(error: str) -> None:
            self.progress.setVisible(False)
            self.log.append(f"[ERROR] {error}")
            self._handle_error(error)

        signals.finished.connect(finished)
        signals.failed.connect(failed)


class ExperimentCenterTab(BaseTaskTab):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        cs_group = QGroupBox("横截面回测")
        cs_layout = QHBoxLayout(cs_group)
        self.cs_config = QLineEdit("configs/backtest_cs.yaml")
        cs_run = QPushButton("运行 CS 回测")
        cs_run.clicked.connect(self._run_cs)
        cs_layout.addWidget(self.cs_config)
        cs_layout.addWidget(cs_run)

        ev_group = QGroupBox("事件研究")
        ev_layout = QHBoxLayout(ev_group)
        self.event_config = QLineEdit("configs/backtest_event.yaml")
        event_run = QPushButton("运行 Event 回测")
        event_run.clicked.connect(self._run_event)
        ev_layout.addWidget(self.event_config)
        ev_layout.addWidget(event_run)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout.addWidget(cs_group)
        layout.addWidget(ev_group)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)

    def _run_task(self, fn: Any, config: str, tag: str) -> None:
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.log.append(f"[RUN] {tag} with {config}")

        signals = self._start_task(fn, config)

        def finished(result: Any) -> None:
            self.progress.setVisible(False)
            self.log.append(f"[DONE] {tag}: {result}")

        def failed(error: str) -> None:
            self.progress.setVisible(False)
            self.log.append(f"[ERROR] {tag}: {error}")
            self._handle_error(error)

        signals.finished.connect(finished)
        signals.failed.connect(failed)

    def _run_cs(self) -> None:
        self._run_task(run_cs_backtest, self.cs_config.text().strip(), "cs-backtest")

    def _run_event(self) -> None:
        self._run_task(run_event_backtest, self.event_config.text().strip(), "event-backtest")


class EvaluationBoardTab(BaseTaskTab):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        load_cs_btn = QPushButton("加载 CS 指标")
        load_event_btn = QPushButton("加载 Event 指标")
        load_cs_btn.clicked.connect(self._load_cs)
        load_event_btn.clicked.connect(self._load_event)
        bar.addWidget(load_cs_btn)
        bar.addWidget(load_event_btn)

        gate_group = QGroupBox("回归门禁（CS）")
        gate_grid = QGridLayout(gate_group)
        self.baseline_input = QLineEdit("tests/baseline/cs_metrics_baseline.json")
        self.current_input = QLineEdit("artifacts/cs_metrics.json")
        self.ic_threshold_input = QLineEdit("0.01")
        self.ls_threshold_input = QLineEdit("0.005")
        gate_run_btn = QPushButton("运行回归校验")
        self.gate_progress = QProgressBar()
        self.gate_progress.setVisible(False)
        self.gate_result = QLabel("尚未运行门禁")
        self.gate_result.setObjectName("muted")

        gate_run_btn.clicked.connect(self._run_regression_gate)

        gate_grid.addWidget(QLabel("Baseline"), 0, 0)
        gate_grid.addWidget(self.baseline_input, 0, 1)
        gate_grid.addWidget(QLabel("Current"), 1, 0)
        gate_grid.addWidget(self.current_input, 1, 1)
        gate_grid.addWidget(QLabel("IC 阈值"), 2, 0)
        gate_grid.addWidget(self.ic_threshold_input, 2, 1)
        gate_grid.addWidget(QLabel("LS 阈值"), 3, 0)
        gate_grid.addWidget(self.ls_threshold_input, 3, 1)
        gate_grid.addWidget(gate_run_btn, 4, 1)
        gate_grid.addWidget(self.gate_progress, 5, 0, 1, 2)

        self.cs_table = QTableWidget()
        self.event_table = QTableWidget()

        layout.addLayout(bar)
        layout.addWidget(gate_group)
        layout.addWidget(self.gate_result)
        layout.addWidget(QLabel("横截面核心指标"))
        layout.addWidget(self.cs_table)
        layout.addWidget(QLabel("事件研究指标"))
        layout.addWidget(self.event_table)

    def _fill_table(self, table: QTableWidget, rows: list[dict]) -> None:
        if not rows:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        columns = list(rows[0].keys())
        table.setColumnCount(len(columns))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(columns)
        for i, row in enumerate(rows):
            for j, col in enumerate(columns):
                table.setItem(i, j, QTableWidgetItem(str(row[col])))

    def _load_cs(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择CS指标JSON", "", "JSON (*.json)")
        if not path:
            return
        payload = read_json(path)
        metrics = payload.get("metrics", {})
        self._fill_table(self.cs_table, [metrics] if metrics else [])

    def _load_event(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择Event指标JSON", "", "JSON (*.json)")
        if not path:
            return
        payload = read_json(path)
        self._fill_table(self.event_table, payload.get("metrics", []))

    def _run_regression_gate(self) -> None:
        baseline = self.baseline_input.text().strip()
        current = self.current_input.text().strip()
        if not baseline or not current:
            self._handle_error("Baseline 与 Current 路径不能为空")
            return

        try:
            ic_threshold = float(self.ic_threshold_input.text().strip())
            ls_threshold = float(self.ls_threshold_input.text().strip())
        except ValueError:
            self._handle_error("阈值必须是数字")
            return

        self.gate_progress.setRange(0, 0)
        self.gate_progress.setVisible(True)
        self.gate_result.setText("门禁运行中...")

        signals = self._start_task(
            run_regression_check,
            baseline,
            current,
            ic_threshold,
            ls_threshold,
        )

        def finished(result: Any) -> None:
            self.gate_progress.setVisible(False)
            status = "PASS" if result["passed"] else "FAIL"
            self.gate_result.setText(
                f"{status} | ΔIC={result['delta_ic']:.6f} (<= {result['ic_threshold']:.6f}) "
                f"| ΔLS={result['delta_ls']:.6f} (<= {result['ls_threshold']:.6f})"
            )

        def failed(error: str) -> None:
            self.gate_progress.setVisible(False)
            self.gate_result.setText("门禁运行失败")
            self._handle_error(error)

        signals.finished.connect(finished)
        signals.failed.connect(failed)


class ReportCenterTab(BaseTaskTab):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.config_input = QLineEdit("configs/report.yaml")
        browse_btn = QPushButton("浏览")
        run_btn = QPushButton("生成报告")
        browse_btn.clicked.connect(self._browse)
        run_btn.clicked.connect(self._run)
        bar.addWidget(self.config_input)
        bar.addWidget(browse_btn)
        bar.addWidget(run_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.result_label = QLabel("尚未生成报告")
        self.result_label.setObjectName("muted")

        layout.addLayout(bar)
        layout.addWidget(self.progress)
        layout.addWidget(self.result_label)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择配置", "", "YAML (*.yaml *.yml)")
        if path:
            self.config_input.setText(path)

    def _run(self) -> None:
        config = self.config_input.text().strip()
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)

        signals = self._start_task(run_report, config)

        def finished(result: Any) -> None:
            self.progress.setVisible(False)
            self.result_label.setText(f"报告已生成: {result['report_path']}")

        def failed(error: str) -> None:
            self.progress.setVisible(False)
            self._handle_error(error)

        signals.finished.connect(finished)
        signals.failed.connect(failed)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("research-signal-nlp | 研究工作台")
        self.resize(1260, 800)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.addTab(DataManagerTab(), "数据集管理")
        tabs.addTab(SignalWorkshopTab(), "信号工坊")
        tabs.addTab(ExperimentCenterTab(), "实验中心")
        tabs.addTab(EvaluationBoardTab(), "评估看板")
        tabs.addTab(ReportCenterTab(), "报告中心")

        self.setCentralWidget(tabs)
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage("Ready")

        self.setStyleSheet(
            """
            QWidget { font-size: 13px; }
            QMainWindow { background: #f5f7fb; }
            QGroupBox {
                border: 1px solid #d9e1ec;
                border-radius: 8px;
                margin-top: 8px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: #1f2937;
            }
            QLineEdit, QTextEdit, QTableWidget {
                border: 1px solid #d9e1ec;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            QPushButton {
                background: #1f4db8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background: #123a93; }
            QLabel#muted { color: #6b7280; }
            """
        )


def run_gui() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

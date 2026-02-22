"""CLI entrypoint for research-signal-nlp."""

from __future__ import annotations

import typer
from rich import print

from research_signal_nlp.core.services import (
    run_cs_backtest,
    run_event_backtest,
    run_ingest,
    run_regression_check,
    run_report,
    run_signal_build,
)
from research_signal_nlp.gui.app import run_gui

app = typer.Typer(help="research-signal-nlp command line")
backtest_app = typer.Typer(help="Backtest commands")
app.add_typer(backtest_app, name="backtest")


@app.command("ingest")
def ingest_command(
    config: str = typer.Option(..., "--config", "-c", help="DataSource yaml path"),
    output: str = typer.Option("artifacts/text_records.parquet", "--output", "-o"),
) -> None:
    """Standardize text records from raw source."""

    result = run_ingest(config_path=config, output_path=output)
    print(
        "[green]Ingest done[/green] "
        f"rows={result['records_after']} "
        f"output={result['output_path']}"
    )


@app.command("build-signal")
def build_signal_command(
    config: str = typer.Option(..., "--config", "-c", help="SignalBuildConfig yaml path"),
) -> None:
    """Build signal scores from text source."""

    result = run_signal_build(config)
    print(
        "[green]Signal build done[/green] "
        f"rows={result['rows']} "
        f"score={result['score_path']} "
        f"events={result['event_path']}"
    )


@backtest_app.command("cs")
def backtest_cs_command(
    config: str = typer.Option(..., "--config", "-c", help="CrossSectionBacktestConfig yaml path"),
) -> None:
    """Run cross-sectional factor evaluation."""

    result = run_cs_backtest(config)
    print(f"[green]CS backtest done[/green] output={result['output_path']}")
    print(result["metrics"])


@backtest_app.command("event")
def backtest_event_command(
    config: str = typer.Option(..., "--config", "-c", help="EventBacktestConfig yaml path"),
) -> None:
    """Run event study evaluation."""

    result = run_event_backtest(config)
    print(f"[green]Event backtest done[/green] output={result['output_path']}")


@app.command("report")
def report_command(
    config: str = typer.Option(..., "--config", "-c", help="ReportConfig yaml path"),
) -> None:
    """Build html report from backtest metrics."""

    result = run_report(config)
    print(f"[green]Report done[/green] path={result['report_path']}")


@app.command("gui")
def gui_command() -> None:
    """Launch PyQt6 research workstation."""

    run_gui()


@app.command("check-regression")
def check_regression_command(
    baseline: str = typer.Option(..., "--baseline", "-b", help="Baseline CS metrics json"),
    current: str = typer.Option(..., "--current", "-c", help="Current CS metrics json"),
    ic_threshold: float = typer.Option(0.01, "--ic-threshold"),
    ls_threshold: float = typer.Option(0.005, "--ls-threshold"),
) -> None:
    """Validate CS metrics against IC/LS regression thresholds."""

    result = run_regression_check(
        baseline_path=baseline,
        current_path=current,
        ic_threshold=ic_threshold,
        ls_threshold=ls_threshold,
    )
    status = "[green]PASS[/green]" if result["passed"] else "[red]FAIL[/red]"
    print(
        f"{status} "
        f"delta_ic={result['delta_ic']:.6f} (<= {result['ic_threshold']:.6f}) "
        f"delta_ls={result['delta_ls']:.6f} (<= {result['ls_threshold']:.6f})"
    )
    if not result["passed"]:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

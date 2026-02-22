"""Chart generation utilities for reports."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Noto Sans CJK SC", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_ic_chart(daily_ic: pd.DataFrame, out_dir: Path) -> str:
    _ensure_dir(out_dir)
    out_path = out_dir / "ic_timeseries.png"

    fig, ax = plt.subplots(figsize=(10, 4))
    if not daily_ic.empty:
        x = pd.to_datetime(daily_ic["trade_date"])
        ax.plot(x, daily_ic["ic"], label="IC", linewidth=1.2)
        ax.axhline(daily_ic["ic"].mean(), linestyle="--", color="tab:orange", label="IC Mean")
    ax.set_title("Daily IC")
    ax.set_xlabel("Date")
    ax.set_ylabel("IC")
    if not daily_ic.empty:
        ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return str(out_path)


def save_ls_chart(daily_ls: pd.DataFrame, out_dir: Path) -> str:
    _ensure_dir(out_dir)
    out_path = out_dir / "long_short_cumret.png"

    fig, ax = plt.subplots(figsize=(10, 4))
    if not daily_ls.empty:
        temp = daily_ls.copy()
        temp["trade_date"] = pd.to_datetime(temp["trade_date"])
        temp = temp.sort_values("trade_date")
        temp["cum_ls"] = temp["ls_return"].cumsum()
        ax.plot(temp["trade_date"], temp["cum_ls"], label="Long-Short Cumulative", linewidth=1.2)
    ax.set_title("Long-Short Cumulative Return")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return")
    if not daily_ls.empty:
        ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return str(out_path)


def save_event_chart(event_metrics: pd.DataFrame, out_dir: Path) -> str:
    _ensure_dir(out_dir)
    out_path = out_dir / "event_car.png"

    fig, ax = plt.subplots(figsize=(10, 4))
    if not event_metrics.empty:
        labels = event_metrics.apply(
            lambda r: f"{r['event_type']}-w{r['window']}",
            axis=1,
        )
        ax.bar(labels, event_metrics["car_mean"])
        ax.tick_params(axis="x", rotation=45)
    ax.set_title("Event CAR Mean")
    ax.set_xlabel("Event Type-Window")
    ax.set_ylabel("CAR Mean")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return str(out_path)

"""Event study evaluator for textual event signals."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from research_signal_nlp.backtest.base import BaseBacktestAdapter


def _require_columns(frame: pd.DataFrame, required: list[str], frame_name: str) -> None:
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"{frame_name} missing required columns: {missing}")


@dataclass(slots=True)
class EventStudyEvaluator(BaseBacktestAdapter):
    windows: list[int]

    def __post_init__(self) -> None:
        if not self.windows:
            raise ValueError("windows must not be empty.")
        if any(window <= 0 for window in self.windows):
            raise ValueError(f"windows must be positive integers: {self.windows}")

    def _event_car(
        self,
        returns_by_asset: dict[str, pd.DataFrame],
        asset: str,
        event_date: pd.Timestamp,
        window: int,
    ) -> float | None:
        frame = returns_by_asset.get(str(asset))
        if frame is None or frame.empty:
            return None

        post = frame[frame["trade_date"] > event_date].head(window)
        if len(post) < window:
            return None
        return float(post["abnormal_return"].sum())

    def evaluate(
        self,
        events_df: pd.DataFrame,
        returns_df: pd.DataFrame,
        return_col: str = "return",
        benchmark_col: str = "benchmark_return",
    ) -> dict:
        _require_columns(events_df, ["asset", "event_date", "event_type"], "events_df")
        _require_columns(returns_df, ["asset", "trade_date", return_col], "returns_df")

        if events_df.empty:
            raise ValueError("events dataframe is empty")

        events = events_df.copy()
        events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce")
        invalid_event_dates = int(events["event_date"].isna().sum())
        if invalid_event_dates > 0:
            raise ValueError(
                f"events_df contains {invalid_event_dates} invalid event_date values."
            )

        rets = returns_df.copy()
        rets["trade_date"] = pd.to_datetime(rets["trade_date"], errors="coerce")
        invalid_trade_dates = int(rets["trade_date"].isna().sum())
        if invalid_trade_dates > 0:
            raise ValueError(
                f"returns_df contains {invalid_trade_dates} invalid trade_date values."
            )
        rets[return_col] = pd.to_numeric(rets[return_col], errors="coerce")
        if rets[return_col].isna().all():
            raise ValueError(
                f"returns_df column '{return_col}' has no valid numeric values."
            )
        if benchmark_col in rets.columns:
            rets[benchmark_col] = pd.to_numeric(rets[benchmark_col], errors="coerce")
            rets["abnormal_return"] = rets[return_col] - rets[benchmark_col]
        else:
            rets["abnormal_return"] = rets[return_col]
        rets = rets.dropna(subset=["trade_date", "abnormal_return"])
        if rets.empty:
            raise ValueError("returns_df has no valid rows after cleaning trade_date and returns.")

        returns_by_asset = {
            str(asset): frame.sort_values("trade_date")
            for asset, frame in rets.groupby("asset", observed=True)
        }

        detail_rows = []
        for _, row in events.iterrows():
            for window in self.windows:
                car = self._event_car(
                    returns_by_asset=returns_by_asset,
                    asset=str(row["asset"]),
                    event_date=row["event_date"],
                    window=window,
                )
                if car is None:
                    continue
                detail_rows.append(
                    {
                        "asset": row["asset"],
                        "event_date": row["event_date"].strftime("%Y-%m-%d"),
                        "event_type": row["event_type"],
                        "window": window,
                        "car": car,
                    }
                )

        if not detail_rows:
            raise ValueError("No valid events with enough post-event returns.")

        detail_df = pd.DataFrame(detail_rows)
        summary_rows = []
        grouped = detail_df.groupby(["event_type", "window"], observed=True)
        for (event_type, window), frame in grouped:
            mean_car = float(frame["car"].mean())
            std_car = float(frame["car"].std(ddof=1)) if len(frame) > 1 else 0.0
            if len(frame) <= 1 or std_car <= 1e-12:
                t_stat = 0.0
            else:
                t_stat = mean_car / (std_car / math.sqrt(len(frame)))
            summary_rows.append(
                {
                    "event_type": event_type,
                    "window": int(window),
                    "car_mean": mean_car,
                    "t_stat": float(t_stat),
                    "win_rate": float((frame["car"] > 0).mean()),
                    "count": int(len(frame)),
                }
            )

        type_sets = {
            str(event_type): set(
                map(tuple, frame[["asset", "event_date"]].to_records(index=False))
            )
            for event_type, frame in detail_df.groupby("event_type", observed=True)
        }
        full_overlap = False
        if len(type_sets) > 1:
            first_set = next(iter(type_sets.values()))
            full_overlap = all(values == first_set for values in type_sets.values())

        return {
            "metrics": summary_rows,
            "event_details": detail_df.to_dict(orient="records"),
            "diagnostics": {
                "event_type_count": len(type_sets),
                "full_overlap_event_types": full_overlap,
            },
        }

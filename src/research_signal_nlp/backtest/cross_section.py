"""Cross-sectional factor backtest metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from research_signal_nlp.backtest.base import BaseBacktestAdapter
from research_signal_nlp.data.schema import CSMetrics


def _require_columns(frame: pd.DataFrame, required: list[str], frame_name: str) -> None:
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"{frame_name} missing required columns: {missing}")


def _trade_date_sort_key(trade_date: object) -> tuple[int, int | str]:
    parsed = pd.to_datetime(trade_date, errors="coerce", utc=True)
    if pd.isna(parsed):
        return (1, str(trade_date))
    return (0, int(parsed.value))


@dataclass(slots=True)
class CrossSectionEvaluator(BaseBacktestAdapter):
    quantiles: int = 5

    @staticmethod
    def _daily_ic(frame: pd.DataFrame) -> tuple[float, float]:
        if frame["score"].nunique() <= 1 or frame["fwd_return"].nunique() <= 1:
            return 0.0, 0.0
        ic = frame["score"].corr(frame["fwd_return"], method="pearson")
        rank_ic, _ = spearmanr(frame["score"], frame["fwd_return"])
        return float(ic if pd.notna(ic) else 0.0), float(rank_ic if pd.notna(rank_ic) else 0.0)

    def evaluate(
        self,
        score_df: pd.DataFrame,
        returns_df: pd.DataFrame,
        score_col: str = "score",
        return_col: str = "fwd_return",
    ) -> dict:
        if self.quantiles < 2:
            raise ValueError("quantiles must be >= 2 for cross-sectional bucketing.")

        _require_columns(score_df, ["asset", "trade_date", score_col], "score_df")
        _require_columns(returns_df, ["asset", "trade_date", return_col], "returns_df")

        prepared_score = score_df[["asset", "trade_date", score_col]].copy()
        prepared_returns = returns_df[["asset", "trade_date", return_col]].copy()
        prepared_score[score_col] = pd.to_numeric(prepared_score[score_col], errors="coerce")
        prepared_returns[return_col] = pd.to_numeric(prepared_returns[return_col], errors="coerce")

        merged = prepared_score.merge(
            prepared_returns,
            on=["asset", "trade_date"],
            how="inner",
        ).rename(columns={score_col: "score", return_col: "fwd_return"})

        if merged.empty:
            raise ValueError(
                "No joined rows found between score_df and returns_df on ['asset', 'trade_date']."
            )

        ic_rows = []
        quant_rows = []
        top_sets: dict[object, set[str]] = {}

        for trade_date, frame in merged.groupby("trade_date"):
            daily = frame.dropna(subset=["score", "fwd_return"]).copy()
            if len(daily) < self.quantiles:
                continue

            ic, rank_ic = self._daily_ic(daily)
            ic_rows.append({"trade_date": trade_date, "ic": ic, "rank_ic": rank_ic})

            try:
                daily["bucket"] = pd.qcut(
                    daily["score"],
                    q=self.quantiles,
                    labels=False,
                    duplicates="drop",
                )
            except ValueError:
                continue

            bucket_ret = daily.groupby("bucket", observed=True)["fwd_return"].mean()
            if bucket_ret.empty:
                continue
            top = float(bucket_ret.iloc[-1])
            bottom = float(bucket_ret.iloc[0])
            quant_rows.append({"trade_date": trade_date, "ls_return": top - bottom})

            top_assets = set(
                daily.loc[daily["bucket"] == daily["bucket"].max(), "asset"].astype(str)
            )
            top_sets[trade_date] = top_assets

        if not ic_rows:
            raise ValueError("No valid trading dates to evaluate cross-sectional metrics.")

        ic_df = pd.DataFrame(ic_rows)
        ls_df = (
            pd.DataFrame(quant_rows)
            if quant_rows
            else pd.DataFrame(columns=["trade_date", "ls_return"])
        )

        turnovers = []
        ordered_dates = sorted(top_sets.keys(), key=_trade_date_sort_key)
        for prev_date, curr_date in zip(ordered_dates, ordered_dates[1:], strict=False):
            prev_set, curr_set = top_sets[prev_date], top_sets[curr_date]
            union_size = len(prev_set | curr_set)
            if union_size == 0:
                turnovers.append(0.0)
                continue
            overlap = len(prev_set & curr_set)
            turnovers.append(1.0 - overlap / len(prev_set) if prev_set else 0.0)

        ic_mean = float(ic_df["ic"].mean())
        ic_std = float(ic_df["ic"].std(ddof=0))
        metrics = CSMetrics(
            ic_mean=ic_mean,
            ic_ir=float(ic_mean / ic_std) if ic_std > 1e-12 else 0.0,
            rank_ic_mean=float(ic_df["rank_ic"].mean()),
            ls_return_mean=float(ls_df["ls_return"].mean()) if not ls_df.empty else 0.0,
            turnover_mean=float(np.mean(turnovers)) if turnovers else 0.0,
        )

        return {
            "metrics": metrics.model_dump(),
            "daily_ic": ic_df.to_dict(orient="records"),
            "daily_ls": ls_df.to_dict(orient="records"),
        }

"""Core typed records for dataset contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TextRecord(BaseModel):
    id: str
    asset: str
    publish_time: datetime
    source: str
    title: str
    body: str


class FactorScore(BaseModel):
    asset: str
    trade_date: str
    score: float
    signal_name: str
    version: str = "0.1.0"


class CSMetrics(BaseModel):
    ic_mean: float
    ic_ir: float
    rank_ic_mean: float
    ls_return_mean: float
    turnover_mean: float


class EventMetrics(BaseModel):
    event_type: str
    window: int
    car_mean: float
    t_stat: float
    win_rate: float
    count: int


class EventDiagnostics(BaseModel):
    event_type_count: int
    full_overlap_event_types: bool

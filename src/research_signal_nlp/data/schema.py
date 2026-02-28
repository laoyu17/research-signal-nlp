"""Core typed records for dataset contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class DailyICRecord(BaseModel):
    trade_date: str
    ic: float
    rank_ic: float


class DailyLSRecord(BaseModel):
    trade_date: str
    ls_return: float


class EventDetailRecord(BaseModel):
    asset: str
    event_date: str
    event_type: str
    window: int
    car: float


class CSPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    metrics: CSMetrics
    daily_ic: list[DailyICRecord] = Field(default_factory=list)
    daily_ls: list[DailyLSRecord] = Field(default_factory=list)


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    metrics: list[EventMetrics]
    event_details: list[EventDetailRecord] = Field(default_factory=list)
    diagnostics: EventDiagnostics | None = None

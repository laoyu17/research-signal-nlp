"""Typed configuration models and YAML loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from research_signal_nlp import __version__

T = TypeVar("T", bound=BaseModel)


class FieldMapping(BaseModel):
    """Source text field mapping."""

    id_field: str = "id"
    asset_field: str = "asset"
    publish_time_field: str = "publish_time"
    source_field: str = "source"
    title_field: str = "title"
    body_field: str = "body"


class DataSourceConfig(BaseModel):
    """Text data source descriptor."""

    path: str
    format: Literal["csv", "parquet"] = "csv"
    mapping: FieldMapping = Field(default_factory=FieldMapping)
    timezone: str = "Asia/Shanghai"
    deduplicate_by: list[str] = Field(default_factory=lambda: ["id"])

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Invalid timezone: {value}") from exc
        return value


class LexiconConfig(BaseModel):
    positive_words: list[str] = Field(default_factory=list)
    negative_words: list[str] = Field(default_factory=list)


class EventPatternConfig(BaseModel):
    rating_upgrade_patterns: list[str] = Field(
        default_factory=lambda: [
            r"上调.*评级",
            r"维持.*买入",
            r"首次覆盖.*买入",
        ]
    )
    target_up_patterns: list[str] = Field(
        default_factory=lambda: [
            r"目标价.*上调",
            r"提高目标价",
        ]
    )
    earnings_positive_patterns: list[str] = Field(
        default_factory=lambda: [
            r"业绩预增",
            r"净利润同比增长",
        ]
    )


class ModelConfig(BaseModel):
    enabled: bool = True
    model_type: Literal["ridge", "logistic"] = "ridge"
    min_df: int = 2
    max_features: int = 5000


class SignalWeights(BaseModel):
    lexicon: float = 0.4
    event: float = 0.3
    model: float = 0.3


class SignalBuildConfig(BaseModel):
    data_source: DataSourceConfig | None = None
    ingested_records_path: str | None = None
    output_path: str = "artifacts/signal_scores.parquet"
    events_output_path: str | None = None
    debug_output_path: str | None = None
    lexicon: LexiconConfig = Field(default_factory=LexiconConfig)
    event_patterns: EventPatternConfig = Field(default_factory=EventPatternConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    weights: SignalWeights = Field(default_factory=SignalWeights)
    train_label_path: str | None = None
    text_concat_fields: list[str] = Field(default_factory=lambda: ["title", "body"])
    signal_name: str = "nlp_fusion_v1"
    signal_version: str = __version__

    @model_validator(mode="after")
    def validate_input_source(self) -> SignalBuildConfig:
        if not self.data_source and not self.ingested_records_path:
            raise ValueError(
                "SignalBuildConfig requires either data_source or ingested_records_path"
            )
        return self


class CrossSectionBacktestConfig(BaseModel):
    score_path: str
    returns_path: str
    returns_format: Literal["csv", "parquet"] = "csv"
    output_path: str = "artifacts/cs_metrics.json"
    quantiles: int = 5


class EventBacktestConfig(BaseModel):
    events_path: str
    returns_path: str
    returns_format: Literal["csv", "parquet"] = "csv"
    output_path: str = "artifacts/event_metrics.json"
    windows: list[int] = Field(default_factory=lambda: [1, 3, 5])


class ReportConfig(BaseModel):
    run_name: str = "default_run"
    output_path: str = "reports/report.html"
    cs_metrics_path: str | None = None
    event_metrics_path: str | None = None


def read_yaml(path: str | Path) -> dict[str, Any]:
    """Read YAML file to raw dictionary."""

    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(path: str | Path, model_cls: type[T]) -> T:
    """Load and validate YAML against target model."""

    payload = read_yaml(path)
    return model_cls.model_validate(payload)

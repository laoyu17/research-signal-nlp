"""HTML report builder."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Template
from pydantic import BaseModel, ValidationError

from research_signal_nlp.core.config import ReportConfig
from research_signal_nlp.data.schema import CSPayload, EventPayload
from research_signal_nlp.utils.io import read_json

from .charts import save_event_chart, save_ic_chart, save_ls_chart

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>{{ run_name }} - Research Signal Report</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 24px;
      color: #1f2937;
    }
    h1, h2 { margin-bottom: 8px; }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 14px; }
    table { border-collapse: collapse; width: 100%; font-size: 14px; }
    th, td { border: 1px solid #e5e7eb; padding: 8px; text-align: left; }
    th { background: #f9fafb; }
    img { max-width: 100%; border: 1px solid #e5e7eb; border-radius: 6px; }
    .muted { color: #6b7280; font-size: 13px; }
  </style>
</head>
<body>
  <h1>{{ run_name }} - 文本因子研究报告</h1>
  <p class="muted">自动生成：research-signal-nlp</p>

  <div class="card">
    <h2>横截面核心指标</h2>
    {% if cs_metrics %}
    <table>
      <tr><th>ic_mean</th><th>ic_ir</th><th>rank_ic_mean</th><th>ls_return_mean</th><th>turnover_mean</th></tr>
      <tr>
        <td>{{ '%.4f'|format(cs_metrics.ic_mean) }}</td>
        <td>{{ '%.4f'|format(cs_metrics.ic_ir) }}</td>
        <td>{{ '%.4f'|format(cs_metrics.rank_ic_mean) }}</td>
        <td>{{ '%.4f'|format(cs_metrics.ls_return_mean) }}</td>
        <td>{{ '%.4f'|format(cs_metrics.turnover_mean) }}</td>
      </tr>
    </table>
    {% else %}
    <p>无横截面结果。</p>
    {% endif %}
  </div>

  <div class="card">
    <h2>横截面可视化</h2>
    {% if ic_chart %}<img src="{{ ic_chart }}" alt="IC chart" />{% endif %}
    {% if ls_chart %}<img src="{{ ls_chart }}" alt="LS chart" />{% endif %}
  </div>

  <div class="card">
    <h2>事件研究指标</h2>
    {% if event_metrics %}
    <table>
      <tr><th>event_type</th><th>window</th><th>car_mean</th><th>t_stat</th><th>win_rate</th><th>count</th></tr>
      {% for row in event_metrics %}
      <tr>
        <td>{{ row.event_type }}</td>
        <td>{{ row.window }}</td>
        <td>{{ '%.4f'|format(row.car_mean) }}</td>
        <td>{{ '%.4f'|format(row.t_stat) }}</td>
        <td>{{ '%.4f'|format(row.win_rate) }}</td>
        <td>{{ row.count }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <p>无事件研究结果。</p>
    {% endif %}
  </div>

  <div class="card">
    <h2>事件研究可视化</h2>
    {% if event_chart %}<img src="{{ event_chart }}" alt="Event chart" />{% endif %}
  </div>
</body>
</html>
"""


def _load_payload(path: str | None, *, name: str, strict: bool) -> dict | None:
    if not path:
        if strict:
            raise ValueError(f"{name} path is required when strict_inputs=true.")
        return None
    target = Path(path)
    if not target.exists():
        if strict:
            raise FileNotFoundError(f"{name} file not found: {path}")
        return None
    return read_json(target)


def _validate_loaded_payload(
    payload: dict | None,
    *,
    name: str,
    model_cls: type[BaseModel],
    strict: bool,
) -> dict | None:
    if payload is None:
        return None
    try:
        return model_cls.model_validate(payload).model_dump()
    except ValidationError as exc:
        if strict:
            raise ValueError(f"{name} payload schema validation failed: {exc}") from exc
        return None


def build_html_report(
    config: ReportConfig,
    cs_payload: dict | None = None,
    event_payload: dict | None = None,
) -> str:
    if cs_payload is None:
        cs_payload = _load_payload(
            config.cs_metrics_path,
            name="cs_metrics",
            strict=config.strict_inputs,
        )
    if event_payload is None:
        event_payload = _load_payload(
            config.event_metrics_path,
            name="event_metrics",
            strict=config.strict_inputs,
        )

    cs_payload = _validate_loaded_payload(
        cs_payload,
        name="cs_metrics",
        model_cls=CSPayload,
        strict=config.strict_inputs,
    )
    event_payload = _validate_loaded_payload(
        event_payload,
        name="event_metrics",
        model_cls=EventPayload,
        strict=config.strict_inputs,
    )

    if config.strict_inputs:
        if cs_payload is None:
            raise ValueError("Strict report mode requires a valid CS metrics payload.")
        if event_payload is None:
            raise ValueError("Strict report mode requires a valid event metrics payload.")

    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asset_dir = output_path.parent / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    cs_metrics = None
    ic_chart = None
    ls_chart = None
    if cs_payload and "metrics" in cs_payload:
        cs_metrics = cs_payload["metrics"]
        daily_ic = pd.DataFrame(cs_payload.get("daily_ic", []))
        daily_ls = pd.DataFrame(cs_payload.get("daily_ls", []))
        ic_chart = Path(save_ic_chart(daily_ic, asset_dir)).name
        ls_chart = Path(save_ls_chart(daily_ls, asset_dir)).name

    event_rows = []
    event_chart = None
    if event_payload and "metrics" in event_payload:
        event_rows = event_payload["metrics"]
        event_df = pd.DataFrame(event_rows)
        event_chart = Path(save_event_chart(event_df, asset_dir)).name

    template = Template(REPORT_TEMPLATE)
    html = template.render(
        run_name=config.run_name,
        cs_metrics=cs_metrics,
        event_metrics=event_rows,
        ic_chart=f"assets/{ic_chart}" if ic_chart else None,
        ls_chart=f"assets/{ls_chart}" if ls_chart else None,
        event_chart=f"assets/{event_chart}" if event_chart else None,
    )

    output_path.write_text(html, encoding="utf-8")
    return str(output_path)

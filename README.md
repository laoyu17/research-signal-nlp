# research-signal-nlp

一个面向量化研究开源小框架：把研报/公告/新闻文本信号转成可量化、可回测、可展示的因子。

## 核心能力
- 文本信号构建：规则词典情绪 + 事件抽取 + TF-IDF 线性 baseline
- 双轨评估：日频横截面（IC/分层收益）+ 事件研究（CAR/t-stat/win-rate）
- 可视化：PyQt6 研究工作台（数据、信号、实验、评估、报告）+ GUI 内回归门禁
- 工程化：Conventional Commits、CI 门禁、测试分层、回归阈值门禁

## 快速开始

### 1) 安装
```bash
python -m pip install -e .[dev]
```

### 2) 运行示例全流程
```bash
bash examples/demo_run.sh
```

### 3) 启动 GUI
```bash
rsnlp gui
```

## CLI 用法
```bash
rsnlp ingest -c configs/data_source.yaml -o artifacts/text_records.parquet
rsnlp build-signal -c configs/signal_build.yaml
rsnlp backtest cs -c configs/backtest_cs.yaml
rsnlp backtest event -c configs/backtest_event.yaml
rsnlp report -c configs/report.yaml
rsnlp check-regression -b tests/baseline/cs_metrics_baseline.json -c artifacts/cs_metrics.json
```

## 目录结构
```text
src/research_signal_nlp/
  data/        # ingest + schema
  signals/     # 词典/事件/信号融合
  models/      # TF-IDF + linear baseline
  backtest/    # 横截面 + 事件评估
  reporting/   # 图表 + HTML 报告
  gui/         # PyQt6 研究工作台
  core/        # 配置与应用服务
tests/
configs/
examples/
docs/
```

## 数据契约（最小）

### 文本输入
- `id`
- `asset`
- `publish_time`
- `source`
- `title`
- `body`

### 收益输入
- `asset`
- `trade_date`
- `fwd_return`（横截面）
- `return`、`benchmark_return`（事件研究）

### 因子输出（`signal_scores`）
- `asset`
- `trade_date`
- `score`
- `signal_name`
- `version`

### 事件输出（`events`）
- `asset`
- `event_date`
- `event_type`
- `event_strength`

## 信号输入模式
- 直接读取原始文本：配置 `data_source`
- 接 ingest 标准化产物：配置 `ingested_records_path`（优先）

## 信号输出路径配置（可选）
- `output_path`：主因子输出
- `events_output_path`：事件明细输出（默认与 `output_path` 同目录，文件名 `events.parquet`）
- `debug_output_path`：调试特征输出（默认与 `output_path` 同目录，文件名 `signal_debug.parquet`）

## 指标口径说明
- 事件研究 CAR 使用 `T+1...T+N`（不包含事件当日）。
- 事件回测输出包含 `diagnostics.full_overlap_event_types`，用于提示不同事件类型是否样本完全重合。
- 横截面 `turnover_mean` 为相邻两日 Top 组合的 `1 - overlap/prev_size`。

## 结果追溯路径（可解释性）
- `signal_scores.text_id` 可回溯到 ingest 后文本主键（`artifacts/text_records.parquet` 的 `id`）。
- `signal_debug`（默认 `artifacts/signal_debug.parquet`）保留 `lexicon_score` / `event_score` / `model_score` / `raw_score` 中间特征。
- `events`（默认 `artifacts/events.parquet`）记录 `asset/event_date/event_type/event_strength`，用于事件回测输入。
- `cs_metrics.json` 除汇总指标外，还包含 `daily_ic` 与 `daily_ls` 明细。
- `event_metrics.json` 除汇总指标外，还包含 `event_details` 与 `diagnostics`（含 `full_overlap_event_types`）。

## 文档索引
- 需求：`docs/product-requirements.md`
- 架构：`docs/architecture-design.md`
- 开发计划：`docs/development-plan.md`
- 测试回归：`docs/testing-regression-policy.md`
- 案例：`docs/case-study-01.md`
- 面试亮点：`docs/interview-highlights.md`

## 协作规范
见 `AGENTS.md`（远端地址、提交规范、测试回归、文档更新要求）。

## License
MIT

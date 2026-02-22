# Architecture Design - research-signal-nlp

## 1. 模块分层
- `data/`: ingest 与 schema
- `signals/`: 规则、词典、事件抽取与融合
- `models/`: 文本 baseline 模型
- `backtest/`: 横截面 + 事件研究评估
- `reporting/`: 图表 + HTML 报告
- `gui/`: PyQt6 研究工作台
- `core/`: 配置模型与应用服务
- `cli.py`: 命令行编排入口

## 2. 关键数据契约
- `TextRecord`: id/asset/publish_time/source/title/body
- `FactorScore`: asset/trade_date/score/signal_name/version
- `SignalDebugRecord`: text_id 级中间特征（lexicon/event/model/raw）
- `CSMetrics`: ic_mean/ic_ir/rank_ic_mean/ls_return_mean/turnover_mean
- `EventMetrics`: event_type/window/car_mean/t_stat/win_rate/count
- `EventDiagnostics`: event_type_count/full_overlap_event_types
- `CSPayload`: metrics + daily_ic + daily_ls
- `EventPayload`: metrics + event_details + diagnostics
- `CSPayload` / `EventPayload` 在服务层写出前与报告层读取时均进行 Pydantic 契约校验（兼容模式下可降级为空结果）

## 3. 主流程
1. Ingest 标准化文本数据（含 timezone 对齐与 trade_date 生成）
2. 读取信号输入（优先 `ingested_records_path`，否则 `data_source`）；对 `trade_date` 做严格合法性校验（不可解析即失败）
3. 计算 lexicon_score / event_score / model_score
4. 权重融合 + 按日截面 z-score 标准化
5. 写出信号产物（`signal_scores` + `events` + `signal_debug`，其中后两者支持自定义输出路径）
6. 横截面与事件研究评估
7. 服务层对 `CSPayload` / `EventPayload` 做结构校验后落盘 JSON
8. 报告层读取 payload 并按 `strict_inputs` 执行契约校验（严格模式失败即中断）
9. 产出 HTML 报告并使用回归门禁校验 `ΔIC` 与 `ΔLS`

## 4. 接口设计
### CLI
- `rsnlp ingest`
- `rsnlp build-signal`
- `rsnlp backtest cs`
- `rsnlp backtest event`
- `rsnlp report`
- `rsnlp check-regression`
- `rsnlp gui`

### GUI（研究工作台）
- 数据集管理：支持 ingest 配置执行 + 结果预览
- 信号工坊：运行 `build-signal`
- 实验中心：运行 CS / Event 回测
- 评估看板：加载指标 + 运行回归门禁
- 报告中心：生成 HTML 报告
- 任务执行：统一由 `TaskRunner` 管理线程生命周期，页签不再持久堆积线程引用

### 插件接口
- `BaseExtractor`
- `BaseModel`
- `BaseBacktestAdapter`

### 报告配置补充
- `ReportConfig.strict_inputs`：默认 `false`
  - `false`：缺失输入时兼容生成空报告
  - `true`：缺失输入文件或 payload 契约不合法时 fail-fast

## 5. 指标口径说明
- 事件窗 CAR 使用 **T+1...T+N**，不包含事件当日（`trade_date > event_date`）。
- `turnover_mean` 口径为相邻两日 Top 组合的 `1 - overlap/prev_size`。
- 当不同事件类型对应的 `(asset, event_date)` 集合完全重合时，事件回测结果中会给出 `full_overlap_event_types=true` 诊断标记。
- 可解释性追溯链路：`signal_scores.text_id -> text_records.id`，并通过 `signal_debug`/`event_details` 还原指标来源。

## 6. 可替换层
- 数据源层：CSV/Parquet -> 商业接口适配器
- 模型层：线性 baseline -> Transformer
- 回测层：本地 evaluator -> 第三方回测引擎

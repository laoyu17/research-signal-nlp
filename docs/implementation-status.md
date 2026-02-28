# Implementation Status Matrix（2026-02-22）

## 1. PRD 必须项对照

| PRD 必须项 | 当前状态 | 关键证据 |
|---|---|---|
| 数据导入与字段标准化 | ✅ 已实现 | `src/research_signal_nlp/data/ingest.py`、`src/research_signal_nlp/cli.py` |
| 规则词典情绪与事件抽取 | ✅ 已实现 | `src/research_signal_nlp/signals/lexicon.py`、`src/research_signal_nlp/signals/events.py` |
| TF-IDF + 线性模型 baseline | ✅ 已实现 | `src/research_signal_nlp/models/tfidf_linear.py` |
| 横截面回测与事件研究 | ✅ 已实现 | `src/research_signal_nlp/backtest/cross_section.py`、`src/research_signal_nlp/backtest/event_study.py` |
| PyQt6 工作台与报告导出 | ✅ 已实现 | `src/research_signal_nlp/gui/app.py`、`src/research_signal_nlp/reporting/report.py` |

## 2. 设计一致性（架构大方向）

- 模块分层与职责符合 `docs/architecture-design.md` 的 `data/signals/models/backtest/reporting/gui/core` 结构。
- 主流程保持 ingest → build-signal → backtest(cs/event) → report → regression-check 的闭环。
- 新增契约校验层：服务层写出前校验 `CSPayload` / `EventPayload`，报告层读取时按 `strict_inputs` 执行同构校验。

## 3. 当前未实现（可选增强）

| 可选增强项 | 当前状态 | 备注 |
|---|---|---|
| Transformer 推理/微调接口 | ⏸ 未启动 | 保留 `BaseModel` 可替换入口 |
| 行业中性化、风格中性化 | ⏸ 未启动 | 可作为回测前置处理器 |
| 多数据源适配器 | ⏸ 未启动 | 现阶段仅 CSV/Parquet |

## 4. 收尾项（非性能）

- 已收敛：空数据图表不再触发 legend 警告，减少测试噪音。
- 已收敛：GUI 实验中心与其他页签一致展示任务完成反馈。
- 已收敛：报告 `strict_inputs=true` 由“字段存在”升级为“payload 契约合法”。

## 5. 验证口径

- 最低回归：`pytest tests/unit tests/integration tests/e2e`
- 示例链路：`bash examples/demo_run.sh`
- 指标门禁：`rsnlp check-regression -b tests/baseline/cs_metrics_baseline.json -c artifacts/cs_metrics.json`

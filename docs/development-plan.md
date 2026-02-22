# Development Plan

## 当前状态（2026-02-22）
- Phase 1~5（PRD 必须项）已落地并通过 CI 与回归门禁
- 当前重点：稳定性与可维护性收尾（GUI 线程任务生命周期、输入契约错误提示、文档追溯口径）
- 可选增强（Transformer / 行业风格中性化 / 多数据源适配）尚未启动
- 本轮新增：GUI ingest 入口、GUI 回归门禁入口、信号输出路径可配置、事件诊断标记
- 本轮新增：重构 `examples/data/text_sample.csv` 让三类事件天然可分，并刷新 `tests/baseline/cs_metrics_baseline.json`
- 本轮新增：`ingested_records_path` 的 `trade_date` 严格校验、GUI 任务生命周期统一托管、报告 `strict_inputs` 模式

## Phase 1 - 基础设施
- 建立仓库结构与打包
- 建立 AGENTS、CI、PR 模板

## Phase 2 - 数据与信号
- ingest 标准化
- lexicon 与 event 抽取
- TF-IDF 线性 baseline

## Phase 3 - 回测与报告
- 横截面 IC/分层收益/换手
- 事件窗 CAR 与显著性
- HTML 报告与图表

## Phase 4 - GUI
- 数据、信号、实验、评估、报告 5 页签
- 异步任务执行与日志反馈
- 支持 GUI 执行 ingest 与结果预览
- 支持 GUI 执行 CS 回归门禁校验

## Phase 5 - 质量与求职包装（已完成）
- 完善 unit/integration/e2e
- 案例文档 + 面试讲解文档
- 完善边界测试（单类标签回退、事件窗口径、事件重合诊断）
- 增加 GUI 自动化回归（数据页 ingest、评估页回归门禁）
- 统一 README/架构文档中的指标定义与可配置项说明

## 后续增量（非必须）
- Transformer 推理/微调接口
- 行业中性化、风格中性化增强
- 多数据源适配器

## 提交策略
- 小步提交，单次提交单一目的
- 每次提交前完成最低测试回归

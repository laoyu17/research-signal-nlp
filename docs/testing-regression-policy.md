# Testing & Regression Policy

## 1. 测试分层
- Unit：函数与模块级逻辑
- Integration：跨模块流水线
- E2E：CLI 全流程回归
- GUI：PyQt6 自动化回归（关键页签流程）+ 服务层兜底

## 2. 必跑策略
- 默认：`pytest tests/unit tests/integration`
- 影响因子计算或回测：追加 `pytest tests/e2e`
- 修改 GUI 入口时，至少验证 GUI 自动化回归 + CLI E2E 不回退

## 3. 指标回归阈值
- `|ΔIC| <= 0.01`
- `|ΔLS| <= 0.005`
- 校验命令：`rsnlp check-regression -b <baseline_cs.json> -c <current_cs.json>`

## 4. 回归数据集
- 使用 `examples/data/*` 作为固定样本
- 随机过程固定 seed
- 示例文本数据约束：三类事件样本需可区分，禁止长期完全重合
- 事件研究输出需关注 `diagnostics.full_overlap_event_types`，若为 `true`，应在实验说明中标注事件类型可分性受限

## 5. 基线管理
- 当前基线文件：`tests/baseline/cs_metrics_baseline.json`
- 基线刷新时间：2026-02-22（配套事件样本重构）
- 刷新基线时，必须同步运行 `bash examples/demo_run.sh` 并记录 delta 结果

## 6. CI 门禁
- ruff / mypy / pytest 全通过后才允许合并
- 运行示例流水线并执行回归阈值校验，超阈值直接失败

## 7. 关键边界测试
- 单类标签训练场景应自动回退，不得中断信号构建
- 事件窗口 CAR 口径固定为 `T+1...T+N`（不含事件当日）
- 旧版配置（未声明 `events_output_path`/`debug_output_path`）必须继续可用
- `ingested_records_path` 下 `trade_date` 必须严格可解析；混入非法日期应直接报错
- 报告 `strict_inputs=true` 时，缺失输入文件或 payload 契约不合法应直接失败

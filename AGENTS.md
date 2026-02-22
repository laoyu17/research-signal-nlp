# AGENTS.md（项目级）

## 仓库信息
- GitHub 远端地址：`https://github.com/laoyu17/research-signal-nlp.git`
- 主分支：`main`
- 分支命名：`feat/*`、`fix/*`、`docs/*`、`refactor/*`

## 提交与 PR 规范
- 采用 Conventional Commits：`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:`。
- 每个 PR 必须说明：变更目的、关键改动、验证结果、风险与回滚点。
- 禁止将无关改动混入同一 PR。

## 开发测试回归要求
- 每次开发至少运行：`pytest tests/unit tests/integration`。
- 若改动 `signals/`、`models/`、`backtest/`，必须追加运行 `tests/e2e`。
- 关键指标回归阈值：
  - 横截面 IC 偏移阈值：`|ΔIC| <= 0.01`
  - 分层多空收益偏移阈值：`|ΔLS| <= 0.005`
- 若超出阈值，必须在 PR 中给出原因与处理。

## 文档更新要求
- 变更公开接口（CLI/API/配置）时，必须同步更新：
  - `docs/architecture-design.md`
  - `README.md`
- 变更实验流程或回归基线时，必须同步更新：
  - `docs/development-plan.md`
  - `docs/testing-regression-policy.md`

## 工程习惯
- 默认小步提交，保证每次提交可构建、可测试。
- 优先新增测试再改实现（至少同时提交）。
- 保持 KISS/YAGNI，避免过度抽象。

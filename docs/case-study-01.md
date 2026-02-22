# Case Study 01 - 文本信号到可回测因子

## 背景
示例数据包含研报风格文本（利好/中性/利空）以及对应收益标签。

## 实验流程
1. `rsnlp build-signal -c configs/signal_build.yaml`
2. `rsnlp backtest cs -c configs/backtest_cs.yaml`
3. `rsnlp backtest event -c configs/backtest_event.yaml`
4. `rsnlp report -c configs/report.yaml`
5. `rsnlp check-regression -b tests/baseline/cs_metrics_baseline.json -c artifacts/cs_metrics.json`

## 结果解读
- 横截面指标：观察 IC 均值与 ICIR
- 分层收益：观察 Long-Short 累计收益曲线
- 事件研究：观察不同事件类型在窗口 1/3/5 的 CAR

## 可复现说明
- 所有输入文件与配置已固定在 `examples/data` 与 `configs` 下

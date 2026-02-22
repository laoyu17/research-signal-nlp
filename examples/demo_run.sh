#!/usr/bin/env bash
set -euo pipefail

rsnlp ingest -c configs/data_source.yaml -o artifacts/text_records.parquet
rsnlp build-signal -c configs/signal_build.yaml
rsnlp backtest cs -c configs/backtest_cs.yaml
rsnlp backtest event -c configs/backtest_event.yaml
rsnlp report -c configs/report.yaml
rsnlp check-regression -b tests/baseline/cs_metrics_baseline.json -c artifacts/cs_metrics.json

echo "Demo finished: reports/sample_report.html"

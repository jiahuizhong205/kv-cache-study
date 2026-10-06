# 分析

`summarize.py` 将官方 benchmark JSON 中的常用字段摘录为 Markdown；不将缺失字段补成0，不替代正式重复统计或因果归因。

```bash
.venv-checks/bin/python analysis/summarize.py results/raw/<run-id>/benchmark.json
```

后续扩展：本轮 prefix counter 增量、KV/等待/抢占时间序列、重复中位数/范围，以及缓存开关/容量/到达率对照图。结果公开前人工脱敏。

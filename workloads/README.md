# Workload

目前配置使用固定引擎的官方 `random` 与 `prefix_repetition` synthetic datasets，固定 seed 与长度参数。完整 formal trace 尚未生成。

正式数据应记录：request ID、文本/token IDs、真实输入token数、输出上限、共享组ID、到达时刻、种子、tokenizer revision 和内容SHA256。禁止只靠语义相似判断前缀相同。

共享前缀须是相同 token 序列。无共享组要尽早出现不同 token，核实少量 BOS/模板命中。runtime warmup 和测试前缀 warmup 分离。

本地生成的 trace 放 `workloads/generated/`（Git忽略）；需要分享时只提交经过审查的公开 trace 或生成规则/校验和。跨引擎使用相同 trace/客户端，不能分别随机生成后宣称公平。

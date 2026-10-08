# 基线协议 v0.1（候选，不是已验证结果）

## 1. 实验身份

引擎直接纳入主仓库。上游来源提交与原版源码树哈希见 `configs/engine.json`、[源码溯源](SOURCE_PROVENANCE.md)；原版入口检查源码树不变，不再读取子模块 HEAD。模型候选见 `configs/models.json`，revision 的 null 表示尚未确认，绝不是 main/latest 的别名。

实际运行前记录：主仓库 commit SHA、engine tree SHA、上游 baseline commit、模型/tokenizer snapshot revision、torch/runtime/backend、GPU UUID/型号、硬件预约、启动 CLI、KV token 容量/block size、workload 及统计窗口。来源 commit 不代表机制修改后的身份，engine tree 与主仓库 commit 才标识本次代码。环境冻结清单放 `configs/locks/`，目前没有经过 GPU 验证的 lockfile。

首选单卡 TP=1、BF16。模型为普通 GQA/full-attention：7B 的 KV 约为 56 KiB/token，计算来自 `2 × 28 layers × 4 KV heads × 128 head_dim × 2 bytes`，不包括分页/保留块。2/4/8 GiB KV 池约容纳 37449/74898/149797 token；启动日志的实际容量优先于手算。

租卡前确认 GPU 级独占、Linux/软件权限、主机资源及存储；容器独立不等于 GPU 独占。严肃性能结果不能用有未知高负载邻居的共享卡替代。

## 2. 最小实验与扩展

| ID | 阶段 | 控制变量 | 结果 |
| --- | --- | --- | --- |
| E0 | S0 冒烟 | 1.5B，256/64 token，C=1，30 请求 | 接口、stream、采集成功 |
| E1 | S1 前缀 | 7B，2048 前缀+128 后缀，输出128；C=1/8 | 无共享/有共享 × off/on × 初始冷态/预热态 |
| E2 | S2 长度/并发，待实现 | KV=4GiB；输入512/2048/8192，C=1/8/32 | KV 压力点，单因素扫描 |
| E3 | S2 容量 | 输入8192，输出128，C=32；KV=2/4/8GiB | 抢占、等待与延迟的容量干预 |
| E4 | S2 淘汰，待实现 | 热前缀→冷工作集超容量→重访 | 前缀命中失效与 TTFT |
| E5 | S3 请求率，待实现 | 固定 workload，扫相对饱和率 | 吞吐/p95/等待/失败率 |
| E6 | S3 跨引擎，待实现 | 同卡/模型/trace，vLLM 与 SGLang off/on | 完整系统比较，披露实现差异 |

关闭 prefix cache 只关闭跨请求复用，仍保留 decode 所需 KV。APC 开关在候选源码中必须显式设置，不能依赖默认值。

## 3. Formal 与 pilot 的边界

当前 E0/E1/E3 编排复用官方 benchmark；其随机数据生成、首条预检请求和 warmup 可能影响缓存状态。入口属于 **pilot**，不是冻结 trace + 严格冷/暖控制的最终客户端。

正式 E1 必须补齐：保存精确 token/text trace、长度校验和、共享组 ID；定义冷/暖状态；runtime 预热与 prefix 预热分开；等待预热请求完成；去除 warmup 对 counters 的影响。不以 same seed 替代这些验证。重启自己的服务是恢复状态的一个安全选项，不清理别人的服务，不随意开放开发 reset API。

无共享 synthetic workload 仍可能共享 BOS/少量 token，报告实际命中；E3 明确关闭前缀复用。输出上限不是实际输出长度，当前 pilot 用 ignore-EOS 控制长度，仍需检查实际返回计数。

E5 将到达率与并发上限分开，记录客户端排队及实际发送。过载点报告失败、超时、未完成请求，不能只保留成功请求延迟。

## 4. 验收

正式点至少三次独立重复，交错执行 off/on；保存状态恢复记录和资源干扰。报告重复中位数与范围，尾部样本不足时不做强 p99 结论。

E0：其他组员能按 README 启动，30 请求及观测文件完整。E1：命中与 TTFT 变化对应。E3：容量干预能解释抢占/等待，或诚实记录未观察到抢占。尚无 GPU 运行记录时，只能称仓库与编排就绪。

参考：[模型配置](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/raw/main/config.json)、[官方 benchmark](https://docs.vllm.ai/en/latest/benchmarking/cli/)。固定源码的实现和实际日志优先于浮动文档。

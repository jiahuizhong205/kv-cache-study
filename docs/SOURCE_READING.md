# vLLM 源码阅读路线：围绕 KV Cache

所有链接指向 `engines/vllm`，当前固定提交 `9b2f34cad446f73b1699e8236ec0b611a65f48af`。先阅读上游 [AGENTS.md](../engines/vllm/AGENTS.md)；本阶段只读，无需运行 CUDA。

## 1. 一个请求的主路径

```text
HTTP 请求
  → OpenAI completion/chat API
  → engine core 接收请求
  → scheduler 决定 token budget、等待/运行与抢占
  → KV cache manager 查询前缀、申请 blocks
  → block pool 管理 hash、引用和可复用块
  → model runner 执行 prefill/decode，读写 KV
  → token 输出与统计
```

这是理解关系的路线图，不是所有实现都严格串行调用这七步；具体以代码为准。

## 2. 分四轮阅读

### 第一轮：定义和配置（约半天，自定节奏）

- [cache.py](../engines/vllm/vllm/config/cache.py)：`CacheConfig`。找 `block_size`、`enable_prefix_caching`、`gpu_memory_utilization`、`kv_cache_memory_bytes`。
- [observability.py](../engines/vllm/vllm/config/observability.py)：`kv_cache_metrics` 与采样规则。

写下：KV 块与 token 的关系是什么？KV 显存预算是否包含权重？prefix 关闭之后 decode 是否还使用 KV？

### 第二轮：调度与分配（1–2 天，自定节奏）

- [scheduler.py](../engines/vllm/vllm/v1/core/sched/scheduler.py)：搜 `schedule`、`preempt`、`allocate_slots`，追一次分配失败的分支。
- [kv_cache_manager.py](../engines/vllm/vllm/v1/core/kv_cache_manager.py)：搜 `get_computed_blocks`、`allocate_slots`、`free`，记录函数输入输出。
- [single_type_kv_cache_manager.py](../engines/vllm/vllm/v1/core/single_type_kv_cache_manager.py)：管理器分层细节，第一遍可只看调用到的类型。
- [block_pool.py](../engines/vllm/vllm/v1/core/block_pool.py)：搜 `get_cached_block`、`get_new_blocks`、`free_blocks`、`get_usage`，理解引用计数与 free queue。

重点：free block 可能仍保留缓存内容；引用为零不等于立刻抹掉。前缀淘汰与活跃请求抢占不是同一事件。记录哪些分支真正决定复用/淘汰，不仅看函数名。

### 第三轮：执行与容量（约 1 天）

- [kv_cache_utils.py](../engines/vllm/vllm/v1/core/kv_cache_utils.py)：缓存 spec、组与容量计算。起步只关注普通 full attention，暂跳 hybrid/MLA/Mamba。
- [core.py](../engines/vllm/vllm/v1/engine/core.py)：调度输出如何送往执行层。
- [gpu_model_runner.py](../engines/vllm/vllm/v1/worker/gpu_model_runner.py)：搜 `execute_model`，追正常 prefill/decode 主路径，暂不深挖全部 kernel。

写下：同样 8192 token，GQA 的 KV 存储为何小于所有 attention heads 都存 K/V 的情况？逻辑 token 容量与 nvidia-smi 显存为何不是一回事？

### 第四轮：指标（约半天）

- [stats.py](../engines/vllm/vllm/v1/metrics/stats.py)：统计在何处产生。
- [loggers.py](../engines/vllm/vllm/v1/metrics/loggers.py)：指标名、类型、标签与单位。
- [completion API](../engines/vllm/vllm/entrypoints/openai/completion/api_router.py)：回看请求和 stream 输出入口。

为每个指标写四列：产生位置、累加/采样方式、分母/单位、能支持什么结论。尤其分清 prefix hit token 数、抢占事件数、抽样 eviction 生命周期和实际重算 token 数。

## 3. 第一份阅读笔记的完成标准

不用通读整个仓库。能够解释以下过程，即可形成有用的 A 组笔记：

1. 新请求到来、未命中前缀，如何分配 KV？
2. 同一前缀再次请求，哪些 blocks 可以复用？
3. 请求完成后，块如何进入可分配状态？
4. 空闲前缀被复用，旧请求重访为什么 miss？
5. 活跃请求无法获得新块，调度器如何处理？

使用 [笔记模板](notes/TEMPLATE.md)。只提交你的总结、函数引用与必要短片段，不复制整份源文件作为笔记。暂时不要把阅读推测标成实验结论。

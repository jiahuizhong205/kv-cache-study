# KV Cache Study

面向 AI Infra 课程的 LLM serving / KV Cache 实验仓库。

**当前阶段：阅读源码与搭建可复现实验入口。不是已完成的性能复现。**

实验主仓库：[jiahuizhong205/kv-cache-study](https://github.com/jiahuizhong205/kv-cache-study)。
引擎源码仓库：[jiahuizhong205/vllm](https://github.com/jiahuizhong205/vllm)。两者按当前要求设为 **PUBLIC**。

源码仓库是官方 `vllm-project/vllm` 的 GitHub fork，子模块固定到未修改的候选提交。上游地址保留为 `https://github.com/vllm-project/vllm.git`；上游 LICENSE 和版权说明未改动。源码 fork 的继承 Actions 暂禁用，主仓库仅运行 CPU 编排检查。

## 1. 先从哪里开始

准备阅读 vLLM 的同学，先看 [源码阅读路线](docs/SOURCE_READING.md)，从缓存配置、调度器、KV 管理器与 block pool 入手，不必立即租 GPU。

建议阅读顺序：

1. [基线协议](docs/BASELINE_PROTOCOL.md)：我们固定什么、比较什么。
2. [源码阅读路线](docs/SOURCE_READING.md)：代码入口、问题清单与笔记模板。
3. [协作与子模块](docs/CONTRIBUTING.md)：源码修改如何提交、如何共享。
4. [运行指南](docs/RUNBOOK.md)：审批之后如何安装、启动与采集。
5. [指标口径](docs/METRICS.md)、[进度与审批](docs/STATUS.md)。

## 2. 团队定位

| 组 | 任务 | 交付 |
| --- | --- | --- |
| A：System Reproduction | 固定环境、baseline/workload、profiling | 可重复且可解释的系统基线 |
| B：Paper Reproduction | 复现所选论文核心机制 | 独立机制开发分支与可运行实现 |
| C：Extension & Evaluation | 小延伸与完整评测 | 改进、对照与可重复 evaluation |

首轮以 A 组为主。模型推理不会更新权重，不需要先训练模型。B/C 组与 A 组共享评测协议，但不能直接修改 A 组的原版基线。

## 3. 目录结构

```text
kv-cache-study/
  engines/vllm/            # 完整引擎源码，独立 Git 子模块
  configs/                # 版本身份、候选模型与实验配置
  scripts/                # 默认 dry-run 的服务/压测入口
  workloads/              # workload 规则与实验矩阵
  analysis/               # 结果摘要工具与分析说明
  docs/                   # 协议、阅读、运行、指标、协作与进度
  tests/                  # 不依赖 torch/GPU 的编排测试
  results/                # 脱敏汇总与图表
  results/raw/            # 本地原始结果，Git 忽略
```

Windows 本地实际根目录目前为 `C:\Users\zhongjiahui\Desktop\vllm`，源码入口为 `engines/vllm`。原来的 `vllm/`、历史计划和训练材料暂留本地且被忽略，不会上传；不要在旧目录中开展新实验。

## 4. 当前候选基线

| 项目 | 约定 |
| --- | --- |
| 引擎 | vLLM，提交 `9b2f34cad446f73b1699e8236ec0b611a65f48af` |
| 状态 | `candidate_unvalidated`，尚未在研究 GPU 上运行 |
| 冒烟模型 | Qwen2.5-1.5B-Instruct |
| 正式模型 | Qwen2.5-7B-Instruct |
| 精度/并行 | BF16 权重与 KV，单卡 TP=1 |
| 控制因素 | 前缀复用、KV 容量、输入长度、并发/到达率 |
| 尚未冻结 | 模型与 tokenizer revision、实际 GPU/环境/后端 |

第一轮准备 E0 冒烟、E1 前缀复用探索、E3 KV 压力。SGLang 与论文机制尚未接入。详细定义见 [基线协议](docs/BASELINE_PROTOCOL.md)。不能用一个模型名字或一次成功启动代替实验版本冻结。

## 5. 获取项目与日常更新

```bash
git clone --recurse-submodules https://github.com/jiahuizhong205/kv-cache-study.git
cd kv-cache-study
```

已经 clone、但 `engines/vllm` 为空：

```bash
git submodule update --init --recursive
```

主仓库更新后同步固定的子模块提交：

```bash
git pull --ff-only
git submodule update --init --recursive
```

子模块通常处于 detached HEAD，这是复现固定提交的正常状态；**需要修改时先建立开发分支**。不要在有未提交引擎修改时盲目更新子模块。

## 6. 只预览实验命令

脚本运行于 Linux/WSL，使用隔离 Python 环境。只需标准库即可预览，不需要 torch、CUDA 或模型：

```bash
uv venv --python 3.12 .venv-checks
PYTHON_BIN="$PWD/.venv-checks/bin/python" ./scripts/run_server.sh --experiment E0
PYTHON_BIN="$PWD/.venv-checks/bin/python" ./scripts/run_baseline.sh --experiment E0
PYTHON_BIN="$PWD/.venv-checks/bin/python" ./scripts/collect_metrics.sh
.venv-checks/bin/python -m unittest discover -s tests -v
```

默认只打印计划，不启动 GPU、不下载权重、不请求服务、不产生结果目录。实际执行须添加 `--execute` 并提供资源许可记录、固定模型 snapshot、revision 和 GPU UUID；见 [运行指南](docs/RUNBOOK.md)。权限参数是显式确认记录，不是操作系统硬隔离。

目前入口复用固定源码的官方 `vllm serve` 和 `vllm bench serve`，不截取引擎实现。E1 入口暂用于探索，不自动保证冷态、预热态或冻结 request trace；完成这些控制之前不能作为正式前缀实验结果。

## 7. 分享与安全

- 这个仓库是公开的；不要提交个人地址、内网服务器信息、密钥、账号密码、私有 workload 或未经授权的数据。
- 模型权重、环境和原始请求响应不提交。模型有独立许可证，使用/分享前核对对应模型条款。
- 公开结果只放脱敏摘要，必须保留实验身份、失败率与测量定义。
- 采用双层提交：先推送引擎开发提交，再提交主仓库子模块指针。
- 引擎保留上游许可。本仓库自写实验编排目前未额外授予开源许可证，公开可见不等于自动获得任意再分发许可；团队确认后再统一选择许可。

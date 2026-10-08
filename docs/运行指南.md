# 运行指南：先预览，再审批，最后执行

当前未安装 GPU 环境、未下载模型、未启动服务。所有默认命令是 dry-run。当前脚本用于 pilot，正式冷/暖 trace 协议仍待实现。

## 1. 无 GPU 的预览与测试

使用 Python 3.12 的独立 `.venv-checks`。Linux/WSL：

```bash
uv venv --python 3.12 .venv-checks
export PYTHON_BIN="$PWD/.venv-checks/bin/python"
./scripts/run_server.sh --experiment E0
./scripts/run_baseline.sh --experiment E1
./scripts/run_server.sh --experiment E3 --kv-gib 2 --cache-mode off
./scripts/collect_metrics.sh --duration 60
.venv-checks/bin/python -m unittest discover -s tests -v
```

Windows 也可用隔离环境的 `Scripts/python.exe scripts/runner.py server --experiment E0` 预览；实际 serve/bench 限 Linux。默认不访问 GPU/网络，不生成原始结果。

## 2. GPU 环境前置审批

- [ ] GPU UUID、独占/共享许可、时间窗、总显存余量与压测规模明确。
- [ ] 固定模型/tokenizer revision，许可、下载和磁盘位置已确认。
- [ ] Linux、Python、torch/runtime/backend 与源码提交兼容。
- [ ] 独立 `.venv`，不升级整机驱动，不修改公共 base 环境。
- [ ] 自己的实例、端口、数据与结果目录明确；无其他用户流量。

审批后按照固定提交的安装文档与 AGENTS.md，用 uv 创建 `.venv`。vLLM 在此环境以 `engines/vllm` editable 源码安装；预编译扩展要与提交匹配，若不可用则讨论固定发行版或构建方案，不能自动切浮动 nightly。记录依赖锁后再 GPU 冒烟。

单仓库注意：引擎没有独立 Git HEAD，上游构建的 Git 自动探测可能读到主仓库身份或缺少发行版标签。安装前由环境负责人核查固定源码 `setup.py` 的 `VLLM_VERSION_OVERRIDE` 与 `VLLM_PRECOMPILED_WHEEL_COMMIT`，显式采用经确认的版本和上游 commit，而不是当前主仓库 commit；预编译 wheel 要验证存在、匹配 CUDA/torch/硬件并记录来源。不能只设置一个版本字符串就声称扩展兼容。这里尚未验证单仓库 GPU 构建，不能直接把上游通用安装命令视为已跑通。

验证环境使用的是这个源码副本：

```bash
.venv/bin/python -c 'import vllm, torch; print(vllm.__file__); print(torch.__version__, torch.version.cuda)'
```

`nvidia-smi` 的 CUDA 显示值不是实际 toolkit/runtime；检查硬件支持与一条请求，不能只看 import。

## 3. 实际执行示例（占位符须替换，尚未执行）

只有自己获得许可的实例可启动/压测。模型事先下载到固定 snapshot；启动/压测设置 offline，禁止自动下载。

```bash
# terminal 1：前台运行，日志位于 results/raw/server-e0-001/server.log
./scripts/run_server.sh --experiment E0 --execute \
  --approval-id reservation-001 --run-id server-e0-001 \
  --gpu-uuid GPU-REPLACE-WITH-ACTUAL-UUID \
  --model-dir /absolute/path/to/model/snapshot \
  --model-revision REPLACE_WITH_40_HEX_COMMIT

# terminal 2：先确认服务 ready，再压测自己的实例
./scripts/run_baseline.sh --experiment E0 --execute \
  --approval-id reservation-001 --run-id bench-e0-001 \
  --gpu-uuid GPU-REPLACE-WITH-ACTUAL-UUID \
  --model-dir /absolute/path/to/model/snapshot \
  --model-revision REPLACE_WITH_40_HEX_COMMIT \
  --server-manifest results/raw/server-e0-001/manifest.json

# terminal 3：与 benchmark 时间窗重叠的定时采集
./scripts/collect_metrics.sh --execute \
  --approval-id reservation-001 --run-id observe-e0-001 \
  --gpu-uuid GPU-REPLACE-WITH-ACTUAL-UUID --duration 120
```

UUID、model revision 与资源许可是人工确认，不代表系统自动授予权限。collector 只采样该 GPU，不终止任务。server manifest 只证明由该脚本生成，不提供服务端身份认证；专用端口与资源窗口仍须确认。审批后自己的前台服务用 Ctrl-C 正常结束，不按其他人的 PID 杀进程。

E0 使用 eager 模式用于功能验证。E1/E3 使用候选引擎默认图配置，后端和图配置必须记录，不能把 E0 性能直接混入正式对比。

## 4. 参数与结果

`--cache-mode on/off` 和 `--kv-gib 1/2/4/8` 可覆盖候选配置；server 与 bench 的有效配置必须一致。变更池容量通常重启自己的服务。KV bytes 只限制 KV 池，不是总显存上限；权重/激活/graph 仍占显存。

一个 run ID 一个目录，已存在则拒绝覆盖。服务保存 manifest/log；benchmark 保存前后 metrics、官方 detailed JSON、日志；collector 保存原始 metrics 快照与 GPU JSONL（包含原始CSV文本和UTC/monotonic）。文件在 `results/raw/`，默认不公开。

当前自动 manifest 记录源码与配置身份，不包含完整环境/硬件锁或 GPU readiness 验证。首轮需手工补齐版本、实际 KV 容量、block size、backend、图配置与日志；不要将 pilot manifest 视为正式协议已全部满足。

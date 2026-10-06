# 环境锁

当前尚未生成经过 GPU 验证的依赖锁。不要把 `engine.json` 中的 null 解释为自动安装最新版。

GPU 冒烟通过后在此提交脱敏版本清单：Python、引擎/torch/transformers、CUDA runtime、attention backend、所有依赖及容器 digest（若采用容器）。不提交机器账户、访问令牌、环境变量 dump 或本地绝对私有路径。

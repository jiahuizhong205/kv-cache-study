# 协作与子模块

## 1. 两层版本

主仓库管理协议/workload/分析；`engines/vllm` 管理引擎源码。子模块指针固定到 commit，不自动跟随 baseline/main。

源码仓库 origin 是团队公开研究副本；upstream 为官方 `https://github.com/vllm-project/vllm.git`。新 clone 通常只自动获得 origin，可自行添加 upstream。当前 baseline 未改动上游代码，保留 LICENSE 和版权。

## 2. 只读阶段

阅读笔记放 `docs/notes/`。不需要修改引擎，也不需要启动服务。主仓库的提交不会自动保存子模块未提交的文件修改。

## 3. 引擎开发

先阅读子模块自己的 AGENTS.md 和对应区域规范。上游要求 uv 环境、测试及人类审核；当前研究副本同样保留这些规范，不自动向官方提 PR。

示例（由成员在需要机制开发时手动执行）：

```bash
cd engines/vllm
git switch -c mechanism/topic-name
# 修改、审核、测试后提交；需要写权限
git add <reviewed-files>
git commit -m "Implement mechanism: topic-name"
git push -u origin mechanism/topic-name
cd ../..
git add engines/vllm
git commit -m "Pin mechanism engine revision"
git push --recurse-submodules=check
```

不要把机制分支覆盖 baseline。A 组原版实验引用最初固定 SHA，机制实验记录自己的 SHA。主仓库切分支后子模块可能需要同步，但在有未提交引擎更改时先保护工作，不盲目更新或 reset。

## 4. 环境与共享

可修改源码不等于环境正在使用该源码。用对应版本的 editable 安装，核查 `vllm.__file__`；修改 Python 后重启服务，C++/CUDA 修改按上游流程重编译。不要把浮动 nightly 预编译扩展冒充固定提交。

两个仓库需要分别给成员写权限；一个仓库权限不自动赋予另一个。只读成员可以通过公开仓库 clone；没有写权限的成员通过自己分支/PR 协作。

参考：[Git 子模块](https://git-scm.com/book/en/v2/Git-Tools-Submodules)、[源码安装](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)。

# 当前状态与待办

更新：2026-10-08。状态只描述可核验成果，不将准备工作写成已完成实验。

## 已准备

- 实验单仓库结构，完整 vLLM 源码直接纳入 `engines/vllm/`，不再使用子模块。
- 保留原版源码 tree 与上游 commit 溯源，适配 baseline 源码保护和运行 manifest。
- E0/E1-pilot/E3 配置，默认只预览的启动/压测/采集入口。
- README、源码阅读路线、协作、基线与指标协议。
- 无 GPU/模型依赖的编排测试与公开 CI。

本地验证：27 项 unittest 通过，涵盖原版 tree、已提交源码变动、未提交变动和缺失源码的保护；源码导入 tree 与上游完全一致，真实提交后的 baseline 保护通过，shell 语法检查通过。[单仓库转换 GitHub CPU CI](https://github.com/jiahuizhong205/kv-cache-study/actions/runs/37732535750) 已通过，覆盖测试和三个 dry-run；这不代表 GPU 验证。

用户已授权删除独立 `jiahuizhong205/vllm` fork；已核验账号拥有 ADMIN、目标是官方项目的 fork，但 CLI 删除返回 HTTP 403，当前凭证缺少 `delete_repo` scope。因此远程 fork 尚未删除，不声称删除完成，需用户自行网页删除或先为 CLI 授予删除权限。实验主仓库不再依赖该 fork。最初创建的空仓库 `jiahuizhong205/vllm-kv-cache` 不参与实验，未纳入本次明确指定的远程 fork 删除范围。

本地清理已完成：在核验 GitHub 中的完整源码 tree 后，删除旧 `vllm/` 重复副本；单仓库快照与已验证的 Git bundle 可用于恢复。历史规划、训练材料和子模块元数据已移入 `.cleanup-backups/2026-10-08/`，不公开。`.venv-checks`、编辑器与工具配置仍有用途，保留。

## 未执行或尚未验收

- [ ] GPU 租用/独占预约与资源许可。
- [ ] 模型/tokenizer revision 冻结及权重下载。
- [ ] GPU 依赖安装、源码构建/预编译兼容性验证。
- [ ] E0 模型冒烟。
- [ ] 正式 E1 冷/暖状态、精确 trace 与长度校验。
- [ ] E2/E4/E5 及 SGLang 接入。
- [ ] 任意 TTFT、吞吐、命中、抢占性能结果。
- [ ] 论文选定及与 B 组版本关系确认。
- [ ] 增加团队成员权限（需要成员账号）。

## 下一步：读源码

共享进度入口：[实验仓库 Issues](https://github.com/jiahuizhong205/kv-cache-study/issues)。已建立源码阅读、A1 环境冻结、A2 正式前缀协议、A3 指标采集四项待办，未指定成员负责人。

从 `docs/SOURCE_READING.md` 第一轮开始，提交一份阅读笔记。先理解配置、分配、命中与抢占，不修改原版引擎，不把读代码的推断标作实测。

GPU 运行前使用 `docs/RUNBOOK.md` 的清单完成审批。本次仓库建立不授权自动租用、收费、安装或启动负载。

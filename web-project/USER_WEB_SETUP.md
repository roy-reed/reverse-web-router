# 用户一次性设置

## ChatGPT Project

1. 打开项目 `网页端调用本地`。
2. 将 `PROJECT_INSTRUCTIONS.md` 粘贴到该项目的项目指令。
3. 连接获准使用的 GitHub 仓库。只授予需要的仓库范围。
4. 日常直接输入自然语言任务，不输入路由命令、Codex 命令、DeepSeek 命令、本地路径或 JSON。

网页端应把普通分析留在网页，把可云端验证的仓库工程写入 GitHub，把真正依赖本机的阶段交给 `LOCAL_EDGE`。

## GitHub 设置

先在一个测试仓库验证。需要手动启用：

- GitHub Actions；
- `main` 分支保护；
- 必需检查：`Agent verification / deterministic`；
- 禁止 force push；
- 默认禁止 agent 自动合并 `main`；
- Environment：`agent-workers`，建议配置审批人和分支限制；
- Repository variable：`RWR_LIVE_WORKER=false`，完成干跑验收前不要改为 `true`。

云端 DeepSeek 只需要一个 Secret 名称：`DEEPSEEK_API_KEY`。不要复制本机 DPAPI 文件，不要在 Issue、PR、日志或 Artifact 中填写密钥。项目第一次上线前应检查 workflow 权限仍为最小范围。

## 正常使用与状态

示例：在 ChatGPT Project 中输入“在仓库 Y 实现功能 X，适合时拆分并行任务，不要合并 main”。网页模型应创建父 Run Issue 和子任务 Issues。之后可直接问：

- 项目现在到哪一步？
- 哪些任务失败或等待本地？
- 为什么某个任务被阻塞？
- 只修复验收失败，不要合并。

无需打开本机即可从 GitHub Issues、PR 和 Actions 查看 `GITHUB_CLOUD` 状态。本机关闭时云任务应继续。

## LOCAL_EDGE

只有出现本地依赖时才按 `local-edge/LOCAL_EDGE_SETUP.md` 安装。扩展弹窗必须显示已绑定项目；合法本地任务会出现 Native Messaging 回执，并明确显示 `CODEX_DIRECT`、`CODING_RUNNER` 或 `NEEDS_USER`。没有回执就表示本地执行尚未发生。

安装扩展、注册 Native Messaging host、映射 workspace alias、启动本地 worker、启用网络、提升权限、推送、合并或写入线上 Secrets 都仍需要你的明确批准。

## 禁用与卸载

- 云端：把 `RWR_LIVE_WORKER` 设为 `false` 或禁用相关 Actions workflows；撤销 GitHub 连接时同时审查残留 Secrets 和 Environment。
- 本地：在扩展中解除项目绑定，禁用或删除扩展，再删除 Native Messaging 注册项。无需删除仓库历史或本地工作成果。

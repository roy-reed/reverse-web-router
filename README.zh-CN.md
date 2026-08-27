# Reverse Web Router

面向 ChatGPT Project「网页端调用本地」的云端优先任务路由与验收控制面。

当前定位是公开 MVP：默认采用 dry-run，不调用外部模型、不产生外部模型费用。GitHub 是规范控制面，GitHub Actions 负责可复现检查；只有确实需要用户 Windows 机器或本地验收时，才使用 `LOCAL_EDGE` 兼容路径。

## 主要能力

- 以 `rwrouter/2` 任务信封、状态机、依赖门和声明/预算门约束任务流转。
- 支持 `CONTROL`、`WEB_DIRECT`、`GITHUB_CLOUD`、`LOCAL_EDGE` 和 `HYBRID_CLOUD_LOCAL` 等表面与路由边界。
- 通过 Issue、PR 和 GitHub Checks 保留可审计的任务账本、验收结果与失败原因。
- 保留 V2 Chromium 扩展、Native Messaging、本地 Codex 执行器的兼容适配，但不默认安装或启动本地组件。
- 对 arXiv、AnySearch 和 Research Harness 提供低开销、可复现的研究工具接入契约。

具体架构以 [`ARCHITECTURE_DECISION.md`](ARCHITECTURE_DECISION.md) 为准，传输和状态契约见 [`PROTOCOL.md`](PROTOCOL.md) 与 [`docs/contracts/`](docs/contracts/)。

## 目录结构

| 目录 | 用途 |
| --- | --- |
| `.agent-orchestrator/` | Schema、状态机、依赖/声明门、Worker 适配器和验证脚本 |
| `.github/workflows/` | Issue 分发、PR 确定性检查和 verify-only 集成门 |
| `web-project/` | ChatGPT Project 指令与用户侧配置清单 |
| `local-edge/` | `rwrouter/1.1` 兼容转换器、扩展和 stdio Native Messaging 主机 |
| `codex-skill/` | 复用 `coding-project-runner` 的本地 Codex 执行策略 |
| `docs/` | 研究工具、路由策略、契约和运维说明 |
| `tests/` | 离线标准库验收测试 |

## 快速开始

要求 Python `>=3.10`；项目运行依赖为空，优先使用当前平台的 Python 虚拟环境隔离开发。

```powershell
git clone https://github.com/roy-reed/reverse-web-router.git
Set-Location reverse-web-router
python -m unittest discover -s tests -v
python -m compileall -q .agent-orchestrator local-edge
python .agent-orchestrator/scripts/validate_repo.py
```

日常改动建议按以下顺序验收：

1. 修改契约或实现后运行单元测试。
2. 运行 `compileall` 和仓库结构/安全边界验证。
3. 检查 `git diff --check`，确认没有尾随空白或异常差异。
4. 需要接入本地端时，再阅读 [`local-edge/LOCAL_EDGE_SETUP.md`](local-edge/LOCAL_EDGE_SETUP.md) 和 [`web-project/USER_WEB_SETUP.md`](web-project/USER_WEB_SETUP.md)。

## 跨平台与安全边界

- Python 代码使用标准库和环境变量，路径应通过 `pathlib` 处理，不写死用户目录、盘符、代理端口或服务地址。
- GitHub Actions 以 Linux runner 为基线；Windows 本地操作以 PowerShell 为示例，具体本地桥接配置必须放在仓库外。
- 不要把 API key、Cookie、私钥、浏览器状态、真实本地绝对路径或原始日志提交到仓库、Issue、PR、Actions 日志或验收回执。
- DeepSeek 等真实 Provider 调用必须同时满足显式授权、凭据配置、声明/账本门和外部调用预算；默认不会触发。
- 验证脚本不会创建仓库、安装扩展、注册 Native Messaging、修改分支保护、写入 Secrets、推送、合并或调用外部模型。

发现疑似凭据或安全问题时，请先按 [`SECURITY.md`](SECURITY.md) 处理；日常贡献规范见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 相关文档

- [`docs/web-local-reasoning-routing.md`](docs/web-local-reasoning-routing.md)：网页端与本地端的路由策略
- [`docs/research-tooling.md`](docs/research-tooling.md)：研究工具集成契约
- [`local-edge/LOCAL_EDGE_SETUP.md`](local-edge/LOCAL_EDGE_SETUP.md)：本地兼容路径配置边界
- [`LICENSE`](LICENSE)：MIT 许可证

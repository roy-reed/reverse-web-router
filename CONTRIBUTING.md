# 贡献指南

感谢参与维护 Reverse Web Router。这个仓库同时承载公开协议、GitHub 控制面和可选的本地兼容路径，贡献时请先保持边界清晰，再扩大实现范围。

## 提交前检查

在仓库根目录运行：

```text
python -m unittest discover -s tests -v
python -m compileall -q .agent-orchestrator local-edge
python .agent-orchestrator/scripts/validate_repo.py
git diff --check
```

如果修改了 `docs/contracts/`、`PROTOCOL.md`、状态机或工作流，还应在 PR 描述中说明兼容性影响、失败路径和验收证据。

## 变更边界

- 优先保持 `rwrouter/2` 契约、dry-run 默认值和 fail-closed 校验行为。
- 不提交凭据、Cookie、私钥、浏览器状态、真实本地路径、原始日志或用户数据。
- 不在未经明确评审的情况下新增自动推送、自动合并、分支保护修改、扩展安装或 Native Messaging 注册行为。
- 外部 Provider 只能通过已有的显式授权、账本、声明和预算门进入；测试应保持离线可复现。
- 新增平台适配时，使用环境变量和 `pathlib`，同时补充对应平台的验证说明。

## PR 建议

PR 标题应概括协议、实现、文档或测试变更。正文至少包含：变更目的、影响范围、运行的检查命令、已知限制，以及是否改变公开安全边界。

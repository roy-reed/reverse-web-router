# Reverse Web Router

Cloud-first task routing for the ChatGPT Project `网页端调用本地`.

The canonical control plane is GitHub. Repository engineering defaults to cloud workers and GitHub checks. The V2 Chromium extension, Native Messaging bridge, local Codex executor, and existing `coding-project-runner` remain available as the `LOCAL_EDGE` compatibility path for work that materially requires the user's Windows machine or local acceptance.

The source contracts are preserved under `docs/contracts/`. The binding architecture decision is `ARCHITECTURE_DECISION.md`.

## Components

- `.agent-orchestrator/`: schemas, state machine, dependency and claim gates, worker adapters, boundary checks, workflows, and validation scripts.
- `.github/workflows/`: Issue dispatch, deterministic PR verification, and a verify-only integration gate.
- `web-project/`: exact ChatGPT Project instructions and the user setup checklist.
- `local-edge/`: rwrouter/1.1 compatibility translator, Manifest V3 extension, and stdio-only Native Messaging host.
- `codex-skill/reverse-web-router-executor/`: local Codex execution policy that reuses `coding-project-runner`.
- `tests/`: offline standard-library acceptance tests.

## Safe local validation

```text
python -m unittest discover -s tests -v
python -m compileall -q .agent-orchestrator local-edge
python .agent-orchestrator/scripts/validate_repo.py
```

The repository is dry-run by default. It does not create a GitHub repository, install an extension, register a Native Messaging host, change branch protection, write Secrets, push, merge, or call an external model during validation.

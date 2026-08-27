# Reverse Web Router

Cloud-first task routing for the ChatGPT Project `网页端调用本地`.

中文说明见 [README.zh-CN.md](README.zh-CN.md)。

Status: public MVP. Dry-run behavior and zero external-model spend are the defaults.

The canonical control plane is GitHub. Repository engineering defaults to cloud workers and GitHub checks. The V2 Chromium extension, Native Messaging bridge, local Codex executor, and existing `coding-project-runner` remain available as the `LOCAL_EDGE` compatibility path for work that materially requires the user's Windows machine or local acceptance.

The source contracts are preserved under `docs/contracts/`. The binding architecture decision is `ARCHITECTURE_DECISION.md`.

## Components

- `.agent-orchestrator/`: schemas, state machine, dependency and claim gates, worker adapters, boundary checks, workflows, and validation scripts.
- `.github/workflows/`: Issue dispatch, deterministic PR verification, and a verify-only integration gate.
- `web-project/`: exact ChatGPT Project instructions and the user setup checklist.
- `local-edge/`: rwrouter/1.1 compatibility translator, Manifest V3 extension, and stdio-only Native Messaging host.
- `codex-skill/reverse-web-router-executor/`: local Codex execution policy that reuses `coding-project-runner`.
- `docs/research-tooling.md`: reproducible, low-overhead integration contract for arXiv, AnySearch, and Research Harness.
- `tests/`: offline standard-library acceptance tests.

Substantive web-originated work uses the DEEP/Sol High gateway; CONTROL traffic is the zero-handoff exception. Local execution is cost-first: scores 0–5 use FAST/Luna with the recorded `none` through `high` effort, 6–7 use BALANCED/Terra at `high` or `xhigh`, and 8–10 use DEEP/Sol at `max`. Provider-native model names remain in adapters rather than transport envelopes. DeepSeek `fast` and `balanced` use V4 Flash, while V4 Pro is reserved for a bounded planner/reviewer stage or an isolated non-decomposable deep unit. The complete two-axis policy is documented in [`docs/web-local-reasoning-routing.md`](docs/web-local-reasoning-routing.md).

DeepSeek delegation is disabled by default, including when `delegated_stage` is `AUTO`. A live provider call requires an explicit delegated stage, `RWR_ALLOW_LIVE=1`, the configured credential, and the claim/ledger gates.

## Quick start

```powershell
git clone https://github.com/roy-reed/reverse-web-router.git
Set-Location reverse-web-router
python -m unittest discover -s tests -v
python .agent-orchestrator/scripts/validate_repo.py
```

Do not commit API keys or other credentials. Live-provider execution is opt-in and may not exceed the external-call budget recorded in the reasoning plan.

## Safe local validation

```text
python -m unittest discover -s tests -v
python -m compileall -q .agent-orchestrator local-edge
python .agent-orchestrator/scripts/validate_repo.py
```

The repository is dry-run by default. It does not create a GitHub repository, install an extension, register a Native Messaging host, change branch protection, write Secrets, push, merge, or call an external model during validation.

## License

MIT. See [LICENSE](LICENSE).

# Architecture Decision: Cloud-first with LOCAL_EDGE compatibility

## Precedence

`docs/contracts/github-cloud-supplement.md` governs the overall architecture. `docs/contracts/codex-bootstrap-v2.md` remains authoritative only for the local transport and local execution path, which is named `LOCAL_EDGE`.

If the documents conflict, apply this order:

1. security and explicit user constraints;
2. GitHub Cloud Control Plane Supplement;
3. V2 local Bridge contract within `LOCAL_EDGE` only;
4. implementation defaults.

## Canonical routing surfaces

- `CONTROL`: acknowledgements, approvals, status requests, and orchestration control.
- `WEB_DIRECT`: analysis, writing, research, and other work requiring no repository execution.
- `GITHUB_CLOUD`: default for repository engineering that can run and be verified off-machine.
- `LOCAL_EDGE`: local-only files, desktop applications, hardware, local credentials, proprietary environments, or local final acceptance.
- `HYBRID_CLOUD_LOCAL`: cloud-safe repository stages followed by explicit local acceptance stages.

The legacy V2 values `WEB`, `LOCAL`, and `HYBRID` are accepted only through a compatibility translator. They map to `WEB_DIRECT`, `LOCAL_EDGE`, and `HYBRID_CLOUD_LOCAL` respectively.

## Protocol

The canonical semantic envelope is `rwrouter/2`. The `rwrouter/1.1` Native Messaging wire format remains supported by a translation adapter at the `LOCAL_EDGE` boundary. Core task records use provider-neutral fields. Provider model names, credentials, and cost controls stay inside adapters.

## GitHub control plane

GitHub is the durable task ledger and state machine. One parent Issue represents a run; child Issues represent bounded work units. Each work unit has a UUID, dependency set, narrow allowed and forbidden paths, deterministic acceptance commands, and time/cost limits. Workers use isolated branches and linked pull requests. GitHub Actions provide deterministic verification, with an independent semantic reviewer where required.

`main` remains protected and human-controlled. No agent may force-push or merge into `main` by default. A task cannot invoke duplicate paid workers; idempotency must use task IDs, concurrency groups, claim records, and provider run IDs rather than labels alone.

## LOCAL_EDGE

Preserve the V2 chain as an optional edge adapter:

```text
ChatGPT Web -> Chromium Extension -> Native Messaging Bridge -> Local Codex
                                                        -> coding-project-runner when locally eligible
```

The extension transports and displays status. The Bridge validates and normalizes handoffs, maps workspace aliases using local-only configuration, and launches Codex. Codex remains the final local authority. The Bridge and extension never call DeepSeek directly. The existing `coding-project-runner` remains authoritative for local Pi and DeepSeek execution.

Do not require `LOCAL_EDGE` for `GITHUB_CLOUD`. Cloud tasks must continue while the user's computer is off.

## Security boundary

Never place credentials, private keys, browser authentication state, unrelated personal data, local absolute paths, restricted local material, or sensitive configuration in Issues, pull requests, logs, artifacts, receipts, or model packets. GitHub execution uses least-privilege permissions and protected Environments for worker secrets. The local Bridge uses Native Messaging and must not expose a TCP listener or permit arbitrary web-to-shell execution.

## Implementation boundary

The initial implementation is a local, dry-run-capable MVP. It may create source files, schemas, workflows, tests, and setup documentation. It must not create or modify live GitHub repositories, Secrets, Apps, branch protection, or project instructions without a separate explicit approval.


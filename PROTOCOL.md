# Reverse Web Router protocol

## Canonical envelope

The canonical semantic protocol is `rwrouter/2`. Routing and provider selection are separate.

Routing surfaces are exactly:

- `CONTROL`
- `WEB_DIRECT`
- `GITHUB_CLOUD`
- `LOCAL_EDGE`
- `HYBRID_CLOUD_LOCAL`

The envelope schema is `.agent-orchestrator/schema/rwrouter2.schema.json`. Repository work units use `agent-task/v1`; parent runs use `agent-run/v1`. Provider model names, credentials, endpoint settings, and pricing never appear in these core contracts.

## Durable GitHub records

One parent Issue represents a run. One child Issue represents one bounded work unit. Every work unit carries a unique task ID, dependency IDs, provider-neutral worker selection, narrow allowed and forbidden paths, definition of done, acceptance commands, budget, and canonical state.

The authoritative state is a structured record or one canonical status comment. Labels are visibility aids. Dispatch requires a valid contract, accepted dependencies, and an atomic claim. Paid invocation is marked before the network boundary. A repeated webhook resolves to the existing claim and must not create another provider run.

## Compatibility boundary

`rwrouter/1.1` remains only as the Native Messaging wire format for `LOCAL_EDGE`:

| rwrouter/1.1 | rwrouter/2 |
|---|---|
| `WEB` | `WEB_DIRECT` |
| `LOCAL` | `LOCAL_EDGE` |
| `HYBRID` | `HYBRID_CLOUD_LOCAL` |

`GITHUB_CLOUD` and `CONTROL` do not have local wire representations. Translation fails closed for unknown enums, credentials, or raw local paths.

## State and acceptance

Task states are `draft`, `ready`, `queued`, `claimed`, `running`, `pr-open`, `verifying`, `changes-requested`, `accepted`, `blocked`, `waiting-local`, `failed`, and `cancelled`.

GitHub Actions are the deterministic gate. Semantic verification returns `pass`, `changes_requested`, or `unknown`. `main` remains protected and human-controlled. No workflow in this MVP auto-merges `main`.

# Reverse Web Router — GitHub Cloud Control Plane Supplement

## Status

This document supplements, rather than replaces, `reverse-web-router-codex-bootstrap-v2.md`.

The local path remains useful for tasks that genuinely require the user's Windows machine, local applications, local-only data, or local verification.

The new primary operating mode is cloud-first:

```text
ChatGPT Project: 网页端调用本地
        |
        | top-level planning / routing / dispatch
        v
      GitHub
  persistent control plane
        |
        +----------------------+----------------------+----------------------+
        |                      |                      |
        v                      v                      v
  cloud worker A        cloud worker B        verification worker
  DeepSeek/API          future provider       tests/review/checks
        |                      |                      |
        +----------- branches / PRs / Issues / Checks -------------------+
                               |
                               v
                        protected repository
                               |
                       optional integration branch
                               |
                               v
                        human/local acceptance
```

The local edge remains:

```text
ChatGPT Web -> Browser Extension -> Native Bridge -> Local Codex
```

but is no longer the default for repository engineering.

---

# 1. Design goal

The user should normally interact only with the ChatGPT Project `网页端调用本地`.

The web model should:

1. understand the user's objective;
2. decide whether the task is web-only, GitHub-cloud, local-edge, or hybrid;
3. for project work, design the top-level plan and task decomposition;
4. publish bounded work contracts to GitHub;
5. inspect milestones, PRs, checks, and worker reports from GitHub;
6. issue follow-up tasks when appropriate;
7. keep local Codex optional for local-only execution and final fine-tuning.

The user should be able to leave the local computer off while GitHub-cloud tasks continue.

---

# 2. Routing surfaces

Replace the old WEB / LOCAL / HYBRID-only concept with:

- `WEB_DIRECT`
- `GITHUB_CLOUD`
- `LOCAL_EDGE`
- `HYBRID_CLOUD_LOCAL`
- `CONTROL`

## WEB_DIRECT

Use for ordinary analysis, discussion, writing, research, and tasks that require no repository execution.

## GITHUB_CLOUD

Default for repository-based engineering that can run using GitHub-hosted infrastructure and provider APIs.

Use for:

- bounded implementation tasks;
- multi-file repository work;
- CI-testable work;
- independent parallel tasks;
- task decomposition into multiple agents;
- review and verification workflows;
- long-running work that should continue while the local computer is off.

## LOCAL_EDGE

Use only when useful work materially depends on:

- local-only files;
- local-only data;
- installed desktop applications;
- proprietary/local execution environments;
- hardware;
- local credentials that must not move to cloud;
- local final acceptance/fine-tuning.

## HYBRID_CLOUD_LOCAL

Use when cloud agents can perform the repository portion but one or more acceptance stages require a local environment.

Cloud tasks should finish in PRs / artifacts and then enter a `waiting-local-acceptance` state.

---

# 3. GitHub is the canonical task ledger

Do not use GitHub merely as a file drop.

Use GitHub as the durable state machine.

## Canonical objects

### Project Run

One parent Issue represents the overall run.

Example title:

`[RUN] Implement <objective>`

The parent issue records:

- run ID;
- objective;
- architecture decision;
- task graph;
- budgets;
- global constraints;
- child issue links;
- final acceptance state.

### Work Unit

One child Issue represents one bounded agent task.

Each child task includes a machine-readable contract:

```yaml
schema: agent-task/v1
task_id: UUID
run_id: UUID
objective: "one bounded objective"
depends_on: []
preferred_worker: auto
allowed_paths:
  - src/**
  - tests/**
forbidden_paths:
  - .env*
  - secrets/**
definition_of_done:
  - "condition"
acceptance_commands:
  - "command"
budget:
  max_wall_minutes: 60
  max_cost_usd: 1.00
state: ready
```

The task contract must never contain API keys or unrelated sensitive material.

### Implementation result

Each coding worker works on its own branch and produces a Pull Request linked to its Issue.

### Machine verification

GitHub Actions and checks are the canonical deterministic acceptance result.

### Reasoning/review verification

A separate verifier agent may inspect the PR and publish a structured review.

### Human acceptance

The protected main branch remains the final human-controlled boundary unless the user explicitly enables an automated integration policy.

---

# 4. GitHub state model

Recommended task states:

- `draft`
- `ready`
- `queued`
- `claimed`
- `running`
- `pr-open`
- `verifying`
- `changes-requested`
- `accepted`
- `blocked`
- `waiting-local`
- `failed`
- `cancelled`

Use labels for visibility, but keep the authoritative state in a structured task record or one canonical status comment so label manipulation alone cannot corrupt the state machine.

Recommended visible labels:

- `agent:ready`
- `agent:deepseek`
- `agent:review`
- `state:running`
- `state:blocked`
- `state:accepted`
- `requires:local`
- `priority:p0|p1|p2`

---

# 5. Dispatch trigger

Prefer Issue-based dispatch because the ChatGPT GitHub connector can create/update Issues and labels directly.

Recommended trigger:

```yaml
on:
  issues:
    types: [opened, labeled]
```

A task becomes dispatchable when its canonical contract is valid and it receives `agent:ready`.

Alternative/API trigger:

- `workflow_dispatch`
- `repository_dispatch`

Keep these available for external orchestrators and future integrations.

Do not require the browser extension for GitHub-cloud task submission.

---

# 6. Off-machine worker execution

A local self-hosted runner is NOT sufficient for true off-machine operation because it disappears when the user's computer is off.

For true unattended execution, use one of:

1. GitHub-hosted runner;
2. always-on cloud VM/container registered as a runner;
3. provider-managed/cloud agent adapter.

Default V1 cloud worker: GitHub-hosted Actions.

---

# 7. DeepSeek cloud worker

The existing local `coding-project-runner` remains unchanged for local execution.

Create a separate cloud adapter for DeepSeek.

Do NOT attempt to reuse the local DPAPI-decrypted key from `F:\codingenv`.

Instead, for the cloud worker:

- store the DeepSeek API credential in GitHub Actions Secrets or an appropriate protected Environment;
- inject it only into the worker job;
- never copy it into Issue bodies, task manifests, PR bodies, logs, artifacts, or receipts;
- redact model request/response logs as needed.

The cloud worker should preserve the useful concepts from `coding-project-runner`:

- frozen objective;
- narrow allowed paths;
- forbidden paths;
- deterministic acceptance commands;
- time/token/cost budget;
- isolated branch/worktree equivalent;
- no duplicate paid fallback;
- structured milestones;
- acceptance gate.

Do not duplicate local DPAPI assumptions in the cloud implementation.

---

# 8. Multi-agent orchestration

The web ChatGPT model is the default top-level architect.

For a complex request it should:

1. create/update the parent Run Issue;
2. decompose the project into bounded child tasks;
3. identify dependencies;
4. mark independent tasks as parallelizable;
5. choose worker hints;
6. publish child Issues;
7. trigger eligible tasks.

Example dependency graph:

```text
T1 architecture/schema
   |
   +--------+
   |        |
   v        v
T2 API    T3 UI
   |        |
   +---+----+
       v
    T4 integration
       |
       v
    T5 verification
```

Only tasks whose dependencies are `accepted` become dispatchable.

Parallel tasks should use distinct branches and narrow, minimally overlapping `allowed_paths`.

If two tasks need the same files, serialize them or define an explicit integration task.

---

# 9. Worker claiming and idempotency

Every task has a UUID.

The dispatcher must ensure that one task cannot create duplicate paid worker runs.

Use at least:

- a unique `task_id`;
- GitHub Actions concurrency group keyed by task ID;
- a canonical claim record;
- a check before provider invocation;
- a recorded provider run ID.

Do not rely only on issue labels for idempotency.

A repeated webhook or duplicate label event must resolve to the existing run rather than start another paid model call.

---

# 10. Milestone verification

Split verification into two layers.

## Deterministic gate

Run:

- unit tests;
- integration tests;
- lint/type checks;
- changed-path boundary checks;
- generated-artifact checks;
- user-provided acceptance commands.

Publish results as GitHub checks / workflow results.

## Reasoning gate

For changes that need semantic review:

- use a separate verifier worker;
- give it the task contract, diff, test results, and relevant repository context;
- require a structured verdict:
  - pass
  - changes_requested
  - unknown
- do not allow the implementation worker to be the sole final reviewer of its own output for high-impact tasks.

The verifier should create review feedback rather than directly rewriting the implementation unless a separate repair task is created.

---

# 11. Branch strategy

Recommended:

- `main`: protected, human/local acceptance boundary;
- `agent/<task_id>/<worker>`: worker branch;
- optional `agent-integration/<run_id>`: cloud integration branch for fully checked intermediate work.

Default policy:

- agents may create branches, commits, PRs, comments, checks, and artifacts;
- agents do not force-push protected branches;
- agents do not merge into `main`;
- optional automated merging into `agent-integration/<run_id>` may be enabled only after deterministic and reasoning gates pass.

The user's local final acceptance can then pull/review the integration branch or approved PRs.

---

# 12. Web conversation workflow

Normal usage from `网页端调用本地`:

### User

"Implement feature X in repository Y. Split it into parallel tasks where useful."

### Web router

1. classify as `GITHUB_CLOUD`;
2. inspect GitHub repository context;
3. design architecture/task graph;
4. show concise plan if user-impactful choices exist;
5. create a parent Run Issue;
6. create child task Issues;
7. mark ready tasks for dispatch.

### While running

The user may ask:

- "项目现在到哪一步了？"
- "有哪些任务失败？"
- "为什么 T3 被阻塞？"
- "让模型先修复验收失败，不要合并。"
- "把下一阶段发出去。"

The web model reads GitHub state and updates Issues/labels/comments accordingly.

The user does not need local Codex to inspect routine status.

---

# 13. Repository-side orchestrator files

Create an installable orchestration package, preferably reusable across repositories:

```text
.github/
  workflows/
    agent-dispatch.yml
    agent-verify.yml
    agent-integrate.yml

.agent-orchestrator/
  schema/
    agent-task.schema.json
  config.yml
  prompts/
    implement.md
    verify.md
  scripts/
    parse_task.py
    claim_task.py
    run_worker.py
    boundary_check.py
    publish_status.py
    dependency_gate.py
```

For reuse across multiple projects, support a dedicated control repository plus per-project installation.

Recommended long-term layout:

```text
orchestrator-control-repo
  |
  +-- task/run metadata
  +-- reusable workflows
  +-- worker adapters
  |
  +------ target repo A
  +------ target repo B
  +------ target repo C
```

But V1 should start with one repository to reduce failure modes.

---

# 14. Worker adapter interface

Define a provider-neutral interface:

```yaml
worker:
  provider: deepseek
  model_class: balanced
  role: implementer
```

Adapters may later include:

- DeepSeek API;
- OpenAI API;
- Codex cloud adapter, if a stable externally triggerable interface is available;
- other model providers.

Core task protocol must not hard-code provider-specific fields.

Provider-specific model names, cost controls, and credentials belong in the adapter configuration.

---

# 15. Routing priorities

Use:

1. adequate completion probability;
2. lowest expected total cost;
3. stability and verifiability;
4. lowest operational complexity.

Suggested default:

- web reasoning/planning: ChatGPT web;
- large bounded repository implementation: DeepSeek cloud worker when suitable and quota is available;
- deterministic verification: GitHub Actions;
- semantic verification: separate reviewer agent when necessary;
- local-only work: local Codex edge;
- final project acceptance: user/local environment.

Do not move a task to cloud solely because it is large if it contains restricted local material or requires local-only tooling.

---

# 16. Security boundary

GitHub-cloud execution is allowed only for material approved for the repository/cloud boundary.

Keep restricted local material local.

Never put into GitHub task contracts:

- credentials;
- private keys;
- browser auth state;
- unrelated personal data;
- local absolute paths;
- unpublished or restricted material not approved for cloud storage;
- sensitive local configuration.

Use least-privilege GitHub permissions.

Protect `main` with required checks.

Use protected GitHub Environments for worker secrets where available and appropriate.

---

# 17. ChatGPT Project instruction update

Update `PROJECT_INSTRUCTIONS.md` so the semantic router prefers:

```text
WEB_DIRECT
  -> answer on web

GITHUB_CLOUD
  -> create/manage GitHub task graph

LOCAL_EDGE
  -> emit rwrouter local handoff

HYBRID_CLOUD_LOCAL
  -> execute cloud-safe stages in GitHub,
     then mark local-required stages waiting-local
```

For repository tasks, prefer GitHub-cloud over local Codex when:

- the repository is available through the approved GitHub connection;
- the task can be executed and verified in cloud infrastructure;
- no restricted local dependency prevents cloud execution.

Do not use local Bridge merely because it exists.

---

# 18. Protocol evolution

Move from `rwrouter/1.1` to `rwrouter/2`.

Suggested semantic envelope:

```json
{
  "protocol": "rwrouter/2",
  "task_id": "uuid",
  "surface": "GITHUB_CLOUD",
  "web_capability": "DEEP",
  "project": {
    "repository_alias": "project-a"
  },
  "orchestration": {
    "mode": "MULTI_AGENT",
    "planner": "WEB",
    "worker_policy": "AUTO",
    "merge_policy": "NO_MAIN_AUTO_MERGE"
  },
  "objective": "..."
}
```

The local wire format may remain compatible through a translation adapter.

Do not break V1.1 local Bridge unnecessarily.

---

# 19. Migration strategy

Do NOT discard V2.

Implement in this order:

## Phase A — current local path

Complete enough of V2 to preserve local-edge capability.

## Phase B — GitHub control plane MVP

Add:

- Project instruction update;
- parent/child Issue schema;
- GitHub task state machine;
- issue-triggered Actions dispatcher;
- DeepSeek cloud worker adapter;
- deterministic verifier;
- protected-branch policy;
- structured status publication.

## Phase C — multi-agent

Add:

- dependency graph;
- parallel dispatch;
- separate reviewer worker;
- integration branch;
- cost ledger;
- retry/escalation policy.

## Phase D — optional additional agents

Add provider adapters only after the provider has a stable supported execution path.

---

# 20. Acceptance criteria

The supplement is successful when:

1. the user can start a repository project by speaking normally in ChatGPT web;
2. the web model can publish bounded tasks to GitHub;
3. the user's computer may be off during cloud execution;
4. DeepSeek can execute a task from a GitHub-hosted runner without access to the local DPAPI secret;
5. one task cannot launch duplicate paid workers;
6. multiple independent tasks can run in parallel;
7. each task produces an Issue state, branch/PR, verification evidence, and final status;
8. failed verification creates a visible repair state rather than silently merging;
9. `main` remains protected by default;
10. the user can ask ChatGPT web for project status using GitHub state alone;
11. local Codex is required only for explicitly local stages or optional final fine-tuning;
12. no cloud workflow requires the local Windows computer to remain powered on.

---

# 21. Codex implementation instruction

Treat this document as a supplement to V2.

First inspect the existing V2 implementation state.

Do not rebuild working local components unnecessarily.

Implement the GitHub-cloud control plane as a separate module with a compatibility layer to the existing router.

Before changing any live repository settings, secrets, branch protection, or installing GitHub Apps, produce the exact required configuration and ask for the user's approval where the action has external or irreversible impact.

Do not create, rotate, print, or migrate API credentials automatically.

After implementation, report:

1. architecture/files added;
2. GitHub repository settings the user must enable;
3. required GitHub secrets by NAME only;
4. exact Project instructions update;
5. tests and dry-run results;
6. one safe cloud smoke-test procedure;
7. how the user checks status entirely from ChatGPT web;
8. what still requires local Codex.

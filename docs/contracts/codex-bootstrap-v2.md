# Reverse Web Router V2 — Codex Implementation Contract

## Purpose

Upgrade the previously proposed reverse router into a practical system for the ChatGPT Project named `网页端调用本地`.

The user will use that Project as the normal web entry point. They should not need to type routing commands. A normal natural-language request should be classified automatically and either:

1. stay on ChatGPT web;
2. be handed to local Codex;
3. use a hybrid web-planning/local-execution flow.

For local engineering work, Codex must also be able to choose between:

- direct Codex execution; and
- the user's existing `coding-project-runner` skill, which uses `F:\codingenv`, Pi, and DeepSeek V4 Flash in an isolated Git worktree.

Do NOT create a second DeepSeek launcher. Reuse the existing `coding-project-runner` as the authoritative DeepSeek execution mechanism.

The design priorities, in order, are:

1. reliable task completion;
2. lowest expected total resource/cost among sufficiently reliable choices;
3. stable and verifiable execution;
4. least privilege and fail-closed behavior.

---

# 1. Correct architecture

Implement:

```text
ChatGPT Project: 网页端调用本地
          |
          | semantic routing decision
          v
Chromium Extension
          |
          | Native Messaging
          v
Local Bridge
          |
          v
Codex Router / Executor
      /                 \
     /                   \
Codex Direct       coding-project-runner
                         |
                         v
                 Pi + DeepSeek V4 Flash
                 isolated Git worktree
```

Important separation of responsibilities:

- ChatGPT Project = semantic entry point and web/local/hybrid classifier.
- Extension = transport detector and status UI.
- Bridge = secure local transport and Codex launcher.
- Codex = local authority that can inspect real local state.
- `reverse-web-router-executor` = local routing/execution skill.
- existing `coding-project-runner` = DeepSeek project worker orchestration.
- DeepSeek is NOT called directly by the browser extension or bridge.

This separation is required because the web page cannot safely know:
- whether a repository is clean;
- exact allowed paths;
- local acceptance commands;
- local secrets or paths;
- whether a task is actually suitable for the detached worktree worker.

---

# 2. Protocol version

Use:

`rwrouter/1.1`

The key change from V1 is that execution location and local backend are separate concepts.

## Route dimensions

### `execution_surface`

Allowed values:

- `WEB`
- `LOCAL`
- `HYBRID`

### `web_capability`

Allowed values:

- `FAST`
- `BALANCED`
- `DEEP`

This is an abstract capability, not a hard-coded model name.

### `local_backend_preference`

Allowed values:

- `AUTO`
- `CODEX_DIRECT`
- `CODING_RUNNER`

This is a preference/hint only. Codex is the final local authority.

Default: `AUTO`.

### `local_capability`

Allowed values:

- `FAST`
- `BALANCED`
- `DEEP`

Used only for direct Codex execution.

Do not use this field to configure DeepSeek. The existing `coding-project-runner` remains authoritative for its own thinking/budget policy.

---

# 3. Web handoff packet

A local or hybrid handoff is emitted in exactly one fenced code block with language `rwrouter`.

Example:

```json
{
  "protocol": "rwrouter/1.1",
  "task_id": "uuid-v4",
  "execution_surface": "LOCAL",
  "web_capability": "FAST",
  "local_backend_preference": "AUTO",
  "local_capability": "BALANCED",
  "task_kind": "coding",
  "workspace_alias": "default",
  "execution_policy": "SAFE_WORKSPACE",
  "network_policy": "OFF",
  "objective": "Concrete task objective",
  "context": {
    "public_or_approved": "Minimal context safe and necessary for the local task"
  },
  "constraints": [
    "Do not modify files outside approved local scope"
  ],
  "acceptance_checks": [
    "Concrete, testable condition"
  ],
  "return_mode": "SUMMARY_AND_RECEIPT"
}
```

Allowed `task_kind` values initially:

- `coding`
- `file_ops`
- `analysis`
- `artifact`
- `research`
- `system`
- `other`

Unknown enum values must be rejected.

For ordinary web-only work, emit NO `rwrouter` packet.

---

# 4. What the user does on the web

The user intends to use the existing ChatGPT Project named:

`网页端调用本地`

The final installation must make this Project the default semantic entry point.

After bootstrap, the intended user workflow is only:

1. Open the ChatGPT Project `网页端调用本地`.
2. Start or continue a conversation.
3. Type the task normally in natural language.
4. Do not type `/route`, model names, Codex commands, DeepSeek commands, paths, or JSON.
5. If the task is web-suitable, ChatGPT answers normally.
6. If the task needs local execution, the Project emits a valid `rwrouter/1.1` handoff.
7. The extension detects it and starts local execution automatically.
8. The extension exposes status.
9. The local result/receipt is made available according to the implemented return path.

The only one-time web-side configuration should be:

### A. Project instructions

Create a production-ready file:

`web-project/PROJECT_INSTRUCTIONS.md`

The user will paste its content into the Project instructions/settings of `网页端调用本地`.

The Project instructions must explicitly say:

- this Project is the reverse-router entry point;
- classify every substantive task before executing it;
- simple control/acknowledgement messages stay in the current conversation;
- ordinary web-capable tasks remain on web;
- local-resource-dependent tasks produce a local handoff;
- tasks needing both web reasoning/research and local action use HYBRID;
- use the lowest sufficient reasoning capability;
- do not claim local execution occurred before a receipt exists;
- do not send local absolute paths, credentials, secrets, raw private files, browser auth state, or unrelated personal data;
- use `workspace_alias`, never a raw local path;
- for local backend preference, default to `AUTO`;
- use `CODING_RUNNER` only as a hint for clearly large, bounded, repository-based engineering tasks with deterministic acceptance potential;
- use `CODEX_DIRECT` only as a hint when the task is clearly unsuitable for the long-running coding runner;
- leave final backend choice to local Codex.

### B. Project reference files

Document that the user should keep the following router references available in the Project if convenient:

- the existing forward `web-thinking-router`;
- the existing `coding-project-runner`.

The Project must not assume these references contain local secrets.

### C. Extension binding

The extension popup must provide:

- `Bind current Project`
- visible bound Project name;
- bound Project identifier/URL fingerprint;
- `Unbind`;
- test button for dry-run local handoff.

The extension must reject valid-looking `rwrouter` packets outside the bound Project.

---

# 5. Web reasoning model routing

Do not hard-code current ChatGPT UI labels into the core protocol.

Use abstract:

- `FAST`
- `BALANCED`
- `DEEP`

The extension may later map these to visible web models/effort levels.

V1/V2 rule:

- `FAST`: current conversation can answer normally.
- `BALANCED` / `DEEP`: if verified model-switch automation exists and is enabled, the extension may re-run/continue under the configured stronger tier.
- otherwise, report that the stronger tier was requested but not verified; do not pretend the model changed.

Keep web model picker automation behind a feature flag because it is DOM/UI dependent.

---

# 6. Local backend arbitration

Implement local backend selection inside `reverse-web-router-executor`.

The web packet may provide a preference, but local Codex decides after inspecting the real task environment.

## Prefer `CODEX_DIRECT` when

Any of these materially apply:

- task is not repository-based;
- task requires local file/application/terminal interaction outside the coding runner's repository workflow;
- task is inspection, diagnosis, configuration, or a narrowly scoped modification;
- task requires interactive reasoning with local evidence;
- repository is dirty and the coding runner therefore cannot legally launch;
- deterministic acceptance commands cannot yet be defined;
- the task is planning/review/estimation only;
- the existing `coding-project-runner` explicitly says not to launch for that request type.

Use lowest sufficient direct Codex capability.

## Prefer `CODING_RUNNER` when

The task is:

- a real coding/engineering implementation;
- repository-based;
- sufficiently bounded to freeze one objective;
- large enough that an isolated worker is worthwhile;
- compatible with narrow `allowedPaths`;
- compatible with sensitive `forbiddenPaths`;
- compatible with concrete `definitionOfDone`;
- compatible with deterministic `acceptanceCommands`;
- suitable for isolated worktree implementation and later review.

Do not launch merely because DeepSeek quota exists.

The isolated worker overhead is not justified for every small edit.

## Mandatory runner preconditions

Before launching the existing runner:

1. resolve the repository;
2. run Git status as required by the existing skill;
3. if tracked or untracked changes exist, do not launch the worker;
4. define narrow allowed paths;
5. define forbidden sensitive paths;
6. define deterministic acceptance commands;
7. freeze the task contract;
8. launch only through the existing `F:\codingenv` control path.

Do not silently bypass any `coding-project-runner` rule.

---

# 7. Existing DeepSeek runner remains authoritative

The existing skill uses:

- `F:\codingenv`;
- Pi + DeepSeek V4 Flash;
- an isolated Git worktree;
- Codex as planner, monitor, and acceptance gate.

Preserve its current behavior.

In particular:

- publish/start creates a frozen contract;
- status/milestone checks do not relaunch;
- stop requires an explicit named task ID;
- planning/review/estimation does not launch work;
- dirty repositories block launch;
- `allowedPaths` must be narrow;
- sensitive paths remain forbidden;
- success requires completed state, boundary check success, and all acceptance commands exit 0;
- do not merge, cherry-pick, push, or delete the worktree without a separate explicit user request;
- never expose or read back the DeepSeek API key.

Current runner defaults should remain owned by that skill, including its current default high thinking and resource caps. Do not duplicate these defaults in the reverse router.

If task size or the user's explicit limits require adjustment, let `coding-project-runner` form the correct contract.

---

# 8. Cost-aware routing policy

Optimize expected total cost, not merely cheapest first call.

Conceptually:

```text
expected_total_cost
  = execution_cost
  + retry_probability * retry_cost
  + escalation_probability * escalation_cost
  + human_intervention_cost
```

Apply:

1. first choose routes that have an adequate completion probability;
2. among them, prefer lower expected resource/cost;
3. under similar expected cost, prefer the more stable and more verifiable route;
4. do not repeatedly retry a clearly insufficient low tier;
5. do not silently launch a second paid worker after a failed/stalled paid run.

DeepSeek quota is a valid cost advantage for suitable large coding tasks, but it does not override runner preconditions or task fit.

---

# 9. Bridge changes

The bridge should continue to use Native Messaging, not a TCP listener.

Responsibilities:

- validate `rwrouter/1.1`;
- map `workspace_alias` using LOCAL-ONLY configuration;
- create task-local state;
- invoke Codex as the local authority;
- pass the entire normalized handoff to the executor skill;
- return normalized state;
- never directly call DeepSeek;
- never store API credentials in the web packet or receipt.

Add states:

- `accepted`
- `routing_local`
- `running_codex`
- `running_coding_runner`
- `succeeded`
- `failed`
- `needs_user`

---

# 10. Executor skill

Create/update:

`codex-skill/reverse-web-router-executor/SKILL.md`

The skill must:

1. parse the normalized task;
2. inspect only enough local state to choose the backend safely;
3. classify backend as `CODEX_DIRECT`, `CODING_RUNNER`, or `NEEDS_USER`;
4. record the reason;
5. execute or delegate;
6. verify acceptance criteria;
7. produce a receipt.

If selecting `CODING_RUNNER`, invoke/reuse the installed `coding-project-runner` skill/process rather than reimplementing it.

If a runner launch is blocked after attempted preflight, return `needs_user` before changing to another paid execution backend unless the original `AUTO` policy and current local evidence already support a no-cost/non-duplicative direct action that does not conflict with the runner's rules. Default to asking rather than risking duplicate paid work.

---

# 11. Receipt schema update

Use:

```json
{
  "protocol": "rwrouter/1.1",
  "task_id": "uuid-v4",
  "state": "succeeded",
  "execution_surface": "LOCAL",
  "web_capability": "FAST",
  "local_backend_preference": "AUTO",
  "local_backend_selected": "CODING_RUNNER",
  "local_backend_reason": "Bounded repository implementation with deterministic tests",
  "workspace_alias": "default",
  "direct_codex": null,
  "coding_runner": {
    "task_id": "runner-task-id",
    "state": "completed",
    "boundary_ok": true,
    "acceptance_ok": true,
    "reported_cost": null,
    "reported_tokens": null
  },
  "acceptance": [
    {
      "check": "Concrete condition",
      "status": "pass",
      "evidence": "Short evidence"
    }
  ],
  "summary": "Concise final result",
  "errors": []
}
```

Do not expose absolute local paths in any receipt content that may return to the web.

Local-only receipts may contain paths when operationally necessary, but web-returnable summaries must sanitize them.

---

# 12. Security constraints

Preserve all prior restrictions:

- no arbitrary web-supplied absolute paths;
- no browser cookie/auth/token scraping;
- no direct web-to-shell execution;
- no direct web-to-DeepSeek execution;
- no `danger-full-access`;
- no `--yolo`;
- no silent network enablement;
- no silent privilege expansion;
- no silent paid fallback;
- no credentials in receipts;
- no copying restricted local material to the web unless explicitly approved.

---

# 13. Tests to add

Retain previous protocol/bridge/extension tests and add:

1. `AUTO` selects Codex Direct for non-repository local file task;
2. `AUTO` can select Coding Runner for a bounded clean repository coding task;
3. dirty Git repository blocks Coding Runner;
4. planning-only task never launches Coding Runner;
5. Coding Runner preference cannot bypass dirty repo rule;
6. Codex Direct preference does not silently become a paid runner;
7. DeepSeek API key never appears in packet, logs intended for web, or receipt;
8. duplicate web `task_id` cannot create duplicate Coding Runner tasks;
9. runner task ID is preserved for status/stop operations;
10. successful runner delivery is not merged/cherry-picked automatically;
11. failed/stalled runner does not trigger a second paid run automatically;
12. local backend decision reason is recorded.

---

# 14. One-time installation and web setup

After implementing the code, provide the user with an exact one-time checklist.

It should be approximately:

1. Install/register the Native Messaging host.
2. Load the Chromium extension in Edge/Chrome.
3. Open ChatGPT Project `网页端调用本地`.
4. Paste the generated `PROJECT_INSTRUCTIONS.md` into that Project's instructions.
5. Bind that Project from the extension popup.
6. Configure local workspace aliases.
7. Run a dry-run handoff test.
8. Run one harmless Codex Direct smoke test.
9. Run one harmless eligible Coding Runner/DeepSeek smoke test in a disposable clean Git repository.

The user should not need to manually configure routing on each conversation after this.

---

# 15. Deliverables

Update/create:

```text
reverse-web-router/
  README.md
  PROTOCOL.md
  web-project/
    PROJECT_INSTRUCTIONS.md
    USER_WEB_SETUP.md
  extension/
    ...
  bridge/
    ...
  codex-skill/
    reverse-web-router-executor/
      SKILL.md
      ...
  tests/
    ...
```

`USER_WEB_SETUP.md` is required and must be written for the user, not for a developer.

It must answer, explicitly:

- What do I change in the ChatGPT Project `网页端调用本地`?
- What files/references should remain in the Project?
- How do I bind the Project?
- What do I type for normal use?
- How do I know a local task was routed?
- How do I know whether Codex or DeepSeek was selected?
- What still requires my approval?
- How do I disable/uninstall the system?

---

# 16. Acceptance criteria

The upgrade is accepted only if:

- ordinary natural-language messages in `网页端调用本地` are the normal entry point;
- the user does not need to manually choose Codex or DeepSeek;
- web-only tasks do not trigger local execution;
- local tasks reach Codex through Native Messaging without a network listener;
- Codex is the final local backend authority;
- eligible large repository engineering tasks can be delegated through the existing `coding-project-runner`;
- DeepSeek is never called directly from the browser/bridge;
- dirty repository protection remains intact;
- paid-run duplication is prevented;
- local backend selection is observable in the receipt/status UI;
- Project setup is documented precisely;
- all tests pass;
- dry-run, direct Codex smoke test, and disposable-repo Coding Runner smoke test are documented.

After implementation, report:

1. files created/changed;
2. tests and smoke-test results;
3. exact manual steps the user must perform in the ChatGPT Project;
4. exact manual local installation/approval steps;
5. known limitations;
6. whether web model switching remains disabled or experimental.

---
name: reverse-web-router-executor
description: "Execute validated LOCAL_EDGE handoffs from the Reverse Web Router. Use when Codex receives a normalized rwrouter/2 task from the Native Messaging bridge, must inspect minimal local state, select CODEX_DIRECT, CODING_RUNNER, or NEEDS_USER, enforce workspace aliases and sensitive-path boundaries, run acceptance checks, and return a sanitized receipt. Reuse the installed coding-project-runner for eligible large clean-repository work; never reimplement or bypass it."
---

# Reverse Web Router Executor

Accept only normalized `rwrouter/2` envelopes produced by the bound LOCAL_EDGE bridge. Reject unknown protocols, routing surfaces, workspace aliases, absolute web-supplied paths, credentials, missing acceptance criteria, or an invalid `reasoning_plan`.

## Select the local backend

Inspect only enough local state to decide safely.

- Use `CODEX_DIRECT` for local files or applications, diagnosis, configuration, small changes, planning, dirty repositories, or work without deterministic acceptance.
- Use `CODING_RUNNER` only for a bounded coding implementation in a clean Git repository with narrow allowed paths, forbidden sensitive paths, and concrete acceptance commands.
- Use `NEEDS_USER` when the requested preference conflicts with local evidence or requires new authority.

Treat the web execution tier and delegated stage as hints. Codex is the final local authority. A Pro planner/reviewer artifact may narrow an eligible coding run, but it never authorizes paths, mutations, credentials, or acceptance by itself. When selecting `CODING_RUNNER`, invoke the installed `coding-project-runner` skill and preserve all of its preflight, worktree, budget, stop, and delivery rules. Never call DeepSeek from this skill or the Bridge.

## Execute and verify

Freeze the local objective and boundaries before mutation. Enforce `max_external_reasoning_calls`; default to one or zero and require a new paid authorization for any retry. Do not enable network, elevate privileges, install the extension, register the Native Messaging host, merge, push, or expose secrets without explicit approval. Verify every acceptance criterion and record `pass`, `fail`, or `unknown`.

Return a sanitized receipt containing task ID, state, selected backend and reason, acceptance results, concise summary, and errors. Remove absolute local paths and credentials from any receipt that may return to the web.

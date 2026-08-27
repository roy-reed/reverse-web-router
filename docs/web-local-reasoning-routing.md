# Bidirectional ChatGPT web and local Codex routing policy

This policy keeps the canonical execution surfaces while adding one cost-aware OpenAI reasoning decision. It prevents duplicate planning and creates a packet only for a real cross-surface handoff.

## Invariants

1. Select exactly one execution surface: `CONTROL`, `WEB_DIRECT`, `GITHUB_CLOUD`, `LOCAL_EDGE`, or `HYBRID_CLOUD_LOCAL`.
2. A substantive web-originated request is answered or planned first by a visibly selected ChatGPT GPT-5.6 Sol High. `CONTROL` is the zero-handoff exception.
3. A local-originated request stays local unless one Sol High web pass can be lossless, safe, independently checkable, and expected to save more Work than packaging, waiting, reintegration, and verification cost.
4. The receiver audits one frozen contract and repairs only demonstrated gaps. It does not independently repeat the full planning pass.
5. Logical model roles must be resolved against the receiving surface's live capabilities, and the effective model and effort must be recorded.

## Retrieval and research ladder

Choose the smallest sufficient layer; do not run several discovery paths by default.

1. Use direct reasoning, normal web retrieval, and primary or official sources for ordinary current-fact questions.
2. Use the `arxiv` skill for focused paper discovery by title, author, identifier, category, or bounded keywords.
3. Use the global `anysearch` skill only when vertical-domain search, multi-query batching, URL extraction, or materially broader discovery is needed. AnySearch is a discovery layer; verify consequential claims against the retrieved primary source. Anonymous access is an available fallback when `ANYSEARCH_API_KEY` is absent, and credentials must never enter prompts, packets, repositories, or logs.
4. Use the global `research-harness` skill only for long, multi-stage, resumable research deliverables that need evidence records, checkpoints, or completion checks. A one-off question or literature lookup must not pay this setup cost.

Stop escalating as soon as the evidence is sufficient. Do not transmit private queries, manuscripts, unpublished parameters, or other restricted research content to an external search service without explicit approval.

## Local target matrix

Score cross-source synthesis, reasoning depth, ambiguity, verification burden, and context volume from 0 to 2 each.

| Total | Logical local role | Effort |
|---:|---|---|
| 0 | `gpt-5.6-luna` | `none` |
| 1–2 | `gpt-5.6-luna` | `low` |
| 3–4 | `gpt-5.6-luna` | `medium` |
| 5 | `gpt-5.6-luna` | `high` |
| 6 | `gpt-5.6-terra` | `high` |
| 7 | `gpt-5.6-terra` | `xhigh` |
| 8–10 | `gpt-5.6-sol` | `max` |

Use the cheapest verified capable fallback when Luna or Terra is unavailable, and report it. Score the hardest unit after decomposition; project size alone never selects Sol Max.

## Web-originated route

`WEB_DIRECT` stays in Sol High and creates no packet. When execution is required, Sol High freezes the objective, minimum evidence, facts, assumptions, unknowns, path boundaries, implementation constraints, acceptance checks, budgets, and stop conditions. GitHub or local Codex then validates sensitivity, capability, scope, dependencies, and acceptance commands before assigning the matrix target.

## Local-originated route

The default is `local-direct` with zero web calls. A web pass is permitted only for a web-only capability or material net Work saving, lossless minimum-context transfer, approved transmission, independently checkable output, and a likely one-round answer. Passing the gate creates one reviewed packet and one Sol High call; the result re-enters the same receiver audit and local target matrix.

## Optional provider delegation

DeepSeek is a separate, default-off axis. `AUTO` resolves to `NONE`; an external call requires an explicit `planner`, `reviewer`, or `planner-and-reviewer` request. Use one bounded `planner` or `reviewer` only for value distinct from Sol High. `planner-and-reviewer` requires high risk, explicit dual-call approval, and a two-call budget. Combining a ChatGPT web pass with DeepSeek needs a separate need and explicit cost authorization. The Browser extension and Native Messaging bridge never call a provider directly.

The concrete DeepSeek model name belongs only in the worker adapter. `deep` maps to V4 Pro; `fast` and `balanced` map to V4 Flash. Live provider execution remains disabled unless the explicit live gate, credentials, claim, ledger record, and `paid_invoked` marker are all present.

## Authority and privacy

Web owns the direct answer or frozen plan. GitHub Checks are authoritative for deterministic repository checks. Local Codex owns local mutation safety and local acceptance. The user remains authoritative for consequential decisions marked in the contract. No provider output can widen paths, change acceptance checks, authorize paid retries, or approve its own work.

Never transmit secrets, browser state, personal data, unpublished parameters, private repository contents, or unapproved non-public payloads. Approval to inspect local files is not approval to upload them.

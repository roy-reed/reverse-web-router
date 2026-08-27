# Research retrieval tooling

The router uses a progressive capability ladder so ordinary tasks incur no extra packet, model call, or research-workspace overhead.

| Layer | Use when | Global capability |
|---|---|---|
| Direct and primary sources | Ordinary questions and current facts | Built-in web retrieval |
| Focused paper discovery | Title, author, identifier, category, or bounded keyword lookup | `arxiv` |
| Broader or structured discovery | Vertical-domain search, multi-query batches, or URL extraction | `anysearch` |
| Recoverable research workflow | Long, multi-stage delivery with evidence, checkpoints, and completion checks | `research-harness` |

AnySearch's website is the hosted search service; `anysearch-ai/anysearch-skill` is its Codex-facing client. They are one integration, not two independent search passes. Search results are discovery leads and consequential claims still require primary-source verification.

## Validated Windows installation

- AnySearch Skill: upstream tag `v3.1.0`, installed at `%USERPROFILE%\.codex\skills\anysearch`.
- Research Harness: upstream commit `ba974658d523a018da77bdeffd9211b6453f0128`, checked out at `%USERPROFILE%\.codex\tools\research-harness`.
- Research Harness wrapper: `%USERPROFILE%\.codex\skills\research-harness\scripts\invoke_research_harness.ps1`.
- Research Harness executes in `Ubuntu-22.04` through checksum-verified `uv 0.12.6`, with its Linux environment outside the source checkout. This preserves the upstream tree and supplies the POSIX `fcntl` locking required by the Harness.

The API credential is optional. Store `ANYSEARCH_API_KEY` as a user environment variable; never place it in a repository, prompt, task packet, or log. Anonymous access or normal web retrieval is the non-blocking fallback.

## Update contract

Updates are deliberate rather than automatic during a task:

1. Fetch the upstream tag or commit and inspect its diff, dependencies, network endpoints, and subprocess behavior.
2. Record the accepted tag or commit here.
3. Re-sync locked dependencies without modifying the upstream lockfile.
4. Run offline CLI validation, one public AnySearch query, Research Harness goal creation/status, and the repository test suite.
5. Commit and push the policy and pin update only after all existing routes still pass.

Optional workflows remain optional: `arxiv-survey-latex` needs a TeX toolchain, and PDF ingestion for `source-tutorial` needs `pdftotext`. Do not install those large dependencies until a requested workflow needs them.

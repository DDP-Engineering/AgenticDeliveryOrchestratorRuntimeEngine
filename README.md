<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE - Agentic Delivery Orchestrator & Runtime Engine

Current release: **ADORE 0.5.0**. Its release identity is aligned with
AEGIS 0.5.0.

ADORE 0.5 is the hard break to the current agent-driven AEGIS 0.5.x companion
CLI and JSON schema 1. It has no AEGIS 3.x compatibility or state migration
layer.

ADORE selects opt-in GitHub, GitLab or Gitea tickets, creates an isolated task
branch/worktree/container, and supervises a fresh executor session for each
AEGIS journal stage. It preserves forge adapters, executor launchers, budgets,
clarification, review monitoring and draft MR/PR publication. It never merges.

```text
ticket
  -> schema-4 ADORE run
  -> branch + worktree + container
  -> active AEGIS TASK journal
  -> local checkpoint after each stage
  -> target integration + independent strict check
  -> candidate presentation + fresh human approval label
  -> push + draft MR/PR + AEGIS close-out
  -> human review/merge
```

Full tasks use `frame -> specify -> design -> build -> validate -> deliver ->
done`; quick tasks use `frame -> build -> validate -> deliver -> done`. The
frame executor, not the ticket label, selects and justifies the path.

Failures are bounded and loud. The default third failed attempt in a stage
aborts with durable JSONL evidence and a visible incident/terminal comment.
Questions park without consuming the counter. Required comment writes use a
persisted outbox; notification failure stops code work until polling delivers
it.

Validated publication requires a fresh post-presentation `agent-approved`
label bound to the exact candidate fingerprint and target commit. Target drift,
candidate mutation or a revision forces validation and fresh approval again.

## Repository Layout

- `00_Planning/` - planning and design history;
- `01_Documentation/` - operator/user guidance;
- `02_Tools/` - setup, packaging and release tools;
- `04_Software/` - runnable Python package, tests, deploy and container assets;
- `05_SoftwareDocu/` - implementation/component contracts;
- `07_Delivery/` - generated release artifacts.

Start with [Getting Started](01_Documentation/Getting_Started.md), then read the
[runtime integration contract](01_Documentation/Integrating_A_Runtime_Project.md)
and [operations guide](01_Documentation/Operations_Guide.md).

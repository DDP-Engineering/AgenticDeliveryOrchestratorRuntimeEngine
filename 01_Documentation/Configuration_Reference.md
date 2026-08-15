<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration Reference

This reference describes the ADORE 0.5 hard-break configuration. The canonical
annotated example is [config.example.toml](../04_Software/config.example.toml).
Unknown sections and keys fail validation. Secrets do not belong in TOML.

## Agent, Platform and State

| Key | Meaning | Default |
| --- | --- | --- |
| `agent.name` | Visible comment identity. | `ADORE` |
| `agent.slug` | Branch/container/state marker prefix. | derived |
| `agent.email` | Author for ADORE-owned local checkpoint commits. | derived |
| `platform.kind` | `github`, `gitlab`, or `gitea`. | `gitlab` |
| `platform.repo` | Forge repository identity. | required |
| `platform.login` | Named `tea` login; Gitea only. | empty |
| `state.channel` | `comments`, `labels`, or `both`. | `comments` |
| `state.store_root` | Local schema-4 state root. | `.<slug>` |

ADORE 0.5 state schema is `4`. Old ADORE 3.x state is rejected with an
actionable hard-break message and is never reinterpreted or migrated.

## Polling and Readiness

| Key | Meaning | Default |
| --- | --- | --- |
| `polling.mode` | `once` or `loop`. | `loop` |
| `poll_interval_seconds` | Base loop interval. | `60` |
| `poll_jitter_seconds` | Added random jitter. | `5` |
| `poll_backoff` | Back off after forge errors. | `true` |
| `max_concurrent_runs` | Capacity ceiling for persisted `working` runs; it does not enable parallel conduction. | `1` |
| `quiet_hours` | `HH:MM-HH:MM` windows. | `[]` |
| `readiness.require_acceptance_criteria` | Require heading or task list. | `true` |
| `readiness.require_priority_label` | Require a configured priority. | `true` |

`require_known_component` and `max_scope_hint` remain reserved configuration
intent and are not pickup filters.

Conduction is synchronous and serial: one `poll_once` call works at most one
run at a time. Values above `1` do not create parallel gates or workers.

## Labels

Lifecycle defaults are `agent-ready`, `agent-working`, `agent-clarify`,
`agent-answered`, `agent-mr`, `agent-failed`, and `agent-done`. Selection
defaults include priorities `P1/P2/P3` and type labels. Control defaults are
`agent-hold` and `no-agent`. The review trigger defaults to `agent-revise`.

The delivery approval label is configured separately and must not collide with
lifecycle or control labels.

## Executor and Container

`executor.default` selects a command table. Every command is non-interactive
and must contain `{prompt}`. `executor.env_keys` is the allowlist of
model-provider environment variables copied into a container. Forge credential
names such as `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GLAB_TOKEN`,
`GITEA_TOKEN`, and `TEA_TOKEN` are rejected.

`container.runtime` is Docker/Podman or a WSL-wrapped equivalent.
`container.image`, cache volumes, `run_args`, `runtime_env`,
`required_tool_checks`, and the egress mode configure isolation. Unit tests
remain offline. ADORE never places forge credentials in the executor
environment.

For CLI engine commands, `.env` beside the resolved `config.toml` is loaded
first; if absent, cwd `.env` is used. The real process environment has highest
precedence, and only names in `executor.env_keys` reach the executor container.

## Workflow

```toml
[workflow]
default_kind = "feature"
kind_labels = { bug = "fix", fix = "fix", change = "change" }
quick_label = "agent-quick"
aegis_python = "python"
stage_timeout_overrides = { build = 5400, validate = 3600 }
```

- `default_kind` and mapping values accept `feature`, `fix`, or `change`.
- Bug/fix labels win over change, configured feature labels follow, and
  `default_kind` is used only when no configured label matches.
- `quick_label` is only a framing hint. ADORE does not select the path.
- `aegis_python` is the one-token executable used with `.agentic/aegis.py`.
- timeout override keys are `frame`, `specify`, `design`, `build`, `validate`,
  or `deliver`.

ADORE supports AEGIS `0.5.x` and JSON schema `1` only.

## Recovery

```toml
[recovery]
max_stage_failures = 3
max_transient_retries = 3
retry_backoff_seconds = [5, 30, 120]
```

`max_stage_failures` is the number of total failed attempts for the current
stage. With the default, attempts 1 and 2 may remediate; attempt 3 stops and
there is no fourth launch. A check invocation counts once even when it reports
many findings. The counter resets after a successful legal stage transition.

`max_transient_retries` independently bounds container, fetch, and forge
transport retries. Those attempts do not consume the stage counter.

## Clarification

| Key | Meaning | Default |
| --- | --- | --- |
| `max_rounds` | Human question/answer rounds. | `3` |
| `reminder_after` | Reserved reminder threshold. | `24h` |
| `answer_timeout` | Loud-failure timeout. | `72h` |
| `timeout_state` | Validated terminal choice. | `failed` |

Questions park the run, stop the container, release the slot, and do not count
as stage failures. Resume requires a human comment plus `agent-answered`.

## Budgets

| Key | Meaning | Default |
| --- | --- | --- |
| `max_iterations` | Total executor launches. | `20` |
| `max_wall_clock_seconds` | Active-work time; reset by explicit retry. | `3600` |
| `per_gate_timeout_seconds` | One executor attempt. | `1800` |
| `max_cost_usd` | Reported model spend. | `5.0` |
| `max_files_touched` | Product plus governance paths. | `120` |

Budget exhaustion fails immediately, preserves evidence, and requires
`adore retry` after operator remediation.

## Delivery and Review

```toml
[delivery]
target_branch = "main"
draft = true
reviewers = ["reviewer"]
remove_source_branch = true
approval_label = "agent-approved"

[review]
trigger = "label"
revise_label = "agent-revise"
max_review_rounds = 3
review_reminder_after = "48h"
```

`draft=false` is invalid. ADORE removes `approval_label` before presenting a
candidate and accepts only a fresh re-add after presentation. Approval is
bound to candidate fingerprint and target commit. Every revision creates a
new task and repeats validation and approval. Review reminder behavior remains
reserved; the hard round limit is enforced.

`awaiting-approval` and `in-review` are intentionally human-paced and have no
timers. They wait until reconciliation observes approval, revision, merge,
close, deletion, or source-ticket closure.

## Reconciliation and Metrics

The `[reconcile]` values remain reserved. Current schema-4 behavior is fixed:
deleted/closed resources fail visibly, stale `working` runs become loud
failures, pending notifications replay without consuming a slot, and terminal
runs retain state evidence.

`[metrics]` controls SQLite/JSONL/static HTML summaries. Metrics are
best-effort and can never change governance outcomes.

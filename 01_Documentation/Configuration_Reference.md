<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration Reference

This reference describes the ADORE configuration. The canonical
annotated example is [config.example.toml](../04_Software/config.example.toml).
Unknown top-level sections fail validation. Unknown keys within known sections
are currently ignored, so use only documented keys and run `adore config
validate` after an edit. Secrets do not belong in TOML.

## Agent, Platform and State

| Key | Meaning | Default |
| --- | --- | --- |
| `agent.name` | Visible comment identity. | `ADORE` |
| `agent.slug` | Branch/container/state marker prefix. | derived |
| `agent.email` | Author for ADORE-owned local checkpoint commits. | derived |
| `platform.kind` | `github`, `gitlab`, or `gitea`. | `gitlab` |
| `platform.repo` | Forge repository identity. | required |
| `platform.login` | Named `tea` login; Gitea only. | empty |
| `state.channel` | Reserved compatibility setting; status uses its comment and lifecycle labels regardless of this value. | `comments` |
| `state.store_root` | Local run-state root. | `.<slug>` |

ADORE's run-state schema is `1`, numbered alongside the AEGIS JSON schema it
is conducted with and independent of any ADORE release number. Any other
value is rejected with an actionable message and never reinterpreted or
migrated.

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
`required_tool_checks`, `selinux_relabel`, and the egress mode configure
isolation. Unit tests remain offline. ADORE never places forge credentials in
the executor environment.

`container.egress` mode `allowlist-proxy` requires Podman 4.0 or newer with the
netavark backend, because the executor resolves the proxy by DNS alias on an
internal network. Podman 3.x with CNI cannot serve that alias. Docker is
unconstrained, as are the `open` and `none` modes.

`container.selinux_relabel` is `off` or `shared` and defaults to `off`. Set it
to `shared` on a host with SELinux enforcing, which is the default on Fedora,
RHEL, CentOS Stream, Rocky, and Alma. It appends `z` to ADORE's host bind
mounts, namely the clone, the worktree, the run io directory, and the generated
egress-proxy config, so the container may read them; without it every stage
fails on permission denied. Named cache volumes are not relabeled because the
runtime already labels them. The private `Z` label is rejected: it labels
content per container, and the clone is shared by every run and by host git, so
`Z` would bind the clone to one container and break the next run.

`executor.mode` is validated but reserved: the current conductor always uses
thick executor sessions. Parked containers are stopped and retained for resume
or explicit cleanup. The accepted `container.keep_parked`,
`parked_ttl_mode`, `parked_ttl_seconds`, and `parked_ttl_polls` settings are
reserved and do not currently change that behavior.

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

ADORE conducts AEGIS major 0 from 0.5.0 upward over JSON schema `1`; a
different major, a payload below the floor, or any other contract is refused
at probe.

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
| `reminder_after` | Reserved; its format and ordering are validated, but no reminder is sent. | `24h` |
| `answer_timeout` | Loud-failure timeout. | `72h` |
| `timeout_state` | Reserved; its choice is validated, but expiry currently fails the run. | `failed` |

Questions park the run, stop the container, release the slot, and do not count
as stage failures. Resume requires a human comment plus `agent-answered`.

## Budgets

| Key | Meaning | Default |
| --- | --- | --- |
| `max_iterations` | Total executor launches. | `20` |
| `max_wall_clock_seconds` | Active-work time; re-armed by retry, clarification resume, revision, or approval invalidation. | `3600` |
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

`review.on_pipeline_failure` is `revise` (default), `notify`, or `ignore`, and
decides what a newly `failed` forge pipeline on the published draft does.
`revise` starts a governed repair round on the same bounded path the revise
label uses, so the repair still ends at strict validation and a fresh human
approval before any push; `notify` posts one comment and waits; `ignore` skips
the pipeline read. All three obey `max_review_rounds`, which bounds repairs and
human-requested revisions together. Only a changed verdict is a signal, and an
unreadable verdict is silent.

`draft=false` is invalid. ADORE removes `approval_label` before presenting a
candidate and accepts only a fresh re-add after presentation. Approval is
bound to candidate fingerprint and target commit. Every revision creates a
new task and repeats validation and approval. Review reminder behavior remains
reserved; the hard round limit is enforced.

`awaiting-approval` and `in-review` are intentionally human-paced and have no
timers. They wait until reconciliation observes approval, revision, merge,
close, deletion, or source-ticket closure.

## Reconciliation and Metrics

The `[reconcile]` values remain reserved. Current schema-1 behavior is fixed:
deleted/closed resources fail visibly, stale `working` runs become loud
failures, pending notifications replay without consuming a slot, and terminal
runs retain state evidence.

`[metrics]` controls SQLite/JSONL/static HTML summaries. Metrics are
best-effort and can never change governance outcomes. `capture_resource` is
reserved; ADORE currently performs no resource-usage probing.

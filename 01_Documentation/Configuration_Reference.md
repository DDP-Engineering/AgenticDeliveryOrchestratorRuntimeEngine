<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuration Reference

`target_branch` is shown as **Target branch** (Romanian: **Ramura de integrare**). New jobs start from `origin/<target_branch>` and their PR/MR targets that branch. Enter an existing remote branch’s short name, such as `main`, `master` or `develop`, without `origin/`. A human performs the merge; changing this setting does not retarget existing PRs/MRs.

This reference describes the ADORE configuration. The canonical
annotated example is [config.example.toml](../04_Software/config.example.toml).
Unknown top-level sections fail validation. Every section and subtable,
including `labels.*`, `executor` and `container.egress`, refuses a key
this build does not read with `[section] unknown key 'x': remove it from
config.toml`. A missing key takes its documented default. Run `adore config
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
| `state.store_root` | Durable local run-state root; visible read-only in web Settings. | `.<slug>` |

Every run-state change is mirrored on the ticket by one status comment, edited
in place, and the lifecycle labels; there is no setting for it.

ADORE's run-state schema is `1`, numbered alongside the AEGIS JSON schema it
is conducted with and independent of any ADORE release number. Any other
value is rejected with an actionable message and never reinterpreted or
migrated. A `state.json` with unknown or missing keys, or a stage outside
`frame`, `specify`, `design`, `build`, `validate`, `done` and `publishing`, is
refused the same way, and the message names the run directory to delete.

## Branch naming

Repository settings provides **Job branch name template** and **Optional branch name rule**. Administrators edit one field at a time, prepare the validated candidate, review active/proposed values, stop project pickup and apply while no jobs are active. Existing jobs retain their configuration. Developers see the same effective settings and example without edit actions. Worktree paths and runtime setup remain externally managed.

The template generates a name; the optional Python regular expression checks it. For example `feature/{slug}-{iid}` produces `feature/adore-1`, compatible with `^feature/.*$`. Empty rule means no extra naming rule. The repository convention is entered explicitly; ADORE does not fetch it automatically.

The server preview uses the effective agent slug, ticket number `1` and run identifier `sample-run-1`. It refreshes while editing and when reviewing a branch candidate, shows the generated name and rule result, and writes neither configuration nor Git branches. This is one example, not a guarantee for every future identifier. Missing/unsupported variables, invalid Git names or Python regex, mismatch and unavailable/slow checking block preparation; refresh after a stale revision. Allowed fields are `{slug}`, `{iid}` and `{run_id}` without format modifiers; include `{iid}` or `{run_id}`. Template and rule are bounded to 512 characters each; generated examples to 255 characters; regex matching to one second.

## Polling and Readiness

| Key | Meaning | Default |
| --- | --- | --- |
| `polling.mode` | Standalone CLI startup: `once` or `loop`, configured in TOML; explicit `--once`/`--loop` override it. Web schedules its own rounds; GUI controls show cadence settings. | `loop` |
| `poll_interval_seconds` | Base wait after each completed CLI loop/web round. | `60` |
| `poll_jitter_seconds` | Add 0..maximum random seconds after backoff, CLI loop/web. | `5` |
| `poll_backoff` | Double failed-round waits up to 8x, reset on success; CLI loop/web. | `true` |
| `max_concurrent_runs` | Capacity ceiling for persisted `working` and `handoff-pending` runs; clarification, approval and review waits release capacity. Conduction remains serial. | `1` |
| `quiet_hours` | Server-local `HH:MM-HH:MM` automatic polling pause windows, CLI loop/web. | `[]` |
| `readiness.require_acceptance_criteria` | Optional text gate: `acceptance criteria` or an unchecked `- [ ]` item. | `false` |
| `readiness.require_priority_label` | Require a configured priority. | `true` |

`max_scope_hint` remains reserved configuration intent and is not a pickup filter.

Conduction is synchronous and serial: one `poll_once` call works at most one
run at a time. Values above `1` do not create parallel gates or workers.

Acceptance checking defaults to false; priority checking stays true. Explicit values override these defaults. Maximum additional revision rounds defaults to five (minimum one), excluding initial implementation and sharing the budget between human requests and automatic pipeline repairs. After exhaustion, a new human request fails with REVIEW_LIMIT; a failed pipeline stops automatic repairs, posts a notice and leaves the job in review.

## Labels

Lifecycle defaults are `agent-ready`, `agent-working`, `agent-clarify`,
`agent-answered`, `agent-mr`, `agent-failed`, and `agent-done`. Selection
defaults include priorities `P1/P2/P3` and type labels. Control defaults are
`agent-hold` and `no-agent`. The review trigger defaults to `agent-revise`.

The delivery approval label is configured separately and must not collide with
lifecycle or control labels.

`labels.control.exclude` names the **Exclude from pickup label** (default `no-agent`). ADORE skips a ticket while that label is present, including tickets carrying the ready label. Removing it permits pickup if all other eligibility conditions hold. Adding it does not stop an already-started job. Apply the configured label on the ticket in its GitHub, GitLab or Gitea repository.

The GUI exposes `labels.lifecycle.ready` directly in Tickets as **Ready for pickup label**. `answered` is **Clarification answered label** and needs a new reply comment as well as the label. `answered`, `clarify`, `done`, `failed`, `review` and `working` are in the initially closed **Status labels** group; ADORE manages their ticket state presentation. `working` includes waiting for publication approval, `review` covers a published draft or ready PR/MR, and `done` follows a human merge. Manual status-label changes do not transition the saved job; retry is a separate action. Reserved `readiness.max_scope_hint` remains accepted technical configuration with no runtime effect and has no GUI control. There is no `[labels.executor]` table: a ticket cannot choose the coding agent, and the key is refused with `[labels] unknown key 'executor': remove it from config.toml`.

## Executor and Container

Pi is ADORE's only coding agent. The `[executor]` table holds:

| Key | Meaning | Default |
| --- | --- | --- |
| `executor.provider` | A Pi API-key provider id (for example `openai`, `anthropic`, `google`, `openrouter`, `mistral`; Settings → Agent and model lists them all), `chatgpt` (the server's ChatGPT Plus/Pro sign-in, made in the web interface; container execution only, stage time limits at most 3000 seconds) or `custom` (an OpenAI-compatible endpoint). | required |
| `executor.model` | Model ID within the provider, for example `gpt-5.4`; Pi's list or any ID the provider accepts. | required |
| `executor.endpoint.base_url` | Only with `custom`: the endpoint address as seen from the container. | required with `custom` |
| `executor.endpoint.api` | Only with `custom`: `openai-completions`, `openai-responses`, `anthropic-messages` or `google-generative-ai`. | `openai-completions` |
| `executor.internet` | **Internet access for the agent**: `false` limits a container run to the model provider's hosts; `true` opens its network and loads Pi's web tools. | `false` |
| `executor.web.search` | Web search while `internet = true`: `exa` (no key), `brave`, `tavily` or `none`. | `exa` |
| `executor.command` | Argv template of a native (installed on the server) Pi run. A container run ignores it and starts the image's pinned Pi in RPC mode. | `pi -p --mode json --model {model} {prompt}` |
| `executor.mode` | `thick` or `headless`; see below. | `thick` |
| `executor.questions_file` | Clarification questions file the agent writes in the worktree. | `<SLUG>_QUESTIONS.md` |
| `executor.env_keys` | Additional secret variables passed to Pi besides the provider's key variable. | `[]` |

```toml
[executor]
provider = "openai"
model = "gpt-5.5"
```

An OpenAI-compatible endpoint (LM Studio, Ollama, vLLM):

```toml
[executor]
provider = "custom"
model = "qwen/qwen3.5-9b"

[executor.endpoint]
base_url = "http://192.168.1.20:1234/v1"
api = "openai-completions"
```

The provider list and each provider's models come from the Pi version ADORE
pins (Pi 1.4.0), generated offline into `adore/pi_catalog.json` by
`02_Tools/generate_pi_catalog.py`; a model ID outside the list is accepted.
`provider` is refused when missing or unknown, `model` when missing or not one
ID (no spaces, quotes or control characters, at most 200 characters).
`[executor.endpoint]` is required for `custom` and refused for any other
provider; its `base_url` must be `http` or `https` with a host and no user
name, password, query or fragment, and `custom` needs a container run (a
local run has no ADORE-owned Pi agent directory). An inline key such as
`[executor] api_key` or `[executor.endpoint] key` is refused as an unknown key.

The provider's API key is a credential, never a value in `config.toml`: save it
in Settings → Agent and model or put it in the profile `.env` under the
variable Pi reads for the provider (`OPENAI_API_KEY` for `openai`,
`ANTHROPIC_API_KEY` for `anthropic`, `GEMINI_API_KEY` for `google`, and so on;
`ADORE_ENDPOINT_API_KEY`, optional, for `custom`). Pi receives it only as that
variable. For `custom` ADORE writes Pi's `models.json` into the ADORE-owned
agent directory before every stage: one provider `adore-endpoint` with the
base URL, API type and model, and `apiKey` set to `$ADORE_ENDPOINT_API_KEY`
when that key is set or to the placeholder `adore-no-key` when it is not.
`base_url` is the address as seen from the container: `localhost` is the
container itself, and `host.docker.internal` reaches the host only on Docker
Desktop; with Docker Engine on Linux or in WSL use the host's network address
(for a server on Windows reached from Docker in WSL, the WSL default gateway).
With internet access off the run reaches the endpoint through the per-run
proxy, which admits the `base_url` host (a name or an IP address).

`executor.internet` decides a container run's network. With `false` (the
default) every stage container and the **Test AI connection** container sit
behind a per-run Squid proxy that admits only the provider's hosts
plus `[container.egress] allowlist`. ADORE derives the provider's hosts: for an
API-key provider the hosts of Pi's own base URLs for it in
`adore/pi_catalog.json` (for example `api.openai.com` for `openai`,
`api.anthropic.com` for `anthropic`), for `chatgpt` the `openai` hosts, and for
`custom` the endpoint's host. Pi's web tools are not loaded and its system
prompt says that only the model provider is reachable and web search, page
reading and downloads are unavailable. With `true` the container network is
open; unless `executor.web.search` is `none`, Pi loads its web search and page
reading tools (pi-web-access) with the chosen search provider, and downloads
use bash (`curl`, `npm`, `pip`). `brave` and `tavily` need `BRAVE_API_KEY` or
`TAVILY_API_KEY`, saved like the provider key; Exa needs no key. A malicious web
page could try to make the agent send its API key or ChatGPT token out: with
internet on prefer limited, short-lived keys. A local (server-installed) run is
not restricted by this switch. Package installs (`pip install`, `npm install`)
in an internet-off run fail unless their hosts are in `[container.egress]
allowlist`.

`executor.command` must be non-interactive, contain `{prompt}` and not use
`--auto`. The supported placeholders are `{prompt}`, `{model}` and
`{worktree}`; any other, `{resume}` included, is refused. `executor.default`,
`executor.stage_host_auth` and every `[executor.<name>]` table (`opencode`,
`codex`, `qwen`, `pi`) are refused with `[executor] unknown key '<key>':
remove it from config.toml`.
`executor.env_keys` lists additional secret variables copied into a container; the provider's key variable is always added. Forge credential
names such as `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GLAB_TOKEN`,
`GITEA_TOKEN`, and `TEA_TOKEN` are rejected.

`container.runtime` is Docker/Podman or a WSL-wrapped equivalent. Standard WSL prefixes use direct argument execution internally; custom wrappers place `--` or `--exec` before the container command.
`container.image`, cache volumes, `run_args`, `runtime_env`,
`required_tool_checks`, `selinux_relabel`, `executor.internet` and
`[container.egress]` configure isolation. Unit tests remain offline. ADORE
never places forge credentials in the executor environment.

`[container.egress]` holds the per-run proxy of an internet-off run:

| Key | Meaning | Default |
| --- | --- | --- |
| `allowlist` | Extra hosts an internet-off run may reach besides the model provider: exact names or `*.` wildcards. Refused for a local project unless empty. | `[]` |
| `no_proxy` | Hosts proxy-aware tools reach without the proxy. | `["localhost", "127.0.0.1", "::1"]` |
| `proxy_image` | Squid image of the proxy, built from `docker/Dockerfile.egress-proxy`; never pulled. | `adore-egress-proxy:1.0.0` |
| `proxy_port` | Proxy port. | `3128` |
| `network_prefix` | Prefix of each run's internal network. | `adore-egress` |

There is no egress mode: `[container.egress] mode` is refused with
`[container.egress] unknown key 'mode': remove it from config.toml; [executor]
internet decides the agent's network access`. The proxy container receives the
`--add-host` options of `container.run_args`, so a host alias such as
`host.docker.internal:host-gateway` resolves in the proxy too.

An internet-off project requires Podman 4.0 or newer with the netavark backend,
because the executor resolves the proxy by DNS alias on an internal network.
Podman 3.x with CNI cannot serve that alias. Docker is unconstrained, as is a
project with internet on.

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
precedence, and only the provider's key variable, the web search key (internet on with `brave` or `tavily`) and the names in `executor.env_keys` reach the executor container.

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
- timeout override keys are `frame`, `specify`, `design`, `build`, or
  `validate`; any other key, `deliver` included, fails validation as not an AEGIS stage. Each positive override bounds one executor attempt, replacing the general stage-attempt limit. In the GUI, all five stages offer General or Custom seconds; General removes that stage’s entry.

ADORE conducts AEGIS major 0 from 0.15.0 upward over JSON schema `1`; a
different major, a payload below the floor, or any other contract is refused
at probe. From 0.15.0 validate closes the AEGIS task; there is no deliver stage.

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
transport retries. Those attempts do not consume the stage counter. The first attempt counts toward this limit. Backoff delays run in order before each retry and repeat the final value when exhausted; the same schedule paces forge notification replay. With three attempts, the first two delays are used.

## Clarification

| Key | Meaning | Default |
| --- | --- | --- |
| `max_rounds` | Human question/answer rounds. | `3` |
| `reminder_after` | Reserved; its duration format is validated, but no reminder is sent. | `24h` |
| `answer_timeout` | Positive duration per question; expiry fails the run, independently of reserved reminder timing. | `72h` |
| `timeout_state` | Reserved; its choice is validated, but expiry currently fails the run. | `failed` |

Questions park the run, stop the container, release the slot, and do not count
as stage failures. Resume requires a human comment plus `agent-answered`.

## Budgets

| Key | Meaning | Default |
| --- | --- | --- |
| `max_iterations` | Total executor launches across stages, including failed attempts, retries and revisions throughout the job lifetime. | `20` |
| `max_wall_clock_seconds` | Active-work time; re-armed by retry, clarification resume, revision, or approval invalidation. | `3600` |
| `per_gate_timeout_seconds` | One executor attempt and the strict AEGIS check; recovery may retry a timed-out stage attempt. Stage overrides affect executor attempts only. With `provider = "chatgpt"` this value and every stage override must be at most 3000, because a ChatGPT access token lasts about an hour. | `1800` |
| `max_cost_usd` | Recorded executor-reported model cost in US dollars over the job lifetime; `0` disables the cap. | `5.0` |
| `max_files_touched` | Distinct product and AEGIS paths changed from the job base, including committed, pending and new files. | `120` |

The GUI names `max_iterations` **Maximum executor launches per job** and
`max_wall_clock_seconds` **Active work time limit (seconds)**. The active clock
restarts on retry, clarification resume, revision or approval invalidation.
Time and cost are checked between attempts; an attempt may exceed either cap
before the next check. Its own timeout bounds that executor launch.

Cost accounting sums recorded usage across the job lifetime. Recording new
usage requires `metrics.capture_tokens = true` and executor token telemetry;
cost-only reports do not enter this sum. Values use reported USD without
currency conversion, subscription allocation or reconstruction of missing cost.
Previously recorded usage continues to count. The file-count check runs outside
an unfinished merge; an unavailable Git count skips that check and conduction
continues. A count exceeding the limit fails the job.

Detected budget exhaustion preserves evidence and requires `adore retry` after
operator remediation.

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
max_review_rounds = 5
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

`reviewers` lists the forge accounts to request a review from when a new
PR/MR is created; an empty list requests no review. Each account is 1–255
characters without whitespace, controls or a leading `-`. In GUI, **Request review from** accepts one account per line;
an administrator prepares the candidate, reviews the old/new lists and applies
it through the existing configuration flow. Review requests grant no publication
approval or merge permissions. GitHub/GitLab submit reviewers at creation;
Gitea requests them separately and retains the PR if the request is rejected.

`remove_source_branch` accepts only booleans and defaults to `true`. On GitHub,
GitLab and Gitea, ADORE removes its remote run branch on the next reconciliation
after a human merge. An exact commit lease protects branches changed since
publication; an already absent branch succeeds. GitLab also receives its native
delete-on-merge flag. With `false`, ADORE requests no remote deletion; the
repository's own auto-delete policy remains independent. Closed unmerged reviews
keep their remote branches. Cleanup uses bounded infrastructure retries; an
unverified deletion completes the human-merged job with a branch-retained warning
and preserves its local worktree for operator remediation.

`draft` accepts only booleans: `true` (default) creates a draft; `false` creates a PR/MR ready for review. Both require human publication approval and ADORE never merges. Existing PR/MRs retain their current state, including during revisions and crash recovery. ADORE removes `approval_label` before presenting a
candidate and accepts only a fresh re-add after presentation. Approval is
bound to candidate fingerprint and target commit. Every revision creates a
new task and repeats validation and approval. Review reminder behavior remains
reserved; the hard round limit is enforced.

`awaiting-approval` and `in-review` are intentionally human-paced and have no
timers. They wait until reconciliation observes approval, revision, merge,
close, deletion, or source-ticket closure.

## Reconciliation and Metrics

The `[reconcile]` values remain reserved. Current schema-1 behavior is fixed.
For a run waiting for approval, a clarification answer or review, a deleted
source ticket fails the run visibly (`TICKET_DELETED`; the container stops and
the worktree and evidence stay), and a closed source ticket cancels it with
outcome `ticket closed`, removing its container, worktree and local branch
while its state history stays. A run in review checks its MR/PR first: a
merged MR/PR completes the run and a closed-unmerged MR/PR fails it
(`MR_CLOSED`), whatever the ticket's state, and an MR/PR that stays missing
for `recovery.max_transient_retries` polls fails it (`MR_DELETED`). Stale
`working` runs become loud failures, pending notifications replay without
consuming a slot, and terminal runs retain state evidence.

`[metrics]` controls SQLite/JSONL/static HTML summaries. Metrics are
best-effort and can never change governance outcomes. `capture_resource` is
reserved; ADORE currently performs no resource-usage probing.

Statistics displays **Statistics database file** as an informational row with
four-locale guidance. Server `config.toml` owns `metrics.db_path`,
`metrics.export_jsonl` and `metrics.html_out`; web candidate preparation rejects
all three. JSONL and static HTML paths remain available through TOML/CLI and
are omitted from Project Settings controls. Project/global statistics, usage
and their CSV exports read summaries from the configured database with the
same relative-path semantics as CLI. Missing databases contribute no summaries
and remain absent; malformed configuration or database evidence returns the
existing typed 503 response. Metadata-only profiles retain their state-root
summary history until a configuration file exists. Analytical reads preserve
SQLite bytes, authorization, scope and financial redaction.

## Web executor configuration

**Project → Settings → Agent and model** shows **Test AI connection**, the provider (`executor.provider`), the model (`executor.model`), for an endpoint its base URL and API type (`executor.endpoint.*`), the launch command (`executor.command`), **Internet access for the agent** (`executor.internet`), **Web search** (`executor.web.search`), the additional credential variables (`executor.env_keys`), **Provider API key**, the execution environment and estimated prices. There is no agent choice: Pi is the only coding agent. Provider, model and endpoint are edited together and staged as one reviewed candidate (`executor.connection`); the model list comes from the pinned Pi and any typed ID is accepted. The launch command is an ordinary reviewed setting. Prepare reviews the change, then Apply writes one complete paused/idle candidate. For a container project the launch command offers only the Pi preset, because a container run starts the image's pinned Pi in RPC mode; a local project accepts any native argv that contains `{prompt}` and does not use `--auto`. **Provider API key** saves or removes only the configured provider's variable (none for a ChatGPT subscription) and, with internet on and Brave or Tavily search, `BRAVE_API_KEY` or `TAVILY_API_KEY`. Runtime preparation remains external. The old `/executor` URL redirects to Settings. Developers read non-secret settings/results without mutation actions.

The names-only credential selector offers known provider names and retained custom names. An empty list suits a local project that uses the account's existing Pi sign-in. Applying names does not delete saved `.env` values. Provider API keys offers private Save/Disconnect for known allowed variables and shows sources only; key changes require paused pickup and idle/pending-free state. A container project uses its provider API key, or for a ChatGPT subscription a short-lived access token from the server's ChatGPT sign-in; no host sign-in is copied into the container. A ChatGPT project's model evidence counts only while the server stays signed in. Explicit Test AI connection runs Pi and remains the evidence of model access; it may incur provider charges. New jobs use applied values; active jobs retain their durable configuration. Current model evidence is invalidated by configuration/credential drift.

## Container preparation

The optional closed `[execution]` table selects a reviewed `path.yml#job@full-commit` recipe. Defaults are container backend, no preparation, 300-second step limit, 900-second total attempt limit and two explicit attempts. [Container preparation](Container_Preparation.md) defines the authoritative grammar, image precedence, selection/review commands and recovery.

## Native local execution

execution.backend accepts container (default) or local. Closed local fields: account="current", home="", path="", environment={}, cgroup_root="". Local selection rejects recipes, a non-empty `[container.egress] allowlist`, staging/container-only options; `executor.internet` does not restrict a local run; policy pins machine/account/environment/executable. Unknown execution/local fields reject.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.

## Agent system packages

`container.system_packages` is a strict boolean, false by default, for direct agent installation with noninteractive sudo in a compatible container image. It is independent of `container.egress` and rejected for native execution. See [Agent dependency installation](Agent_Dependency_Installation.md) for image prerequisites, supported package managers, runtime argument restrictions and recovery.

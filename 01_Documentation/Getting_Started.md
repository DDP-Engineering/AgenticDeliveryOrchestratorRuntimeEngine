<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Getting Started

For the complete portable web application, extract the matching Windows ZIP
or Linux TAR.GZ from `07_Delivery/`. Start `Start-ADORE.cmd` (Windows) or
`./start-adore.sh` (Linux). The included Python starts the API and worker and
opens the browser when ready. No system Python, uv or Node.js setup is needed
for this package. Read its README for first sign-in, stop controls, data and
logs. Prepare Git/forge/executor/container tools when configuring projects.
The following sections describe source/CLI setup.

ADORE selects eligible GitHub, GitLab or Gitea tickets, runs AEGIS
inside dedicated worktrees with container or native local execution, and opens draft MR/PRs after fresh
human approval by default. It never merges.

## Prerequisites

- Python 3.11 or newer for ADORE;
- Git and a non-interactively pushable target clone;
- Docker or rootless Podman for container profiles; native scope controls for local profiles;
- authenticated `gh`, `glab`, or `tea` on the host;
- Pi, ADORE's only coding agent: built into the executor base image for container
  profiles, installed for the service account (`pi --version`) for local profiles;
- AEGIS installed in the target repository as `.agentic/aegis.py`;
- schema 1 from `status --all --json` and valid configured AEGIS tests.

ADORE reads only its own schema-1 run state and migrates nothing. Point it
at a fresh state root and profile.

## Install and Configure

From `04_Software`:

```text
python -m pip install -e .
adore init my-project
adore --profile my-project config validate
```

The wizard creates non-secret configuration. Put only model-provider values in
the ADORE process environment or `.env` beside the generated profile
`config.toml` (cwd `.env` is the fallback); forge authentication belongs to the
host CLI and is not exposed to executor containers. For corporate GitLab or
GitHub, ensure `glab`/`gh` has the intended instance selected as its
active/default authenticated host. ADORE adds no separate host route.

Minimum project-specific settings:

```toml
[platform]
kind = "github" # or gitlab / gitea
repo = "owner/repository"

[worktree]
repo_path = "D:/source/runtime-project"

[container]
runtime = "docker"
image = "my-project-adore:latest"

[executor]
provider = "openai"   # Pi API-key provider, "chatgpt" or "custom" (an endpoint)
model = "gpt-5.5"     # model ID within the provider
# The key goes in .env beside config.toml as OPENAI_API_KEY (never here),
# or in Settings -> Agent and model.

[workflow]
aegis_python = "python"

[recovery]
max_stage_failures = 3
max_transient_retries = 3
retry_backoff_seconds = [5, 30, 120]

[delivery]
target_branch = "main"
reviewers = ["human-reviewer"]
approval_label = "agent-approved"
draft = true
```

## Verify AEGIS and the Environment

In the target clone:

```text
python .agentic/aegis.py --version
python .agentic/aegis.py status --all --json
```

Expected version is a supported `aegis` version; expected JSON schema is `1`. The assisted
environment check reports a missing, malformed or incompatible payload before
the first run.

Build the executor image and verify the configured container runtime. For
rootless Podman, the typical setting is:

```toml
[container]
runtime = "podman"
run_args = ["--userns=keep-id"]
```

## Create the Labels First

GitHub and Gitea reject an unknown label name, so a missing label makes the
very first poll fail before it can post anything to the ticket; the reason is
printed to the console and `adore.log`. All of these must exist in the forge
repository before the first run. The web interface creates the missing ones when
you enroll a project (**Create the ADORE labels in the repository**, ticked by
default) or from Settings → Repository → **Create missing labels**; it never
changes existing labels. `adore init` does not create them, so after a CLI setup
create them in the forge or use that Settings button. Rename them here only if you
also change the matching configuration key:

| Label | Config key |
| --- | --- |
| `agent-ready` | `labels.lifecycle.ready` |
| `agent-working` | `labels.lifecycle.working` |
| `agent-clarify` | `labels.lifecycle.clarify` |
| `agent-answered` | `labels.lifecycle.answered` |
| `agent-mr` | `labels.lifecycle.review` |
| `agent-failed` | `labels.lifecycle.failed` |
| `agent-done` | `labels.lifecycle.done` |
| `agent-approved` | `delivery.approval_label` |
| `agent-revise` | `review.revise_label` |

All seven lifecycle labels are needed, not only the ones you expect to see: on
every status update ADORE removes the five it is not currently applying.

## Prepare a Ticket

An eligible ticket normally needs:

- `agent-ready`;
- one configured priority label such as `P1`, `P2`, or `P3`;
- acceptance criteria in the body;
- optionally `bug`, `fix`, or `change` for AEGIS task type;
- optionally `agent-quick` as a framing hint only.

Run selection without mutation:

```text
adore --profile my-project run --dry-run
```

Then conduct one poll:

```text
adore --profile my-project run --once
```

## Approval and Draft Publication

With human approval enabled (the default), when strict validation passes ADORE removes the approval label, presents the
evidence and fingerprint on the ticket, enters `awaiting-approval`, stops the
container, and releases the slot. Review the evidence, then freshly add
`agent-approved`. The next poll rechecks the exact candidate and target before
publication.

When the project disables human approval, ADORE checks the validated candidate and target and publishes automatically. ADORE opens the configured draft or ready MR/PR,
and stops in `in-review`; the AEGIS task already closed in validate. A human
reviews and merges.

## Failure and Recovery

A stage receives three failed attempts by default; the third stops. Questions
park without consuming that counter. Every problem is durable in local JSONL
and visible on the active ticket or MR/PR. A notification outage stops code
work and remains queued for later polling.

Inspect and explicitly retry after remediation:

```text
adore --profile my-project logs <run-id>
adore --profile my-project retry <run-id>
```

Retry is refused while a required notification remains pending.

## Native local execution

Choose server or container execution in setup. Server profiles require the [managed Pi installation](Local_Execution.md), native Python for AEGIS and Windows Jobs or delegated Linux cgroup v2. Prepare project tools and forge login for the service account on the ADORE machine.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.

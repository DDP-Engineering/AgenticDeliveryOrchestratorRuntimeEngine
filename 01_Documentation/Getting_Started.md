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

ADORE selects eligible GitHub, GitLab or Gitea tickets, conducts either the
repository's AEGIS workflow or a direct implementation inside a dedicated
worktree with container or native local execution, and opens draft or ready
MR/PRs after fresh human approval. It never merges.

## Prerequisites

- Python 3.11 or newer for ADORE;
- Git and a non-interactively pushable target clone;
- Docker or rootless Podman for container profiles; native scope controls for local profiles;
- authenticated `gh`, `glab`, or `tea` on the host;
- Pi, ADORE's only coding agent: built into the executor base image for container
  profiles, installed for the service account (`pi --version`) for local profiles;
- documented project build/test instructions and ignore rules for generated files;
- optionally AEGIS as `.agentic/aegis.py`; when present, a supported payload,
  schema 1 from `status --all --json` and valid configured AEGIS tests.

No AEGIS means the direct workflow, with an explicitly unverified candidate
for human approval. An unsupported or broken installed payload is refused,
never treated as absence. Web enrollment still requires AEGIS; use the
CLI/configuration path for repositories without it in this build.

ADORE reads only its current schema-1 run shape and migrates nothing. Delete
run-state directories under the configured `store_root/runs/` before starting
this build if they lack `workflow`. The metrics summary shape also changed:
delete the configured statistics database if its column contract is refused.
Neither store is reset automatically.

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

## Verify the Environment and Optional AEGIS

When the target clone contains `.agentic/aegis.py`, check it with:

```text
python .agentic/aegis.py --version
python .agentic/aegis.py status --all --json
```

The version must satisfy the client-declared supported range and JSON schema
must be `1`. A present malformed or incompatible payload is refused.
Without that file, `adore init` and doctor report the information:
"No AEGIS found: tickets run in the direct workflow". No AEGIS probe is run
for absence, and ADORE does not install the payload for you.

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

An AEGIS candidate needs independent strict validation. A direct run instead
uses one bounded fresh Pi session per attempt to implement the whole ticket;
ADORE checks settled success, no questions file and genuine changes other than
the two exchange files. Pi's summary is retained as reported checks, not
independent verification. The ticket and MR/PR show its summary, changed-file
count and "Verification: not configured. This candidate is unverified."
Summary-only work fails with `NO_CHANGES`. There is no direct verification
command in this build.

Both paths remove the old approval label, present the evidence and fingerprint,
enter `awaiting-approval`, stop execution and release the slot. Review the
evidence, then freshly add `agent-approved`. The next poll rechecks the exact
candidate and target before publication. Target or candidate drift requires
another presentation and fresh approval.

ADORE publishes the approved candidate as the configured draft or ready MR/PR
and stops in `in-review`, at stage `done`. Progress checkpoints may already be
on the owned branch when `delivery.publish_checkpoints` is enabled (the default);
they are not review publication and do not bypass approval. A human reviews
and merges.

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

Choose server or container execution in setup. Server profiles require the
[managed Pi installation](Local_Execution.md) and Windows Jobs or delegated
Linux cgroup v2; AEGIS projects also require the configured native Python.
Prepare project tools and forge login for the service account on the ADORE machine.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.

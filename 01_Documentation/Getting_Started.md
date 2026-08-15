<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Getting Started

ADORE 0.5 selects eligible GitHub, GitLab or Gitea tickets, runs AEGIS 0.5
inside isolated worktrees and containers, and opens draft MR/PRs after fresh
human approval. It never merges.

## Prerequisites

- Python 3.11 or newer for ADORE;
- Git and a non-interactively pushable target clone;
- Docker or rootless Podman;
- authenticated `gh`, `glab`, or `tea` on the host;
- an executor supported by the configured launcher;
- AEGIS 0.5.x installed in the target repository as `.agentic/aegis.py`;
- schema 1 from `status --all --json` and valid configured AEGIS tests.

ADORE 0.5 does not read or migrate ADORE 3.x state. Start with a separate
schema-4 state root/profile; retain old state only as historical evidence.

## Install and Configure

From `04_Software`:

```text
python -m pip install -e .
adore init my-project
adore --profile my-project config validate
```

The wizard creates non-secret configuration. Put only model-provider values in
the ADORE process environment or `.env`; forge authentication belongs to the
host CLI and is not exposed to executor containers.

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

Expected version is `aegis 0.5.x`; expected JSON schema is `1`. The assisted
environment check reports a missing, malformed or incompatible payload before
the first run.

Build the executor image and verify the configured container runtime. For
rootless Podman, the typical setting is:

```toml
[container]
runtime = "podman"
run_args = ["--userns=keep-id"]
```

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

When strict validation passes, ADORE removes the approval label, presents the
evidence and fingerprint on the ticket, enters `awaiting-approval`, stops the
container, and releases the slot. Review the evidence, then freshly add
`agent-approved`. The next poll rechecks the exact candidate and target before
publication.

ADORE pushes only after approval, opens a draft MR/PR, records close-out in the
AEGIS task, and stops in `in-review`. A human reviews and merges.

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

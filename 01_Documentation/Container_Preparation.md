<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Reviewed container preparation

Configure preparation after creating a project with `adore init`, or through
Project → Settings → Isolated environment. Preparation is optional; old profiles
keep their existing container image and gate behavior.

## Select and review

Commit a recipe to the configured clone and review its complete commands. Set
`execution.preparation` to `path.yml#job@commit`, using the full lowercase 40- or
64-character Git commit ID. The commit must equal the selected target branch's
current `origin/<target>` revision. The conductor fetches before checking a new
run and pins its worktree to that exact commit. A changed target requires a new
selection/review; resume uses the original immutable plan.

```toml
[execution]
backend = "container"
preparation = "prepare.yml#setup@0123456789012345678901234567890123456789"
preparation_step_timeout_seconds = 300
preparation_total_timeout_seconds = 900
preparation_max_attempts = 2
```

The example commit is a placeholder; replace it with the reviewed target commit.
`adore --profile <name> config set execution.preparation <selection>` validates
source and configuration before applying. `adore --profile <name> config plan`
prints the effective image, image authority, exact source selection, hashes and
commands without running them. `config validate` also validates a selected recipe.
In the GUI, prepare a candidate, inspect **Container preparation** and expand
**Preparation commands**, then Apply. Apply requires an idle paused project and
rechecks the same configuration, Git revision and plan. The GUI does not upload,
edit or generate recipes. Execution settings use the pending-review API.

## Recipe grammar, version 1

This Actions-style subset is a preparation contract, with plan schema 1. It is
not a general Actions workflow runner. [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
and [Gitea compatibility](https://docs.gitea.com/usage/actions/comparison/) describe
the broader systems; only the following ADORE fields execute:

```yaml
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See LICENSE.txt. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
name: Prepare project
jobs:
  setup:
    container:
      image: adore-executor-project:latest
    steps:
      - name: Install dependencies
        run: |-
          uv sync --locked
          npm ci
```

Root `name` and step `name` are optional; `jobs`, `container.image`, nonempty
`steps`, and each `run` are required. Use two-space indentation. Plain text,
single quotes with doubled apostrophes, JSON-compatible double quotes, literal
`|`/`|-` run blocks, comments and blank lines are supported. All jobs are validated,
including jobs not selected. Each run is one shell launch at the run worktree.

Unknown keys (including `uses`, `runs-on`, `env`, `working-directory`, `timeout-minutes`,
triggers, matrices, services, expressions and workflow permissions), duplicate
fields/jobs, aliases, anchors, tags, flow structures, folded blocks, document
markers and ambiguous plain booleans/numbers/null are refused with a typed error.
Quote text that resembles those values. No remote action or workflow download occurs.

Only regular tracked Git blobs under safe relative `.yml`/`.yaml` paths are
accepted. Links, submodules, traversal, absolute/backslash paths, and `.git`,
`.adore`, `.agentic` sources are refused. Limits are 64 KiB UTF-8 source, 16 jobs,
32 steps across all jobs, 8 KiB per script, and 256 script lines across all jobs.

## Image, environment and ordering

The selected job declares the effective image. A profile's explicitly declared
`container.image` must match, or may be empty in recipe mode. An omitted default
image is not a competing declaration. The image must already exist locally;
ADORE never pulls it for recipe execution. It must supply `python3`, `sh`, the
executor and declared image tool checks. Existing egress, mounts, cache volumes,
non-secret `container.runtime_env`, allowlisted executor credentials and supported
host-auth staging remain in force. Forge credentials are excluded.

Provision and image-tool checks precede auth staging and preparation. Preparation
finishes before any AEGIS task or AI gate starts, using the same container and
worktree. Steps execute sequentially with `sh -eu`; shell exports are step-local.
To expose newly installed tools to later gates, configure a shared non-secret
`container.runtime_env.PATH`, for example
`/adore/work/.venv/bin:/usr/local/bin:/usr/bin:/bin`. Dependency/package downloads
obey existing egress; scripts should use lockfiles. Keep secrets in the existing
credential environment, not literal recipe text: source and commands are review
and recovery evidence.

Host prerequisites, model checks and plan preview never run preparation. They use
the effective image and remain distinct from a successful prepared job.

## Bounds, evidence and recovery

Per-step timeout is 1–1800 seconds; total attempt timeout is 1–3600 seconds;
maximum explicit attempts is 1–3. Defaults are 300, 900 and 2. The remaining job
wall budget also bounds setup. Project child commands share that step lifetime;
timeout stops its process group and failure interrupts the owned container.
Cancellation interrupts the owned container and retains the existing release
semantics. Setup does not invent token/cost data; changed dependency files count
against the existing product file limit.

`state.json` carries optional closed `execution` evidence in run-state schema 1:
plan, actual container/image IDs, status, attempt count, ordered step outcomes and
prior attempt history. Missing legacy evidence does not imply preparation success.
The immutable `execution-plan.json` and timestamped redacted stdout/stderr receipts
under `preparation/attempt-N/step-M.json` remain outside the mounted exchange
folder. Each stream is capped at 64 KiB per step; inherited credential values and the already-staged supported executor auth values are redacted before file retention. Job details show status, attempts,
image and authoritative step exits, timestamps, timeouts and cancellation.

Profiles without recipes retain their existing recovery/profile-update contract and do not acquire preparation records. Recipe success is reusable only with the same plan, policy, verified container and image
IDs and intact evidence. Changed/missing resources, configuration drift, corrupt
state/receipts and incomplete setup fail closed. Ordinary retry does not replay
partial setup. Inspect evidence, then explicitly authorize:

```text
adore --profile <name> retry <run-id> --reprepare
```

This removes/recreates only the owned run container, retains the worktree and its
partial effects, and replays **all** steps within the attempt cap. Prior outcomes
remain immutable. There is no exactly-once guarantee after a crash. Cancel/delete
release their existing owned resources; shared images/cache volumes remain.
Old binaries reject new execution keys; complete/remove affected runs or retain a
compatible binary for rollback. No earlier run-state schema is migrated.

## Integration seams

`ExecutionBackend` supplies paths/shell, executor homes/auth destinations,
provisioning, tool checks, identity, bound commands, stop/interrupt and owned
cleanup. `ContainerBackend` is the only adapter enabled here. Local execution
(#21) will use that seam and its native transport. Image GUI/build integration
(#22) will use normalized plans and separate image/build identity. Portable rule
exports keep their existing narrow allowlist and never carry executable selection,
runtime environment, credentials or recipes.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Reviewed container execution plans

## Profile and source contract

`[execution] backend = "container"` defaults for all profiles. Other backends
fail before execution. `preparation = ""` preserves legacy operation; a selected
value is `repository/path.yml#job@full-lowercase-commit-id` (40 or 64 hex).
This is an operator acknowledgement of executable project input at that exact
revision. The CLI `config plan` and web review display commands before use.
Only tracked regular Git blobs are accepted, read from the configured clone
using injected argv runners. Relative POSIX paths exclude traversal, links,
`.git`, `.adore` and `.agentic` generated/governance sources. Initial run target
must equal the reviewed revision; changed targets require a new reviewed
selection. Existing recipe runs retain their original source/plan and refuse profile
drift. No repository upload/editor or second recipe authority is introduced.

The effective image comes from the selected job. An explicitly declared profile
image must agree; an omitted legacy default is not a competing declaration.
Empty profile image is permitted only in recipe mode. Legacy mode retains its
existing selected image. Plan identity covers schema, backend, source selection,
raw-byte SHA-256, normalized steps, image reference and non-secret execution
policy (runtime, egress, mount/cache/tool settings, runtime environment,
executor choice/command/model/questions, clone/worktree/target paths, AEGIS Python and preparation bounds). Secret values are excluded.
Image ID/build identity and per-run container identity are recorded separately.

## Published preparation syntax, version 1

This is a bounded schema-specific grammar, not a general YAML parser/importer.
The supported document is UTF-8 block mappings with two-space indentation:
optional root `name`, required `jobs`; one or more named jobs, each containing
only `container` with required `image`, and nonempty `steps`. Every step has
optional `name` and required `run`. Strings may be plain, single quoted
(doubled apostrophe escaping), JSON-compatible double quoted, or literal `|`
and `|-` blocks for run. Literal blocks preserve spaces/newlines. Comments and
blank lines are accepted. Unsupported indentation, flow structures, tags,
anchors, aliases, duplicate fields/jobs, coercible plain booleans/numbers/null,
folded blocks, document markers, expressions and all undeclared fields are
field-specific typed errors. All jobs are validated, including unselected jobs.
Working-directory and timeout-minutes are excluded in version 1.

Limits: 64 KiB source, 16 jobs, 32 steps across the document, 8 KiB per script,
256 physical script lines across the document. Each declared step is one
bounded command launch; project scripts may invoke child commands within the
same wall-clock bound. UTF-8 NUL/control input fails closed. Core and delivery
retain `dependencies = []`; no parser or packaging dependency is added.

## Preparation and evidence

Provision in the normal run worktree/container, then required-tool checks and
executor auth staging, then setup. Each step executes `sh -eu` at `/adore/work`
with the existing controlled container environment and configured egress.
Shell exports are step-local. Profile `container.runtime_env.PATH` explicitly
exposes new tools (for example `/adore/work/.venv/bin:/usr/local/bin:/usr/bin:/bin`)
to both preparation and gates. Script text travels through files, never host
shell argv, including WSL. No forge credentials or new secret sources are used.

Preparation executes only at run start; readiness/plan preview never installs.
The image supplies Python 3 for the file runner as well as the executor/tools.
The runner drains stdout/stderr to bounded files, records authoritative exit
and timeout, and stops its process group on timeout. Host cancellation stops
the owned container. Retained results are bounded to 64 KiB per stream/step
and redact inherited credential values and already-staged supported executor auth values before file retention. Scripts/source and results are archived
outside the worktree; the immutable operator plan remains outside mounted IO.

`[execution] preparation_step_timeout_seconds = 300` (1..1800),
`preparation_total_timeout_seconds = 900` (1..3600),
`preparation_max_attempts = 2` (1..3). Remaining total run wall time also bounds
setup. Timing begins before setup and gate budgets include setup. Setup adds
no fabricated cost telemetry. Generated dependency files keep existing product
file accounting; evidence files outside the worktree use separate fixed limits.

## Durable recovery

Run-state schema remains 1, with a closed `execution` record. An empty record
means the legacy container contract, not recipe success; any recipe profile on
an already active legacy run fails closed. No earlier schema is migrated: run
state with unknown or missing keys was written by another ADORE build and is
refused with the run directory to delete. No version is assigned by this task.

Persist complete plan before setup, actual container/image IDs before steps,
and running state before every side effect. Complete success is reusable only
for identical verified resources and plan. Missing/replaced containers, image
drift, stale config and incomplete/failed setup require explicit recovery.
Ordinary transient provision retries and ordinary retry never replay setup.
`retry --reprepare` acknowledges replay of ALL steps in a freshly recreated owned
container with the retained worktree; dependencies and prior partial effects
in that worktree remain. Attempts are capped and prior evidence is retained.
There is no exactly-once guarantee across crashes. Cancel/delete retain their
existing release boundaries and never delete shared caches/images.

## Extension boundaries and acceptance

The backend protocol owns target paths/shell/environment, provisioning/tool
readiness, bound commands, identity, interruption/stop and owned-resource cleanup.
The conductor owns ticket/AEGIS/recovery/approval/publication. #21 supplies a local
adapter and native gate transport through these paths; recipe+local is rejected
before any setup. Project images are prepared outside ADORE and selected by
reference; ADORE builds no images.

All new contracts use offline injected runners, including source/runtime/state
trust boundaries. Full Python/frontend suites, integrated legacy/recipe/local
acceptance, and live model/forge/runtime acceptance remain deferred
under the originating user's explicit focused-validation instruction.

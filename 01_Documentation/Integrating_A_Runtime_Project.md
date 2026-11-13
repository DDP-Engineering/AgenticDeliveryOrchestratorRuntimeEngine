<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Integrating a Runtime Project

ADORE conducts repositories with or without AEGIS through CLI/configured
profiles. It selects the workflow from `.agentic/aegis.py` in the isolated
worktree at claim, then keeps that identity through clarification, Retry,
reset and review. Web enrollment still requires AEGIS in this build.
ADORE never installs, upgrades or edits the target's AEGIS payload.

## Required Repository Contract

Both workflows need Git with a configured `origin` and target branch, documented
project instructions, ignore rules for generated artifacts and project build/test
tools in the chosen container image or native account. Native ownership and
container preparation remain independent of workflow selection.

### Without AEGIS: direct workflow

Absence of `.agentic/aegis.py` selects direct. No task journal is created.
The run starts at `build`; each attempt launches a fresh bounded Pi session to
implement the ticket completely, reading `AGENTS.md`, `CLAUDE.md`,
`CONTRIBUTING.md` and README when present and adding tests where the project
has tests. The existing build timeout override, general gate timeout, egress,
package permission and cumulative budgets all apply.

Pi writes blocking questions to the configured questions file and a short
change/check summary to root `ADORE_SUMMARY.md`. Do not use either exchange
path for tracked project source: source-owned or unsafe collisions are refused.
A questions file, even empty, parks the run without consuming a stage failure;
a human reply plus `agent-answered` resumes a fresh session with the thread.
A settled successful session must change the product progress fingerprint,
excluding both exchange files. Otherwise the run fails with `NO_CHANGES` and
retains the summary. Errors and timeouts use normal bounded build failures.

ADORE owns `validate`: it saves a bounded sanitized summary before removing
its file, checkpoints product changes, integrates the target and records the
exact candidate at `done` / `awaiting-approval`. Both exchange paths are literally
excluded and unstaged at every checkpoint, including recovery and handoff.
The agent selects and reports suitable checks using the repository instructions.
ADORE does not execute a separate verification command. Approval and MR/PR show
the retained summary, changed-file count and candidate/target fingerprints.
Summary absence alone is not a completion failure; unsafe summary artifacts are refused.
Recovery can finish a checkpoint from durable implementation evidence without
repeating a successful session. Review revisions keep the same workflow, branch
and worktree. The project approval policy applies to both workflows.

### With AEGIS: governed workflow

A present payload, including an unusable entry, never selects direct. The clone
is probed before pickup when that entry is present. AEGIS projects provide:

- `.agentic/aegis.py` reporting a supported `aegis` version;
- schema-1 JSON from `python .agentic/aegis.py status --all --json`;
- readable AEGIS task journals with no path escapes;
- project test commands configured in AEGIS for the selected execution environment;
- a `.gitignore` covering build artifacts and tool caches;
- for container execution, a project-specific image with Python and required build tools.

### AEGIS commands run in the selected execution environment

For container profiles ADORE executes `[commands]` from `.agentic/aegis.toml`
inside the Linux executor container during its own strict verification. A command written for the
workstation that authored it fails there, whatever it does locally. A Windows
entry such as:

```toml
test = ".\\.venv\\Scripts\\python.exe -m pytest -q"
```

must be expressed for the container instead:

```toml
test = "python3 -m unittest discover -s tests -q"
```

Check the repository's configured commands in the intended executor image
before the first run:

```bash
docker run --rm -v "$PWD:/w" -w /w <your-executor-image> sh -lc "<your test command>"
```

Depend only on what the image guarantees. The ADORE base image carries Python,
uv, Node, and Git, but no test framework: a `pytest` entry needs pytest in your
project image, while the standard library's `unittest` needs nothing.

### Ignore rules are part of the contract

ADORE checkpoints with `git add -A` (plus literal exchange exclusions for direct
runs), capturing governed artifacts and new source the executor wrote. It cannot tell those apart from
generated files; only your `.gitignore` can. Without one, bytecode and tool
caches join the candidate, consume the `max_files_touched` budget, and give the
reviewer noise to read past. `adore init` reports a target repository that has
none.

Verify the contract in the target clone:

```text
python .agentic/aegis.py --version
python .agentic/aegis.py status --all --json
```

ADORE rejects unknown versions, schemas, malformed output, or unreadable
journals before governed work. Repository probing accepts AEGIS adoption
journals at `survey`, `components`, or `close`, and a legacy journal another task
left at `deliver`; those are valid foreign journals but are never valid stages
for the ADORE-created task, whose decoder remains restricted to `frame`,
`specify`, `design`, `build`, `validate`, and `done`. An AEGIS release older
than the supported range, a different major, or any other contract is refused
at probe. The range is declared only in `adore/aegis.py`.

The pre-pick repository probe runs directly on the host. After a run container
is provisioned, ADORE writes each fully shell-quoted AEGIS command to the run's
host-mounted `io` directory and executes only `sh /adore/io/aegis.sh` through
Docker or Podman. Bounded stdout/stderr files carry the result back. Ticket
titles and other raw AEGIS arguments therefore never enter wrapped-runtime
argv, where WSL can split elements containing spaces; absent, unreadable, or
oversized exchange output fails closed.

## Ownership Boundary

One ADORE run owns this durable relationship:

```text
forge ticket
  -> ADORE run state
  -> task branch + worktree + container
  -> AEGIS task/history OR direct completion/summary evidence
  -> optional draft MR/PR
```

For AEGIS runs the executor owns task-journal content and transitions. ADORE reads and
validates it, but never writes it directly. ADORE owns local checkpoint
commits, target integration, push, draft MR/PR creation, comments, labels and
publication state. Executors may not commit, push, open an MR/PR, access forge
credentials, or merge. ADORE also never merges.

## AEGIS Task Types and Paths

Ticket labels map to task types in this precedence:

1. `bug` or `fix` selects `fix`;
2. `change` selects `change`;
3. all other eligible tickets select `feature`.

`agent-quick` is only a frame hint. The frame executor applies AEGIS rules and
records why the task uses `full` or `quick`.

Full path:

```text
frame -> specify -> design -> build -> validate -> done
```

Quick path:

```text
frame -> build -> validate -> done
```

Validation may route backward to specify, design, or build, and validate closes
the task by advancing to done. A done task returns to validation when ADORE
must revalidate it. Unknown stages, forward skips, and other regressions fail
closed.

## AEGIS Stage Sessions and Shared Checkpoints

ADORE creates the task after creating the branch. Every stage prompt declares
the task in autopilot by explicit conductor instruction, the per-task
override AEGIS defines for its `[interaction]` default: the executor records
`interaction: autopilot` in the journal header and never pauses to present
choices to a human, because no human is reading. Autopilot governs who decides,
not how much the executor does in one session. The target repository's
`[interaction]` setting keeps governing human sessions and needs no change for
conducted runs. ADORE supervises every stage and owns the configured approval before
publication. Each attempt uses a fresh executor session. Durable AEGIS artifacts
are the resume authority. The prompt has the executor finish a stage with
`python .agentic/aegis.py advance`, record unfinished work with `log` and end
with `pause` (`pause --blocked` for a question); a following session resumes
from `brief` and the journal State.

The prompt asks for exactly one stage per session, and the session boundary is
what gives ADORE a checkpoint to recover from, a per-stage error budget, and the
chance to hand the executor what failed last time. An executor that runs several
stages in one session is accepted when the journal carries a Log entry for every
stage it crossed, recorded as a `stages-run-ahead` event rather than tolerated
silently, and refused when entries are missing, because a gap cannot be told
apart from a skipped stage. Either way the run loses the three benefits above,
so a model that follows the one-stage instruction reliably is worth more than a
marginally faster one.

After successful stage transitions ADORE checkpoints locally. Direct runs
checkpoint completed implementation and integration without journal artifacts.
With `delivery.publish_checkpoints` enabled (the default), guarded WIP commits
may be visible on the owned branch before approval, without opening an MR/PR;
explicit false keeps them local. Neither policy bypasses human approval.

## AEGIS Final Validation and Shared Approval

For AEGIS runs, before final validation ADORE fetches and integrates the current target. It
then launches validation, whose session ends with AEGIS's own final strict
check, `report` and `advance` to done. ADORE accepts the observed Validate to
Done transition from the successful executor session and records it against the
checkpoint. A done task without matching evidence returns to Validate in a
fresh executor session.

ADORE fingerprints the target commit, candidate tree and exact local commit
series. When project approval is enabled, it removes `agent-approved`, verifies absence, posts the evidence together
with every `DEVIATION <stage>` entry the AEGIS journal recorded, and stops
the container in `awaiting-approval`. Only a fresh re-addition after that
presentation is accepted. Candidate changes or target drift invalidate the
approval and force integration, validation, presentation and approval again.

## Publication and Review

After any configured approval, ADORE pushes the branch and opens or adopts the draft or ready
MR/PR. No executor session or AEGIS command runs during publication. The approval or automatic freshness check fetches the target and rechecks the candidate fingerprint before the push. The run keeps the stage `done` while it waits for approval,
publishes and is in review.

Before draft creation, ADORE looks up and adopts an existing open MR/PR for the
task branch. A failed push keeps the validation evidence, so `adore retry` checks
freshness again and publishes the same candidate.

An AEGIS revision creates a new task journal on the same branch; earlier
journals remain history. A direct revision starts build without a task.
Every review round is bounded and requires a new evidence presentation and
fresh approval before review publication. The revise trigger remains applied
until provisioning and, for AEGIS, probing and new-task creation succeed.

## Failure Visibility

Every failure is appended to local JSONL. Recoverable stage failures update one
marker-owned incident comment with stage, attempt, stable code, redacted
evidence and next action. The configured final attempt posts a separate
terminal comment, stops the container, preserves the worktree and releases the
slot. Required notification writes are outboxed before transport; a forge
outage stops code work until polling delivers the pending notification.
Executor timeouts are classified only from the command runner's authoritative
timeout flag. Exit code or stderr text containing the word `timeout` is not
treated as proof that ADORE killed the process.

## Container preparation

Projects may select a tracked preparation recipe at an exact reviewed target commit after `adore init`. It prepares the ordinary run worktree/container before any AI stage; declared image tools must already exist and dependencies follow existing egress. Later gates discover installed tools through explicit `container.runtime_env.PATH`. See [Container preparation](Container_Preparation.md) for the closed Actions-style grammar and immutable recovery contract.

## Native local execution

Local projects use dedicated worktrees with independently prepared account tools. Container recipes/tool-check manifests cannot be selected for local profiles.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.

When `delivery.require_human_approval` is false, the validated candidate and
fetched target are checked before automatic publication; no approval label is
required. The human merge boundary remains unchanged.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Integrating a Runtime Project

ADORE conducts repositories that already contain AEGIS. It uses the
payload exactly as installed and never edits AEGIS source or payload files.

## Required Repository Contract

The target clone must provide:

- Git with a configured `origin` and the target branch;
- `.agentic/aegis.py` reporting a supported `aegis` version;
- schema-1 JSON from `python .agentic/aegis.py status --all --json`;
- readable AEGIS task journals with no path escapes;
- project test commands configured in AEGIS, written for the CONTAINER;
- a `.gitignore` covering build artifacts and tool caches;
- a project-specific container image with Python and required build tools.

### Commands run in the container, not on your machine

ADORE executes `[commands]` from `.agentic/aegis.toml` inside the Linux
executor container during its own strict verification. A command written for the
workstation that authored it fails there, whatever it does locally. A Windows
entry such as:

```toml
test = ".\\.venv\\Scripts\\python.exe -m pytest -q"
```

must be expressed for the container instead:

```toml
test = "python3 -m unittest discover -s tests -q"
```

Every stage passes and the run then dies at validation, because the commands
ADORE runs to verify the candidate independently are the repository's own. Check
them by hand before the first run:

```bash
docker run --rm -v "$PWD:/w" -w /w <your-executor-image> sh -lc "<your test command>"
```

Depend only on what the image guarantees. The ADORE base image carries Python,
uv, Node, and Git, but no test framework: a `pytest` entry needs pytest in your
project image, while the standard library's `unittest` needs nothing.

### Ignore rules are part of the contract

ADORE checkpoints each stage with `git add -A`, which is what captures governed
artifacts and any new source the executor wrote. It cannot tell those apart from
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
journals at `survey`, `components`, or `close`; those are valid foreign journals
but are never valid stages for the ADORE-created task, whose decoder remains
restricted to `frame`, `specify`, `design`, `build`, `validate`, `deliver`, and
`done`. Any other AEGIS contract is refused at probe.

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
  -> active AEGIS TASK journal
  -> historical TASK journals from revisions
  -> optional draft MR/PR
```

The executor owns task-journal content and transitions. ADORE reads and
validates it, but never writes it directly. ADORE owns local checkpoint
commits, target integration, push, draft MR/PR creation, comments, labels and
publication state. Executors may not commit, push, open an MR/PR, access forge
credentials, or merge. ADORE also never merges.

## Task Types and Paths

Ticket labels map to task types in this precedence:

1. `bug` or `fix` selects `fix`;
2. `change` selects `change`;
3. all other eligible tickets select `feature`.

`agent-quick` is only a frame hint. The frame executor applies AEGIS rules and
records why the task uses `full` or `quick`.

Full path:

```text
frame -> specify -> design -> build -> validate -> deliver -> done
```

Quick path:

```text
frame -> build -> validate -> deliver -> done
```

Validation may route backward to specify, design, or build. Delivery may route
back to validation. Unknown stages, forward skips, and other regressions fail
closed.

## Stage Sessions and Checkpoints

ADORE creates the task after creating the branch. Every stage prompt declares
the task autopilot-to-deliver by explicit conductor instruction, the per-task
override AEGIS defines for its `[interaction]` default: the executor records
`interaction: autopilot` in the journal header and never pauses to present
choices to a human, because no human is reading. Autopilot governs who decides,
not how much the executor does in one session. The target repository's
`[interaction]` setting keeps governing human sessions and needs no change for
conducted runs. ADORE supervises every stage and owns the pre-publication
approval. Each attempt uses a fresh executor session. Durable AEGIS artifacts
are the resume authority.

The prompt asks for exactly one stage per session, and the session boundary is
what gives ADORE a checkpoint to recover from, a per-stage error budget, and the
chance to hand the executor what failed last time. An executor that runs several
stages in one session is accepted when the journal carries a Log entry for every
stage it crossed, recorded as a `stages-run-ahead` event rather than tolerated
silently, and refused when entries are missing, because a gap cannot be told
apart from a skipped stage. Either way the run loses the three benefits above,
so a model that follows the one-stage instruction reliably is worth more than a
marginally faster one.

After every successful stage transition, ADORE creates an unpushed local
checkpoint commit. Those commits preserve journal evolution, give crash
recovery a clean tree, and are not remotely visible before approval.

## Final Validation and Approval

Before final validation ADORE fetches and integrates the current target. It
then launches validation and independently runs:

```text
python .agentic/aegis.py check --task TASK-<id> --strict --run --json
```

Success requires schema 1, exit zero, `strict.passed == true`, no errors or
promoted warnings, at least one executed verification command, successful
completion of every executed command, and a valid task journal at `deliver`.

ADORE fingerprints the target commit, candidate tree and exact local commit
series. It removes `agent-approved`, verifies absence, posts the evidence together
with every `DEVIATION <stage>` entry the AEGIS journal recorded, and stops
the container in `awaiting-approval`. Only a fresh re-addition after that
presentation is accepted. Candidate changes or target drift invalidate the
approval and force integration, validation, presentation and approval again.

## Publication and Review

After approval, a constrained delivery session records approval and AEGIS
bookkeeping. ADORE invokes the AEGIS report/evolution operations, creates the
final local commit, rechecks target freshness, pushes the branch and opens or
updates a draft MR/PR. A close-out session records the successful remote result
and must leave the task at `done`; ADORE pushes that small commit to the same
draft.

Before draft creation, ADORE looks up and adopts an existing open MR/PR for the
task branch. Restart recovery for a task already at `done` repeats the final
checkpoint and push before entering review, so close-out evidence is not left
only in the worktree.

A requested revision creates a new AEGIS task journal on the same branch.
Earlier journals remain history. Every review round is bounded and requires a
new validation presentation and fresh approval before push.
The revise trigger remains applied until provisioning, payload probing, and
new-task creation succeed.

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

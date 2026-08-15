<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Integrating a Runtime Project

ADORE 0.5 conducts repositories that already contain AEGIS 0.5.x. It uses the
payload exactly as installed and never edits AEGIS source or payload files.

## Required Repository Contract

The target clone must provide:

- Git with a configured `origin` and the target branch;
- `.agentic/aegis.py` reporting `aegis 0.5.x`;
- schema-1 JSON from `python .agentic/aegis.py status --all --json`;
- readable AEGIS task journals with no path escapes;
- project test commands configured in AEGIS;
- a project-specific container image with Python and required build tools.

Verify the contract in the target clone:

```text
python .agentic/aegis.py --version
python .agentic/aegis.py status --all --json
```

ADORE rejects unknown versions, schemas, malformed output, or unreadable
journals before governed work. There is no AEGIS 3.x detection, compatibility,
or migration path.

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

ADORE creates the task after creating the branch. Frame runs in autonomous
autopilot-to-deliver mode and does not pause at its checkpoint. Each attempt
uses a fresh executor session. Durable AEGIS artifacts are the resume authority.

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
series. It removes `agent-approved`, verifies absence, posts the evidence, and
stops the container in `awaiting-approval`. Only a fresh re-addition after that
presentation is accepted. Candidate changes or target drift invalidate the
approval and force integration, validation, presentation and approval again.

## Publication and Review

After approval, a constrained delivery session records approval and AEGIS
bookkeeping. ADORE invokes the AEGIS report/evolution operations, creates the
final local commit, rechecks target freshness, pushes the branch and opens or
updates a draft MR/PR. A close-out session records the successful remote result
and must leave the task at `done`; ADORE pushes that small commit to the same
draft.

A requested revision creates a new AEGIS task journal on the same branch.
Earlier journals remain history. Every review round is bounded and requires a
new validation presentation and fresh approval before push.

## Failure Visibility

Every failure is appended to local JSONL. Recoverable stage failures update one
marker-owned incident comment with stage, attempt, stable code, redacted
evidence and next action. The configured final attempt posts a separate
terminal comment, stops the container, preserves the worktree and releases the
slot. Required notification writes are outboxed before transport; a forge
outage stops code work until polling delivers the pending notification.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Integrating A Runtime Project

Use this guide after ADORE is installed and one operator account can run it.
Each target repository is a **runtime project** and receives its own profile,
state, metrics, worktree location, and container-image selection.

This guide does not repeat host installation. Start with
[Getting_Started.md](Getting_Started.md) if the ADORE host is not already
working.

## 1. Prepare the Target Project

Before creating a profile, establish the following for `<runtime-project>`:

- a local, clean clone available to the ADORE run-as account;
- a forge repository identifier accepted by `glab`, `gh` or `tea`
  (Gitea: exactly `owner/repo`);
- **an AEGIS 2.x payload installed in the repository**, providing
  `.agentic/tools/run.sh` and a schema-3 `.agentic/workflow.toml` (see below);
- a default target branch and the human reviewers responsible for merge
  decisions;
- a project image containing the build, test, lint, and verification tools the
  target needs; and
- a ticket-label convention that distinguishes ready, hold, excluded, priority,
  and revision work, plus the labels that select the AEGIS run kind and the
  quick profile.

### AEGIS 2.x Is Required, And Only AEGIS 2.x

ADORE 2.0 speaks exactly one governance contract: the AEGIS 2.x grouped CLI.
There is no AEGIS 1.x support, no detection, and no migration path. A
repository carrying an older payload cannot be conducted; install or upgrade
it with WAEGIS first.

ADORE does not judge whether work is correct. It verifies with the target
repository's own AEGIS payload, invoked inside the run container as:

```text
bash .agentic/tools/run.sh <group> <action> --run <run-id> --json
```

Smoke-test the payload from the clone before creating a profile - this is the
same probe `adore init` runs:

```bash
bash .agentic/tools/run.sh config validate --json
```

It must answer `"status": "ok"` with `"schema_version": 3`.

#### The response contract ADORE relies on

Every AEGIS command answers with the same four-key envelope, plus
command-specific extras:

```text
status:   ok | blocked | failed
stage:    <stage-or-none>
artifact: <path-or-none>
next:     <exact-next-command-or-none>
```

Exit codes are discriminated, not merely non-zero: `0` is success, `1` is a
governance signal ADORE reads as data, and anything else - `2` for a usage
error or a wrapper that cannot resolve Python - is treated as a broken command
or a broken payload and escalates. Unparseable output, a missing envelope key,
or a status contradicting the exit code escalate the same way. ADORE never
degrades silently.

#### Run identity

ADORE starts exactly one AEGIS run per ticket with
`aegis run start <kind> [--quick]`, records the run id it mints, and pins it
with `--run` on every later call and every run-local file it reads. It never
consults `.agentic/.workspace/state/current_run`. The executor is instructed to
pin the same run id.

#### The stage cycle

AEGIS owns the stage pointer; ADORE asks `run status` for it on every
iteration and checks it against the sequence declared for the run's profile:

```text
full   intake -> alignment -> requirement -> design -> check ->
       implementation -> validation -> delivery
quick  intake -> implementation -> validation -> delivery
```

Per stage, the executor runs `stage prepare`, fills the generated form at the
`artifact` path, and runs `stage apply` - content enters through forms, never
through CLI flags. ADORE then verifies objectively (`stage show` reports
`ready` with no blockers; validation and delivery additionally survive
`aegis verify run`) and issues `aegis stage close` itself. **ADORE is the
delegated approver; the executor is instructed never to close a stage.** The
real human approval stays at the draft MR review. When AEGIS reports the run
complete, ADORE's own publication phase integrates the target branch, re-runs
`aegis verify run`, composes the MR body from `aegis delivery report`, pushes,
and opens the draft MR.

#### Escalation semantics

| AEGIS signal | ADORE reaction |
| --- | --- |
| Unresolved questions in the stage form, an alignment `pause`, a `repo-wide` access request, or a `route_to` request | Parks the run and asks on the ticket. |
| A live `PERSISTENCE-LOCK-TIMEOUT` | One bounded retry after a short delay, then escalates. |
| `GRAPH-STALE-UPDATE`, `REQUIREMENT-STALE-UPDATE`, schema corruption, any run-resolution error | Escalates: state repair is a human task and ADORE never performs it. |
| A waivable blocker | Escalates with the exact `aegis waive add <id> --reason "..."` command. **ADORE never waives.** |
| A stage outside the declared sequence, or a backwards move | Escalates: routing is a human decision in this version. |
| Exit 2, a timeout, or a non-conforming envelope | Escalates, tagged as a contract failure - look at ADORE or the payload, not the ticket. |

Because ADORE invokes AEGIS inside the run container, the project image must
also satisfy the payload's runtime prerequisites: Python 3.11+ resolvable as
`python3`, `git`, `bash`, and `node` for the guard hooks - which fail closed
without it, silently. Cover them with `[container] required_tool_checks` so a
mismatched image fails before a stage starts rather than midway through a run.

AEGIS is versioned independently of ADORE. ADORE uses only its stable command
surface and its run artifacts, so an AEGIS 2.x upgrade normally requires no
ADORE change - but a move off the 2.x contract does.

The run-as account must be able to read the repository, create a worktree, push
an ADORE branch, and open a draft MR/PR. It must not be granted authority to
merge protected branches.

## 2. Build and Prove the Project Image

The generic `adore-executor-base:1.0.0` image supplies shared tooling. Build a
separate image for the runtime project's dependencies and tag it clearly:

```bash
docker build \
  -f <project-dockerfile> \
  -t adore-executor-<runtime-project>:<tag> \
  <project-build-context>
```

Configure fast, non-mutating checks for project tools:

```toml
[container]
image = "adore-executor-<runtime-project>:<tag>"
required_tool_checks = [
  # the AEGIS 2.x prerequisites
  "python3 --version",
  "node --version",
  # plus the runtime project's own tooling
  "<build-tool> --version",
  "<test-tool> --version",
]
```

Do not put provider keys, forge tokens, local user configuration, or project
source code into the image. ADORE mounts the source and injects only explicitly
allowed executor environment variables at run time.

## 3. Create a Dedicated Profile

Create a profile from the ADORE runtime directory:

```bash
adore init <profile-name>
```

Choose the local clone, forge kind, repository, runtime command, project image,
executor, model, reviewers, and target branch for this runtime project. The
wizard creates a profile under the ADORE configuration home; it does not modify
the target repository configuration.

Use profile-owned state by default. It prevents different projects from sharing
locks, run journals, metrics, or worktrees accidentally. Use a clone-adjacent
`.adore` store only when the team deliberately wants project-local state.

## 4. Review the Project Contract

Before a real poll, review these configuration areas in the profile:

| Area | Confirm |
| --- | --- |
| `[platform]` | Correct forge and repository identifier. |
| `[worktree]` | Local clone path, worktree root, and branch naming convention. |
| `[container]` | Verified runtime command, project image, tool checks, and egress policy. |
| `[executor]` | Approved executor, model, secret key names, and supported auth mode. |
| `[readiness]` | Ticket quality requirements match the team's intake process. |
| `[labels.*]` | Ready, hold, exclude, priority, executor-pin, and lifecycle names match the forge. |
| `[workflow]` | Label-to-AEGIS-kind mapping, the quick label, and any per-stage timeout overrides. |
| `[delivery]` | Target branch, draft behavior, reviewers, and human merge boundary. |
| `[review]` | Revision label and review-round limit. |

See [Configuration_Reference.md](Configuration_Reference.md) for every
setting and [Security_And_Credentials.md](Security_And_Credentials.md) for
authentication and secret handling.

## 5. Prepare Tickets for Pickup

The default readiness gate expects a ticket to have:

- a clear goal;
- acceptance criteria;
- a known component or path;
- a scope no larger than the configured maximum;
- one priority label;
- the configured ready label, normally `agent-ready`; and
- optionally a kind label (`bug`/`fix`/`change` by default) selecting the AEGIS
  run kind, and the quick label (`agent-quick` by default) opting into the
  four-stage profile. An unlabelled ticket starts a `feature` run; the quick
  label is ignored on anything that does not resolve to `fix` or `change`,
  because AEGIS permits `--quick` only there.

A concise ticket structure is:

```text
## Goal
Describe the change to make.

## Acceptance Criteria
- State the observable result.
- State the required validation.

## Scope
Name the permitted component or path and keep the change bounded.

## Notes
Add constraints, examples, or links the executor must respect.
```

The human controls pickup with `agent-ready`, `agent-hold`, and `no-agent` by
default. ADORE controls lifecycle labels only when `[state] channel` is
`labels` or `both`; in comment mode, local state remains authoritative and
status is mirrored in ticket comments.

## 6. Validate Before Enabling Work

Use an explicit profile for the first verification sequence:

```bash
adore --profile <profile-name> config validate
adore --profile <profile-name> config show
adore --profile <profile-name> run --dry-run
adore --profile <profile-name> run --once
```

Confirm the target repository is AEGIS-ready in the same pass, from the clone:

```bash
bash .agentic/tools/run.sh config validate --json
```

Inspect the dry-run decision before the supervised poll. It should explain why
each visible ticket is eligible or skipped. After a real poll, verify the run
with:

```bash
adore --profile <profile-name> status
adore --profile <profile-name> runs
adore --profile <profile-name> logs <run-id>
```

Only then allow scheduled or loop operation. See
[Operations_Guide.md](Operations_Guide.md) for the normal operating model.

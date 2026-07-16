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
- a forge repository identifier accepted by `glab` or `gh`;
- a default target branch and the human reviewers responsible for merge
  decisions;
- a project image containing the build, test, lint, and verification tools the
  target needs; and
- a ticket-label convention that distinguishes ready, hold, excluded, priority,
  and revision work.

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
- one priority label; and
- the configured ready label, normally `agent-ready`.

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

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-b3251e39 — Repository-URL enrollment

Status: active. This specification retains the requirement's detailed repository
source protocol and ownership boundaries while describing the accepted enrollment
eligibility change. It does not define runtime workflow execution.

## Enrollment behavior

An administrator confirms the exact valid reviewed repository configuration.
Creation makes the selected clone or reuses an existing matching-origin clone,
requires the selected target branch, and publishes the project with pickup stopped
under the existing guarded publication contract. A repository with no AEGIS files,
with `.agentic/aegis.py` alone, or with both AEGIS files is eligible. No
`repository_aegis_missing` rejection or instruction to install AEGIS belongs to
this contract. Enrollment does not install, upgrade or modify AEGIS or create
other files inside the clone.

Preview and explicit draft checks do not create a pending clone. Before a clone
exists, its workflow is not inspected. File inspection of an available clone
identifies AEGIS solely from `.agentic/aegis.py`; `aegis.toml` is not necessary.
This identifies the workflow, not its executable version or correctness. The
existing live pre-pick AEGIS probe retains authority, including refusal of a
present unsupported or broken payload without Direct fallback.

## Retained repository-source protocol

These boundaries remain in force; they are not permission to change unrelated
repository-source or branch-selection behavior:

- Repository URLs use `https`, `http` or `ssh`, including `user@host:path`, without
  embedded passwords. Invalid addresses are refused, not repaired or guessed.
- Repository path, forge kind, Gitea login, remote branches and default branch
  are derived at the existing explicit repository-source boundary. `github.com`
  identifies GitHub, `gitlab.com` identifies GitLab and a matching server tea login
  identifies Gitea; otherwise forge kind is unset for administrator selection.
- Git reads remote branches and symbolic HEAD noninteractively through the same
  injected command boundary on GitHub, GitLab and Gitea, including self-hosted
  addresses, using the ADORE account's Git access.
- A unique project ID derives from the repository name. Reserved route names,
  including `new`, `clone` and `import`, receive a suffix. The initial clone
  proposal is `<ADORE home>/repos/<project ID>`.
- Administrators can choose another absolute clone folder outside ADORE home or
  within its `repos` folder. Another existing folder is never overwritten; a
  clone is reused only when its origin matches the selected repository.
- Enrollment branch controls offer validated remote branches, mark and initially
  select the advertised default, and preserve an explicit selection on same-URL
  rereads only while that branch remains present. Changed URLs, failed reads and
  stale responses cannot reuse old choices. Missing symbolic HEAD requires
  explicit selection. An empty branch list disables continuation with recovery
  guidance.
- Malformed, duplicate, inconsistent or oversized advertisements (over 2 MB or
  10,000 branches) fail closed with typed errors, without partial choices or an
  invented default. Existing empty/detached and SHA-256 remote handling remains.

## Failure and publication boundaries

The reviewed configuration, identity, administrator/CSRF authority, profile and
conductor locks, and revision-bound readiness evidence retain their existing
contracts. Workflow information is not another eligibility gate. A stale review
cannot publish changed inputs. Creation removes only a fresh clone it owns on
clone verification or subsequent publication failure; matching existing clones
and unrelated folders are not cleanup targets. A missing target branch retains
`repository_branch_missing`; other existing clone and publication failures retain
their typed responses and cleanup guarantees. Failure never publishes a runnable
partial profile.

## Acceptance examples

| Clone contents | Creation with valid branch | File-inspection workflow |
|---|---|---|
| No `.agentic` directory | succeeds, pickup stopped | Direct |
| `aegis.toml` only | succeeds, pickup stopped | Direct |
| `aegis.py` only | succeeds, pickup stopped | AEGIS |
| Both AEGIS files | succeeds, pickup stopped | AEGIS |
| Present broken `aegis.py` | enrollment does not execute it | AEGIS, not a compatibility claim |
| No clone yet | preview/check creates no clone | not inspected |
| Valid clone, selected branch missing | typed refusal; owned fresh clone removed | not a workflow fallback |
| Destination belongs to another repository | typed occupied-folder refusal | no overwrite |

Offline API and browser tests prove successful Direct and aegis.py-only creation,
no enrollment-added clone files, matching-origin reuse, no preview/check clone
writes and the retained error/cleanup boundaries. All Git/forge/runtime commands
are fake; no live acceptance is implied.

## Design handoff

The requirements establish observable workflow states, not a workflow-selection
setting. TASK-988d986a Design D2 chooses the separate top-level enum
`workflow = aegis | direct | not-inspected`, outside prerequisite checks and
verdict calculation, across preview, measured evidence and browser validators.
Readiness persistence uses only schema 3, with explicit readiness.json deletion
guidance on any other schema; no migration or automatic reset. The readiness
section of `REQ-REL-c598b075.md` records the current shape.

Design D3/D5 adds a strict optional verify_command string, default empty, with
CR/LF/NUL and nontext refusal, exact TOML string serialization and canonical
review binding. Enrollment's Verification step shows an empty optional field
until a current file observation identifies AEGIS, then substitutes the
repository-owned-test-command note; it never silently clears entered text.
Pending clone evidence remains honest until an actual inspection; creation
neither reruns nor promotes measured evidence. Command suggestion and Jobs
presentation are outside this scope.

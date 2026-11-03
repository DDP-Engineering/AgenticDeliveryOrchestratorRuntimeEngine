<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# PI-08 #58 acceptance record

- Audit date: 2026-11-03.
- ADORE product commit: `c4c410b4fb5bb9da580f6146a83860fe88049fab` on
  `task/adore-web-interface`.
- Build pins for the executor image and managed server installation: Pi
  `1.4.0`, `pi-web-access` `0.46.0`. Installed versions still need verification
  on each live target.
- AEGIS: use a test project with repository-installed AEGIS 0.15.
- Live status: all rows below are pending. No live measurements or PR/MR links
  exist yet. An em dash in the evidence columns means no observation.

## Live run procedure

1. Use a disposable ADORE home, dedicated test project, test repository and
   least-privilege service account. Confirm the test forge account and repository
   access separately. Have the owner enter API keys through the dedicated UI
   and complete ChatGPT sign-in in the isolated instance. Keep production and
   ticket #25 outside the session. Confirm the executor image and proxy are
   present for container scenarios. For native targets, run `adore pi install`
   and `adore pi verify` as the isolated service account. Check Windows Job
   ownership or delegated Linux cgroup v2 with `cgroup.kill` as applicable.
2. Run one ticket at a time with monitoring paused. Check host prerequisites
   and use **Test AI connection** to check the model and a shell call. Start
   from **Jobs → Tickets → Start** and verify monitoring stays paused. Use the
   proposed ceilings of 20 launches, 30 minutes of active work, 5 minutes per
   stage and 25 changed files per job. Use an owner-approved provider budget and
   a nonzero per-job reported cost cap within it. Track spend separately where
   usage or price reporting is incomplete. Stop when a limit is reached.
3. Confirm AEGIS validation, inspect the candidate and record its head SHA,
   terminal or waiting state, active duration and reported token totals. Use
   the usage journal or job statistics and mark unknown or partial totals.
   Starting a live job can update labels and comments before publication, so
   use only test tickets where those writes have been authorized.
4. Stop at `awaiting-approval`. Keep approval labels off the tickets and
   withhold branch push access. Publication is blocked by the current push
   restriction. If separately authorized later, verify that the human
   approval binds the recorded candidate, `delivery.draft = true` creates a
   draft on the intended base and the PR/MR head matches that candidate.
5. Keep only sanitized evidence here. Exclude credentials, account emails,
   host IDs, authentication links and raw traces. For each failed live row,
   record the typed cause and an authorized follow-up ticket. Clean up only
   the isolated resources identified for the run.

## Success scenarios

Use one small deterministic change and a focused test per row. S02 adds a
pinned dependency download to a disposable environment with a cold cache.
Keep system package elevation disabled for this acceptance.

| ID | Target and credential | Internet | Evidence to collect before approval | Run result | Draft PR/MR | Input/output tokens | Active duration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | Container, provider API key | Off | Pi reaches the provider. A controlled unrelated destination outside the effective allowlist is denied. Web tools are absent. | Pending owner session | Blocked by push restriction | — | — |
| S02 | Container, same provider API key | On | Fetch the pinned library from the approved registry, import it and run the focused test. Verify the selected web extension is available. | Pending owner session | Blocked by push restriction | — | — |
| S03 | Container, OpenAI-compatible LM Studio or Ollama endpoint | Off | Pi uses the configured endpoint and model. Reachability is checked inside the job's network boundary. An unrelated destination outside the allowlist is denied. | Pending owner session | Blocked by push restriction | — | — |
| S04 | Container, ChatGPT subscription | Off | Complete sign-in and run a stage. Check mount and injection metadata with values suppressed. Only the helper mounts the credential directory. Stage evidence redacts the access token. | Pending owner session | Blocked by push restriction | — | — |
| S05 | Linux server, provider API key | Host policy | Verify both installed pins, current account, controlled tool PATH and owned cgroup. Use inert personal Pi settings in the dedicated account to confirm isolation. | Pending owner session | Blocked by push restriction | — | — |
| S06 | Windows server, provider API key | Host policy | Verify both installed pins, current account, direct Node launch, PowerShell tool call and owned Job Object. Use inert personal Pi settings in the dedicated account to confirm isolation. | Pending owner session | Blocked by push restriction | — | — |

For S01, S03 and S04, Internet Off uses the effective model allowlist plus any
explicit operator entries. The ChatGPT credential helper uses its own network.
For S05 and S06, the host controls network access.

## Failure scenarios

Use the same isolated project controls and bounds. For timeout and cancellation,
use a disposable ticket that keeps the stage active long enough to observe
abort and process cleanup. Check that the test branch and PR/MR are absent.

| ID | Trigger | Expected evidence | Live result | Input/output tokens | Active duration | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | Replace the test provider key with a synthetic invalid value | Credential rejection in the probe and bounded job failure. The value stays out of retained evidence. | Pending owner session | — | — | — |
| F02 | Stop the dedicated test endpoint | Connection failure with the endpoint unavailable. No cloud fallback. | Pending owner session | — | — | — |
| F03 | Disconnect the isolated ChatGPT sign-in, then separately induce an expired credential with a provider-rejected refresh | Disconnect gives **Not signed in**. A refused refresh gives **Sign in again** and prevents Pi from starting the stage. Record the two observations separately. | Pending owner session and safe refresh-rejection fixture | — | — | — |
| F04 | Let a stage exceed a short per-stage limit | RPC abort is attempted. ADORE removes a process that survives the grace period and records the timeout. | Pending owner session | — | — | — |
| F05 | Cancel during an active stage | Abort and verified cleanup of the owned scope. Job is cancelled and publishes nothing. | Pending owner session | — | — | — |

## Offline evidence

- PI-07 handover at the audited commit records a passing full offline suite
  and two approved review rounds. It explicitly defers live Linux and Windows
  acceptance. See the [PI-07 journal](../../.agentic/tasks/TASK-2813a6af.md).
- PI-08 re-ran 334 Python tests covering configuration refusals, managed Pi
  installation and execution, RPC usage/abort and web tools, model diagnostics,
  ChatGPT helper/refresh and stage injection, and web settings. All passed.
- Another 215 Python checks passed across orchestration, provider configuration,
  executor inventory and metrics. Two Linux-only inventory cases were skipped
  on Windows. Both Python runs emitted the FastAPI/Starlette TestClient
  deprecation warning.
- The frontend Help and Statistics suites passed 14 checks covering Help parity
  and links in all four languages, plus partial or unavailable token totals.
- Offline tests use injected runners and fixtures. Model responses, downloads,
  installed image contents and forge publication require live evidence.

## Documentation audit

Manually compared the four Help locales, operator guides, component documents,
AEGIS knowledge and affected requirements against the audited code. Corrected
guidance for managed native Pi, Windows launch, Linux delegation, provider
credentials, endpoint support and read-only executor discovery. Clarified the
ChatGPT helper-only credential mount and retired the OpenCode response
requirement `REQ-FUNC-a8865e64`. Corrected unreleased changelog descriptions
of server RPC and endpoint support. Help already describes the managed
launcher, paused manual Start and current credential paths. The plan preserves
the original proposal, including the ChatGPT run mount that PI-05 replaced with
the helper-only mount and per-stage access token.

Release notes check passed with the advisory for a changelog-only edit. These
edits correct descriptions of existing behavior, so they require no new
release note.

## Superseded backlog

Read the live ticket bodies and closure comments on 2026-11-03. The
replacements cover the reported behavior at the implementation and offline
level. Live confirmation for server behavior belongs to S05 and S06.

| Ticket | Replacement | Evidence and disposition |
| --- | --- | --- |
| #43 | #53 | Qwen removed from execution, setup, connection checks, executor image and Help. Removed configuration fails with remediation. Changelog and four-locale release notes record the single-agent change. Keep closed. |
| #45 | #53 | The local Codex launcher and its account configuration path were removed. The native runtime launches managed Pi. Keep closed. |
| #46 | #53 | ADORE no longer launches OpenCode. Managed Pi gates exclude personal and untrusted project resources, covered by the hostile-configuration fixture in `test_local_execution.py`. Keep closed. |
| #33 | #53, #57 | Case-insensitive removed-prefix checks refuse old settings. Native profiles reject arbitrary local environment overrides and the managed native environment filters forge credentials. `test_config.py` and `test_local_execution.py` cover refusals. Keep closed. |
| #44 | #57 | Managed Pi uses a fresh agent directory and a filtered environment instead of personal Pi settings or sign-in. The native gate fixture and updated local execution guide cover the replacement. Keep closed, with live confirmation pending. |
| #32 | #57 | Native launches resolve managed Node and Pi. Readiness reports missing or incompatible prerequisites. Enrollment has no cgroup or executable picker, and arbitrary local environment overrides are refused. Offline coverage is in `test_pi_installation.py`, `test_local_execution.py` and `local-executors.spec.ts`. Keep closed, with Windows acceptance pending. |
| #34 | #52 | `test_pi_rpc.py` covers per-turn accounting, large bounded evidence and unreadable usage. The usage journal receives complete counts, and Statistics represents partial or unavailable totals. Keep closed. |

#26 is open and outside PI-08 backlog cleanup. S02 checks a user-level library
download and does not exercise adaptive system package installation.

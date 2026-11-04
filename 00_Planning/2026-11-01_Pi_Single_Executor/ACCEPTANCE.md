<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# PI-08 #58 acceptance record

- Documentation audit date: 2026-11-03.
- Test repository: `dpasare/adore-web-acceptance-20260930`.
- ADORE product commit: `c4c410b4fb5bb9da580f6146a83860fe88049fab` on
  `task/adore-web-interface`.
- Build pins for the executor image and managed server installation: Pi
  `1.4.0`, `pi-web-access` `0.46.0`. Installed versions still need verification
  on each live target.
- AEGIS: use a test project with repository-installed AEGIS 0.15.
- Live session date: 2026-11-04, resumed from documentation commit
  `a16ffef10b89ebf56a51c3564d86b60f6a58335d`.
- Owner scope: complete jobs use the ChatGPT subscription only. LM Studio is
  limited to connection and a simple response. API-key runs and LM Studio
  end-to-end acceptance remain unexecuted. Linux is available through WSL2.
- Financial cap: none supplied by the owner. The isolated profile sets
  `max_cost_usd = 0`, disabling that cap, and keeps the execution bounds below.
- Live status: the owner completed the isolated ChatGPT sign-in and the Pi
  model/shell probe passed. Both Internet Off and Internet On jobs reached validated candidates. Dedicated timeout, active cancellation and sign-out checks passed.
  Publication remains blocked by the push restriction.
  An em dash in the evidence columns means no observation.

## Live run procedure

1. Use a disposable ADORE home, dedicated test project, test repository and
   least-privilege service account. Confirm the test forge account and repository
   access separately. Have the owner complete ChatGPT sign-in in the isolated
   instance. Keep production and
   ticket #25 outside the session. Confirm the executor image and proxy are
   present for container scenarios. For native targets, run `adore pi install`
   and `adore pi verify` as the isolated service account. Check Windows Job
   ownership or delegated Linux cgroup v2 with `cgroup.kill` as applicable.
2. Run one ticket at a time with monitoring paused. Check host prerequisites
   and use **Test AI connection** to check the model and a shell call. Start
   from **Jobs → Tickets → Start** and verify monitoring stays paused. Use the
   ceilings of 20 launches, 30 minutes of active work, 5 minutes per stage
   and 25 changed files per job. Bound this session to five jobs and 90 minutes.
   Record reported usage and keep unavailable cost explicit.
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

Use one small deterministic change and a focused test per executed row. S04b adds a
pinned dependency download to a disposable environment with a cold cache.
Keep system package elevation disabled for this acceptance.

| ID | Target and credential | Internet | Evidence to collect before approval | Run result | Draft PR/MR | Input/output tokens | Duration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | Container, provider API key | Off | Pi reaches the provider. A controlled unrelated destination outside the effective allowlist is denied. Web tools are absent. | Excluded by owner scope, unexecuted | Blocked by push restriction | — | — |
| S02 | Container, same provider API key | On | Fetch the pinned library from the approved registry, import it and run the focused test. Verify the selected web extension is available. | Excluded by owner scope, unexecuted | Blocked by push restriction | — | — |
| S03 | Container, OpenAI-compatible LM Studio or Ollama endpoint | Off | Pi uses the configured endpoint and model. Reachability is checked inside the job's network boundary. An unrelated destination outside the allowlist is denied. | Excluded by owner scope, unexecuted | Blocked by push restriction | — | — |
| S04 | Container through WSL2, ChatGPT subscription | Off | Complete sign-in and run a stage. Check mount and injection metadata with values suppressed. Only the helper mounts the credential directory. Stage evidence redacts the access token. | Passed through validated candidate, ticket #3 | Blocked by push restriction | 920205 / 16763 | 10m59s |
| S04b | Container through WSL2, ChatGPT subscription | On | Download a pinned user-level library and complete a focused test with the selected web extension. | Passed through validated candidate, ticket #4 | Blocked by push restriction | 1718635 / 24017 | 21m07s |
| S05 | Linux server, provider API key | Host policy | Verify both installed pins, current account, controlled tool PATH and owned cgroup. Use inert personal Pi settings in the dedicated account to confirm isolation. | Excluded by owner scope, unexecuted | Blocked by push restriction | — | — |
| S06 | Windows server, provider API key | Host policy | Verify both installed pins, current account, direct Node launch, PowerShell tool call and owned Job Object. Use inert personal Pi settings in the dedicated account to confirm isolation. | Excluded by owner scope, unexecuted | Blocked by push restriction | — | — |

For S01, S03 and S04, Internet Off uses the effective model allowlist plus any
explicit operator entries. The ChatGPT credential helper uses its own network.
For S05 and S06, the host controls network access.

## Failure scenarios

Use the same isolated project controls and bounds. For timeout and cancellation,
use a disposable ticket that keeps the stage active long enough to observe
abort and process cleanup. Check that the test branch and PR/MR are absent.

| ID | Trigger | Expected evidence | Live result | Input/output tokens | Duration | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | Replace the test provider key with a synthetic invalid value | Credential rejection in the probe and bounded job failure. The value stays out of retained evidence. | Excluded by owner scope, unexecuted | — | — | — |
| F02 | Stop the dedicated test endpoint | Connection failure with the endpoint unavailable. No cloud fallback. | Outside the narrowed LM Studio connection check, unexecuted | — | — | — |
| F03 | Missing ChatGPT sign-in and a separate synthetic expired credential with invalid refresh | Sign-in required prevents the probe. Provider-refused refresh marks the isolated fixture Sign in again. | Passed missing sign-in, disconnect and refresh-refusal checks | 0 model tokens | Refresh rejection 1.34 s | None |
| F04 | Let a stage exceed a short per-stage limit | RPC abort is attempted. ADORE removes a process that survives the grace period and records the timeout. | Passed, ticket #5 | 4445 / 95 | 2m30s | None |
| F05 | Cancel during an active stage | Abort and verified cleanup of the owned scope. Job is cancelled and publishes nothing. | Passed, ticket #6 | 34072 / 784 | 2m14s | None |

## Observed live preparation and connection

- Built separate executor and egress-proxy images from this checkout with bounded
  build commands. The executor reports Node `22.23.4`, Pi `1.4.0` and
  `pi-web-access` `0.46.0`. The older installed executor image was left in place.
- Started the isolated ADORE web instance with a fresh home and one paused
  project. Existing profiles remain separate. The owner completed a renewed
  sign-in flow after closing the first browser window.
  The account's personal Pi reports a stored sign-in, while the ADORE credential
  directory reports `not-signed-in`. Personal Pi credentials were not imported.
- The test repository's remote base is `cb34c08153bce032aaa03a72e37c1e673d46f161`.
  Prepared a local-only fixture with AEGIS 0.15, autopilot enabled and explicit
  review disabled at `e961cf355ec9331140c88fc3ec78db52cd970bbf`. A local bare
  mirror supplies that prepared `main` for run worktrees. Fetching the actual
  forge would restore its older AEGIS, so this fixture setup is part of the
  evidence. Both repository remote push URLs are disabled. Checkpoint
  publication is off and the unique approval label is absent.
- Created four missing acceptance labels through ADORE and test tickets #3–#6.
  Its subtract-helper request has a positive test and invalid-input boundaries.
  The pre-existing test tickets were left untouched.
- L01, LM Studio connection only, reached the selected model through
  `/v1/models`. The first response used 18 input and 40 output tokens, all
  output allocated to reasoning, and had empty answer content. A second,
  bounded request with a 512-token ceiling returned `PI08_OK` in 4.47 seconds
  using 21 input and 340 output tokens, including 317 reasoning tokens.
  Total observed tokens were 39 input and 380 output. The owner supplied 128K
  context. This check did not independently measure the loaded context size.
  This is host HTTP evidence. It does not prove Pi tool calls, container
  reachability or an end-to-end LM Studio job.
- F03, the unauthenticated ADORE model check returned `sign-in-required`.
  A separate synthetic expired credential exercised a real helper refresh
  request and returned `sign-in-again` in 1.34 seconds. The real sign-in
  directory was kept separate from that invalid-credential fixture.
- An isolated container provisioned through ADORE's `ContainerManager` reached
  the model API with Internet Off, receiving HTTP 401 without a credential.
  An unrelated HTTPS destination was denied by the proxy with HTTP 403.
  The fixture's three baseline unittest cases passed in that container.
  ADORE removed the container, proxy and network after the check. These steps
  took 15.84 seconds and used no model tokens.

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
level. The original live server job confirmations belong to S05 and S06 and remain outside the narrowed scope.

| Ticket | Replacement | Evidence and disposition |
| --- | --- | --- |
| #43 | #53 | Qwen removed from execution, setup, connection checks, executor image and Help. Removed configuration fails with remediation. Changelog and four-locale release notes record the single-agent change. Keep closed. |
| #45 | #53 | The local Codex launcher and its account configuration path were removed. The native runtime launches managed Pi. Keep closed. |
| #46 | #53 | ADORE no longer launches OpenCode. Managed Pi gates exclude personal and untrusted project resources, covered by the hostile-configuration fixture in `test_local_execution.py`. Keep closed. |
| #33 | #53, #57 | Case-insensitive removed-prefix checks refuse old settings. Native profiles reject arbitrary local environment overrides and the managed native environment filters forge credentials. `test_config.py` and `test_local_execution.py` cover refusals. Keep closed. |
| #44 | #57 | Managed Pi uses a fresh agent directory and a filtered environment instead of personal Pi settings or sign-in. The native gate fixture and updated local execution guide cover the replacement. Keep closed. Native job confirmation is outside the narrowed scope. |
| #32 | #57 | Native launches resolve managed Node and Pi. Readiness reports missing or incompatible prerequisites. Enrollment has no cgroup or executable picker, and arbitrary local environment overrides are refused. Offline coverage is in `test_pi_installation.py`, `test_local_execution.py` and `local-executors.spec.ts`. Keep closed. Native Windows job acceptance is outside the narrowed scope. |
| #34 | #52 | `test_pi_rpc.py` covers per-turn accounting, large bounded evidence and unreadable usage. The usage journal receives complete counts, and Statistics represents partial or unavailable totals. Keep closed. |

#26 is open and outside PI-08 backlog cleanup. S04b checks a user-level library
download and does not exercise adaptive system package installation.

## Complete ChatGPT job evidence

S04, ticket #3, reached `awaiting-approval` after five launches. The final state update was 659 seconds after creation. The approval-presented event occurred after 646 seconds.
The validated candidate is `a768bcc4c28ba93e66eaf9067b9b230a94ce8aea` and
its recorded fingerprint is
`2e038dc03f52a6a7d3782409e263b6bafe03d5711e7e5b3ddfb8757698001ce4`.
ADORE's final strict verification passed both configured test and lint commands
with zero errors and one unpromoted `fingerprints-tracked` warning for four
sidecars already tracked by the fixture. The candidate is clean and changes
13 files, including four tracked bytecode files inherited from the test
repository. Those generated binary changes are a fixture limitation.
The subtraction helper's public import, ordinary arithmetic and type/finiteness
refusals have unittest coverage. All five stage usage observations report
tokens. The 920205 input tokens include 785152 reported cache-read tokens.
The monetary cost remains unavailable.

The active run mounts exclude the ChatGPT credential directory. The container
creation environment has neither `OPENAI_API_KEY` nor the checked forge token
names. A value-only scan of retained RPC evidence found neither the stored
access token nor the refresh token. This scan establishes absence from retained
evidence. The offline redaction tests exercise echoed secrets explicitly.

S04b, ticket #4, reached `awaiting-approval` after six launches. The final state
update was 1267 seconds after creation. The approval-presented event occurred
after 1250 seconds. The first build attempt reached its 300-second stage limit
and recorded `EXECUTOR_TIMEOUT` with exit 124. ADORE aborted that attempt,
preserved the work and completed build with a fresh launch under the existing
limits. The dedicated timeout check is tracked by acceptance ticket #5.
The validated candidate is `13021f68d6144164e5ad108cc55ea72d991b0f89` and its
fingerprint is
`c24bbe3ad9c7b73710ec84012e09f8b7a6fa8fdc9f09c954c5aae0fc418b8a67`.
Strict verification passed both test and lint with zero errors and the same
tracked-sidecar warning. The clean candidate changes 14 files, including the
fixture's four tracked bytecode files. All six usage observations report tokens.
The 1718635 input tokens include 1508992 reported cache-read tokens. A separate
in-container import printed `26.0` from `/tmp/pi08-packaging`, and the gate
script loads the managed web extension. No repository dependency file changed.

Reported run durations above measure creation to final durable state update.
They include setup, execution, verification and forge notification time.

## Native ChatGPT availability

The owner additionally requested native availability checks on Windows and
WSL2. Both used isolated test configuration and the public configuration
validator. ADORE accepts ChatGPT sign-in only for container projects. The stored
sign-in used successfully by S04 leaves that native restriction in force.

| Check | Product result | Additional native prerequisite observation | Model launch or job |
| --- | --- | --- | --- |
| N01, Windows native ChatGPT | Refused by the container-only sign-in rule | `verify_pi` refuses installed Node `24.15.0`. Managed Pi requires Node `22.23.4` or later in the `22.x` line. | Unexecuted |
| N02, WSL2 native ChatGPT | Refused by the same container-only sign-in rule | `verify_pi` reports the required Node executable missing from the native WSL2 service environment. | Unexecuted |

The initial diagnostic incorrectly attributed the refusal to absent managed
native Pi. TASK-fbe9d636 corrects that explanation to name container-only
ChatGPT sign-in. Fresh Windows and WSL2 `adore config validate` commands both exited 1 with the corrected
message, as expected for this unsupported configuration. The original native API-key scenarios S05 and S06 remain excluded by
the owner's narrowed scope. These availability checks prove neither a native
model response nor a native end-to-end job.

## Timeout, cancellation and final controls

- F04, ticket #5, used one permitted launch and a one-second Pi stage limit.
  Its single attempt ended with `EXECUTOR_TIMEOUT`, exit 124 and retained
  evidence. The RPC archive contains an abort response. The run is `failed`
  as expected for this negative test and its container is stopped.
- F05, ticket #6, was cancelled only after its RPC stream showed `agent_start`.
  The normal web cancellation request was delivered by the worker's watcher.
  The RPC archive contains an abort response and `agent_settled`. The run
  reached `cancelled` after one launch and its container was removed. The queued
  cancellation operation also completed successfully.
- The original isolated ChatGPT sign-in was disconnected through ADORE after
  the job checks. The API then reported `not-signed-in` with no pending flow.
  This completes the real sign-out observation for F03.
- All four isolated project stores remain paused. Both successful jobs retain
  their validated candidates with stopped containers. The timeout evidence is
  retained and the cancelled job has released its container. There are no
  checkpoint-pushed, branch-pushed or MR-opened journal events in these runs.
- A final read-only forge check listed only the pre-existing branch for ticket
  #1 and `main`, plus the pre-existing PR #2 last updated on 2026-09-30.
  No branch or PR for tickets #3–#6 was published. The first final Git read
  returned an authentication error. One bounded noninteractive retry succeeded
  and confirmed the unchanged `main` head. The authenticated forge CLI reads
  succeeded throughout the final check.

## Local correction validation and session close

TASK-fbe9d636 corrected the inaccurate native ChatGPT refusal explanation.
The focused provider/configuration tests passed 97 cases. Two independent
reviewers approved the correction. The complete offline Python suite passed
in 1505.3 seconds and Ruff passed in 2.7 seconds. The strict advisory check
exited 0 with zero errors and 34 unpromoted existing record/path and release-note
coverage warnings. Release-note validation passed with all four locales.
The combined full check was stopped during its serial Chromium phase to keep
this work within the original bounded acceptance session. The frontend reached
browser execution after its helper/type/build checks, but complete browser
regression remains unproven. The correction's time allowance increased from
35 to 45 minutes within the original session limit to finish available proof.

The isolated acceptance API was stopped after sign-out. State, candidates and
sanitized execution evidence remain in the isolated test area. Production and
ticket #25 were outside these operations. The original API-key and LM Studio
end-to-end rows remain unexecuted. Publication acceptance remains unexecuted
under the push restriction, so this record does not close the original #58
acceptance criteria in full.

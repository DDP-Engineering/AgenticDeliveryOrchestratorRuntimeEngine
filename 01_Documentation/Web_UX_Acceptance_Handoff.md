<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web UX acceptance handoff

Prepared 2026-10-06 (Europe/Bucharest) for [epic #3](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/3)
and [W16 / #20](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/20).
**The delivered UI is deployed for human testing; integrated acceptance and epic
completion remain pending.** Initial preparation performed no deployment or live
acceptance. A later human-authorized coordinator deployment and bounded smoke
inspection are recorded below; no participant session, authenticated UI acceptance
or live forge/runtime/executor acceptance is claimed.

## Authority, scope and candidate

The human's autonomous-delivery instruction expressly authorized preparing the
human checklist. Coordinator chat `01a10aec-6ac2-79f3-ada3-741950212fb8` delegated
this standalone documentation to chat `01a11021-03a2-74f1-a6de-c7ae2a32170b`.
Standing human authority permits unattended scope/stage acceptance, review and
scoped normal commit/push/Gitea update **after coordinator acceptance**. This
provenance record does not approve a product definition or replace validation.
This candidate stops before publication for coordinator review.

Frozen scope: this one new operator document; no existing acceptance artifact
was found. It complements the existing guides rather than replacing their
contracts. No product, tests, config, planning, component contract, changelog,
AEGIS journal or issue checkbox changes. Root AGENTS.md excludes standalone
documentation from AEGIS; no implementation workflow is started. No deeper
AGENTS.md was found in the documentation subtree. Bounds: four hours, three
documentation correction cycles, twenty authored files; zero additional paid
executors/APIs/subagents/reviewers. Read-only tracking-forge inspection is the
only external operation performed by this documentation session. It performed no
live forge/container/executor acceptance, real participant session, PR/MR, merge,
release, tag, version bump, force-push or deployment. The initial no-deployment
restriction was subsequently superseded **only for the coordinator's deployment
to the existing DCP host** by a new direct human instruction authorizing SSH
deployment to `192.168.1.15`. That authority does not approve #16's product
decision, #17 implementation, #20 acceptance or any further deployment.
Preserve canonical InfoShare labels; never autoapply ready/agent-approved or
restore removed labels.

Baseline branch: `task/adore-web-interface`; HEAD
`37106ea740884783d4f02e3a3fa690a167cf2259` (W15 journal closeout), following W15
delivery `69979e8892adb923737268c1a885926376c0a89e`. The coordinator independently
verified normal remote publication and clean checkout; local inspection agrees
with that HEAD and a clean initial status. No branch switch occurred.

## Observed deployment smoke evidence

Coordinator chat `01a10aec-6ac2-79f3-ada3-741950212fb8` reported deployment
completed on **2026-10-06 at 10:44 Europe/Bucharest**, under the new direct human
authorization. This section records coordinator-observed evidence relayed to the
documentation session; this session did not repeat SSH or live probes.
Human testing can now use [the deployed UI](https://192.168.1.15:18443).

- Deployed branch `task/adore-web-interface`, exact commit
  `37106ea740884783d4f02e3a3fa690a167cf2259`, without product edits. Git archive of
  `04_Software` and license material has SHA-256
  `424bd7a2abc50e0af511667154a46e40886dd96f5e3e8dd70a2edf0335081677`.
  Source location: `/home/dpasare/apps/adore/web-ux-37106ea/04_Software`.
- Existing runtime, TLS and networking were reused. Both `adore-web.service` and
  `adore-web-worker.service` are active with service-specific PYTHONPATH drop-ins
  named `99-web-ux-37106ea.conf`; actual process environments verify the new
  source, and the worker heartbeat is fresh.
- Preflight on copied DB/profile metadata migrated schema 13 to 14 with integrity
  OK. Services were stopped for a full private ADORE-home tar/DB/unit backup at
  `/home/dpasare/apps/adore/backups/web-ux-37106ea-20261006104419` before switching.
  The deployed script
  `/home/dpasare/apps/adore/web-ux-37106ea/deploy-existing-instance.sh` provides
  failure rollback by moving failed data aside and restoring DB/drop-ins.
  Rollback availability is recorded; no rollback execution is claimed.
- Actual deployed schema 14 integrity is OK; 44 audit rows are preserved, ten
  existing succeeded operations are unchanged, and no queued/running work exists.
- HTTPS `/` and `/projects` return 200. The served index references
  `index-DZ53tnS4.js`; fetched JavaScript bytes match the deployed Git archive.
  Its Git LF-byte SHA-256 is
  `dd9950e857d2e9d3966004ed71712f3387f331cbbc4c2bff7ba9e31c20ce042e`.
  A different working-copy CRLF inventory hash is expected byte normalization,
  not a claim that the remote asset differs from the archived commit.
- Unauthenticated projects/audit API requests return 401
  `authentication_required`. Serving the SPA routes proves availability, not
  authenticated account, project or audit acceptance. TLS smoke inspection used
  the existing certificate with verification disabled only for that inspection;
  it does not establish certificate trust or prescribe disabling verification
  for human use.

No SSH password, credential or private backup content is included. This smoke
evidence establishes deployment availability on this host, not all supported
forge/container/executor combinations. The checklist and novice sessions below
remain prepared and unexecuted; #16/#17/#20 and epic #3 remain pending.

## Delivered work and remaining gates

Live issue bodies/comments and native dependencies were read on 2026-10-06.
#4–#15, #18 and #19 are closed; #16, #17, #20 and epic #3 are open. Native #20
blockers are #8, #10, #12, #13, #15, #17, #18, #19; only #17 remains open.
Native #17 depends on open #16 and closed #14; #16's #4 dependency is closed.
Historical catalogs and the prototype do not override these live gates.

| Issue / work item | Delivery commit | Durable implementation record |
| --- | --- | --- |
| #4 BASE | `705e248` | [Publication report](../00_Planning/2026-10-05_Web_UX_Redesign/PUBLICATION.md) |
| #5 W01 shell | `9da9747` | [TASK-7546e6dc](../.agentic/tasks/TASK-7546e6dc.md) |
| #6 W02 identity/enrollment backend | `132cc3a` | [TASK-8265e125](../.agentic/tasks/TASK-8265e125.md) |
| #7 W03 guided enrollment | `9b81bd0` | [TASK-e30045d4](../.agentic/tasks/TASK-e30045d4.md) |
| #8 W04 exact TOML | `d159ba2` | [TASK-74eebc5c](../.agentic/tasks/TASK-74eebc5c.md) |
| #9 W05 portable export | `8a1bd87` | [TASK-c4655839](../.agentic/tasks/TASK-c4655839.md) |
| #10 W06 portable import/copy | `1d8959a` | [TASK-b93bf854](../.agentic/tasks/TASK-b93bf854.md); session `01a10e4d-f2a8-7663-9d04-986ec8143f80` |
| #11 W07 global job evidence | `54f70d6` | Delivery history in Git and #11; session ID not recorded here |
| #12 W08 hubs/jobs | `5261588` | [TASK-60c83db1](../.agentic/tasks/TASK-60c83db1.md); session `01a10d7b-02e4-7752-81a1-0663a3dbdc97` |
| #13 W09 settings review | `dc51264` | [TASK-6461cd25](../.agentic/tasks/TASK-6461cd25.md) |
| #14 W10 scoped metrics | `0627a78` | [TASK-97d530c5](../.agentic/tasks/TASK-97d530c5.md); session `01a10e8e-198d-7e11-a88d-cba056403dbc` |
| #15 W11 statistics UI | `9b689b6` | [TASK-bb98355e](../.agentic/tasks/TASK-bb98355e.md); session `01a10ee0-fb7a-7b12-b886-0f3149806e27` |
| #16 W12 proposal only | `d38b5b0fc2697cc4eae309f3126146f8045460c2` | [Contract](../00_Planning/2026-10-05_Web_UX_Redesign/Message_Count_Contract.md), [evidence](../00_Planning/2026-10-05_Web_UX_Redesign/Message_Count_Evidence.md); session `01a10f3c-3de9-7201-b5c3-f8fc02f899e3` |
| #18 W14 user/access creation | `ccad687` | [TASK-287ae997](../.agentic/tasks/TASK-287ae997.md) |
| #19 W15 audit evidence | `69979e8` | [TASK-965eaba9](../.agentic/tasks/TASK-965eaba9.md); closeout `37106ea` |

All listed delivery commits are ancestors of the baseline. Sessions omitted from
the table are not inferred; journals/issue records remain the evidence source.
The [approved design brief](../00_Planning/2026-10-05_Web_UX_Redesign/Gitea_Issues/DESIGN_BRIEF.md)
and [illustrative prototype](../00_Planning/2026-10-05_Web_UX_Redesign/Prototip.html)
establish direction, not participant or production acceptance.

The concrete #16 owner decision remains pending: approve or revise separate
executor conversation human + assistant counts, separate tool counts, separate
forge observed/received-external/posted-by-ADORE sets, no mixed total, fresh
retry/revision instances without replay/echo/edit inflation, proven version-pinned
count-only source mappings and 90-day metadata retention. Current OpenCode, Pi,
Codex and Qwen evidence proves no normalized conversation-count contract; forge
comment candidates are partial. Unsupported roles/sources remain unavailable.
The published recommendation is **not approval**. Owner records the decision in
#16; revisions need an explicit amended contract. Only then can authorized #17
implementation proceed. #20 implementation/validation pickup remains blocked
until #17 and its other native gates are complete. The whole epic is not ready.

## Observed technical evidence and nine #20 criteria

The [W15 final strict proof](../.agentic/tasks/TASK-965eaba9.verification.json)
and journal record Python **1145 passed / 1 existing Windows symlink skip**,
**111 Chromium journeys**, **51 Node helper cases**, typecheck, isolated frontend
build and Ruff passing; strict exit 0 / 0 errors. Production build success is
recorded in the W15 journal. Strict reporting retains 12 advisories and 29
unrelated manual notes. Earlier timeout/failure records remain historical;
the final successful full proof is authoritative for that candidate. Browser
global limit was explicitly human-approved at 480 seconds, one worker/no retries;
that approval is not a new allowance for this documentation session.
These suites were **not rerun here** and do not prove future #17 integration,
live infrastructure, novice success, other browser engines or WCAG certification.

| #20 criterion (in issue order) | Honest present status / evidence needed |
| --- | --- |
| 1 Full offline regression and negative trust boundaries | Prior delivered baseline observed above; pending integrated rerun and trust-boundary review after #17 on an agreed exact candidate. |
| 2 4/5 distinguish pickup/clarification in ≤1 minute | Pending real participants; card A. |
| 3 4/5 enroll in ≤10 minutes, no instruction | Pending real participants; card B; infrastructure setup timed separately. |
| 4 4/5 locate approval and understand no merges | Pending real participants; card C. |
| 5 4/5 identify portable inclusions/exclusions/target values | Pending real participants; card D. |
| 6 Every participant reviews before apply and corrects enrollment | Pending all five; cards B/E, recorded per participant. |
| 7 Project/period/timezone consistent; unknown differs from zero | Delivered scoped metrics/helper/E2E evidence; pending integrated #17 series/export and manual card E. |
| 8 Dev cannot bypass restrictions or access finance/admin | Existing server/worker/API/helper/E2E negatives observed in delivered work; pending integrated role/direct-route/API/export recheck. |
| 9 Findings/gaps have reproduction and owner; no fabrication | This report prepares recording; actual findings and manual accessibility outcomes pending. |

After authorized #20 pickup, use its AEGIS implementation validation and agreed
candidate. With dependencies provisioned separately, documented offline commands
are `uv run pytest` and `uv run ruff check .` in `04_Software`, then
`npm run typecheck`, `npm run build`, `npm run validate` in `04_Software/web`.
Record exact commit, environment, exits, counts, skips and retained diagnostics;
do not copy the old numbers as new results. Fixtures simulate external CLI
boundaries; no real forge/git/container/executor work belongs in unit tests.

## Prepared novice session

Human acceptance owner recruits five people unfamiliar with ADORE/AEGIS and
obtains voluntary consent before timing. Explain that evaluation concerns the
interface, allow withdrawal, and collect no name, contact, credential, message
content, screen/audio recording or identifiable quotations. Use anonymous P1–P5
counts/outcomes only. Keep recruitment/consent records outside this result sheet.
Owner confirms an actual retention/deletion policy before collecting results.
Consent is currently not recorded; no participant has been tested.

Infrastructure owner prepares a disposable isolated home, safe repositories,
Admin/Dev/no-grant accounts, deterministic job states, no real recipients or
paid executors, known-zero/unknown/partial measurements, portable JSON and exact
TOML examples. Confirm reset/backup procedure and disable pickup. Record setup
duration independently; it never reduces the participant's enrollment time.
Participants use the production candidate, not the prototype. Facilitator reads
only the task prompt, starts timing when the prepared screen is available,
provides no coaching, hints, glossary lesson or verbal instruction, and records
timeouts/errors/help requests as outcomes. Assistance invalidates uncoached
success. Do not supply the evaluator answer key to participants.

| Card / participant prompt | Evaluator completion rule |
| --- | --- |
| A: “Two projects show Pickup stopped and Waiting for clarification. Explain what each means and where the next action happens.” | ≤60 seconds; stopped pickup prevents new issues, active jobs continue; clarification needs a reply in the repository issue. Threshold ≥4/5. |
| B: “Add the provided repository as a new project. Before creating it, inspect the choices, correct the supplied display-name choice, and finish with pickup stopped.” | ≤600 seconds without instruction, ≥4/5 enrollment; separately require every participant to find review, return to correct, revalidate/review and create the corrected candidate. Use only prepared server clone/target sheet. |
| C: “Find the next action for the job waiting for approval. Show where its candidate is approved, and explain who decides whether the change is merged.” | ≥4/5 locate current candidate-bound forge approval; ADORE can publish a draft MR/PR and never merges; humans decide merge. Record duration, no imposed time threshold. |
| D: “Use the supplied portable settings package for a new target. Explain what carries over, what does not, and what you must provide here.” | ≥4/5 identify working-rule allowlist, host/identity/secrets/history/access exclusions and new target values; record duration and explanation outcome without storing quotations. |
| E: “Inspect a proposed settings change before applying it. Then compare statistics for two projects and two periods/timezones, export the selected view, and explain an unavailable value beside a zero.” | Every participant inspects actual before/after/effect and revision before apply; record scope parity and zero/unknown understanding separately. Safe disposable mutation only; no hidden activation/publication. |

Card D answer key: the 16 polling/readiness/recovery/budget rules transfer under
the exact installed-version portable contract. Identity, forge/repository/branch,
paths, labels/reviewers, models/runtime/images/network/mounts, credentials and
references/endpoints, history/jobs, grants/audit, pending revisions and price
history do not. Target supplies new display name/stable ID, repository identifier,
existing absolute server clone/branch, independent locations, actual runtime/image/
model, reviewers/labels, limits and credential environment names or supported host
auth, and explicitly reconfirms target setup. See [portable guide](Portable_Project_Settings.md).
Exact TOML retains host locations and requires its guarded byte-exact review.

Blank anonymous result sheet (dash means not recorded, never failure or zero):

| ID | Consent confirmed | A seconds / pass | B seconds / pass | C pass | D pass | B correction / review | E pre-apply inspection / scope / zero | Help / timeout count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | — | — | — | — | — | — | — | — |
| P2 | — | — | — | — | — | — | — | — |
| P3 | — | — | — | — | — | — | — | — |
| P4 | — | — | — | — | — | — | — | — |
| P5 | — | — | — | — | — | — | — | — |

Record candidate/environment/date/timezone and aggregate eligible completion
counts. Fewer than five genuine consenting participants leaves the gate pending;
do not silently change the denominator. All five must satisfy review/correction.
Failures require findings/remediation; a human records any accepted shortfall.

## Operator live checklist (prepared, not executed)

Infrastructure owner selects disposable targets and explicitly authorizes each
live probe, its identities, egress, resource/time/cost/file bounds and cleanup.
Setup downloads and infrastructure validation are separate from offline tests and
novice tasks. Do not execute this checklist against the delivery repository or
real participant data. Start API and worker in separate processes only in the
prepared home: from `04_Software`,
`uv run --extra web adore-web --home <ADORE_HOME>` and
`uv run --extra web adore-web-worker --home <ADORE_HOME>`. Default origin is
`http://127.0.0.1:8765`; bind/proxy/TLS changes follow [web guide](Web_Interface.md).
One web worker per home; no concurrent `adore run --loop` scheduler.

| Prepared check / supported entry | Expected observation / owner |
| --- | --- |
| `adore --profile <name> config validate`, `status`, `runs`, `logs <run-id>`; `/api/v1/health`, `/api/v1/ready`, `/admin/status` | Valid config distinguished from verified environment; liveness distinguished from worker readiness. Infrastructure owner records actual versions and failures. |
| `/projects/new` Check environment; guided and exact `/projects/import` | Separately authorize bounded tool/auth/disposable-container/local-model probes. GitLab/GitHub/Gitea via glab/gh/tea; Docker/Podman/WSL-wrapped runtime; OpenCode/Pi/Codex/Qwen supported choices, actual available combinations recorded. Missing combinations remain untested. No automatic cloning; Pi/Qwen host-auth unsupported. |
| Existing local image, clone/AEGIS files, branch, .env, egress open/none/allowlist and optional custom endpoint | Infrastructure owner prepares resources first; secret values stay on host, only allowed environment names pass to executor. No paid proof run. Unavailable/stale/partial/failed checks remain explicit; creation leaves pickup stopped. |
| `/projects/{id}/configuration`; config pending/apply routes | Operator checks meaningful before/after, base/candidate revision, idle/lock/pickup guards, correction/discard, stale revision refusal, unchanged active config after failed apply. Mutation requires authenticated Admin/CSRF; missing/stale CSRF denies. |
| `/jobs?project=<id>&run=<run-id>`, `adore --profile <name> pause`, `handoff <run-id>` | Stopped pickup leaves active work intact; clarification reply versus candidate approval occurs on forge; handoff is separate and preserves evidence. No arbitrary job pause/resume. No merges. Do not apply ready/approval labels automatically. |
| `/admin/users`, `/projects/{id}/access`; `/api/v1/users/with-access`, `/api/v1/projects/{name}/config/portable-settings` | Security owner checks Admin/Dev/no-grant/disabled/revoked sessions, direct URLs/API/export and worker reauthorization; denied users learn no unassigned project/financial/admin metadata. Reviewed creation is atomic on stale grant failure. |
| `/projects/new` portable import/copy; transfer-source/preview/check/create API routes; exact import | Operator checks exclusions/target values, incompatible/duplicate-key/checksum-invalid JSON, stale source/replaced project, exact TOML bytes and failed check. No partial profile or duplicate creation; Back retains corrections and changing source invalidates checks. |
| `/metrics?project=<id>&from=2026-10-06&through=2026-10-06&timezone=Europe%2FBucharest`; `/api/v1/metrics.csv`, `/api/v1/usage.csv`, `/api/v1/projects/{name}/jobs-usage.csv` | Metrics owner compares same project/period/timezone/filter across cards/charts/tables/export; jobs have immutable project+run identity. Local dates become half-open UTC instants including DST. Known zero is measured completeness; null/unknown/partial is not zero. Finance remains Admin-only. #17 message series pending. |
| `/admin/audit`, `/api/v1/audit-page`, `/api/v1/audit-policy` | Security/operator checks redacted actor/resource/before/after, prepare versus applied/rejected/uncertain, legacy “not recorded”, authorized actor/project/action/period paging, explicit retention impact. Never copy passwords/environment/raw errors into evidence. |
| Disposable stopped-service backup/restore and crash/replay fixtures; `adore --profile <name> stats --rebuild` | Recovery owner follows [recovery guide](Recovery_And_Maintenance.md) and web backup guidance; preserve web.db + marker, profiles/state. Corrupt/unsupported identity/audit/run/usage evidence must fail closed, no silent reset. Same valid replay does not duplicate applied audit/usage/notifications; uncertain work is reconciled deliberately, not replayed automatically. Validate retry evidence before retry; do not use destructive reset/delete as a probe. |

API paths above are same-origin authenticated routes, not standalone public URLs.
Payload/CSRF/revision contracts remain in [Web API](../05_SoftwareDocu/Component_Web_API.md),
[identity](../05_SoftwareDocu/Component_Web_Identity.md),
[worker](../05_SoftwareDocu/Component_Web_Worker.md) and [CLI reference](CLI_Reference.md).
Command examples use placeholders that the operator must replace; preparation
does not prove all forge/runtime/executor combinations work on a live host.

## Manual gaps and follow-up recording

Accessibility owner records browser/OS/assistive-tech versions, candidate and
synthetic reproduction evidence. Existing Chromium keyboard/mobile screenshots
are bounded evidence, not a full accessibility audit. These checks are pending:

| Gap/check | Reproduction to perform | Follow-up owner |
| --- | --- | --- |
| Keyboard/focus | Tab/Shift-Tab through shell, menu, forms, review/change/discard, dialogs and direct-link/reload; verify visible focus, logical order, no trap and restoration after close/error. | Accessibility owner |
| Screen reader/status/errors | Named fields/buttons/headings; trigger validation, async loading/success/error, stale review and unknown measurements; check announcements and error-to-field association with actual screen reader. | Accessibility owner |
| Contrast | Measure text, controls, focus indicators and chart distinctions in light/dark, including error/disabled states; target WCAG 2.2 AA with measured values. | Accessibility owner |
| Mobile/zoom/charts/tables | 390px and 200% zoom; long IDs, four locales, menus, review, imports, audit and statistics; verify reflow, readable scrolling/table alternatives and usable target sizes. | UX owner |
| Novice usability and integrated/live gaps | Repeat relevant card or checklist step on exact candidate; capture anonymous count/outcome and sanitized reproduction, not participant identity/content. | Acceptance owner / infrastructure owner |

Each actual finding gets ID, candidate, preconditions, numbered reproduction,
expected/observed result, sanitized evidence path, severity, named human owner,
follow-up issue and retest outcome. No actual finding or success is recorded yet.
Unassigned owner roles must be allocated by the coordinator before evaluation;
never infer a person's acceptance from a role label.

## Documentation review and handoff

Two separate same-agent lenses checked this document: criterion/scope coverage
and source/command/evidence accuracy. These are not independent reviewers.
Coverage retains all nine pending criteria, five task cards and human/live gates;
accuracy separates existing proof from future integration and preserves the #16
decision. One bounded documentation revision added the coordinator's scoped
deployment authority and smoke evidence, explicitly attributed to that source;
it did not repeat live tests or alter earlier technical proof. Both same-agent
lenses were repeated for this revised candidate. Link/commit/route/header/whitespace checks and the exact one-file hash
are reported with the frozen candidate to the coordinator. Software suites are
not needed for this standalone document and were not run.

Coordinator reviews this exact candidate before authorizing scoped publication
under standing human authority. Keep #16/#17/#20/epic open and criteria unchanged.
After genuine #16 decision and delivered #17, separately authorize #20 pickup,
freeze its integrated candidate, run full offline proof, arrange five participants
and authorized live checks, assign/retest findings and record actual limitations.

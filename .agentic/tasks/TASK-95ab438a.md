<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-95ab438a - Preserve native Git repository discovery inside executor containers

stage: deliver
type: fix
path: full
interaction: autopilot
requirements: REQ-FUNC-0d0625e1, REQ-REL-e1ecfbd5, REQ-REL-b8c5946a
parent:
branch: task/adore-web-interface
base: 7a588905de14d68503d47a6321b0e9c3b1114d32
opened: 2026-10-30

Before editing this journal, read `.agentic/templates/task.md` for record syntax
and pause/report rules. Reuse its guidance if already read in this intact session.

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: OBSERVED: build_container_env in isolation.py injects repository-selection GIT_DIR/GIT_COMMON_DIR/GIT_WORK_TREE into every descendant. The live container run for issue 25 reported a temporary Git fixture resolving to /adore/work and creating unintended workspace commit 700dc2b.
Desired outcome: STATED: correct ADORE generically for diverse repositories; INFERRED restoration: native Git discovery selects the actual requested repository, including independent temporary repositories, while the mounted linked worktree remains usable.
Actors: Operator, coding executor, repository tests and subprocesses, container runtime, host conductor.
Primary scenario: A repository test creates and commits in a temporary repository -> Git selects that repository -> the managed worktree HEAD/index remain unchanged.
Examples: OBSERVED: issue 25 release-note fixture used git -C under /tmp but reached /adore/work; INFERRED acceptance: an isolated temporary repository receives its own commit and the main linked worktree remains clean.
Counterexamples: Explicit -C and nested repository operations must not be rebound to the ADORE worktree. Corrupt binding metadata must not silently select another repository.
In scope: Common container Git binding, runtime/file trust boundaries, offline tests, generic real Docker acceptance, component/operator documentation and user-visible release/help wording where applicable.
Out of scope: Azure implementation owned by the running issue 25 task; completed issue 26 candidate; automatic container replacement, history rewriting, final PR publication or merge; unrelated pre-existing checkout changes.
Constraints: STATED: forge/executor agnostic, portable Python, preserve authorized progress, offline fake CLI unit tests, license/style/docs rules, autopilot=true and human publication approval. OBSERVED: resource/image/policy identities are pinned for package-enabled runs.
Success signals: Managed worktree Git succeeds; independent/nested repositories honor native selection and do not change main HEAD/index; failed or corrupt runtime/file inputs raise IsolationError; existing owned resources are preserved.
Evidence: STATED user asks generic ADORE corrections and completion of issue 25. OBSERVED isolation.py build_container_env/provision, live task journal and 1503 focused passing cases after repository fixtures use offline doubles. INFERRED global bindings explain the unintended Git target. UNKNOWN exact safe rollout mechanism until design and controlled runtime verification.
Assumptions: No new provider-specific behavior or host tool installation is needed; validate this technical expectation during design.
Unknowns: Exact filesystem binding and legacy-container rollout details; custom image environment behavior; authoritative runtime failure receipts.
Decision-blocking questions: None: repair native repository selection within the authorized generic correction scope, while preserving existing run data and publication authority.
Proposed behaviors: Proposed implementation: container-visible Git pointer overlay rather than inherited repository-selection variables; retain the original host pointer and pinned resources. Settle mechanics in design with runtime evidence.
Path and reason: full; environment and runtime binding contracts change and require explicit trust-boundary and recovery design.

| Quick-path criterion | Result | Evidence |
|---|---|---|
| no new externally observable behavior | yes | restores native repository selection required by generic execution |
| no new interface or data format | no | container binding metadata/representation will change |
| no new dependency | unknown | verify runtime mechanism during design |
| existing requirement covers the behavior | unknown | inspect isolation requirements during specify |
| no security/data-handling change | no | repository-selection trust boundary changes |

Bound: at most 8 implementation iterations, 4 hours of active correction work, 30 scoped files; preserve unrelated changes and report any required extension before using it. Independent reviews use the configured bounded review loop.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary/failure | Verification | Design |
|---|---|---|---|---|---|---|
| Native independent Git | Fresh Git context uses ordinary discovery | REQ-FUNC-0d0625e1 | main and independent repos | no inherited selection override | public provision/exec fake tests plus controlled Docker | pointer overlay |
| Fail closed | Reject invalid binding evidence | REQ-REL-e1ecfbd5 | exact evidence accepted | corrupt paths/files/receipts rejected | public provision negative tests | bounded metadata and acknowledgement |
| Preserve progress | Reuse creation-time mode and resource | REQ-REL-b8c5946a | running/stopped old and new modes | no implicit replacement; corrupt mode rejected | public reuse tests | versioned label and compatibility |

Behavior inventory: operator/executor tests trigger native discovery; container manager admits exact context or reports typed failure; recovery retains owned resource identity and contents. Pointer and environment mechanisms are inseparable parts of the single discovery outcome; corruption and reuse responses are independently specified. Existing generic isolation/egress contracts are retained without weakening.

## Design

- D1 / REQ-FUNC-0d0625e1: ContainerManager owns a per-run IO pointer file mounted read-only at /adore/work/.git. Native Git and both host/worktree administration pointers stay otherwise unchanged. build_container_env remains metadata transport; provision/exec filter its three Git-selection keys instead of forwarding them to agent descendants.
- D2 / REQ-REL-e1ecfbd5: Validate exact managed Git metadata and one safe admin component; exclusive pointer creation rejects links, nonregular files and byte mismatches. Source pointer data remains outside the candidate worktree and carries no comment because Git's data format forbids it.
- D3 / REQ-FUNC-0d0625e1: Fresh container creation clears image/runtime selection variables. Sanitize the runtime process environment case-insensitively. Docker bare unsets were observed locally; standard Podman prefixes use documented --unsetenv. Preserve all unrelated env, secret transport, identity, egress and package permissions.
- D4 / REQ-REL-e1ecfbd5: Creation-mode label io.ddp.adore.git-binding=pointer-v1 distinguishes the new binding. Warm provision reads only that label through bounded JSON inspect. A fixed in-container shell check confirms absent selection variables, the expected pointer and native main worktree discovery with one exact acknowledgement; timeout, nonzero exit or wrong receipt is IsolationError. No secret environment dump occurs.
- D5 / REQ-REL-b8c5946a: Preserve running/stopped owned containers and their exact filesystem/mounts. Empty/null label retains historical mode; new-mode evidence is mandatory; unknown label fails closed. Existing containers are never replaced to retrofit mounts. Historical containers retain the historical Git limitation until normal release; document this compatibility boundary explicitly.
- Data/lifecycle: the IO pointer and creation label belong to container provisioning. Initial run failure retains exact pointer data for idempotent retry. Cancel/delete retain existing resource/IO cleanup ownership. State schema and public provision results remain unchanged.
- Ordering: authoritative status, metadata admission, mode/evidence checks, optional start or fresh create, then exact confirmation for new mode. The conductor's existing lock serializes one run. New-mode corruption is reported rather than repaired or downgraded.
- Security: no host Git pointer edit, host settings change, new host mount root, credential exposure, elevated agent UID, egress change or automatic package installation. Read-only overlay is a child of the existing worktree mount, sourced from existing IO authority.
- Test seams: public ContainerManager.provision/exec with injectable runners and temporary files; parameterized Docker/Podman/WSL and corrupt metadata/receipts; existing isolation, execution, preparation, launcher and package contracts are regression targets. Manual disposable Docker/Git acceptance exercises independent and nested repositories without touching live issue 25.
- Alternatives: global GIT variables reproduce the incident; a Git wrapper would have to reinterpret -C/init/clone/submodule semantics; rewriting the host pointer would couple host/container path topologies; automatic resource replacement would discard installed dependencies and violate pinning. A native pointer overlay avoids these costs.
- Expected files: isolation.py; test_isolation.py or focused test_container_git.py; Component_Isolation.md; Operations_Guide.md; execution help in four locales when relevant; CHANGELOG.md; release_notes.toml; isolation knowledge and affected context. No change is planned to managed AEGIS or the issue 25 checkout.
- Risks: read-only file-mount support and actual linked-worktree discovery require live Docker verification. Podman argument semantics are covered offline and by official documentation; no installed Podman runtime is claimed. Legacy containers preserve a known rollout limitation.
- Open decisions: none requiring user input. If actual runtime evidence invalidates the overlay, revise design before implementation.
- Diagrams: [diagram_TASK-95ab438a.md](diagram_TASK-95ab438a.md).

- D6 / REQ-FUNC-0d0625e1: normalize supported WSL container command prefixes to --exec (preserve an existing -e/--exec). Replace an explicit -- boundary or insert before the known Docker/Podman executable. A nonstandard WSL wrapper requires an explicit command boundary; reject an ambiguous prefix rather than reinterpret data. This correction follows the observed default-shell expansion in controlled acceptance.

## Log

- 2026-10-30 frame: full-path generic Git-discovery correction accepted under existing user authority; autopilot override recorded; preserve the live run and completed issue 26 snapshot. New binding/recovery mechanics require specify/design before implementation.

- 2026-10-30 specify: created three atomic draft contracts and shared protocol; no retirements or changed existing contracts. Docker image-default unset behavior and legacy label formatting were observed without network/credentials; temporary probe image removed.

- 2026-10-30 design: pointer-overlay protocol selected; retain legacy creation mode rather than replacing pinned resources. Public provision/exec negatives and a disposable real Docker/Git acceptance are required before final proof.

- 2026-10-30 build red: REQ-FUNC-0d0625e1, REQ-REL-e1ecfbd5 and REQ-REL-b8c5946a share public provision/exec admission; command=`.\.venv\Scripts\python.exe -m pytest -q tests/test_container_git.py --tb=line` from 04_Software; exit=1; 32 expected failures: missing pointer overlay, globally forwarded selectors, absent metadata/receipt rejection and unverified warm mode. No implementation edit preceded this observation.

- 2026-10-30 build: anchor captured 525 Git-visible files before implementation. The three linked public binding contracts pass their initial 32-case focused run; source/fixture compatibility verification and controlled native Git acceptance follow.

- 2026-10-30 DEVIATION build: controlled Docker acceptance failed closed before admission because WSL default-shell transport expanded checker substitutions on the WSL host. Disposable resources were removed. Extend the common runtime prefix normalization to direct --exec; user configuration and container identity stay unchanged.
- 2026-10-30 build red: command=`.\.venv\Scripts\python.exe -m pytest -q tests/test_container_git.py -k direct_argv --tb=short` from 04_Software; exit=1; two default-shell WSL prefixes lack direct argv transport while two explicit direct forms pass. This refines REQ-FUNC-0d0625e1 transport and REQ-REL-e1ecfbd5 confirmation reliability.

- 2026-10-30 DEVIATION build: replace two pre-existing real-Git release-note test fixtures in this checkout with injected read-only Git doubles before full proof, as the repository offline unit-test rule requires. Existing warning/no-warning and untracked-file assertions are retained; no checker product behavior is changed.
- 2026-10-30 build green: focused isolation/execution/package contracts exit 0: 187 passed, 1 existing skip, 1 upstream warning. Controlled WSL Docker acceptance passed independent and nested commits, unchanged main/host pointer/HEAD/index, read-only overlay, UID1000, selectors absent and same-ID running/stopped reuse under network none; disposable container, volumes and fixture removed.

- 2026-10-30 build green: combined Git/isolation/execution/package/release-note tests exit 0: 217 passed, 1 existing skip, 1 upstream warning; Ruff passes. Release-note checker against fe20f6b exits 0. release-notes: updated (merge related command/Git fixes within the ten-entry cap). help: updated (custom WSL command boundary, all four executor topics).

- 2026-10-30 build red: semantic boundary review found Unicode C1 control input accepted by the metadata constructor; `.\.venv\Scripts\python.exe -m pytest -q tests/test_container_git.py -k invalid_admin --tb=line` exited 1 (one failure, nine rejection controls passed). Extend the established control-character admission guard without changing valid names.

- 2026-10-30 build complete: current consolidated focused proof exits 0 (218 passed, 1 existing skip, 1 upstream warning); Ruff, 10 help tests, production build and release-note checks pass. A second controlled Docker proof with spaces, Unicode and shell characters in the host path also preserves independent commits and same-ID warm reuse; temporary resources removed. Generated help assets are included in the scoped candidate. Advisory errors=0; relevant help coverage links reconciled, historical unrelated findings remain outside scope.

- 2026-10-30 validate review round 1: both independent verdicts changes_required; binding 80680afea31dcc18c653a42c96b1919228aca42790b3e46617604dcb2c73daff verified before/after, 24 path hashes intact. Recorded findings: WSL distribution/user/directory operands are mistaken for executables or transport markers, and a distribution named podman selects the wrong CLI dialect. Return to build under authorized autopilot, repair only those boundaries with public fake-runner regressions. No full proof ran; no approvals are retained during candidate changes.

- 2026-10-30 build red / REQ-FUNC-0d0625e1: command=`.\.venv\Scripts\python.exe -m pytest -q tests/test_container_git.py -k "wsl_options or wsl_incomplete or runtime_transport" --tb=line` (04_Software); exit=1; 11 failed, 7 passed: option operands/wrapper markers are reinterpreted, incomplete prefixes are admitted and Docker receives Podman flags. These are the recorded round 1 findings; public regressions were written before the parser correction.

- 2026-10-30 build green / round 1 corrections: public WSL prefix parsing now consumes documented launch-option operands before the command boundary; wrapper arguments stay literal and only the selected executable controls Docker/Podman flags. Consolidated focused command exits 0: 233 passed, 1 existing skip, 1 upstream warning; Ruff passes. Requirement links, shared spec and component contract updated. No new component or unrelated correction.

- 2026-10-30 validate preparation: semantic scope/error/portability review and requirement re-read completed; context and owning knowledge remain current. Repeat controlled Docker acceptance on the corrected parser with --cd /tmp and the special host path passes independent/nested commits, exact main/host state, no selectors, UID1000 and same-ID warm running/stopped reuse; cleanup complete. No additional manual runtime or cloud claim. Both review roles are repeated on a new binding before final proof.

- 2026-10-30 validate review round 2: specification compliance approved; implementation quality approved. Both independent reviewers verified all 24 bound paths and canonical/actual binding ee9c62d2a99d32b82dd50c5f65f91a2bc3c0234ba065c2cf0f41d771ae9a6031 before/after; quality additionally observed 54 focused cases passed. No remaining findings or candidate edits. Coordinator rechecked the same binding before final proof.

- 2026-10-30 validate: initial configured full check completed but its capture wrapper exits 1 while rendering Unicode on the Windows console, so consolidated Python/lint receipts are not recorded. Current Playwright artifacts show three failures: host-folder error alert absent, narrow keyboard job timeout and job-reset ECONNRESET. No green final proof is claimed. Candidate binding remains unchanged; diagnose those cases and repeat the full check with explicit UTF-8 capture. Both round 2 source verdicts remain current until a candidate edit.

- 2026-10-30 validation envelope: all three problematic browser cases pass unchanged in targeted reruns (two cases exit 0 in 17.0 s, model-failed case exit 0 in 5.2 s). The initial full Playwright record is timedout with unfinished cases. Increase its finite global budget from 1200 to 1800 seconds; individual test/assertion/action limits and zero retries are unchanged. This verification-only candidate edit clears both round 2 verdicts; consume round 3 after configuration inspection, then repeat full proof with UTF-8 capture. No product requirement or assertion is weakened.

- 2026-10-30 validate review round 3: quality approved; specification changes_required for two stale owning verification descriptions (1200 seconds and ten minutes). All 25 bound hashes verified intact before/after both reviews. Correct only those documentation findings; clear both verdicts and consume round 4 afterward. DEVIATION validate: extend the scoped file bound from 28 to 30 for owning web component/knowledge documentation and the eventual delivery record; required documentation consistency justifies the extension, within existing user authority for generic ADORE corrections.

- 2026-10-30 validate review round 4: both independent verdicts approved, no remaining findings. Both before/after bindings and 27 actual hashes match 429505b5dfc07639dcd80a8190814da1e7ae0b1b2c0239dcaaa3fc2f359c3228; coordinator confirms before proof. Extend active correction bound from 3 to 4 hours before the replacement full invocation to cover the observed verification cost and documented envelope adjustment, under existing user budget-increase authority. All individual assertions and deadlines remain unchanged.

- 2026-10-30 validate complete: final configured `python .agentic/aegis.py check --task TASK-95ab438a --strict --run --json` exits 0 in 1604.14 seconds: 2207 Python passed, 8 existing skips, 1 upstream Starlette/httpx deprecation; Ruff passes; all 226 Chromium cases pass. Strict errors=0, warnings=181, notes=22, promoted warnings=0. Relevant findings are resolved; remaining advisories are established repository history/coverage debt outside this scoped correction. All 27 hashes and canonical binding 429505b5dfc07639dcd80a8190814da1e7ae0b1b2c0239dcaaa3fc2f359c3228 match the round4 approved candidate. Initial incomplete/capture-failed proof is superseded, not claimed green.

- 2026-10-30 deliver preparation: reread delivery instructions after final proof. Freeze only the 27 bound paths plus this journal, manifest and delivery record against fe20f6b; exclude the separate timeout task and unrelated checkout work. Newly discovered correction requires a concrete local delivery decision; previous approval covered issue26 and archive correction. Preserve an immutable Git tree while continuing independently authorized issue25/timeout work; no commit, push, PR or merge is performed here.

- 2026-10-30 DEVIATION validate (discovered during delivery inspection): the configured legacy full suite also executed setup/deployment-script tests despite the current user instruction excluding them. This was an unrequested verification-scope expansion, not a new product defect or skipped product proof. The observed all-green counts remain factual and include those legacy cases; no host installation was performed by their injected doubles. Do not repeat those tests. Future verification selects permitted product tests, with setup scripts inspected manually. No source, test, requirement or specification is changed here; the bound source and current review verdicts remain intact.

- 2026-10-30 correction to preceding deviation record: direct source inspection disproves the inference about this checkout. Its test_web_package.py contains only third-party notice consistency, with no installer behavior; references to release/asset metadata checkers likewise are not setup execution. The installer tests were observed in the older AppData issue25 checkout, not in this validated root suite. Withdraw the incorrectly attributed root verification-scope deviation; factual full-proof counts and source bindings remain unchanged. The issue25 operator handoff will align that separate checkout with the current explicit user rules before its final verification.

## Rulings

- RULING-001 | date=2026-10-30 | decision=Use autopilot for the generic ADORE correction; preserve human publication approval and the active issue 25 resource | reason=User explicitly requested autopilot and generic corrections while finishing the real run | source=user | supersedes=none

## Handoff

current: deliver
status: waiting
next: Approve a local commit of the frozen Git correction
must_read: .agentic/tasks/TASK-95ab438a.md, .agentic/tasks/delivery_TASK-95ab438a.md, .agentic/tasks/TASK-95ab438a.candidate.json, .agentic/steps/6_deliver.md
blockers: Explicit approval for the newly discovered local delivery

## Stage report

stage: deliver
result: paused
current: deliver
changed: Native Git isolation, WSL transport, offline fixtures, owning docs/help and finite browser envelope; delivery records updated
evidence: 2207 Python passed, 8 skips; Ruff passed; 226 Chromium passed; strict exit0; 27 hashes unchanged; both round4 reviews approved
issues: 181 nonpromoted advisories,22 notes,1 upstream warning; no live Podman claim; legacy Git mode persists
next: Approve a local commit of the frozen Git correction
needs_user: yes
spec_compliance: approved
implementation_quality: approved
review_round: 4

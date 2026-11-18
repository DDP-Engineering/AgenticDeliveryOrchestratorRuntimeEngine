# Repository review report - ADORE at cdecfcca (0.19.0 in preparation)

Status: review completed on 2026-11-17. Read-only: no product file was changed, no test,
container or exploit was run. Remediation started the same day; see section 2.1.
Requested: 2026-11-17 - code review of the current ADORE repository, including documentation
errors and an analysis of secrets in the repository and its Git history.
Companion: [remediation plan for C1 and H1-H3](2026-11-17_Isolation_Boundary_Remediation_Plan_cdecfcca_0.19.0-wip.md).

This report describes unremediated security defects. Treat it as internal until they are fixed.

## 1. Analysed state and method

| Item | Value |
|---|---|
| Branch | `master`, equal to `origin/master` (one remote, a self-hosted Gitea) |
| Base commit | `cdecfcca98df2bd5447f9b9419cf2e869e382906` (2026-11-17 04:30 +02:00, ADORE 0.18.0) |
| Working tree | Uncommitted changes that prepare ADORE 0.19.0: 77 changed paths at 04:35, 96 at 05:02, 99 at 05:17 (+02:00). Someone else was changing the tree during the review |
| Reviewed content | The working tree as on disk between 04:35 and 05:00, not `HEAD` |
| Size | 1583 tracked files; about 44 000 lines of Python in `04_Software/adore`; 139 frontend source files; about 75 documents |
| History | 576 commits on all refs; 888 with the local reflog; tags `v0.15.0`, `v0.17.0`, `v0.18.0`; one stash |

Method:

- Nine delegated reviewers read the source in parallel, one area each. They had no tool that
  can write or run anything. Each returned findings with file, line and a quoted line.
- The lead reviewer ran the secret scans directly and re-read the source for the findings
  that matter most.
- Line numbers are from the working tree. These cited files carried uncommitted changes, so
  their numbers differ from `HEAD`: `adore/orchestrator.py`, `aegis.py`, `config.py`,
  `wizard.py`, `state.py`, `forge_labels.py`, `prompts.py`, `README.md`, `CHANGELOG.md`,
  `Configuration_Reference.md`, `Getting_Started.md`, the five touched component documents
  and the frontend copy and help files.

Reading the findings:

- **Verification.** `V` = the lead reviewer re-read the cited code and confirmed the fact.
  `A` = reported by a delegated reviewer from the source, not re-read by the lead.
  `plausible` = the code fact is established but the consequence was not fully traced.
- **Severity.** `critical` = code execution outside the intended boundary. `high` = loss of a
  security property or of data under realistic conditions. `medium` = wrong behaviour or a
  weakened control. `low` = minor defect, stale text or hygiene.
- **Paths.** `adore/` is `04_Software/adore/`; `web/src/` is `04_Software/web/src/`;
  `tests/` is `04_Software/tests/`.
- **"Verified as sound" lists.** They record what the delegated reviewers checked and found
  correct, with their evidence. The lead re-read only the items also cited in a finding.
- No exploit was reproduced. Every attack description is derived from the code.

## 2. Summary

- **No real credential is in the tracked files, in the reachable Git history, in the local
  reflog or in any archive ever committed.** Every match is an obvious test value.
- **A plaintext SSH password sits in an untracked local file**, kept out of Git only by the
  developer's global ignore file (SEC-1).
- **Employer identifiers are still in the pushed history**, in five July commits and in old
  binary files that the earlier text-only history rewrite could not reach (SEC-3).
- **A run container can make the host execute code** (C1). Two routes exist; the simpler
  one needs no Git knowledge.
- **Three further isolation defects** let an agent read host files through a link (H1),
  rewrite its own egress allowlist (H2) and run without privilege or resource limits (H3).
- **The web interface ships a fully privileged `admin`/`admin` account** that the server
  never forces to change its password (WEB-1).
- **The removal of the quick-label feature is clean** in code, tests, documentation, the four
  help locales and the built bundle.
- **Documentation is mostly accurate.** The security claims that were checked match the
  code. The errors found are stale statements, missing configuration keys and garbled characters.

185 findings. Each cell is "verified by the lead / reported only":

| Area | Critical | High | Medium | Low |
|---|---|---|---|---|
| Secrets and sensitive data | 0 | 1 / 0 | 2 / 0 | 5 / 0 |
| Isolation and executor | 1 / 0 | 3 / 0 | 3 / 5 | 2 / 3 |
| Web backend | 0 | 1 / 0 | 3 / 5 | 2 / 15 |
| Orchestrator and state | 0 | 0 | 5 / 4 | 3 / 6 |
| Forge, configuration, CLI | 0 | 0 | 2 / 5 | 3 / 14 |
| Frontend | 0 | 0 | 0 / 6 | 2 / 6 |
| User documentation | 0 | 0 | 3 / 0 | 6 / 8 |
| Component documentation | 0 | 0 | 3 / 6 | 0 / 4 |
| Tooling | 0 | 0 | 4 / 2 | 0 / 11 |
| Tests and dependencies | 0 | 0 | 0 / 12 | 0 / 11 |
| Repository hygiene | 0 | 0 | 1 / 0 | 6 / 1 |
| **Total** | **1 / 0** | **5 / 0** | **26 / 45** | **29 / 79** |

Suggested order of work is in section 15.

### 2.1 Remediation status

Updated 2026-11-18. The first changes were committed on `master` as `f77db636` (on top of
`3ec545f3`, ADORE 0.19.0). Rows marked "second commit" are in `738db488`, rows marked
"third commit" in `20850cd1` and rows marked "fourth commit" in `8494669d`. Rows marked
"fifth commit" are in the commit `Release ADORE 0.20.0`, which also cuts that version. It
sits on top of `9488298c`, a change from outside this remediation that was merged from
`origin/master`. Rows marked "sixth commit" are in the commit that follows `271dfd6d`
(ADORE 0.21.0, cut outside this remediation) and ships with that version. No real
container, forge or service installer was exercised.

Final checks, on the tree of the fifth commit before the version cut:

- Full Python suite: 3942 passed, 31 skipped, none failed. A first run had three failures,
  all in tests that `9488298c` left behind: two cases of
  `tests/test_preparation_lifecycle.py` expected a changed project setting to stop a
  prepared job, which that commit changes on purpose, and one test of
  `tests/test_run_concurrency.py` hooked the backend instance the engine was created with,
  while a job now runs on a backend built from its saved settings. The three tests pass on
  `8494669d` and fail on `9488298c` without any change of this remediation. They were
  brought in line with the new behaviour; resource and evidence drift is still refused.
- Frontend: 193 unit tests passed; both type checks clean; the web bundle was rebuilt and
  holds every message added in this remediation.
- `ruff` clean on `adore` and `tests`. `02_Tools/package/tests/test_delivery_package.py`,
  which covers the portable launcher and the packager: 9 passed, 2 skipped.
- After the version cut: `set_version.py --check` and the release notes check pass; the
  modules that read the version or the notes, with the packaging tests: 121 passed,
  2 skipped. The full suite was not run again after the cut.

The full Python suite ran once, on the tree of the second commit: 3927 passed, 30 skipped,
1 failed. The failure was the replay of captured AEGIS commands, which pins the old form of
the task-creation command (ORC-15). The new form was then run against the real AEGIS 0.16.1
command line in a temporary copy: a one-word title such as `-hotfix` prints the help text in
the old form and creates the task in the new one. The test was brought in line and its
module passes; the full suite was not run again after that one-file change. The frontend
unit tests gave 189 passed and the type check is clean.

| Finding | State | What changed | Proof |
|---|---|---|---|
| C1, route B | Remediated | Run containers mount only the clone's `.git` at `/adore/repo/.git`; the checkout is not mounted. The binding label is `pointer-v2`, so a container of an earlier build is refused. A `.git` that is a file, link or reparse point is refused before creation | `tests/test_isolation.py`, `test_container_git.py`, `test_drift_recovery.py`, `test_container_timeout.py`: 337 passed, 7 skipped; three related modules: 97 passed |
| C1, route A | Open by decision | Not implemented. Making `.git` read-only in the container was declined on 2026-11-17: the risk that Git stops working inside the container was judged too high without a real-container trial | - |
| ORC-1 | Remediated | The `Authorization` rule redacts the scheme word and the credential, also for a JSON-printed header; a bare `bearer <credential>` is redacted too | Three new cases in `test_no_stage_progress_evidence_carries_the_stderr_tail` |
| ORC-3 | Remediated | A run that raises `StateError` or `IsolationError` during reconciliation is logged, named in `summary["reconcile_failed"]` and left untouched. Later runs are reconciled and admission continues | Three tests in `tests/test_orchestrator.py`; six modules that reach reconciliation: 595 passed, 9 skipped |
| ORC-2 | Remediated | On the AEGIS path a failed target integration that already failed the run returns instead of launching the executor again | `test_failed_target_integration_does_not_launch_the_executor_again` |
| ORC-4 | Remediated | An admission that fails after its worktree was created removes that worktree and branch before reporting the failure | Assertion added to `test_claim_selects_worktree_workflow_before_first_save` |
| FRG-1 | Remediated | The Azure scope loop in the wizard no longer reuses the name that holds the host OS | `test_wizard_azure_scope_answers_do_not_replace_the_host_os` |
| FRG-2 | Remediated | One list, `FORGE_CREDENTIAL_ENV` in `adore/config.py`, feeds both the `env_keys` refusal and the scrubbing of forge CLI environments; the refusal ignores letter case. DOC-10 is corrected with it | `test_executor_cannot_receive_any_forge_cli_credential` |
| WEB-3 | Remediated | A request body above its bound is refused with 413 `request_too_large` before it is buffered: 64 KiB for sign-in and own-password requests, about 26 MiB elsewhere; a body without a declared length is counted as it arrives. Own-password values are limited to 1024 characters | Three tests in `tests/test_web_auth.py` |
| WEB-4 | Remediated | Ended sign-in failure windows are deleted when a failure is recorded; expired sessions are deleted when a session is created | `test_ended_login_failure_windows_and_expired_sessions_are_removed` |
| FRG-8 | Remediated | The generated configuration names `adore init NAME --force` | Assertion added to `test_wizard_writes_a_valid_minimal_profile` |
| DOC-1, DOC-2, DOC-3 | Corrected | README no longer says web enrollment needs AEGIS; the configuration reference lists the `[worktree]` keys, the `develop` default, `publish_checkpoints` and `metrics.enabled`; the garbled arrows in `Local_Execution.md` are restored | - |
| H1 | Remediated | One reader, `read_agent_file` in `adore/util.py`, refuses a link, a second name of another file, a non-file and an oversized file. The questions file (conductor and launcher) and the AEGIS exchange output use it; the refusal names neither the target nor its content | `tests/test_util.py`, `test_hard_linked_questions_file_is_never_posted`, one AEGIS exchange test |
| WEB-2 | Remediated | Queued configuration requests store no cookie and no CSRF token. The worker hands transfer handlers the actor it rechecked; stored headers are never replayed, also for records of an earlier build | Assertion added to the retained-request test; `tests/test_web_transfer.py` passes unchanged |
| WEB-5 | Remediated (one part) | `reserve_login` checks the limit and counts the attempt in one transaction before the password check. One client can still try one password against many user names | Two tests in `tests/test_web_auth.py`; they also close TEST-3 |
| DOC-4, DOC-5, DOC-7, DOC-8, DOC-11, DOC-12, DOC-16 (spacing), CMP-2 to CMP-8, CMP-10, CMP-11, FRG-9, ORC-12 | Corrected | Stale or wrong statements replaced after each fact was re-checked in code | - |
| ISO-1 | Remediated | Host writes into the run IO directory (gate script, model and web-search files, AEGIS script, session recording) go through `write_agent_file` / `open_agent_file_for_write` in `adore/util.py`, which refuse a link or a second name of another file. The archived gate script is read with the safe reader | `tests/test_util.py` |
| ORC-9 | Remediated (main cause) | Restart probes the repository workflow before it deletes the stopped job and returns `workflow_unavailable` instead. A forge error while relabelling after the deletion is still possible | `test_restart_workflow_refusal_precedes_destructive_cleanup` |
| WEB-5 | Remediated | A second window counts one client across all user names: 30 unsuccessful attempts in ten minutes; successful sign-ins do not count | Two more tests in `tests/test_web_auth.py` |
| FRG-3, FRG-5 | Remediated | `validate_config` reports a section given as a single value and turns a wrong-type failure into an issue; the CLI reports a wrong type met while loading. `load_config` itself still raises on a wrong-type agent name, because job details rely on that to mark a configuration corrupt | `tests/test_config.py`, `tests/test_smoke.py` |
| ORC-5 | Remediated, second commit | The pipeline verdict is recorded as handled only after an automatic repair holds its execution slot; at capacity nothing is recorded and the next poll tries again | `test_failed_pipeline_repair_waits_for_capacity_instead_of_being_dropped`; `tests/test_orchestrator.py`: 356 passed, 10 skipped |
| WEB-10 | Remediated in part, second commit | Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: same-origin`; API answers carry `Cache-Control: no-store` unless the route sets its own. No `Content-Security-Policy` yet: it needs a check of the built page first | `test_every_response_carries_browser_protections` |
| TOOL-1 | Remediated, second commit, not run | The package export keeps the lock's hashes and dependencies are installed with `--require-hashes`; the project wheel is installed in a separate step. The packaging itself was not run | Compile and lint only |
| TOOL-2 | Remediated, second commit, not run | The Linux installer refuses to start as root or through `sudo` unless `ADORE_USER` is set explicitly; uninstall is unaffected | Shell syntax check only |
| TOOL-4 | Remediated, second commit, not run | In `-Mode once` the scheduled task ends a pass after `-PassTimeLimitHours` (default 24); `-Mode loop` stays unlimited | PowerShell parse check only |
| ORC-6 | Remediated, second commit | The instance lock is written to a draft file and published with a hard link, so no reader sees it empty | `test_lock_is_published_whole_and_leaves_no_draft` |
| ORC-7 | Remediated, second commit | A held execution slot is retried four times (0.05 to 0.4 s) before the error is raised | `test_execution_slot_waits_for_a_briefly_held_slot`, `test_execution_slot_gives_up_after_bounded_waits` |
| ORC-11 | Remediated, second commit | The incident text says "no further launch" | `tests/test_orchestrator.py`: 358 passed, 10 skipped |
| ORC-13 | Remediated, second commit | The deletion audit store is built in a draft file and published complete | `test_audit_store_is_published_whole_and_reopens` |
| ORC-14 | Remediated, second commit | A platform error in the poll log passes `_sanitize` | Read only; no dedicated test |
| ORC-16 | Remediated in part, second commit | The unused constant and the unused template argument are removed. `_claim_and_conduct` stays: two tests use it and removing it is a test rewrite with no product gain | `tests/test_cli_deletion_audit.py`, `tests/test_prompts.py` |
| ORC-17 | Remediated, second commit | A refused rotation no longer loses the line; the log grows past its bound and rotates on a later line | `test_process_log_keeps_writing_when_rotation_is_refused` |
| WEB-8 | Remediated in part, second commit | Recovery reads only the process rows of active owners. Ended rows are still never deleted | `tests/test_web_ownership.py`, `tests/test_web_supervisor.py`, `tests/test_web_audit_evidence.py` |
| WEB-9 | Remediated, second commit | The child time limit is the project wall-clock budget plus one hour, never less than six hours | `test_child_time_limit_follows_the_project_budget` |
| WEB-13 | Remediated, second commit | The failure text of a retry passes `redact_text` before it is stored | `tests/test_web_commands.py` |
| WEB-14 | Remediated, second commit | Keys with the `sk-` prefix are masked. Other bare key formats still pass | `test_redact_text_masks_url_credentials_and_forge_tokens` |
| FRG-11 | Remediated, second commit | The class docstring now calls the four settings reserved, as the configuration reference already did. The settings stay inert | Read only |
| FRG-12 | Remediated, second commit | A malformed branch template asks again | `test_wizard_reprompts_on_malformed_branch_template` |
| FRG-13 | Remediated, second commit | The TOML fallback escapes control characters | `test_toml_string_keeps_a_multi_line_answer_valid` |
| FRG-15 | Remediated, second commit | The remote probe has a 30 second timeout and sets `GIT_TERMINAL_PROMPT=0` | `test_detect_push_access_never_waits_on_a_credential_prompt` |
| FRG-17 | No change needed in part | GitHub: the caller treats every state other than opened as absent, so a closed pull request is harmless. Gitea: still open; it needs a branch template that renders digits only | Read of the publish path in `orchestrator.py` |
| FRG-18 | Remediated, second commit | With `draft = False` the `WIP:` prefix is removed from the title | `test_gitea_open_pr_title_prefix_edges_and_missing_url` |
| FRG-19 | Open | Not changed: the thread status accepted on creation needs a live Azure check, which needs operator authorization | - |
| FRG-20 | Remediated in part, second commit | The docstring states the bound of 500. No failure was added, so a large repository is not blocked | Read only |
| FRG-23 | Remediated, second commit | The branch for per-agent tables is removed; such a table is refused as unknown structure | `test_portable_omits_recognized_nested_secrets_and_rejects_unknown_source` |
| FRG-24 | Remediated, second commit | Both module docstrings are complete sentences | Read only |
| FE-1 | Remediated, second commit | Every request reports an ended session through one event; the interface confirms with one `/me` call and then shows the sign-in form | Type check and bundle build; the expiry path was not exercised against a running server |
| FE-3 | Remediated, second commit | An error boundary shows a reload prompt in the page language | Sign-in page renders through the boundary in the dev server; the fallback itself was not triggered |
| FE-7 | Remediated, second commit | The sentence is present in French, German and Romanian | Frontend unit tests: 189 passed |
| FE-8 | Remediated, second commit | The four help pages list the Tickets tab | `tests/help.test.mjs` |
| FE-12 | Open by decision | Not changed: the value backs the redirect of older addresses to the summary tab | - |
| TEST-3 | Remediated with WEB-3 | The route test exists | `test_sign_in_route_limits_wrong_passwords_and_recovers_after_success` |
| FRG-4, WEB-7, WEB-25 | Open | Not changed: each is a rewrite of a working path (Azure reads, audit retention, the consistent job snapshot) for a performance gain only | - |
| TEST-2, TEST-6 to TEST-10, TEST-13, TEST-14, TEST-16 | Open | Not changed: test refactors or dependency changes with no product effect | - |
| FRG-6 | Remediated, second commit | Every lifecycle and control label must be non-empty and distinct from the others. Selection labels are not checked, so existing configurations with unused priorities keep loading | `test_validation_rejects_empty_and_repeated_role_labels` |
| FRG-14 | Remediated, second commit | `create`, `rename` and the wizard refuse a name with a separator, a drive colon, `.` or `..`. Existing names in other letter cases stay valid | `test_profile_names_that_are_paths_are_refused`, `test_wizard_refuses_a_profile_name_that_is_a_path` |
| FRG-21 | Remediated, second commit | Quiet hours must be clock times; `24:00` stays valid | `test_validation_checks_quiet_hours_are_real_times` |
| FRG-22 | Remediated, second commit | The `.env` reader removes one matching pair of quotes only | `test_load_env_file_removes_one_matching_quote_pair_only` |
| ORC-10 | Remediated, second commit | The apostrophe is plain ASCII in the prompt and in the test baseline | `tests/test_prompts.py` |
| ORC-15 | Remediated, second commit | The title follows `--` in the AEGIS command | `test_task_title_that_starts_with_a_dash_is_not_read_as_an_option`; both forms run against real AEGIS 0.16.1 in a temporary copy |
| WEB-12 | Remediated, second commit | An unknown or disabled name spends one hash check against a decoy hash | `test_unknown_and_disabled_names_spend_one_password_check` |
| WEB-22 | Remediated, second commit | An OS error from the zone lookup is an invalid time zone | `test_timezone_key_that_names_a_directory_is_refused_as_invalid` |
| FE-2 | Remediated, second commit | The private view is still cleared; a sign-out the server did not confirm is shown on the sign-in page | Type check and bundle build only |
| FE-4 | Remediated, second commit | Storage reads and writes are guarded | Sign-in page checked in the dev server with storage available; blocked storage not exercised |
| FE-9 | Remediated, second commit | The Romanian paragraph matches the other three locales | `tests/help.test.mjs` |
| FE-10 | Open by design | Not changed: `readJob` fails closed at the transport boundary on purpose | - |
| FE-11 | Open | Not changed: the same loader serves the reread after a save, where keeping old values would show stale settings. It needs a check against a running server | - |
| FE-13 | Remediated, second commit | A 401 without a readable body is reported as an ended session | Type check and bundle build only |
| CMP-9 | Remediated, second commit | The component document names both defaults: 20 for the CLI, 12 for a web request | Read only |
| DOC-14 | Remediated, second commit | The Azure example sets `env_keys = []` | `tests/test_config.py` |
| DOC-15 | No change needed | In the portable package `User_Guide.md` is shipped as `README.md`, so the link is right where these two guides are read | `01_Documentation/README.md` |
| DOC-16 | Remediated, second commit | The component document is a link. The mode text already read "POSIX 0600" | Read only |
| DEP-1 | Remediated, second commit | `npm audit` confirmed the advisory range 7.0.0 to 7.3.6. vite is 7.3.7 and source-map-js 1.2.2; the audit reports no vulnerability | Frontend unit tests: 189 passed; bundle rebuilt; dev server starts |
| TOOL-3 | Open by decision | Not implemented: service hardening could stop ADORE or the executor from writing where they must, and that risk was declined on 2026-11-17 | - |
| TOOL-7 | Remediated, third commit | The old version is replaced only where it stands alone, not inside a longer number | For 0.19.0 the six text sources and five presentations give the same result as the plain replacement; no release was cut |
| TOOL-8 | Remediated in part, third commit | A rewritten file keeps the mode of the file it replaces. Files are still replaced one at a time; a failed run is undone with Git | Compile only |
| TOOL-9 | Remediated, third commit | A stop record that cannot be read is logged and removed and no longer ends the launcher; the owner record is created with mode 0600 | Compile only; the portable package was not built or run |
| TOOL-10 | Remediated, third commit | A service group that already ended, or that outlives the forced kill, no longer keeps the other service from being stopped | Compile only |
| TOOL-12 | Remediated, third commit | `--service` refuses a checkout path with a space, a pipe, an ampersand, a percent sign, a backslash or a quote before the unit is written | Guard exercised in WSL with 11 paths; installer not run |
| TOOL-13 | Remediated, third commit | The installer warns when `.env` grants any group or other permission. It does not change the file and does not stop | Probe exercised in WSL for modes 600, 640 and 604; installer not run |
| TOOL-15 | Remediated, third commit | The hint names the uv installation page | Shell syntax check |
| TOOL-16 | Remediated in part, third commit | The package checksum is computed from a stream. A missing checksum file is still accepted by the release check | Compile only |
| TEST-1, TEST-4 | Remediated in part, third commit | An automatic fixture points Git at an empty global configuration and disables the system one. The tests still run real `git`, and `HOME`, `USERPROFILE`, `APPDATA` and `XDG_*` are not redirected | The three modules that run `git` and fifteen other modules pass (766 passed, 13 skipped); full suite not run |
| TEST-5 | Remediated in part, third commit | The absence assertion in `tests/test_config.py` is removed. The AEGIS and state cases stay, as they are fail-closed checks | `tests/test_config.py` |
| TEST-11 | Remediated, third commit | The test expects 403, the answer of the administrator check | `tests/test_forge_labels.py` |
| TEST-12 | Remediated, third commit | The project has priced usage before the developer reads its metrics; the test checks the token total and the absence of money fields | `tests/test_web_rbac.py` |
| TEST-15 | Remediated, third commit | The ten direct SQLite connections in the two modules are closed | `tests/test_web_server.py`, `tests/test_web_rbac.py` |
| TEST-17 | Remediated, third commit, not exercised on Windows | The link test uses the `symlink_support` fixture instead of a platform skip. On this Windows account links cannot be created, so the test was skipped | `tests/test_host_folders.py`: 12 passed, 1 skipped |
| TEST-18 | Remediated, third commit | The fixture imports the store module itself, so the first web test of a worker uses the fast hasher too | `tests/test_web_auth.py` |
| DEP-2 | Remediated, third commit | The web extra declares `starlette` and `pydantic` and takes FastAPI 0.141 as its lower bound. `uv lock` changed the project's own metadata only; no locked version moved | Lock diff: 5 lines added, 1 removed |
| DEP-3 | No change | The same suppressions stand on reviewed process calls in product code, so they are a repository convention. Enabling the rule would flag every process call | - |
| DEP-4 | Remediated in part, third commit | `package.json` and its lock state the Node releases vite 7 supports. Exact and caret pins are still mixed | `npm ci --dry-run` |
| WEB-6 | Open by decision, documented, third commit | Confirmed in code for `container.run_args` and `workflow.aegis_python`: import checks the form of the file only, and the dialog shows the project name only. `workflow.verify_command` is no longer a setting, and the absolute paths are required by import and shown for review. Kept as it is on 2026-11-17: an administrator who imports is trusted like the server operator. `01_Documentation/Web_Interface.md` now says so | Read only |
| ORC-8 | Remediated in part, third commit | Comments enter a prompt through the new fragment `review/discussion.md`: a heading per comment names its author, every line is quoted, and the text says they are discussion written by people, not ADORE instructions. An automatic repair round no longer reads the MR/PR comments; a revision requested with the label still does. Not changed: there is no filter on the author's role, and the ticket title and description stay unfenced because they are the order itself. The effect on a real model was not measured | `test_forge_discussion_is_quoted_under_author_headings`, two changed tests; `tests/test_orchestrator.py` and `tests/test_prompts.py`: 453 passed, 10 skipped; five related modules: 170 passed |
| FRG-7 | Documented by decision, third commit | Confirmed in code: on Windows ADORE sets and checks no access restriction. The default home is `%APPDATA%\adore`, inside the user profile. No code was changed: an automatic restriction could remove the access of the account that runs the service. `01_Documentation/Security_And_Credentials.md` now has a section with the command that lists who can open the home and the command that restricts it. On the review machine the default home also lists a local sandbox group and two more accounts with read access, added by other software, so the profile location alone is not proof | Both commands were run on a throwaway folder: three entries remain and the files inside inherit them |
| FE-5 | Remediated, fourth commit | The wait between two questions starts at 150 ms and grows by half each time up to 2 seconds. Up to three unreachable-server answers in a row are retried and the fourth is reported as `network_error`; an unreadable or unexpected answer is the coded error `unexpected_response`. No pause was added for a hidden page: browsers already slow its timers. The 61-minute limit is unchanged | Three new tests in `tests/configurationTasks.test.mjs`; frontend unit tests: 192 passed; type check and bundle build pass; not exercised against a running server |
| FE-6 | Remediated, fourth commit | Measured first: of the 111 settings of the default configuration, 52 were named by a help sentence in each of the three languages (median 91 characters in Romanian). Each now has a short name in French, German and Romanian, and three key patterns (container environment, task type per ticket label, stage time limit) build theirs. Measured again: none is left, apart from three priority labels whose short name equals a short help sentence. The French and German names were not reviewed by a native speaker | New test in `tests/settingHelp.test.mjs`; frontend unit tests: 193 passed; type check and bundle build pass; not viewed in a running interface |
| WEB-15 | Remediated, fourth commit | One project may have at most 256 start, retry and restart operations pending or running; a further new one is refused with 409 `operation_queue_full`. A replayed idempotency key still returns its operation, each project has its own count, and cancel is never counted or refused. Duplicate requests for one job are not merged. The interface has the message in four languages; its bundle is not rebuilt yet | `test_full_job_queue_refuses_new_work_but_never_a_cancel`; `tests/test_web_errors.py`: 7 passed; `tests/errors.test.mjs`: 6 passed |
| WEB-16 | Remediated, fourth commit | At most two branch previews run at once on a server; a further one is refused at once with 429 `branch_preview_busy` and holds no server thread. The limit is on the web route only: the same check at job admission and in configuration validation is unchanged. There is no per-user limit. The interface has the message in four languages; its bundle is not rebuilt yet | `test_previews_beyond_two_at_once_are_refused_at_once_and_then_served`; `tests/test_web_branch_naming.py`: 11 passed; `tests/errors.test.mjs`: 6 passed |
| WEB-17 | Documented by decision, fourth commit | Confirmed in code: a developer's configuration response carries the server paths of the project and, for local execution, the account and machine; only the cost cap and the configuration file path are withheld. Kept as it is on 2026-11-17. `01_Documentation/Web_Interface.md` now says what a developer reads | Read only |
| WEB-18 | No change by decision | Confirmed in code: `GET /api/v1/chatgpt-sign-in` ends a finished sign-in attempt and writes an audit row, and the statistics reads bring the usage projection up to date. The session cookie is set with `SameSite=Strict`, so a request started from another site arrives without it and is refused. The first route does what the administrator's own page does every few seconds; the second is repeatable upkeep. Left as it is on 2026-11-17 | Read only |
| WEB-19 | No change by decision | Not reachable through the shipped entry point: `adore-web` refuses any bind address but loopback (`adore/web/server.py`), so a proxy on another host cannot connect, and forwarded headers are trusted from loopback, so a proxy or tunnel on the same host yields the HTTPS scheme and the `Secure` flag. A launcher of the operator's own that binds elsewhere is outside this guarantee | Read only |
| WEB-20 | No change by decision | True for the supervising process only. The engine child keeps a heartbeat of its own and checks its ownership before every external command (`adore/web/worker_context.py`), so a child that lost its place stops at its next effect. The supervising heartbeat gives up after one failed write, so stopping the child on that signal would end a running job on a momentary store error. Left as it is on 2026-11-17 | Read only |
| WEB-21 | Remediated, fifth commit | The supervising process of a run or of a poll reads the exit code only, so the engine's output goes nowhere instead of into memory; the engine writes its own log beside the job (`adore/cli.py`). Start and retry commands keep their output, because their result is read from it | `test_engine_runner_can_drop_the_output_of_a_long_job`; the runner tests of `tests/test_web_commands.py`: 11 passed. The call in `adore/web/supervisor.py` itself has no test |
| WEB-23 | Reclassified, help clarified, fifth commit | Not a defect: `.agentic/specs/scoped-metrics.md`, under active requirement REQ-FUNC-930e3ae0, specifies that cost efficiency uses period usage for jobs whose done event is in scope, and `05_SoftwareDocu/Component_Metrics.md` says the same. A change to the whole cost of the job was made and taken back on 2026-11-17 when the specification was found. What the reader lacked was the definition: the statistics help now states it in four languages, and a test fixes the rule for a job that crosses the start of the period | `test_cost_per_completed_job_counts_period_usage_across_the_period_start`; `tests/test_web_metrics.py`: 37 passed; `tests/help.test.mjs`: 12 passed |
| WEB-24 | No change by decision | Measured: 3000 additions with a total of 312.30 USD leave an error of about 5e-12 USD. The screen formats money to two decimals, so nothing shows there; a CSV export can carry a value such as `312.29999999999546`. No specification fixes a precision. Left as it is on 2026-11-17 | Measurement only |
| WEB-11 | Documented by decision, fifth commit | Confirmed in code: SQLite creates `web.db` under the process umask and nothing sets a mode, while the token file is written for its owner only. No specification fixes a mode. Kept as it is on 2026-11-17. `01_Documentation/Security_And_Credentials.md` now has a section that says what the file holds and how to close and check the ADORE home on Linux | Read only |
| ORC-18 | Reclassified, documented, fifth commit | Not a defect: `01_Documentation/Container_Preparation.md` says that a job with a preparation recipe is pinned to the recipe's commit and that a changed target needs a new selection and review. True as reported that the target-moved checks then compare the commit with itself. The guide now states the consequence: later target commits are not merged into the job and do not cancel its validation or approval | Read only |
| FRG-10 | Reclassified, docstring corrected, fifth commit | Not a defect: `01_Documentation/Azure_DevOps_Services.md` says that a deleted Work Item cannot be told from a denied one through `az` and is an explicit forge failure. The contract in `adore/forge/base.py` now names that exception | Read only |
| FRG-16 | Remediated in part, fifth commit | Azure: the environment report of `adore init` ran the access check before the organization and project were known, so it always printed `[CHECK] az auth`; it now prints that Azure access is verified with them later. Gitea: no change needed, because the only caller without a configured login is the same report, before any login is configured, and `detect_all` has no caller | Assertions added to `test_wizard_azure_scope_answers_do_not_replace_the_host_os`; `tests/test_wizard.py`: 30 passed |
| DOC-9 | Remediated in part, fifth commit | The license comment is removed from `00_Planning/README.md` and from the two plans of 2026-11-15. `04_Software/.env.example` keeps its comment: it is a configuration template, not a document. Banners inside file examples in the guides are part of the example | Read only |
| DOC-13 | Remediated, fifth commit | A comment above each of the three values says that it is an example, what to put there and what happens when the value stays. The values are unchanged, because the tests read this file | Seven test modules that edit the example's text: 272 passed |
| CMP-13 | Remediated, fifth commit | Each of the nine modules is named in the document of the component it belongs to, with what it does as read in its code: three in `Component_Web_API.md`, one each in `Component_Web_Jobs.md`, `Component_Executor_Launcher.md`, `Component_Worker_Processes.md`, `Component_CLI.md`, `Component_Orchestrator.md` and `Component_Configuration_Worker.md` | Every module name now matches a component document |
| DOC-6 | No change by decision | Half of the finding does not hold: "0.14.0" in the text is the AEGIS release, and ADORE skips version numbers (0.9 to 0.13, 0.13 to 0.15). The repeated headings in the 0.15.0 section are real (6, 5 and 5), but the section is close to a thousand lines of a published release; merging them would rearrange history for appearance only | Counted with a script |
| DOC-17 | Open by decision | Writing Markdown sources for the five presentations is content work and a process decision, not a correction | - |
| CMP-12 | No change by decision | Rearranging 48 documents into the template's headings would not change what a reader learns | - |
| H2 | Remediated in part, fifth commit | A proxy that exists but is not running is removed and created again from an allowlist written at that moment; it is never started on the file as found. The file is written through `write_agent_file`, and a link or a second name of another file in place of the file or its directory is refused. The file still lies in the run IO directory: the move to a host-only directory of the isolation plan (WP3) was not made, because it changes what a reused proxy is checked for. Not exercised on a real container | Three new tests in `tests/test_isolation.py`; the six modules that reach the proxy: 397 passed, 8 skipped. The link test is skipped on this Windows account; the hard-link test runs |
| H3, ISO-9 | Documented by decision, fifth commit | Not changed: default hardening flags could stop the agent from working, the risk declined for C1 route A. `01_Documentation/Security_And_Credentials.md` now shows the options an operator can set in `[container] run_args`, and says that package mode accepts resource limits only. `--init` among them answers ISO-9 | Read only; the options were not tried on a container |
| ISO-2 | No change, by requirement | REQ-SEC-19b768d6 admits IP entries by destination address and its verification lists `::1`; a rule that denies loopback targets would contradict it. Port limits would break allowlisted private endpoints on custom ports, a supported case | Read only |
| ISO-5 | No change, documented | `01_Documentation/Security_And_Credentials.md` says that agent-produced text may hold sensitive values and that the recorded session keeps the literal text with restricted visibility | Read only |
| ISO-6 | No change, by design | A job keeps the execution policy saved at admission, which holds the container and executor settings with the network mode (`execution_policy` in `adore/preparation.py`, restored by `adore/job_configuration.py`). A reused container belongs to a job whose network mode has not changed | Read only |
| ISO-8 | No change by decision | The cache volume names stand in the operator's file and the web cannot edit them; the same trust decision as WEB-6 | Read only |
| ISO-13 | No change, by design | A model endpoint over plain HTTP is a supported case for a model on the local network | Read only |
| ISO-10, ISO-11 | No change | ISO-10: tampering is detected and the job fails closed, so the effect is refusal only; it would move with the WP3 change. ISO-11: values passed as environment are part of how the container runtime works | Read only |
| ISO-3 | Open by decision | Image digests and the way `uv` is installed are supply-chain choices for the owner | - |
| ISO-4 | Documented by decision, sixth commit | Not a defect: REQ-FUNC-c405688e and the security guide give the opted-in agent root inside its own container. Since `9488298c` that mode has a deny-by-default seccomp policy, an AppArmor profile that fails closed when absent, and a validation that accepts resource limits and `--userns=keep-id` only. Still true: default capabilities and, on a rootful runtime, no user namespace. The guide already said that root can modify all writable mounts; it now also names the two effects on the host (root-owned files that ADORE's account cannot remove, set-user-ID files) and that rootless Podman with `--userns=keep-id` avoids them. Mounting with `nosuid` was not done: it changes every container start and needs a real container | Read only; nothing was tried on a container |
| ISO-12 | Remediated, sixth commit, not run on a container | Confirmed in code: after a timed-out session the launcher already stopped the container (`settle_timeout`), but not after a protocol failure. A session that started and ended in a protocol failure now goes the same way: the container is stopped and starts again with the next command. Nothing is stopped when Pi never started, when the container is no longer running or is no longer the admitted one. An interruption that cannot be confirmed is refused as after a timeout. Native local execution is unchanged | `test_pi_rpc_protocol_failure_settles_a_running_container` (five cases), `test_pi_rpc_protocol_failure_refuses_an_unconfirmed_interruption`; four modules: 140 passed |
| WEB-1 | Reclassified | Not a defect: active requirement REQ-UX-178abcf8 specifies a reminder, not a forced change. It stays a product decision to revisit | - |

Consequences to know:

- Containers created by an earlier build are refused for reuse and for cleanup. Finish or
  cancel active jobs before using the new build; remove leftovers with the container runtime.
- The link case of the new `.git` check is skipped on a Windows account that cannot create
  symbolic links.
- A damaged run still counts toward `max_concurrent_runs`. With the default of 1 it keeps
  the only slot until the operator resolves it.
- Second batch (ORC-2, ORC-4, FRG-1, FRG-2): eight affected test modules, 725 passed, 9 skipped.
- Third batch (WEB-3, WEB-4, FRG-8, DOC-1 to DOC-3): all 42 web test modules and the wizard
  tests, 1314 passed, 4 skipped.
- The web interface had no translated text for `request_too_large`; the second commit adds
  it in the four languages.
- Fourth batch (H1, WEB-2, WEB-5, documentation): all web modules plus eleven modules that
  touch the changed code, 2128 passed, 15 skipped. The link cases are skipped on this
  Windows account; the hard-link cases run everywhere.
- H1 covers host reads only. The host still writes fixed file names in the agent-writable
  IO directory with plain `open` (ISO-1).
- Documentation findings left as they are: DOC-6 (release history stays intact by rule),
  DOC-9 (banners), DOC-13 (example content), DOC-15 (link is right inside the package),
  DOC-17, CMP-12 and CMP-13. DOC-14 and CMP-9 were corrected in the second commit.
- Fifth batch (ISO-1, ORC-9, WEB-5, FRG-3, FRG-5): the first run of all web modules plus
  twenty related modules gave 2507 passed, 2 failed. One failure was a regression of this
  batch and was corrected; the other, `test_parent_crash_quiesces_tree_and_preserves_uncertain_claim`,
  passes when run alone. The confirming rerun gave 2510 passed, 17 skipped, and the
  linter is clean.
- Neither the CLI nor the web interface reads `reconcile_failed` yet; the log is the only
  place that shows the error text.
- With route A open, C1 stays critical for any project whose ticket or repository text
  comes from an untrusted author.

## 3. Secrets and sensitive data

### 3.1 Scans performed

| Scope | How | Result |
|---|---|---|
| Tracked files (1583) | `git grep` for AWS, GitHub, GitLab, OpenAI/Anthropic, Google, Slack, npm/PyPI and Azure token formats, private-key blocks, JWTs, credential-bearing URLs, `Bearer`/`Basic` literals and generic `password/secret/token/api_key = "..."` assignments | Test values only |
| Reachable history | Every added line of `git log --all -p`: 576 commits, 681 360 lines, same patterns | Test values only |
| Local reflog | Same scan with `--reflog`: 888 commits, 929 829 lines | No credential; see SEC-4 |
| Archives ever committed | 117 zip, tar.gz and pptx blobs opened in memory; member names and text members checked | No credential, no `config.toml`, `.env`, auth file or database |
| File names ever committed | 2360 distinct paths checked for key, certificate, environment, database and credential names | See SEC-3 |
| Untracked files | `.claude/`, `.codex/`, `.vera/` inspected | See SEC-1, SEC-2 |
| Recorded fixtures | 11 Pi RPC session recordings under `tests/fixtures/pi_rpc/` | Sanitized |

Test values that matched and are harmless: `tests/test_web_jobs.py:806-812` (fabricated
GitHub and GitLab tokens used as redaction inputs), `tests/test_model_connection.py:112`,
private-key headers followed by the word "fixture" in three test modules, and placeholder
URLs such as `https://user:password@forge.example`.

### 3.2 Findings

- **SEC-1** (high, V) `.claude/settings.local.json` - The permission allowlist records a
  shell command that prints an SSH password in clear, next to the account, the LAN address
  of the target host and an employer hostname. The file is untracked and was never committed
  (zero matches in reachable history and reflog). It is ignored only by the developer's
  global Git ignore file, not by the repository. The value also appeared in the output of
  this review session. *Direction:* rotate the password; ignore `.claude/` in the repository.
- **SEC-2** (medium, V) `.gitignore` - `.claude/launch.json` and `.vera/` (an 80 MB database
  and 936 cache files) are untracked and not ignored. `git add -A` would commit them.
- **SEC-3** (medium, V) Git history, pushed to `origin` - Employer identifiers remain after
  the earlier rewrite that replaced the employer's domain in text:
  - the employer's GitLab project path and a reviewer login, in commits `50626975`,
    `9850ac31`, `f7c9822c`, `3b33d733` and `059ed91b` (files `04_Software/config.toml`,
    `config.example.toml`, the wizard module under the earlier package name and three
    documents; see line 20 of `04_Software/config.toml` in `9850ac31`);
  - the employer's name in the slides of five old presentations, the `.pptx` files under
    `01_Documentation/Operator_Cheat_Sheets/Presentations/` whose names carry the earlier
    product acronym;
  - the employer's domain inside the two runtime archives of release 0.3.0 under
    `07_Delivery/` (`.zip` and `.tar.gz`), named with the earlier product name.
  The earlier names are not spelled here: the release check refuses them in any tracked
  text file.
  A text replacement cannot reach compressed blobs. *Direction:* decide whether the history
  will ever leave the private forge; if so, remove these paths and strings with a history
  rewrite, force-push, then expire the reflog.
- **SEC-4** (low, V) Local reflog - 312 commits reachable only from the reflog still hold
  the strings the rewrite removed (in `.agentic/specs/REQ-SEC-553ebd62.md`,
  `tests/test_isolation.py`, `04_Software/config.toml` and planning documents). They are
  never pushed, but they travel with any copy of the folder.
- **SEC-5** (low, V) Personal and infrastructure data in tracked files:
  - the developer's full name and forge login in `tests/test_forge.py:497` and about 20
    other test lines;
  - the real LAN address and port of the Gitea server in `tests/test_repository_source.py:23`;
  - a real-looking LAN address (192.168.1.20) used as the example endpoint in
    `adore/wizard.py:542`, `adore/isolation.py:2355`, `Configuration_Reference.md:125`,
    `Component_Config.md:194` and the help text of all four locales;
  - a personal e-mail address in `LICENSE.txt` and as the author of 436 commits. This looks
    intended; it is listed for completeness.
  *Direction:* use documentation addresses (192.0.2.0/24) and `example` hostnames.
- **SEC-6** (low, V) `tests/fixtures/pi_rpc/*.jsonl` - Recordings of real OpenAI sessions.
  Key hints and paths are replaced by `<REDACTED_KEY_HINT>` and `<REDACTED_PATH>`. Response
  identifiers (`resp_...`) and session UUIDs remain; they are not credentials.
- **SEC-7** (low, V) `07_Delivery/_technical/reports/simple-setup-config-write-failure-trace.zip`
  (history only) - A Playwright trace that contains a Windows user profile path.
- **SEC-8** (low, V) `04_Software/.env` exists locally (705 bytes), is ignored correctly and
  was never committed. Its values were not read.

### 3.3 Not scanned

- `01_Documentation/Setup_And_Credentials.pdf` (history only; its Markdown source was scanned).
- The content of `.vera/vera.db` and the values in `04_Software/.env`.
- Objects that no ref and no reflog entry reaches (`git count-objects` reports
  100 prune-packable objects and 1.51 GiB of temporary pack files).

## 4. Isolation and executor

The container boundary is the main security control: the agent acts on untrusted ticket text
and runs repository code.

### 4.1 Findings

- **C1** (critical, V) `adore/isolation.py:1864`, `:1225`, `:1304`, `:1325`;
  `adore/orchestrator.py:1257-1269`, `:385` - Every run container gets the whole project
  clone, including `.git`, mounted read-write at `/adore/repo`.
  - Route A: the host then runs Git on that clone and its worktrees (`add`, `commit`,
    `merge`, `status`, `diff`, `fetch`, `push`). No call disables hooks or other
    command-bearing Git settings, and `scrub_container_worktree_config` (`:1229-1277`)
    removes only one key. An agent that writes a hook or a Git setting gets code executed
    by the host account, which holds the forge login.
  - Route B: every poll runs `<aegis_python> .agentic/aegis.py --version` on the host with
    the clone as working directory. The agent overwrites that file in the mounted checkout.
  Concurrent runs of one project share the same `.git`, so one run can also alter another.
  *Status 2026-11-17:* route B remediated; route A open by decision (section 2.1).
- **H1** (high, V) `adore/orchestrator.py:3578-3586`; `adore/executor/launcher.py:345`, `:529`;
  `adore/aegis.py:513` - The host reads agent-written files with calls that follow links.
  A questions file that is a link to a host file is read and posted as a ticket comment.
  The native-mode path already refuses links; the container path does not.
  *Status 2026-11-17:* remediated (section 2.1).
- **H2** (high, V; needs a proxy restart) `adore/isolation.py:2360`, `:1866`, `:2410-2421` -
  The Squid allowlist is written inside the run IO directory, which the agent has mounted
  read-write. The file is written only when the proxy is absent; a stopped proxy is
  restarted on the file as it is. After a daemon or host restart the agent's edit applies.
  *Status 2026-11-17:* remediated in part, fifth commit (section 2.1).
- **H3** (high, V) `adore/isolation.py:1860-1896`, `:2412-2419` - Neither the run container
  nor the proxy is started with `--cap-drop`, `--security-opt no-new-privileges`,
  `--pids-limit`, a memory limit or `--init`. `run_args` defaults to empty and the image
  installs `sudo` (`Dockerfile.executor-base:33`).
  *Status 2026-11-17:* documented by decision, code unchanged, fifth commit (section 2.1).
- **ISO-1** (medium, V) `adore/executor/launcher.py:268`, `:292`, `:384`, `:446`;
  `adore/aegis.py:473`; `adore/executor/pi_rpc.py:261` - The host creates, truncates or
  copies fixed file names in the agent-writable IO directory with plain `open`. A planted
  link makes the host overwrite a file of its own account.
  *Status 2026-11-17:* remediated (section 2.1).
- **ISO-2** (medium, V) `adore/isolation.py:2378-2387` - The generated Squid configuration has
  no `Safe_ports` or `CONNECT` port limit and no deny for loopback or link-local targets.
  An allowed name works on any port; a wildcard name that an attacker can resolve to an
  internal address becomes a pivot.
  *Status 2026-11-17:* no change, by requirement (section 2.1).
- **ISO-3** (medium, V for the base image and the installer line; A for the rest)
  `04_Software/docker/Dockerfile.executor-base:12`, `:51-52`, `:55-59`, `:63-66`, `:76-77`;
  `02_Tools/build/executor_images/adore/Dockerfile:58-59`, `:173-181`;
  `adore/pi_installation.py:255-261` - Base images have no digest; `uv` is installed by a
  piped script; the `glab` package, the `gh` keyring, Chromium and ffmpeg have no checksum;
  Pi's transitive npm dependencies float. Node, `fd` and `rg` are checksum-verified.
  *Status 2026-11-17:* open by decision (section 2.1).
- **ISO-4** (medium, A, plausible) `adore/isolation.py:1970-1972` - With
  `system_packages = true` the agent gets root-equivalent package commands in a container
  that has default capabilities and no user namespace.
  *Status 2026-11-18:* documented by decision, code unchanged, sixth commit (section 2.1).
- **ISO-5** (medium, A, plausible) `adore/executor/pi_rpc.py:391` - Only the in-memory tail of
  the session recording is cleaned. `output.jsonl` and its archive receive the raw text, so
  a `printenv` asked for by a ticket stores the model key in clear.
  *Status 2026-11-17:* no change, documented (section 2.1).
- **ISO-6** (medium, A, plausible) `adore/isolation.py:1846-1849` - A reused container is
  checked for mounts and the Git label only. After an egress mode change it keeps its old,
  looser network.
  *Status 2026-11-17:* no change, by design (section 2.1).
- **ISO-7** (medium, A, by design) `adore/local_execution.py:134-150`;
  `adore/executor/adore-guard.ts:24-25` - Local execution has no sandbox and the only guard
  is a `git push` pattern that a shell wrapper bypasses. It is documented, but there is no
  explicit risk acknowledgement in configuration.
- **ISO-8** (medium, A) `adore/config.py:401-402`; `adore/isolation.py:1867` - The cache
  volume names are not validated. A value containing a host path becomes a bind mount; a
  value that starts with `-` becomes an option.
  *Status 2026-11-17:* no change by decision (section 2.1).
- **ISO-9** (low, V) `adore/isolation.py:1896`; `Dockerfile.executor-base:150` - PID 1 is
  `sleep`, which reaps nothing. Leftover processes of one stage survive into the next.
  *Status 2026-11-17:* documented by decision with H3, fifth commit (section 2.1).
- **ISO-10** (low, V) `adore/isolation.py:1834` - The Git pointer `container.git` is mounted
  read-only at `/adore/work/.git` but is writable through `/adore/io`. Tampering is detected
  and fails closed, so the effect is denial only.
  *Status 2026-11-17:* no change (section 2.1).
- **ISO-11** (low, A, plausible) `adore/isolation.py:1894-1904` - Secrets passed at `run`
  are stored in the container configuration and are readable with `inspect`; they also go
  stale in a warm container.
  *Status 2026-11-17:* no change (section 2.1).
- **ISO-12** (low, A, plausible) `adore/executor/pi_rpc.py:492-498` - On a protocol-error exit
  only the `exec` client is killed; the process tree inside the container may keep writing.
  *Status 2026-11-18:* remediated, sixth commit, not run on a container (section 2.1).
- **ISO-13** (low, A) `adore/pi_providers.py:202` - A plain-HTTP endpoint is accepted for a
  request that carries the API key.
  *Status 2026-11-17:* no change, by design (section 2.1).

### 4.2 Verified as sound

- The run argv contains no `--privileged`, host network, host PID or IPC namespace, Docker
  socket mount or extra host mount (`isolation.py:1860-1896`).
- Allowlist mode uses an `--internal` network; the proxy is the only member with outbound
  access (`:2401`, `:1883`, `:2412-2425`).
- Secrets never appear in argv: bare `--env KEY`, values in the client environment (`:1894-1895`).
- The Git pointer is created exclusively and verified byte-exact, without following links
  (`:314-341`); the binding is rechecked inside the container (`:65-71`).
- Containers and networks are removed only by immutable identifier after ownership checks (`:1460-1590`).
- Recipe archives are parsed in memory with name, size and collision checks
  (`recipe_sources.py:513-551`); the recipe store rejects links (`executor_recipes.py:40-66`).
- The Pi RPC reader bounds records at 16 MiB, drains stderr on its own thread and treats
  malformed JSON as a protocol error (`executor/pi_rpc.py:158-190`, `:401-436`).
- `read_summary` reads without following links and proves file identity before, during and
  after (`isolation.py:884-946`). This is the pattern the defects above lack.

## 5. Web backend

113 routes. Five are unauthenticated and intended (`health`, `ready`, `about`, login, static
files). Every other route requires a session; about 75 are administrator-only. No route
without the check that its siblings have was found.

### 5.1 Findings

- **WEB-1** (high, V) `adore/web/store.py:249`; `adore/web/app.py:2927-2931` - The first-run
  account is `admin`/`admin` and is created without `password_change_required`. The server
  checks only that flag; `factory_password` is a hint for the interface. Anyone who can reach
  the service signs in as administrator until the password is changed. The service binds to
  loopback only (`web/server.py:15-19`), so the exposure starts behind a TLS proxy on a LAN.
  *Status 2026-11-17:* reclassified. REQ-UX-178abcf8 specifies a reminder for the factory
  password, so this is specified behaviour and a product decision, not a defect.
- **WEB-2** (medium, V for the headers; A for the body) `adore/web/configuration.py:157-170`,
  `:749-750` - Each configuration request is written to
  `configuration-tasks/<ref>.request.json` with the raw session cookie and CSRF token. The
  request body, which can hold a forge token or a model key, goes to the same file. The file
  stays if the worker is down, crashes, or the request is judged corrupt.
  *Status 2026-11-17:* remediated (section 2.1).
- **WEB-3** (medium, V) `adore/web/app.py:294-298`, `:3088`; `adore/web/server.py:20` - No
  request size limit exists, including on the unauthenticated login route.
  `PasswordChange` has no maximum length, so a huge value is hashed with Argon2.
  *Status 2026-11-17:* remediated (section 2.1).
- **WEB-4** (medium, V) `adore/web/store.py:613`, `:1145-1155` - `login_failures` gets a row
  per unknown user name and is cleared only by that identity's successful login. Expired
  sessions are never purged. An unauthenticated client can grow `web.db` without bound.
  *Status 2026-11-17:* remediated (section 2.1).
- **WEB-5** (medium, A) `adore/web/app.py:3090-3096`; `adore/web/store.py:585-594` - The login
  limit is check, verify, record. Parallel requests all pass the check before any failure
  is stored. The key is user name plus client address, so one address can try one password
  against any number of names.
  *Status 2026-11-17:* remediated (section 2.1).
- **WEB-6** (medium, A, plausible) `adore/web/app.py:2473-2474` - Importing a whole TOML file
  or a bundle bypasses the rule that web edits may not set operator-owned keys such as
  `workflow.verify_command`, `container.run_args` or absolute storage paths.
  *Status 2026-11-17:* open by decision, documented, third commit (section 2.1).
- **WEB-7** (medium, A) `adore/web/store.py:2421-2423` - Audit pruning re-reads and
  re-validates every audit row on every audit write and every audit page read, under the
  writer lock.
- **WEB-8** (medium, A) `adore/web/store.py:1948-1949` - `worker_owners` and
  `worker_processes` rows are never deleted; `recover_interrupted` reads the whole table on
  each supervisor tick (every 0.2 s).
  *Status 2026-11-17:* remediated in part, second commit (section 2.1).
- **WEB-9** (medium, A, plausible) `adore/web/supervisor.py:221-223`; `adore/web/commands.py:72`
  - Any child process is killed after six hours, whatever wall-clock budget the project
  configures.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **WEB-10** (low, V) No response carries `Content-Security-Policy`, `X-Frame-Options` or
  `frame-ancestors`; only one response sets `X-Content-Type-Options` (`app.py:4796`).
  *Status 2026-11-17:* remediated except the Content-Security-Policy, second commit
  (section 2.1).
- **WEB-11** (low, V; impact plausible) `adore/web/store.py:623`, `:354` - `web.db` and its
  marker file are created under the process umask. No code sets a mode.
  *Status 2026-11-17:* documented by decision, code unchanged, fifth commit (section 2.1).
- **WEB-12** (low, A) `adore/web/store.py:813-814` - An unknown or disabled user returns
  before any hash is computed, so response time reveals which names exist.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **WEB-13** (low, A) `adore/web/commands.py:304`; `adore/web/store.py:2037` - Engine outcome
  text reaches the operation API without the redaction that the job view applies.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **WEB-14** (low, A) `adore/web/jobs.py:486-494` - `redact_text` masks keyword-adjacent
  values and known token prefixes. A bare provider key in engine output passes through.
  *Status 2026-11-17:* remediated for the `sk-` prefix, second commit (section 2.1).
- **WEB-15** (low, A) `adore/web/store.py:1472-1481` - Queued execution operations have no
  upper bound; only `configure` is capped at 256.
  *Status 2026-11-17:* remediated, fourth commit (section 2.1).
- **WEB-16** (low, A, plausible) `adore/web/app.py:4626-4628`; `adore/config.py:843-846` - Any
  project member can make the host start a one-second Python process per request (branch
  rule preview), with no per-user limit.
  *Status 2026-11-17:* remediated, fourth commit (section 2.1).
- **WEB-17** (low, A, plausible) `adore/web/app.py:4588-4590`, `:4609-4613` - Non-administrators
  receive host paths and the host account name in the project configuration response.
  *Status 2026-11-17:* documented by decision, code unchanged, fourth commit (section 2.1).
- **WEB-18** (low, A) `adore/web/app.py:4232-4249`, `:2633-2637` - Two `GET` handlers change
  state without the CSRF check. `SameSite=Strict` blocks the practical attack.
  *Status 2026-11-17:* no change by decision (section 2.1).
- **WEB-19** (low, A, plausible) `adore/web/app.py:3098` - The cookie `Secure` flag follows
  the request scheme. Behind a TLS proxy on another host the cookie is issued without it.
  *Status 2026-11-17:* no change by decision, not reachable (section 2.1).
- **WEB-20** (low, A) `adore/web/supervisor.py:410-411` - A lost heartbeat is noticed only
  after the engine child ends; nothing stops the child.
  *Status 2026-11-17:* no change by decision (section 2.1).
- **WEB-21** (low, A) `adore/web/commands.py:69-72` - All engine output is captured in memory
  for up to six hours and then discarded.
  *Status 2026-11-17:* remediated, fifth commit (section 2.1).
- **WEB-22** (low, A, plausible) `adore/web/analytics.py:63-65` - A time-zone key that names a
  directory may raise an uncaught `OSError` and return 500.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **WEB-23** (low, A, plausible) `adore/web/analytics.py:817-822` - Cost per completed job uses
  in-period cost for a job that started before the period.
  *Status 2026-11-17:* not a defect, specified behaviour; help clarified, fifth commit
  (section 2.1).
- **WEB-24** (low, A) `adore/web/analytics.py:323`, `:356` - Money totals are summed as floats.
  *Status 2026-11-17:* no change by decision (section 2.1).
- **WEB-25** (low, A) `adore/web/jobs.py:508-510`; `adore/web/tickets.py:120-121` - The job
  list reads every journal twice per request; the ticket list loads state per ticket.
- **WEB-26** (low, A, by design) `adore/web/host_folders.py:34-54`;
  `adore/web/repository_source.py:84-93` - An administrator can list any host directory and
  point repository checks at internal addresses over plain HTTP.

### 5.2 Verified as sound

- CSRF: constant-time comparison against a per-session token on every state-changing route;
  cookie is `HttpOnly` and `SameSite=Strict`; no CORS middleware (`app.py:2933-2937`, `:3098-3099`).
- Sessions: `secrets.token_urlsafe(32)`, stored hashed, 12-hour expiry, revoked on disable,
  password change and reset (`store.py:1147-1167`, `:1037`, `:1101`, `:1128`).
- Passwords: Argon2id with library defaults (`store.py:30`).
- Authorization: project membership is bound to project identity and creation time, so a
  recreated project name inherits nothing (`store.py:1387-1399`); run and session identifiers
  are pattern-checked and membership re-resolved (`app.py:5160-5162`).
- No route changes an existing user's role; the last administrator cannot be disabled
  (`store.py:1030-1035`).
- SQL is parameterised throughout; the three string-built statements use constants only.
- Credential reads return presence only; user rows never include the hash; CSV export
  neutralises formula injection (`app.py:4158-4171`, `:1771-1775`).
- Static serving and the folder picker refuse traversal and links (`app.py:5982-5983`,
  `host_folders.py:34-101`).
- Model keys are written to the profile `.env` atomically with mode 0600
  (`web/executor_settings.py:82-90`).
- No subprocess call in the web modules uses a shell.

## 6. Orchestrator, state, AEGIS client and prompts

### 6.1 Findings

- **ORC-1** (medium, V) `adore/orchestrator.py:104` - `_sanitize` matches one word after
  `Authorization:`. `Authorization: Bearer <token>` becomes `Authorization: [REDACTED] <token>`.
  The output goes to public ticket and merge-request comments. Confirmed by running the
  pattern on a sample string.
  *Status 2026-11-17:* remediated (section 2.1).
- **ORC-2** (medium, V) `adore/orchestrator.py:1727-1728` - On the AEGIS path a failed target
  integration is treated as a conflict even when it already failed the run. The executor is
  launched once more and the real failure code is overwritten. The direct path checks the
  lifecycle (`:1563`); this path does not.
  *Status 2026-11-17:* remediated (section 2.1).
- **ORC-3** (medium, V) `adore/orchestrator.py:3088-3092` - The reconcile loop catches only
  `LockHeldError`. One run that raises `IsolationError` or `StateError` on every poll stops
  reconciliation of later runs and all new admissions for the project.
  *Status 2026-11-17:* remediated (section 2.1).
- **ORC-4** (medium, V) `adore/orchestrator.py:1361-1364` - The worktree and branch are
  created before the first state save. If workflow resolution then fails, the leftover
  worktree makes every later admission of that ticket fail until someone cleans up by hand.
  *Status 2026-11-17:* remediated (section 2.1).
- **ORC-5** (medium, A) `adore/orchestrator.py:3532-3533`, `:3401-3402` - A failed pipeline
  is recorded as reported before the repair starts. If the project is at capacity the
  repair is skipped and never retried.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-6** (medium, A, plausible) `adore/state.py:1102-1121`, `:1157-1175` - The admission
  lock file is created and then written. A crash in between leaves an empty file that is
  never treated as stale; a reused process identifier has the same effect.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-7** (medium, A, narrow window) `adore/state.py:1075-1086`; `adore/orchestrator.py:1403`
  - A capacity probe that holds an execution lock at the wrong moment makes a resumed run
  fail to take its slot; it is later failed as stale.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-8** (medium, V for the code) `adore/orchestrator.py:3574` - Ticket comments reach the
  Pi prompt as `author: body` with no delimiter and no filter on the author. The ticket
  description is also unfenced. The pipeline auto-repair path needs no human trigger.
  *Status 2026-11-17:* remediated in part, third commit (section 2.1).
- **ORC-9** (medium, A) `adore/orchestrator.py:745`, `:753` - Restart deletes the old job
  before the replacement is admitted. If admission fails, the failed job's state, worktree
  and unpublished branch are gone.
  *Status 2026-11-17:* remediated (section 2.1).
- **ORC-10** (low, V) `adore/prompts/recovery/revalidation-route.md:7` - A double-encoded
  apostrophe is sent to the model verbatim.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-11** (low, V) `adore/orchestrator.py:2684` - The incident text says "no fourth launch"
  although the limit is configurable.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-12** (low, V) `adore/orchestrator.py:2481` - A docstring still names AEGIS 0.15.0; the
  floor is 0.16 (`aegis.py:25`). Reported in the same state: `config.py:94`,
  `web/implementation_settings.py:16`.
  *Status 2026-11-17:* remediated (section 2.1).
- **ORC-13** (low, A) `adore/deletion_audit.py:43-56` - The audit database is created empty
  and initialised afterwards. Two concurrent first uses, or a crash in between, leave a file
  that is refused as unsupported.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-14** (low, A) `adore/orchestrator.py:340` - A platform error is logged without
  `_sanitize`; the sibling branch at `:351` applies it.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-15** (low, A) `adore/aegis.py:349`; `adore/orchestrator.py:3416` - A ticket title that
  starts with `-` is parsed by AEGIS as an option and fails the author's own ticket.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-16** (low, A) Dead code: `Orchestrator._claim_and_conduct` (`orchestrator.py:1381`) is
  called only by tests; `evidence=` at `:1783-1786` is passed to a template that has no such
  placeholder; `deletion_audit.py:16` defines an unused constant.
  *Status 2026-11-17:* remediated in part, second commit (section 2.1).
- **ORC-17** (low, A, plausible) `adore/process_log.py:85` - Log rotation by rename can raise
  on Windows while another process has the file open, and `emit` does not catch it.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **ORC-18** (low, A, plausible) `adore/orchestrator.py:3676-3677` - With a preparation recipe
  the base reference becomes a fixed commit, so the target-moved checks cannot fire.
  *Status 2026-11-17:* not a defect, documented behaviour; consequence documented, fifth commit
  (section 2.1).

### 6.2 Verified as sound

- All 26 prompt fragments exist and none is orphaned; every placeholder matches its call
  site; substitution is single-pass, so `$` in ticket text is harmless (`prompts.py:20-45`, `:93`).
- State writes use a temporary file, `fsync` and `os.replace`; loads validate a closed schema
  and fail closed (`state.py:46-65`, `:1240-1263`).
- Kernel locks use stable files with no unlink or reclaim race (`state.py:967-1022`,
  `resource_lock.py:23-101`).
- Admission is checked and reserved under one lock; publication is idempotent and a retry
  adopts the existing merge request (`orchestrator.py:401-422`, `:2511-2547`).
- Comment delivery is persisted before the write and replayed by an embedded marker
  (`orchestrator.py:2838-2954`).
- Every AEGIS command has a timeout, bounded output and a strict stage transition table
  (`aegis.py:28-29`, `:221-253`, `:411-437`).
- The instruction inbox rejects links and hard links and caps at 256 records
  (`instructions.py:45-58`, `:177-202`).
- Clone cleanup refuses links, shared paths, dirty trees and an origin mismatch
  (`clone_cleanup.py:141-182`).

## 7. Forge adapters, configuration, CLI, wizard and doctor

### 7.1 Findings

- **FRG-1** (medium, V) `adore/wizard.py:441`, used at `:511` and `:719` - A loop variable
  named `key` overwrites the host operating-system key. For an Azure DevOps profile the WSL
  runtime probe is skipped and `profile.json` stores `host_os = "area_path"`.
  *Status 2026-11-17:* remediated (section 2.1).
- **FRG-2** (medium, V) `adore/config.py:72-76`; `adore/repository_auth.py:18-39` - Two lists
  of forge credential variables have drifted. `env_keys` validation does not refuse
  `GH_ENTERPRISE_TOKEN`, `GITHUB_ENTERPRISE_TOKEN`, `GITLAB_ACCESS_TOKEN` or `OAUTH_TOKEN`,
  so such a token can be passed into the executor container.
  *Status 2026-11-17:* remediated (section 2.1).
- **FRG-3** (medium, A) `adore/config.py:1134`, `:1081`, `:1092` - `validate_config` assumes
  field types. `poll_interval_seconds = "60"` raises `TypeError`; a numeric `[agent] name`
  raises `AttributeError`. `config validate`, `status` and engine commands end in a traceback.
  *Status 2026-11-17:* remediated (section 2.1).
- **FRG-4** (medium, A) `adore/forge/azure_devops.py:249`; `adore/azure_cli.py:111` - Each
  Work Item is read by a separate call that starts two Python processes and re-fetches the
  resource areas. 150 ready items cost about 150 process pairs per poll.
- **FRG-5** (medium, A) `adore/config.py:604-605`, `:874-875` - A section that is not a table
  (`polling = 5`) is replaced by defaults without any issue being reported.
  *Status 2026-11-17:* remediated (section 2.1).
- **FRG-6** (medium, A, plausible) `adore/config.py:1507-1512` - Lifecycle, control, revise and
  selection labels are not checked for being non-empty and distinct. An empty ready label
  may select every open ticket on GitLab and GitHub.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-7** (medium, A, plausible) `adore/repository_auth.py:175-186`, `:293`;
  `adore/chatgpt.py:253-255` - On Windows the token file and the ChatGPT directory get no
  access-control restriction; protection relies on the inherited profile permissions.
  *Status 2026-11-17:* documented by decision, code unchanged, third commit (section 2.1).
- **FRG-8** (low, V) `adore/wizard.py:340` - The generated configuration says
  `adore init --profile NAME --force`. `--profile` is a top-level option (`cli.py:65`), so
  that command fails.
  *Status 2026-11-17:* remediated (section 2.1).
- **FRG-9** (low, V) `adore/forge/__init__.py:1`, `:34` - The docstrings list three forges and
  omit Azure DevOps.
  *Status 2026-11-17:* remediated (section 2.1).
- **FRG-10** (low, V for the docstring) `adore/forge/azure_devops.py:276-283`;
  `adore/forge/base.py:165-170` - The base contract says `get_ticket` returns `None` for a
  deleted ticket. The Azure adapter documents that it raises instead, so
  `on_ticket_deleted` can never fire on Azure.
  *Status 2026-11-17:* not a defect, documented behaviour; docstring corrected, fifth commit
  (section 2.1).
- **FRG-11** (low, A) `adore/config.py:397-400` - `keep_parked` and the three `parked_ttl_*`
  settings are read nowhere at run time, yet the class docstring calls `keep_parked` "the
  field parking actually reads" and the example file presents all four as active.
  *Status 2026-11-17:* docstring corrected, second commit (section 2.1).
- **FRG-12** (low, A) `adore/wizard.py:491-493` - A malformed branch template raises an
  uncaught `ValueError` instead of prompting again.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-13** (low, A) `adore/wizard.py:295-298` - The TOML fallback does not escape control
  characters; a multi-line answer produces an invalid file and a traceback.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-14** (low, A) `adore/wizard.py:387-396`; `adore/profiles.py:317-338`, `:449-465` -
  The profile name is validated only in the interactive prompt. `adore init ../../x` writes
  outside the profiles directory.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-15** (low, A) `adore/doctor.py:645` - The remote probe sets neither
  `GIT_TERMINAL_PROMPT=0` nor a short timeout; a credential prompt can stall for ten minutes.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-16** (low, A) `adore/wizard.py:816`; `adore/doctor.py:465-479` - The Azure
  authentication probe always fails at that point; the Gitea probe ignores the configured login.
  *Status 2026-11-17:* Azure half remediated, Gitea half needs no change, fifth commit
  (section 2.1).
- **FRG-17** (low, A, plausible) `adore/forge/github.py:220-223`; `adore/forge/gitea.py:198` -
  A branch lookup on GitHub may return a closed pull request; on Gitea a branch named with
  digits is read as a pull-request number.
  *Status 2026-11-17:* GitHub half needs no change; Gitea half open (section 2.1).
- **FRG-18** (low, A) `adore/forge/gitea.py:371` - With `draft = False` a title that starts
  with `WIP:` still creates a draft.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-19** (low, A, plausible) `adore/forge/azure_devops.py:539` - Status comments create
  active threads, which block completion where a policy requires resolved comments.
  *Status 2026-11-17:* open, needs a live check (section 2.1).
- **FRG-20** (low, A) `adore/forge/github.py:66` - `--limit 500` truncates silently, against
  the function's own docstring; the other adapters page or fail.
  *Status 2026-11-17:* docstring corrected, second commit (section 2.1).
- **FRG-21** (low, A) `adore/config.py:48`; `adore/util.py:269` - Quiet hours accept
  `99:99-99:99`.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-22** (low, A) `adore/util.py:412` - The `.env` parser strips every leading and
  trailing quote character, so a secret that ends in a quote is truncated.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-23** (low, A) `adore/portable_settings.py:141-144` - A branch still accepts the
  per-agent tables of removed coding agents; validation refuses them later with a generic error.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FRG-24** (low, A) `adore/profiles.py:1`; `adore/wizard.py:1` - Module docstrings are cut
  off mid-sentence.
  *Status 2026-11-17:* remediated, second commit (section 2.1).

### 7.2 Verified as sound

- No code disables TLS verification; skip-verify variables are scrubbed from the child
  environment (`repository_auth.py:35-36`, `:123`, `:137`).
- Every command has a timeout (`util.py:139`; `azure_devops.py:162`; `repository_auth.py:227`).
- Tokens reach the forge tools only through environment or a private temporary
  configuration, never argv, clone URLs or error text (`repository_auth.py:127-170`).
- On POSIX the token file is created 0600, written atomically and refused on read when the
  mode is wider or the path is a link (`repository_auth.py:175-186`, `:291-294`).
- Pagination is bounded in every adapter; URL and query parts are encoded; WIQL literals
  are escaped (`gitlab.py:89`, `:452`; `github.py:452`; `gitea.py:501-513`; `azure_devops.py:106-107`).
- The ChatGPT redirect is checked for exact origin, state and single query keys
  (`chatgpt.py:320-354`).
- Unknown sections and keys are refused (`config.py:863-915`).
- Every key in both example files is accepted by `config.py`, and the quoted defaults match.

## 8. Web frontend

No cross-site scripting path was found.

### 8.1 Findings

- **FE-1** (medium, A) `web/src/App.tsx:477` - `authentication_required` is handled only in
  one refresh loop. When the session expires elsewhere the interface keeps polling and
  shows an error that says to sign in, with no sign-in form.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-2** (medium, A, plausible) `web/src/App.tsx:849-850` - A failed logout request still
  clears the local interface while the cookie may remain valid.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-3** (medium, A) `web/src/main.tsx:6-8` - There is no error boundary; any render
  exception blanks the page.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-4** (medium, A) `web/src/App.tsx:96`, `:146`, `:440`, `:445` - `localStorage` is used
  without a guard. Where storage is blocked the first render throws; with FE-3 that is a
  white page.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-5** (medium, A) `web/src/configurationTasks.ts:15`, `:29` - A pending configuration
  operation is polled every 150 ms for up to 61 minutes, with no back-off and no pause when
  the page is hidden. Its errors bypass the normal error mapping.
  *Status 2026-11-17:* remediated, fourth commit (section 2.1).
- **FE-6** (medium, A) `web/src/settingLabels.ts:25` - In French, German and Romanian most
  setting labels fall back to the first sentence of the help text.
  *Status 2026-11-17:* remediated, fourth commit (section 2.1).
- **FE-7** (low, V) `web/src/jobCopy.ts:72`, `:115`, `:154`, `:193` - The cancel confirmation
  ends with "Cancellation cannot be undone." only in English.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-8** (low, V) `web/src/help/content/*/settings.md:11` - The list of project tabs omits
  Tickets in all four locales; the interface has it (`App.tsx:323`).
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-9** (low, A) `web/src/help/content/ro/administration.md:8` - A stale paragraph; the
  other three locales have a newer one. The structural test ignores paragraphs.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-10** (low, A) `web/src/jobModel.ts:49`, `:95` - One malformed evidence link makes the
  whole job list fail validation.
  *Status 2026-11-17:* open by design (section 2.1).
- **FE-11** (low, A) `web/src/App.tsx:604-605`, `:628-629` - One failed background poll clears
  prices or configuration that were already shown.
  *Status 2026-11-17:* open, needs a check against a running server (section 2.1).
- **FE-12** (low, A) `web/src/App.tsx:85`, `:89`; `web/src/routes.ts:5` - A `"projects"`
  metrics tab type is dead code.
  *Status 2026-11-17:* open by decision (section 2.1).
- **FE-13** (low, A, plausible) `web/src/EnrollmentWizard.tsx:301-303` - A bare 401 is shown
  as "unexpected response".
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **FE-14** (low, A) `04_Software/web/package.json:9-11` - Build scripts need `uv`, a virtual
  environment and Node 22.6 or later; there is no `engines` field.

### 8.2 Locale alignment

- The ten help topics exist in all four locales with identical heading identifiers and
  line positions, except `ro/administration.md` (FE-9).
- `settingKeys.json` (113 keys) and the help map agree; tests enforce key parity per locale.
- Placeholder parity across locales was not compared systematically.

### 8.3 Verified as sound

- Forge and agent Markdown is rendered without raw HTML; links allow only `http`, `https`
  and `mailto`; images become placeholders (`web/src/forgeMarkdown.ts:6-51`).
- No `dangerouslySetInnerHTML`, `innerHTML`, `eval` or `new Function` in the sources.
- The CSRF token lives only in component state; nothing writes a token or password to
  `localStorage` or the URL.
- Polling stops when the page is hidden and guards late results with generation counters
  (`web/src/polling.ts:30-41`).
- `static/index.html` references asset files that exist.
- No `.only`, `.skip` or `fixme` in unit or end-to-end tests.

## 9. User and operator documentation

### 9.1 Findings

- **DOC-1** (medium, V) `README.md:109-110` - "Web enrollment still requires AEGIS in this
  build". `Web_Interface.md:51`, `Getting_Started.md:43-44`, `CHANGELOG.md:219` and
  `adore/web/app.py:789` say and do the opposite.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-2** (medium, V) `01_Documentation/Configuration_Reference.md` - It never names
  `worktree.repo_path` (required), `worktree.branch_template`, `worktree.branch_rule` or
  `delivery.publish_checkpoints`. Reported in the same state: `worktree.root`,
  `metrics.enabled`. The default of `delivery.target_branch` is `develop`
  (`config.py:485`), while line 322 and `Getting_Started.md:97` show `main`.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-3** (medium, V) `01_Documentation/Local_Execution.md:3`, `:4`, `:76` - An arrow
  character is garbled into three bytes of mojibake.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-4** (low, V) `01_Documentation/Releases.md:52-53` - The example
  `set_version.py 0.19.0` fails once the version is 0.19.0, because the script refuses a
  version that is not higher.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-5** (low, V) `04_Software/README.md:12-13` - The forge list omits Azure DevOps Services.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-6** (low, V) `CHANGELOG.md:183-1154` - The 0.15.0 section repeats `### Added` six
  times and `### Changed` and `### Fixed` five times each. There is no 0.14.0 heading,
  although the text refers to a 0.14.0 delivery.
  *Status 2026-11-17:* no change by decision (section 2.1).
- **DOC-7** (low, V) `AGENTS.md:3` - "`claude.md` and `QWEN.md` only link here." Both also
  carry the full managed AEGIS block.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-8** (low, V) `00_Planning/README.md:16-18` - The workflow-selection plan is called
  "planned"; the plan file records an implementation result and 0.17.0 shipped it.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-9** (low, V) `AGENTS.md:81-82` forbids license banners in documentation.
  `00_Planning/README.md`, both existing plans and `04_Software/.env.example` have one.
  *Status 2026-11-17:* remediated in part, fifth commit (section 2.1).
- **DOC-10** (low, A) `01_Documentation/Security_And_Credentials.md:125-127`;
  `Configuration_Reference.md:179-181` - The list of refused `env_keys` omits the three
  Azure names that `config.py:72-76` refuses.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-11** (low, A) `01_Documentation/CLI_Reference.md:35-36` - The list of commands that
  load `.env` omits `conduct`, `restart`, `handoff` and `logs`.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-12** (low, A) `04_Software/adore/release_notes.toml:2-3` - It points to an
  `AGENTS.md` heading that does not exist; the rules are in `Releases.md:26-39`.
  *Status 2026-11-17:* remediated (section 2.1).
- **DOC-13** (low, A) `04_Software/config.example.toml:105`, `:116`, `:164` - The example
  sets a project image, four tool checks and a reviewer that do not exist by default.
  Copied as it is, it fails on the base image.
  *Status 2026-11-17:* remediated, fifth commit (section 2.1).
- **DOC-14** (low, A) `04_Software/config.azure-devops.example.toml:31` - `env_keys` repeats
  the provider key, which is always added.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **DOC-15** (low, A) `01_Documentation/Administrator_Guide.md:145`; `Troubleshooting.md:88` -
  "Back to the user guide" links to `README.md`, which is the documentation index in the
  repository. The link is right only inside the portable package.
  *Status 2026-11-17:* no change needed (section 2.1).
- **DOC-16** (low, A) `01_Documentation/Security_And_Credentials.md:301`, `:284-285` - A bare
  file name that is not a link, and "POSIX0600" without a space.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **DOC-17** (low, A) The five `.pptx` presentations have no Markdown source in the repository.
  *Status 2026-11-17:* open by decision (section 2.1).

### 9.2 Verified as correct

- No document other than the changelog entry for the removal mentions the quick-label feature.
- The AEGIS floor 0.16 matches `aegis.py:25` wherever it is stated.
- `CLI_Reference.md` matches `cli.py:60-170` for commands, flags, defaults and exit codes.
- Configuration defaults for polling, clarification, recovery, budgets, container, egress
  and review match the code.
- Security claims that match the code: token file mode and link refusal, tokens kept out of
  argv, redaction of tool output, the 0600 profile `.env`, the ChatGPT directory mode and
  time limits, the single bind mount of the sign-in helper, Argon2 password hashing.
- Version 0.19.0 is consistent across `pyproject.toml`, `adore/__init__.py`, `uv.lock`,
  `CHANGELOG.md`, `release_notes.toml` and six documents.
- Every relative link and anchor that was tested resolves.

## 10. Component documentation (05_SoftwareDocu)

51 component documents were read; the most concrete claims of each were checked. No
document states a safety or data invariant that the code fails to implement, with one
exception found by the lead reviewer (CMP-1).

### 10.1 Findings

- **CMP-1** (medium, V) `05_SoftwareDocu/Component_Isolation.md:164-166` - "a malicious
  executor could damage the local clone". The writable mount allows host code execution (C1).
  *Status 2026-11-17:* the sentence was rewritten with the C1 route B change; it now states
  what a container can still alter.
- **CMP-2** (medium, V) `05_SoftwareDocu/Component_Packaging.md:102-103` - Says the installers
  provision the web extra. Both run `uv sync --frozen` only
  (`install_linux_service.sh:100`, `install_windows_service.ps1:90`).
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-3** (medium, V) `05_SoftwareDocu/Component_Executor_Configuration.md:56` - Points to
  `tests/test_web_launch_presets.py`, which does not exist.
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-4** (medium, A) `05_SoftwareDocu/Component_Wizard.md:117-118` - `kind` is said to
  accept three forges; `wizard.py:414` accepts four, and line 3 of the same document says so.
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-5** (medium, A) `05_SoftwareDocu/Component_Web_Identity.md:167` - The operation list
  omits `restart` (`web/store.py:1457`).
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-6** (medium, A) `05_SoftwareDocu/Component_Orchestrator.md:30-32` - The lifecycle list
  omits `stale` (`state.py:40-42`).
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-7** (medium, A) `05_SoftwareDocu/Component_Executor_Launcher.md:168` - "Sessions are
  not resumed across stages" contradicts lines 15-16 of the same document and
  `executor/launcher.py:253-255`.
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-8** (medium, A) `05_SoftwareDocu/Component_Portable_Distribution.md:182-185` -
  Attributes the archive inventory and link check to `test_delivery_package`; it is done by
  `verify_delivery_package.py:131-146`.
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-9** (medium, A) `05_SoftwareDocu/Component_Wizard.md:218-219` - Says web enrollment
  defaults to 20 executor launches; the API default is 12 (`web/app.py:385`) and only the
  interface sends 20.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **CMP-10** (low, A) `05_SoftwareDocu/Component_CLI.md:221-223` - The start-refusal codes
  omit `pickup_paused` (`cli.py:659-665`).
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-11** (low, A) `05_SoftwareDocu/Component_Aegis_Client.md:58` - The supported version
  is described without the 0.16 floor.
  *Status 2026-11-17:* remediated (section 2.1).
- **CMP-12** (low, A) Only three documents use the headings of
  `component_documentation_template.md`; 48 use an older ten-section layout.
  *Status 2026-11-17:* no change by decision (section 2.1).
- **CMP-13** (low, A) Modules named in no component document: `web/settings_batch.py`,
  `web/tickets.py`, `web/executor_evidence.py`, `executor/diagnostics.py`, `web/server.py`,
  `selection.py`, `deletion_audit.py`, `web/environment.py`, `web/worker_context.py`.
  *Status 2026-11-17:* remediated, fifth commit (section 2.1).

### 10.2 Verified as correct

- No component document describes the quick-label setting or AEGIS 0.14.
- `Component_Prompts.md` matches the fragment table in `prompts.py:19-46`.
- All links, anchors and the index in `05_SoftwareDocu/README.md` resolve and are in sync.
- Constants checked and correct include the stage time limit, record and evidence bounds,
  instruction limits and configuration queue limits.

## 11. Tooling (02_Tools)

### 11.1 Findings

- **TOOL-1** (medium, V) `02_Tools/package/create_delivery_package.py:195` - Dependencies for
  the bundled interpreter are exported with `--no-hashes`, although `uv.lock` has hashes.
  *Status 2026-11-17:* remediated, second commit, packaging not run (section 2.1).
- **TOOL-2** (medium, V) `02_Tools/setup/install_linux_service.sh:30` - The service user
  defaults to the invoking user. Run with `sudo`, the unit gets `User=root` and the
  environment is created root-owned.
  *Status 2026-11-17:* remediated, second commit, installer not run (section 2.1).
- **TOOL-3** (medium, V) `02_Tools/setup/adore.service:32-35` - The unit sets only
  `NoNewPrivileges` and `PrivateTmp`; no `ProtectSystem`, `ProtectHome` or `ReadWritePaths`.
  *Status 2026-11-17:* open by decision (section 2.1).
- **TOOL-4** (medium, V) `02_Tools/setup/install_windows_service.ps1:179-190` - The comment
  says a wedged pass cannot block the schedule. The task uses `IgnoreNew` with an unlimited
  execution time, so a hung pass blocks every later one.
  *Status 2026-11-17:* remediated, second commit, installer not run (section 2.1).
- **TOOL-5** (medium, A, plausible) `02_Tools/package/bundle_native_tools.py:150-155` - Pi's
  transitive npm dependencies are not pinned and the lock files are deleted afterwards.
- **TOOL-6** (medium, A, plausible) `02_Tools/package/create_delivery_package.py:355-356` -
  The archive takes ownership, mode bits and timestamps from the build host; it is not
  reproducible.
- **TOOL-7** (low, A, plausible) `02_Tools/package/set_version.py:170`, `:184` - The old
  version string is replaced wherever it occurs, including inside longer numbers.
  *Status 2026-11-17:* remediated, third commit (section 2.1).
- **TOOL-8** (low, A) `02_Tools/package/set_version.py:190-199` - Files are replaced one at a
  time; a failure leaves mixed versions, and replaced files get mode 0600 on POSIX.
  *Status 2026-11-17:* remediated in part, third commit (section 2.1).
- **TOOL-9** (low, A, plausible) `02_Tools/package/launcher_templates/launch.py:458-468`,
  `:143-150`, `:375` - A malformed stop record ends the launcher; the token record is written
  with default permissions.
  *Status 2026-11-17:* remediated, third commit, package not run (section 2.1).
- **TOOL-10** (low, A, plausible) `02_Tools/package/launcher_templates/launch.py:247-248` -
  `ProcessLookupError` on a forced kill escapes from `finally`.
  *Status 2026-11-17:* remediated, third commit, package not run (section 2.1).
- **TOOL-11** (low, A, plausible) `adore.sh:3`, `start-adore.sh:3`, `stop-adore.sh:3` - The
  wrappers resolve their directory from `$0` and break when called through a link.
- **TOOL-12** (low, A, plausible) `02_Tools/setup/install_linux_service.sh:164-165` - A
  checkout path with `|`, `&`, a space or `%` corrupts the generated unit.
  *Status 2026-11-17:* remediated, third commit, installer not run (section 2.1).
- **TOOL-13** (low, A, plausible) `02_Tools/setup/adore.service:22-25` - The permissions of
  the `.env` file are never checked or set.
  *Status 2026-11-17:* remediated as a warning, third commit, installer not run (section 2.1).
- **TOOL-14** (low, A, plausible) `02_Tools/setup/install_windows_service.ps1:177`, `:126`,
  `:88` - The task user drops the domain; the runtime string is split on spaces; paths with
  brackets fail.
- **TOOL-15** (low, A) `02_Tools/setup/install_linux_service.sh:89` - The installer prints a
  pipe-to-shell command as its installation hint.
  *Status 2026-11-17:* remediated, third commit (section 2.1).
- **TOOL-16** (low, A) `02_Tools/package/release_checks/check_release_consistency.py:401`;
  `create_delivery_package.py:374` - A missing checksum file is accepted; the checksum reads
  the whole archive into memory.
  *Status 2026-11-17:* remediated in part, third commit (section 2.1).
- **TOOL-17** (low, A, plausible) `02_Tools/package/verify_delivery_package.py:131-146` - The
  built bundle is not scanned for local configuration, `.env`, auth files or state.

### 11.2 Verified as sound

- Downloads of Node, `fd` and `rg` are checksum-pinned over HTTPS with a size cap
  (`bundle_native_tools.py:13-45`).
- Archive extraction rejects members that escape the root or are links (`:57-74`).
- The package is built from an explicit allow-list; the launcher refuses any unlisted file
  (`create_delivery_package.py:288-316`, `launch.py:108-117`).
- The launcher binds to loopback and clears `PYTHONPATH`, `PYTHONHOME` and `VIRTUAL_ENV`
  (`launch.py:289`, `:430-433`).
- The Windows task runs as the current user without elevation.

## 12. Tests, lint and dependencies

About 112 Python test modules. Shared helpers and the modules touched by the current change
were read fully; the rest were searched for patterns. Nothing was run.

### 12.1 Findings

- **TEST-1** (medium, A) `tests/test_clone_cleanup.py:45-46`, `:353-379`, `:441-443` - Runs
  real `git` and inherits the developer's global Git configuration, against the rule that
  unit tests use injected runners.
  *Status 2026-11-17:* remediated in part, third commit (section 2.1).
- **TEST-2** (medium, A) `tests/test_orchestrator.py` (about 98 calls); `tests/test_prompts.py:70`,
  `:185`, `:384`; `tests/test_doctor.py:52`; `tests/test_wizard.py:21` - Tests call private
  methods directly.
- **TEST-3** (medium, A) `adore/web/app.py:3090-3091` - The HTTP 429 login limit has no
  test; only the store function is tested (`tests/test_web_auth.py:223-226`).
  *Status 2026-11-17:* remediated with WEB-3 (section 2.1).
- **TEST-4** (medium, A) `tests/conftest.py:73-86` - Only `ADORE_HOME` is isolated. `HOME`,
  `USERPROFILE`, `APPDATA`, `XDG_*` and the Git configuration are not.
  *Status 2026-11-17:* remediated in part, third commit (section 2.1).
- **TEST-5** (medium, A, plausible) `tests/test_config.py:105`; `tests/test_aegis.py:222-229`,
  `:521-523`; `tests/test_state.py:214-229` - Tests assert the absence of retired features.
  The AEGIS and state cases also serve as fail-closed checks; `test_config.py:105` does not.
  *Status 2026-11-17:* remediated in part, third commit (section 2.1).
- **TEST-6** (medium, A) `tests/test_wizard.py:45`; `tests/test_worker_acceptance.py:211`;
  `tests/test_host_folders.py:72` - Module-wide patches replace `subprocess.run`, `time.sleep`
  and `os.scandir` for the whole process.
- **TEST-7** (medium, A) `tests/test_azure_cli.py:259-261` - The only test of the real SDK
  dispatch is skipped wherever `azure-cli` is not installed, which is the standard setup.
- **TEST-8** (medium, A) `04_Software/pyproject.toml:25-31`; `tests/conftest.py:28` - The test
  suite needs the web extra but the development group does not declare it.
- **TEST-9** (medium, A, plausible) `04_Software/pyproject.toml:51-57` - No test timeout,
  although helpers sleep for 60 to 600 seconds.
- **TEST-10** (medium, A) `tests/supervisor_helper.py:25-34`;
  `tests/test_worker_acceptance.py:14-17` - Test modules import other test modules; each
  spawned worker imports the 5000-line orchestrator test module.
- **TEST-11** (low, A) `tests/test_forge_labels.py:222` - Accepts 403 or 404, so it cannot
  tell which control refused.
  *Status 2026-11-17:* remediated, third commit (section 2.1).
- **TEST-12** (low, A, plausible) `tests/test_web_rbac.py:36` - The cost-privacy assertion
  runs on a project with no usage events.
  *Status 2026-11-17:* remediated, third commit (section 2.1).
- **TEST-13** (low, A) `tests/test_prompts.py:129-131` - An assertion checks the patch the
  test just installed.
- **TEST-14** (low, A) `tests/test_worker_acceptance.py:214` - Pins an internal retry count.
- **TEST-15** (low, A) `tests/test_web_server.py:82-89`; `tests/test_web_rbac.py:75`, `:143`,
  `:151` - SQLite connections are committed but never closed.
  *Status 2026-11-17:* remediated, third commit (section 2.1).
- **TEST-16** (low, A, plausible) `tests/test_orchestrator.py:147`, `:170` - Fake paths default
  to `C:/repo`; on POSIX that is a relative path inside the repository.
- **TEST-17** (low, A) `tests/test_host_folders.py:102-111` - The link guard is tested on
  POSIX only, although a `symlink_support` fixture exists (`conftest.py:51`).
  *Status 2026-11-17:* remediated, third commit, not exercised on Windows (section 2.1).
- **TEST-18** (low, A, plausible) `tests/conftest.py:45-47` - The fast password hasher is
  installed only if the store module is already imported.
  *Status 2026-11-17:* remediated, third commit (section 2.1).
- **DEP-1** (medium, A; one source, not cross-checked) `04_Software/web/package-lock.json:2694-2695`
  - `vite 7.3.6` is reported to fall in a directory-traversal advisory fixed in 7.3.7
  (SNYK-JS-VITE-21282039). It affects the development server, not production builds.
  *Status 2026-11-17:* remediated, second commit (section 2.1).
- **DEP-2** (medium, A) `04_Software/pyproject.toml:13-16` - The web extra allows old
  FastAPI releases, and `starlette` and `pydantic` are imported but not declared. The lock
  file pins patched versions, so only installs outside the lock are exposed.
  *Status 2026-11-17:* remediated, third commit (section 2.1).
- **DEP-3** (low, A, plausible) `04_Software/ruff.toml:6` - Security rules are not selected,
  yet three tests carry suppressions for them.
  *Status 2026-11-17:* no change (section 2.1).
- **DEP-4** (low, A) `04_Software/web/package.json:16-27` - Exact pins are mixed with caret
  ranges; there is no `engines` field.
  *Status 2026-11-17:* remediated in part, third commit (section 2.1).
- **DEP-5** (low, A) The repository has no continuous-integration configuration.

Modules with no direct test: `web/analytics.py`, `web/executor_evidence.py`,
`web/implementation_settings.py`, `web/status.py`. The `Host` header path has no test.

### 12.2 Verified as sound

- No reference to the removed quick-label feature or the deleted AEGIS 0.14 fixture.
- The prompt baseline fixtures match the prompt files on disk.
- No real network use; no `xfail`, `assert True` or swallowing `except` in tests.
- All credentials in tests, fixtures and end-to-end specs are fabricated.
- Entry points exist; the lock file matches the declared specifiers.

## 13. Repository hygiene

- **HYG-1** (medium, V) `.gitignore` - `.claude/` and `.vera/` are not ignored (see SEC-1,
  SEC-2). Reported in the same state: `dist/`, `*.egg-info` and `.mypy_cache/`.
- **HYG-2** (low, V) The pack is 1.25 GiB because delivery archives were committed in the
  past: at least 11 distinct blobs of about 80 MB for one Linux archive path alone.
- **HYG-3** (low, V) `.git` holds 1.51 GiB of temporary pack files left by interrupted
  operations.
- **HYG-4** (low, V) `04_Software/adore/web/static/index.html` references the new bundle
  `assets/index-3a9gNcBy.js`, which was untracked at review time. It must be added with the
  release commit, or the committed interface has no script.
- **HYG-5** (low, V) There is no `v0.16.0` tag, although the changelog has that release.
- **HYG-6** (low, V) One stash exists ("pre-merge local work"). It was scanned and is clean.
- **HYG-7** (low, V) `.codex/config.toml` sets `sandbox_mode = "danger-full-access"`. The
  file is local and excluded through `.git/info/exclude`.
- **HYG-8** (low, A, plausible) `.gitattributes:24-37` - The binary list omits font, archive,
  wheel and database extensions; those files rely on content detection.

## 14. Not covered

- `.agentic/` (984 files: the AEGIS payload, requirements, specifications and task
  journals) was scanned for secrets only. Its content was not reviewed.
- `web/src/App.tsx` was read for about a third; about 25 smaller components and helper
  modules were not read; help prose was read for two topics, the others only compared by
  structure.
- `tests/test_orchestrator.py` was read to line 420 of about 5000; most other test modules
  were only searched.
- `CHANGELOG.md` below line 220 and the bodies of the two existing plans were skimmed.
- The `.pptx` files were checked for metadata and a few terms, not for content.
- Dependency advisories were looked up for a handful of packages only.
- Behaviour of the external tools (`gh`, `glab`, `tea`, the Azure SDK, Docker, Podman,
  Squid) was not verified. Findings that depend on it are marked plausible.
- `adore/executor/adore-chatgpt.mjs` (the sign-in helper) was not read.

## 15. Suggested order of work

1. Rotate the SSH password of SEC-1 and ignore `.claude/` and `.vera/`.
2. C1 route A, H2 and H3, as described in the companion plan (C1 route B and H1 are done). Until then: trusted ticket authors
   only, a dedicated host account, and the `run_args` hardening shown in that plan.
3. WEB-1 (factory account) is a product decision. WEB-2 is done.
4. Done: ORC-1, ORC-2, ORC-3 and ORC-4.
5. Done: WEB-3, WEB-4, WEB-5 (one part), FRG-1, FRG-2 and FRG-8.
6. Decide on SEC-3: whether the history must be cleaned before it is ever published.
7. CMP-2 and CMP-3 with the next documentation pass. DOC-1 to DOC-3 and CMP-1 are done.
8. The remaining medium and low findings as ordinary backlog.

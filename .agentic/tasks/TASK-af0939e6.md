<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-af0939e6 - Enroll a project from its repository URL with automatic clone at creation

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-b3251e39, REQ-UX-43f73ffd, REQ-UX-072cf049, REQ-UX-2761363b, REQ-UX-34718dd6
parent:
branch: task/adore-web-interface
base: 7c85eea192d1aec7c3f7df8fc4e46878d66fedbf
opened: 2026-10-12

## Done checklist (current stage)

- [x] red records, anchor, implementation, focused green, links, docs, check clean
- [x] `stage: validate`

## Frame

Problem: during the real enrollment test the user found Repository and identity too technical: a Stable project ID, forge kind, owner/repository, Gitea login, clone path and target branch typed by hand without examples, and no way to know what the "local clone path" is. STATED: "Nu vreau stable project ID ... Vreau ca toate elementele in afara de display name sa fie cele din forge. De asemeni, vreau in casete exemplu de info"; "Nu merge sa introduc path-ul catre un repo (gitlab / github / gitea) si adore sa seteze direct, forge, repository, local clone path si eventual target branch?"; choices: "Yes, as proposed" (URL + Read repository, ADORE clones, advanced existing clone kept) and clone "Only at Create project"; then "dupa, fa deploy pe dcp server".
Desired outcome: enter a repository URL, press Read repository, confirm detected values, type only Display name (prefilled); ADORE clones into <ADORE home>/repos/<ID> at Create; the existing-clone path stays as an advanced option; all fields show examples.
Actors: administrators.
Primary scenario: Enroll new project -> URL ssh://git@192.168.1.15:2222/owner/repo.git -> Read repository -> forge gitea (tea login), repository owner/repo, branch main, ID repo, clone location shown -> continue -> Create clones and publishes.
Examples: DCP Gitea remote ssh://git@192.168.1.15:2222/dpasare/AgenticDeliveryOrchestratorRuntimeEngine.git.
Counterexamples: imports keep exact copies; no clone during preview or checks; no file:// or local sources; no credentials in URLs; no forge API token needed.
In scope: adore/web/repository_source.py, /api/v1/projects/repository-source, ProjectInput.clone_url, preview/check/create (and transfer preview/check/create) clone handling, wizard pending-clone validation, EnrollmentWizard step 1, copy in four locales, help (four locales), pytest/e2e tests, docs, requirements, release notes, deploy to DCP.
Out of scope: listing repositories from forge APIs; changing the import wizard; full suite (STATED: at the end).
Constraints: Gitea/GitLab self-hosted kind detection only via server tea logins; otherwise the user picks the forge; clone uses the service account's git credentials (same as publication).
Success signals: focused tests green; DCP enrollment from the Gitea URL works.
Evidence: OBSERVED _prepare_project requires an existing clone and the wizard validates repo_path with _existing_dir; _probe_setup checks .agentic files in repo_path; probe_runner is injectable (e2e fixture_probe); forge adapters have no repository listing.
Assumptions: the tea logins list JSON output names login URLs (tea logins list -o json). Unknowns: none blocking. Decision-blocking questions: answered.
Proposed behaviors: B1 URL detection and clone at create (REQ-FUNC-b3251e39); B2 step-1 UI (REQ-UX-43f73ffd); revisions of REQ-UX-072cf049 (no ID field) and REQ-UX-2761363b (examples).
Path and reason: full - new server capability (clone), new endpoint and UX change.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| URL detection, clone at create | B1 | REQ-FUNC-b3251e39 (new) | detect, clone, reuse | bad URL, unreachable, occupied folder, missing AEGIS/branch, cleanup | pytest test_repository_source | D1-D4 |
| Step 1 from URL | B2 | REQ-UX-43f73ffd (new) | read and confirm, prefilled display name | unknown forge pick, existing-clone option | e2e enrollment/transfer | D5 |
| No ID field, examples | B2 | REQ-UX-072cf049, REQ-UX-2761363b (revised) | examples in fields | ID generated, shown at review | e2e | D5 |

## Design

- D1 `adore/web/repository_source.py` (pure + runner): parse_repository_url (https/http/ssh/scp-like, no passwords, owner/name segments, strip .git), detect_kind (github.com, gitlab.com, tea login hosts), default_branch (ls-remote --symref output), suggest_id (slug, unique suffix), origin_matches (normalized comparison), read_origin (from .git/config), commands via the injected runner: tea logins list -o json, git ls-remote --symref -- <url> HEAD, git clone -- <url> <dest>, all with GIT_TERMINAL_PROMPT=0 and timeouts.
- D2 `POST /api/v1/projects/repository-source` {url}: admin + CSRF; returns url, kind (or null), repo, login, default_branch, name, display_name, repo_path (<home>/repos/<name>), clone ("new" | "existing"); 400 repository_url_invalid, 502 repository_unreachable.
- D3 `ProjectInput.clone_url` (default ""): _prepare_project validates the URL, requires repo_path == <home>/repos/<name>, repo matching the URL; an existing folder must be a clone with matching origin (else clone_path_occupied); a missing folder is a pending clone (wizard `pending_clone=True` accepts a not-yet-existing path); review carries clone_url and clone state.
- D4 setup-check/transfer-check mark aegis_files "not-checked" for a pending clone; setup-create/transfer-create/POST /projects clone a pending clone before publication (mkdir parents, bounded), verify AEGIS files and origin/<target_branch>, and remove the fresh clone when verification or publication fails.
- D5 EnrollmentWizard step 1: Repository URL + Read repository (detected values panel: forge select preselected or required, repository, login for Gitea, target branch input, project ID and clone location read-only, Display name prefilled); toggle "Use an existing clone on this server" keeps kind/repo/login/repo_path/target_branch with examples; the ID is always derived (URL: detection; existing clone: slug of the repository name checked with id-availability); placeholders for every text field; copy in four locales; help/docs say ADORE clones at creation.

## Log

- 2026-10-12 frame: scope accepted (enrollment from repository URL with clone at Create; user choices recorded in Frame); autopilot; full path; full suite deferred by the user; deploy to DCP afterwards (STATED).
- 2026-10-12 specify: 2 created (REQ-FUNC-b3251e39, REQ-UX-43f73ffd); REQ-UX-072cf049 and REQ-UX-2761363b to be revised in build; 0 retired.
- 2026-10-12 design: see ## Design D1-D5.
- 2026-10-12 build red: REQ-FUNC-b3251e39 command=`.venv/Scripts/python.exe -m pytest -q tests/test_repository_source.py` exit=2 (collection error: no adore.web.repository_source); expected missing behavior=URL detection endpoint, pending-clone preview/check and clone at creation absent.
- 2026-10-12 build green: pytest test_repository_source 23/23 plus enrollment/transfer/wizard/audit-evidence/import/portable suites green (151 and 216 runs), ruff clean (new files formatted with ruff format); node 94/94; tsc + e2e typecheck clean; e2e enrollment 15/15 (new URL test: unreachable address alert, Read repository, detected values, no Stable project ID, creation with simulated clone), shell+transfer+help 25 and import 12 green (import label renamed to Project ID). Built adore/web/repository_source.py, /api/v1/projects/repository-source, ProjectInput.clone_url with pending-clone preview, aegis_files not-checked in setup/transfer checks, clone + AEGIS/branch verification + cleanup at setup/transfer/POST create, wizard pending_clone; EnrollmentWizard step 1 (URL + Read repository, detected panel, existing-clone option, derived ID, example placeholders), copy and error messages in four locales; e2e server simulates ls-remote/tea/clone (REQ-FUNC-b3251e39, REQ-UX-43f73ffd, REQ-UX-072cf049, REQ-UX-2761363b revised).
- 2026-10-12 help: updated (projects.md before-you-start, Repository and identity and Review and create rows; four locales, parity ok); transfer help copy no longer says nothing is cloned.
- 2026-10-12 release-notes: updated (New / Projects entry now says a project is added from its repository URL and cloned); `python 02_Tools/check_release_notes.py --since 7c85eea` ok.
- 2026-10-12 deployed to DCP as af0a (backend + static; repository-source answers 401 without a session). OBSERVED on DCP: the service account dpasare has no SSH private key for Gitea (ls-remote: Permission denied (publickey)) and no tea binary, so Read repository needs git read access for that account and the forge is chosen manually for 192.168.1.15; not changed (server credentials are the user's decision).
- 2026-10-12 DCP git access: at the user's request ("da, genereaza cheia si da-mi cheia publica") generated /home/dpasare/.ssh/id_ed25519 for the service account (no previous key, nothing overwritten); the user added the public key to Gitea ("am adaugat"); `git ls-remote` from DCP now reads the repository (default branch master).
- 2026-10-12 validate review round 1: spec-compliance FAIL and implementation-quality FAIL (shared high finding) -> the clone folder is reserved with an exclusive mkdir before git clone, so a failed or concurrent request never removes another request's clone (test: folder appearing after review is refused and kept; failed clone leaves nothing). Spec: stale never-clones claims fixed (REQ-FUNC-20010f79 spec, existing-clone help in four locales, Web_Interface.md); URL-mode findings point at the URL help. Quality: SSH user/host may not start with '-', control characters rejected, GIT_ALLOW_PROTOCOL=ssh:https:http; reserved IDs treated as taken during detection (and new/clone/repository-source added to reserved project IDs, as /projects/new, /projects/clone and the API route would shadow them); malformed tea login URLs skipped; display name prefilled by a previous URL cleared with it; finding help shows the URL help; correction focus falls back to the heading; detection announced through a status region; deriveId runs once and only for its repository.
- 2026-10-12 scope additions from the user during review (STATED): "Local clone path - poate fi presetat dar modificabil de catre utilizator ... precompletat la read repository - dar sa poata fi modificat apoi" -> the clone path is prefilled and editable (absolute, outside ADORE home or under its repos folder; same reuse/occupied rules); "daca un repo nu poate fi citit in prima pagina - butonul continue sa fie dezactivat" -> Continue is disabled in URL mode until a successful read. REQ-FUNC-b3251e39 and REQ-UX-43f73ffd revised; help (four locales), docs and CHANGELOG updated. pytest 215/215 (repository_source 26, enrollment, transfer, wizard, profiles, import); ruff clean; node 94/94; tsc clean; e2e enrollment+shell+transfer+import+help 59/59; DCP af0b.
- 2026-10-12 validate review round 2: spec-compliance FAIL - the REQ-FUNC-20010f79 spec still fixed the clone location -> reworded to the proposed or another permitted folder.
- 2026-10-12 validate review round 2 (quality): implementation-quality PASS with findings -> repo_path used as typed (no ~ expansion; `~/x` refused); a sibling `.<name>.adore-cloning` marker makes a clone in progress occupied for other requests (created exclusively, removed after publication); parent folders are created only under <home>/repos, elsewhere the parent must exist; tests for ~, marker, missing parent and cleanup after a failed publication. Spec round 3 PASS (REQ-FUNC-20010f79 spec wording). pytest 216/216; ruff clean; e2e enrollment+transfer 28/28; docs updated; DCP af0c.
- 2026-10-12 validate review round 3: spec-compliance PASS (round 4: refinements within REQ-FUNC-b3251e39); implementation-quality PASS (lows applied: a cloning marker older than 15 minutes without a folder is replaced, with a folder it marks an interrupted clone that is refused and never reused; folder-creation and marker OSErrors get accurate coded messages; the shared-custom-folder window between two different IDs is accepted as very low risk). pytest 217/217; ruff clean; docs describe the recovery; DCP af0d.
- 2026-10-12 validate review round 4: spec-compliance PASS (round 5: crash recovery documented and safe); implementation-quality PASS (round 4; its two one-line lows applied afterwards: a marker with a future time counts as stale, an OSError while removing a stale marker falls through to the coded 409; the stale-marker takeover race between simultaneous requests is accepted as very low risk since the exclusive mkdir still protects the folder). pytest repository_source+enrollment 103/103; ruff clean; DCP af0e.
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-af0939e6 --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by pytest 217/217 (repository_source, enrollment, transfer, wizard, profiles, import), node 94/94, tsc (src + e2e), e2e enrollment+shell+transfer+import+help 59/59, help parity and release-notes checks. DCP af0e with git read access for the service account.
- 2026-10-12 scope additions from the user after validation (STATED): "ce e cu optiunea - use an existing clone on this repository - daca se inroleaza un proiect se presupune ca nu exita o clona" + choice "Yes, remove it (Recommended)" -> the existing-clone mode, its copy keys and ID derivation are removed (a matching clone at the chosen path is still reused); "la reviewers - trebuie sa mearga si fara review-uer" -> an empty reviewer list is valid ([delivery] reviewers = [] requests no review; forge adapters already skip an empty list) in config validation, web create, adore init, the wizard and the Settings reviewer editor. Red: e2e enrollment failed on the existing-clone button and on the client rejecting aegis_files "not-checked" for a pending clone (fixed in the verification check). REQ-UX-43f73ffd, REQ-UX-072cf049, REQ-UX-2761363b and REQ-UX-34718dd6 revised; help (four locales, parity ok), Web_Interface, Configuration_Reference, Component_Web_Frontend, knowledge, CHANGELOG and the Settings release note updated. pytest 239/239; ruff clean; node 94/94; tsc clean; e2e enrollment+settings 40/40, transfer+shell+import+help 44/44; release-notes check ok; DCP af0f.
- 2026-10-12 validate review round 5 (scope additions): spec-compliance FAIL - four places still said reviewers are required -> Web_Interface.md, Component_Config.md, knowledge config.md and config.example.toml (comment and MUST-set header) now say an empty list requests no review; unused i18n keys createHelpReviewers/createCloneHint removed. implementation-quality PASS with lows, applied: review row shows — for an empty reviewer list, dead repo-change branch/examples.repo/CSS removed, pending-clone AEGIS row says it is checked at creation (aegisAtCreate, four locales). tsc clean; node 94/94; e2e enrollment+transfer+settings+shell+import+help 83 passed (two settings tests needed a retry under load and pass in isolation, 3/3); pytest 168 + config example 5; DCP af10.
- 2026-10-12 validate review round 6 (scope additions): spec-compliance PASS (round 7: reviewer wording fixed everywhere, unused keys gone, aegisAtCreate consistent with REQ-FUNC-b3251e39); implementation-quality PASS (round 5, lows applied). `aegis.py check --task TASK-af0939e6 --strict` ok. DEVIATION validate: full suite still deferred by the user.
- 2026-10-13 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-13 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-af0939e6.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: Enroll new project and Clone project config start from a repository URL (Read repository detects forge, repository, Gitea login, default branch and a derived project ID; editable prefilled clone path; Continue waits for a successful read; clone only at creation with exclusive folder, marker, reuse of a matching clone, AEGIS/branch checks and cleanup); the existing-clone mode is removed; reviewers are optional (empty list requests no review) in config, web create, adore init, the wizard and Settings; four-locale copy, errors and help; docs, specs, requirements, CHANGELOG, release notes; DCP service account SSH key generated at the user's request
evidence: pytest 239/239 (targeted) + config example 5, ruff clean, node 94/94, tsc clean, e2e 83 passed across enrollment/transfer/settings/shell/import/help, help parity ok, release-notes check ok, aegis check --strict ok; DCP af10
issues: DEVIATION full suite deferred by user; tea is not installed on DCP, so the forge for 192.168.1.15 is chosen manually
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 6

## Delivery report (2026-10-13)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-FUNC-b3251e39 - Enroll a project from its repository URL and clone it at creation
  - REQ-UX-43f73ffd - Fill repository details from the URL and drop the stable ID field
  - REQ-UX-072cf049 - Five-step supported enrollment guidance
  - REQ-UX-2761363b - Explain every project creation field
  - REQ-UX-34718dd6 - Edit requested reviewers through reviewed configuration
- deviations: 2 recorded
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by pytest 217/217 (repository_source, enrollment, transfer, wizard, profiles, import), node 94/94, tsc (src + e2e), e2e enrollment+shell+transfer+import+help 59/59, help parity and release-notes checks. DCP af0e with git read access for the service account.
  - validate: full suite still deferred by the user.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=6
- diff vs task base 7c85eea: 46 file(s) changed, 1651 line(s) added
- checks: errors=0 warnings=18 notes=22
- checklist: 2/2 done

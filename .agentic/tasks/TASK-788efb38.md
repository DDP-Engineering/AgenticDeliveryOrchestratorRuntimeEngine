<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-788efb38 - Make egress proxy and network names unique per run

stage: done
type: fix
path: full
interaction: autopilot
requirements: REQ-SEC-553ebd62, REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f
parent:
branch: task/adore-web-interface
base: fc70d0f3cb869cbf7f6f38305a82791852ecb7d7
opened: 2026-10-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: in allowlist-proxy egress mode each run gets an egress proxy
  container and an internal network named from its executor container
  (`<slug>-run-<run ID>`), but the names are cut to 50 (proxy, before
  `-egress-proxy`) and 48 (network, after `<prefix>-`) characters. For a long
  repository path the ticket number is cut away, so every run of the project,
  and of another project whose names agree in those characters, gets the same
  proxy and network. Provisioning reuses an existing proxy by name, so a later
  run can run behind an earlier run's proxy (mounted with that run's, possibly
  another project's, allowlist config), and reaping one run removes a proxy
  and network another run still uses; cleanup can remove another project's
  shared proxy (stated exception of REQ-SEC-4a3f81cb).
Desired outcome: every run gets its own proxy and network name within the
  current length limits, and cleanup never removes a proxy or network another
  project's existing run uses.
Actors: conductor provisioning/reaping runs; operator running cleanup; other
  projects' runs on the same host.
Primary scenario: a run of gitea `dpasare/2026_Networked_Intelligent_Lab_Orchestrator`
  is provisioned -> ADORE creates a network and proxy whose names end in a
  short hash of the full executor name -> a second run of the same project gets
  different names -> reaping one leaves the other's proxy and network intact.
Examples: runs 26 and 27 of that project: today both use proxy
  `adore-run-gitea-dpasare-2026_Networked_Intelligent-egress-proxy`; after the
  change each has its own (`...-<10 hex>-egress-proxy`, still 63 characters).
  Run `adore-run-x` (short name): names stay `adore-run-x-egress-proxy` and
  `adore-egress-adore-run-x`.
Counterexamples: names that already fit are not changed; executor container,
  branch, worktree and state names are not changed.
In scope: proxy and network name derivation in
  `04_Software/adore/isolation.py` (provision, `remove_egress`, cleanup
  sweeps), handling of resources created under the old cut names, tests,
  REQ-SEC-4a3f81cb/spec exception, docs and knowledge.
Out of scope: executor container naming, run-ID ambiguity (`a/b-c` vs
  `a-b/c`), Docker labels, `open`/`none` egress modes (no proxy or network).
Constraints: names stay runtime-safe and within today's lengths (proxy name
  at most 63 characters, likely to stay a valid DNS label); offline tests with
  a fake runtime; standard library only (`hashlib`).
Success signals: tests show two long-named runs of one project and of two
  projects get distinct proxy and network names; reaping one run leaves the
  other's; short names are unchanged; cleanup keeps a proxy/network that any
  existing container of another run still derives.
Evidence:
  - STATED: task note "Make egress proxy and network names unique per run"
    (finding while scoping cleanup, TASK-d38bd74c); decide in frame how to
    handle resources created under the old cut names.
  - OBSERVED: `04_Software/adore/isolation.py` `_proxy_name` =
    `_safe_name(name, limit=50) + "-egress-proxy"`, `_egress_network_name` =
    `<prefix>-<_safe_name(name)>` (limit 48); `_ensure_proxy_context` creates
    the network ("exists" tolerated), runs the proxy only when absent and
    otherwise starts the existing one, then connects it with alias
    `adore-egress-proxy`; `provision` creates the executor with
    `--network <egress network>` only when the executor is absent and
    restarts an existing executor as-is; `remove_egress` removes the derived
    proxy and network in allowlist-proxy mode.
  - OBSERVED: `.agentic/specs/REQ-SEC-4a3f81cb.md` Assumptions and
    REQ-SEC-4a3f81cb prose carry the truncation exception;
    tests/test_isolation.py `test_container_provision_allowlist_proxy_lifecycle`
    pins short names; REQ-FUNC-7b4caf58 requires bounded derived names;
    REQ-FUNC-fcb2448b covers the allowlist-proxy lifecycle.
  - OBSERVED (DCP, read-only): all six profiles use egress mode `open`; the
    host has no ADORE proxy containers or egress networks.
  - INFERRED: 50 + `-egress-proxy` = 63 keeps the proxy name a valid DNS label.
  - INFERRED: after an upgrade, a parked long-named allowlist-proxy run whose
    executor already exists stays attached to its old-name network while
    provisioning would build a new-name proxy, so its egress breaks unless the
    old names are kept for that run.
Assumptions: SHA-256 of the full executor name cut to 10 hex characters is
  unique enough per host (40 bits).
Unknowns: other installations' in-flight allowlist-proxy runs with long names
  (none on DCP).
Decision-blocking questions:
  - Q1: resources created under the old cut names: (A) keep using them for a
    run whose executor already exists (detected from the runtime) and remove
    them at reap only when no other existing container uses them, or (B)
    clean break: new names only; such in-flight runs must be finished or
    re-provisioned before upgrading; cleanup still collects old names safely.
Proposed behaviors:
  1. A proxy or network name whose runtime-safe executor name fits its limit
     is unchanged; a longer one keeps its first characters and ends in `-`
     plus 10 hex characters of the SHA-256 of the full executor name, at the
     same maximum length.
  2. Provisioning, reaping and cleanup all use that derivation, so runs never
     share a proxy or network.
  3. Old cut names are handled per Q1.
  4. Cleanup removes an old cut name only when no existing container of
     another run derives it, so it never removes a proxy or network another
     project's existing run uses; the REQ-SEC-4a3f81cb exception is removed.
Path and reason: full - changes runtime resource names and the security
  boundary between projects.

| quick-path criterion | met | evidence |
|---|---|---|
| no new externally observable behavior | no | long proxy/network names change |
| no new interface or data format | no | name format changes |
| no new dependency | yes | `hashlib` (standard library) |
| existing requirement covers it | no | REQ-FUNC-7b4caf58 bounds names; nothing requires per-run uniqueness |
| no security or data-handling change | no | egress isolation between runs and projects |

## Requirement coverage

Behavior inventory (specs `specs/REQ-SEC-553ebd62.md`, `specs/REQ-SEC-4a3f81cb.md`):

| Frame outcome | Actor/system | Trigger or state | Response | Positive case | Boundary or failure | Observable result |
|---|---|---|---|---|---|---|
| Per-run names | runtime | provision / reap in allowlist-proxy | bounded name + hash when cut | runs 26/27 and two long projects distinct | short names unchanged; max lengths kept | runtime calls name distinct proxies/networks |
| Reap isolation | runtime | `remove_egress` of one run | removes only its names | run 27's proxy survives run 26's reap | old cut names not removed at reap (clean break) | remove calls name only run 26's resources |
| Cleanup boundary | cleanup | `adore cleanup` | removes new and unshared old cut names of targets | own done run's old names removed | old names shared with a protected run or another existing executor kept; executor listing failure removes no proxy/network | report and remaining resources |

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Per-run names, reap isolation (behaviors 1-3) | provisioning and reaping use per-run bounded names | REQ-SEC-553ebd62 (new) | distinct names for long runs/projects | short names unchanged; old names never reused | pytest, fake runner | `_bounded_name` + `_proxy_name`/`_egress_network_name` |
| Cleanup boundary (behavior 4) | old cut names removed only when no protected run or other existing executor derives them | REQ-SEC-4a3f81cb (revised: exception removed) | other project's executor keeps its shared old name | listing failure removes no proxy/network | pytest, fake runtime | sweeps derive both forms; orchestrator adds other listed executors to retained |
| Cleanup removal (behavior 4) | own finished runs' new and unshared old names removed | REQ-FUNC-aae1904f (verification revised) | done run's old proxy/network removed | shared old names kept | pytest | same as above |

## Design

Behavior lives in the two specs; this note fixes the shape.

- **Naming (REQ-SEC-553ebd62; technical: names stay within today's limits).**
  `ContainerManager._safe_name(value)` returns the unbounded runtime-safe form;
  new `_bounded_name(value, limit)` returns it unchanged when it fits, else
  `safe[:limit - 11].rstrip("-._") + "-" + sha256(value)[:10]`.
  `_proxy_name` = `_bounded_name(name, 50) + "-egress-proxy"`;
  `_egress_network_name(name, prefix)` = `<prefix>-` + `_bounded_name(name, 48)`.
  Provision, `_ensure_proxy_context` and `remove_egress` keep calling these,
  so they switch to per-run names with no other change (RULING-002: no
  old-name lookup at provision or reap).
- **Old cut names (REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f).** Private
  `_proxy_names(name)` / `_egress_network_names(name, prefix)` return the
  per-run and old cut (`safe[:50]`, `safe[:48]`) forms. The three cleanup
  sweeps derive `wanted` from both forms of `targets` minus both forms of
  `retained`.
- **Other existing executors (REQ-SEC-4a3f81cb).** New public
  `ContainerManager.list_executors(prefix)` = `list_containers(prefix)`
  without proxy names. `Orchestrator.cleanup` lists once: the result feeds
  `_cleanup_run_ids` discovery (replacing its own listing) and, minus the
  targets, is added to `retained` for the proxy and network sweeps. When the
  listing raises `IsolationError`, discovery uses no container names and the
  proxy and network sweeps are skipped (fail closed); executor and worktree
  removal continue.
- **Compatibility.** Short names unchanged. Long-named allowlist-proxy runs
  provisioned before the upgrade must be finished or re-provisioned (documented
  in Recovery_And_Maintenance and CHANGELOG); their old names are collected by
  cleanup once unshared. No config, command or report change. Rollback = revert.
- **Security.** A run never reuses another run's proxy (and its allowlist
  config); cleanup never removes a proxy or network still derived by another
  existing executor.
- **Test seams.** `tests/test_isolation.py`: provisioning two long-named runs
  (distinct network/proxy names, lengths), short name unchanged (existing
  lifecycle test), `remove_egress` of one run, two-project names, sweeps with
  old cut names (target removed, retained kept). `tests/test_orchestrator.py`:
  old cut names of a done run removed; shared with a handed-off run or another
  project's existing executor kept; executor listing failure removes no proxy
  or network; `FakeContainers.list_executors`.
- **Alternatives rejected.** Raising the limits (breaks the 63-character DNS
  label); hashing every name (renames all existing short-name resources);
  keeping old names per run (RULING-002 chose a clean break).
- **Risks / open decisions.** 40-bit hash clash negligible (spec assumption).
  None open. No component structure change; no architecture drawing owed.
- **Expected files.** `04_Software/adore/isolation.py`, `orchestrator.py`;
  `04_Software/tests/test_isolation.py`, `test_orchestrator.py`;
  `01_Documentation/{CLI_Reference,Operations_Guide,Recovery_And_Maintenance}.md`
  and others naming proxy/network names (Security_And_Credentials to check);
  `05_SoftwareDocu/Component_{Isolation,Orchestrator,CLI}.md`; knowledge
  `isolation.md`; `CHANGELOG.md`.

## Log

- 2026-10-04 frame: full path (changes runtime resource names and the inter-project egress boundary; no covering requirement). Checkpoint mode; scope and Q1 (old cut names) presented, awaiting the user.
- 2026-10-04 frame accepted: user chose Q1 "Clean break" and "Autopilot to validate"; scope as framed with behavior 3 = clean break; interaction set to autopilot; stop before deliver.
- 2026-10-04 specify: 1 requirement created (REQ-SEC-553ebd62, draft, spec `specs/REQ-SEC-553ebd62.md`), 2 revised (REQ-SEC-4a3f81cb prose: truncation exception removed, verification and spec `specs/REQ-SEC-4a3f81cb.md` steps 4-5 extended to old cut names and listing failure; REQ-FUNC-aae1904f verification: old cut names), 0 reused, 0 retired. REQ-FUNC-7b4caf58 (bounded identity names) and REQ-FUNC-fcb2448b (allowlist-proxy lifecycle) stay consistent: names remain bounded and the lifecycle unchanged.
- 2026-10-04 design: note in `## Design` (`_bounded_name` with 10-hex SHA-256 suffix for cut names; sweeps derive per-run and old cut forms; other existing executors retained; fail closed on listing failure); no architecture change. Advanced to build (autopilot).
- 2026-10-04 build red: REQ-SEC-553ebd62, REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f; command=`.venv/Scripts/python.exe -m pytest -q tests/test_isolation.py tests/test_orchestrator.py -k "egress or cleanup"` (from 04_Software); exit=1 (5 failed); expected missing behavior=three long executor names share one network/proxy, reaping run 26 targets run 27's proxy, sweeps do not derive per-run names, another project's executor loses its shared old cut proxy, and a failed executor listing does not stop the proxy/network sweeps. The unshared old-cut-name removal test already passes (regression guard).
- 2026-10-04 build green: REQ-SEC-553ebd62, REQ-SEC-4a3f81cb, REQ-FUNC-aae1904f; command=`.venv/Scripts/python.exe -m pytest -q tests/test_state.py tests/test_isolation.py tests/test_orchestrator.py tests/test_checkpoint_handoff.py tests/test_smoke.py tests/test_profile_cli.py tests/test_release_consistency.py tests/test_identity.py` (from 04_Software); exit=0 (289 passed, 1 skipped); ruff exit=0. isolation.py: `_bounded_name` (10-hex SHA-256 digest when cut), per-run `_proxy_name`/`_egress_network_name`, `_proxy_names`/`_egress_network_names` (per-run + old cut), `list_executors`; orchestrator.py: one executor listing feeds discovery and keeps other existing executors' proxy/network names, skipping both sweeps when the listing fails. REQ-SEC-553ebd62 active; links updated on all three. Docs: CLI_Reference, Operations_Guide, Recovery_And_Maintenance (exception removed, upgrade note), Component_CLI/Isolation/Orchestrator, knowledge isolation, CHANGELOG (Fixed + upgrade note). `check --task` only pre-existing warnings. Advanced to validate.
- 2026-10-04 validate review round 1: spec_compliance=changes_required (MEDIUM: spec REQ-SEC-553ebd62 examples contradict rule 2 and the code - real long proxy is 62 characters, `...2026_Networked-<h>-egress-proxy`; MEDIUM: REQ-SEC-553ebd62 covers cleanup but its verification/linked tests do not; LOW notes accepted: 40-bit digest uniqueness is probabilistic (spec assumption), journal Frame example says 63 characters); implementation_quality=changes_required (MEDIUM: with a slug of 36+ characters the per-run proxy name no longer starts with `<slug>-run-`, so the prefix-listed proxy sweep cannot find orphaned proxies - a regression; MEDIUM: no test fails when list_executors stops excluding proxies, although an old cut proxy name derives itself and would retain itself; LOW: pin a literal expected name, discovery by container name alone untested (pre-existing), CRLF in new artifacts - not reproduced, 0 CR bytes by Python count). Routed to build for fix cycle 1 of 4.
- 2026-10-04 build fix cycle 1 red: REQ-SEC-553ebd62, REQ-SEC-4a3f81cb; command=`.venv/Scripts/python.exe -m pytest -q tests/test_isolation.py tests/test_orchestrator.py -k "egress or cleanup"` (from 04_Software); exit=1 (7 failed: the proxy sweep still takes and lists by the executor prefix); probe of the current sweep with a 36-character slug: the per-run proxy `examplex-digital-delivery-agent-prod-ru-1cb1a4a1e2-egress-proxy` is filtered out and not removed (expected missing behavior). New end-to-end unshared-old-name, container-only discovery and literal-name assertions are regression guards.
- 2026-10-04 build fix cycle 1: cleanup_egress_proxies(targets, retained) lists proxy candidates by the `-egress-proxy` suffix (long-slug per-run proxies are found); list_executors docstring states why proxies are excluded; tests: long-slug proxy sweep, end-to-end unshared old cut names removed (fails if proxies count as executors), container-only state-less run, literal per-run names pinned, existing sweep tests on the new signature; spec REQ-SEC-553ebd62 examples corrected (62/63-character literals) and interface updated; REQ-SEC-553ebd62 verification covers cleanup with linked sweep tests; REQ-SEC-4a3f81cb links the end-to-end test; Component_Isolation signature. Focused `pytest -q tests/test_state.py tests/test_isolation.py tests/test_orchestrator.py tests/test_checkpoint_handoff.py tests/test_smoke.py tests/test_profile_cli.py tests/test_release_consistency.py tests/test_identity.py` exit=0 (291 passed, 1 skipped); ruff exit=0; evolution refreshed. Returned to validate for review round 2.
- 2026-10-04 validate review round 2: spec_compliance=approved; implementation_quality=approved (independent judges; quality judge observed full suite 728 passed/1 skipped, ruff clean, 0 CR bytes; mutation runs on a scratch copy killed 10 of 11 mutants incl. proxy filter removal, prefix-listed proxies, dropped old-cut derivations, dropped fail-closed skip, protected-only retention, dropped container discovery; the survivor - removing the redundant endswith in the proxy listing - is equivalent). All round-1 findings resolved. Accepted LOW notes (changing them would invalidate both verdicts): Design bullet does not mention the (targets, retained) proxy-sweep signature (Log and specs do); linked test name still says "truncated" (docstring current); cleanup lists executors twice (one extra runtime call); retention covers executors under this slug only (cross-slug old-cut collision theoretical); 40-bit digest uniqueness probabilistic (spec assumption).
- 2026-10-04 validate final: command=`python .agentic/aegis.py check --task TASK-788efb38 --strict --run`; exit=0; test ok 47.9s, lint ok, frontend ok; errors=0, warnings=3, all pre-existing (tracked fingerprint sidecars; TASK-5e99ee1d Handoff status; TASK-c765e6b4 ruling record). Knowledge isolation reconciled; requirements re-read; no manual verification owed; evolution refreshed after the last candidate edit. Validate complete; advanced to deliver; stopping for delivery approval (RULING-003).
- 2026-10-04 deliver: validation evidence, verdicts, accepted notes, diff (15 modified, 3 new files), exclusions, upgrade note and outcome presented; no deviations recorded. User approved "Deploy to DCP, then commit": outcome = DCP deployment of the validated candidate (adore/isolation.py, orchestrator.py), then one repository-local commit (no push/PR).
- 2026-10-04 deliver DCP: archive SHA-256 6d253130f7fdd445e975891c4d75b80c58a6481d9a9d0c135b3b069c54f5fcb1 verified on host; live isolation.py/orchestrator.py matched base fc70d0f; backups suffix .pre-egress-names-20261004073857; services restarted and active; installed modules equal the bundle; live probe: long executor -> `adore-run-gitea-dpasare-2026_Networked-bdeedb3462-egress-proxy`, short -> `adore-run-x-egress-proxy`; health/ready/UI 200; read-only `adore --profile nilo status` exit 0. No cleanup was run; DCP profiles use egress mode open, so no proxies or networks exist there.
- 2026-10-04 deliver close-out: DCP deployment succeeded; stage done; this repository-local commit carries the candidate, requirements, specs, journal and report (no push or PR requested).

## Rulings

- RULING-001 | date=2026-10-04 | decision=work stays on task/adore-web-interface, after TASK-d38bd74c (fc70d0f) | reason=user: "Do this task here"; the task note names this branch and builds on the project-scoped cleanup | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=clean break for old cut names: provisioning and reaping use only the new names; in-flight long-named allowlist-proxy runs are finished or re-provisioned before upgrading (documented); cleanup removes old cut names only when no other existing container derives them | reason=user answered Q1 "Clean break" | source=user | supersedes=none
- RULING-003 | date=2026-10-04 | decision=autopilot through specify, design, build and validate with explicit review, then stop before deliver | reason=user chose "Autopilot to validate" at the frame checkpoint | source=user | supersedes=none

## Handoff


current: done
status: ready
next: none - delivered; DCP runs the candidate and the local commit records it
must_read: .agentic/tasks/TASK-788efb38.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated candidate deployed to DCP and committed locally on task/adore-web-interface
evidence: check --strict --run exit=0; review round 2 approved/approved; DCP deploy verified (live name probe, module hashes, health/ready 200, services active)
issues: accepted LOW review notes (see log)
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-04)

- stage: deliver; type: fix; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-SEC-553ebd62 - Give each run its own egress proxy and network
  - REQ-SEC-4a3f81cb - Confine cleanup to the current project's resources
  - REQ-FUNC-aae1904f - Remove the current project's finished and orphaned run resources
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base fc70d0f: 18 file(s) changed, 798 line(s) added
- checks: errors=0 warnings=4 notes=31
- checklist: 4/6 done; open: agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it

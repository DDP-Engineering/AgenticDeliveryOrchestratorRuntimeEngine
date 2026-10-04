<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-SEC-4a3f81cb — Confine cleanup to the current project's resources

Also governs REQ-FUNC-aae1904f (removal of the project's finished and orphaned
run resources) and REQ-REL-2219035e (corrupt runs keep their resources).

## Behavior

`adore [--profile P] cleanup` works only on run IDs that belong to the current
project.

1. **Run-ID form.** A project's run IDs have the form
   `<platform kind>-<platform repo with "/" as "-" and spaces removed>-<ticket number>`,
   the value ADORE derives for every run. A name has the project's form only
   when everything after `<platform kind>-<safe repo>-` is one or more ASCII
   digits. For gitea `dpasare/alpha`, `gitea-dpasare-alpha-9` has the form;
   `gitea-dpasare-alpha-tools-4` does not.
2. **Owned run IDs** are the union of:
   - runs recorded in the project's state store, whatever their name;
   - run directories in the project's state store whose state is corrupt;
   - directories under the worktree root whose name has the project's form;
   - executor containers named `<slug>-run-<run ID>` whose run ID has the
     project's form.
3. **Protected run IDs** are recorded runs whose lifecycle is active,
   `failed`, `handed-off` or `handoff-pending`, and every corrupt run.
   **Eligible run IDs** are owned run IDs that are not protected: `done`,
   `cancelled` and `stale` runs, and form-matching run IDs without state.
4. For each eligible run ID, cleanup removes whichever of these exist:
   - the executor container `<slug>-run-<run ID>` and the run's recorded
     container name;
   - the egress proxy of each such executor container (the runtime-safe
     executor name cut to 50 characters, then `-egress-proxy`), whatever the
     current egress mode;
   - the egress network of each such executor container under both the
     canonical `adore-egress` prefix and the configured `network_prefix`
     (`<prefix>-<runtime-safe executor name cut to 48 characters>`), whatever
     the current egress mode;
   - the worktree directory `<worktree root>/<run ID>`, deregistered from Git
     and then removed from disk.
5. A resource is removed only when its exact name is derived in step 4 from
   an eligible run ID **and** is not also derived from a protected run ID.
   Everything else stays: other projects' resources (even with the same slug,
   network prefix or worktree root), look-alike project names, unrelated
   folders, and proxy or network names shared through truncation with a
   protected run. The one exception comes from that truncation: a proxy or
   network name that another project's run also derives can be removed (see
   Assumptions).
6. The stale-lock handling is unchanged: a provably stale lock is cleared, a
   live lock is reported with its holder and kept.
7. Runtime failures stay best-effort per resource: a failed listing or
   removal is skipped, the rest continues, and the command exits 0.

## Data / interface

- Command line unchanged: `adore [--profile P] cleanup`; exit 0.
- JSON report keys unchanged: `lock_cleared`, `lock_held_by`,
  `containers_removed`, `proxy_containers_removed`, `egress_networks_removed`,
  `worktrees_removed`, `corrupt_runs`. The three container/network lists name
  only resources that existed and were removed; `worktrees_removed` names the
  run IDs whose directory existed and was removed; `corrupt_runs` names the
  corrupt run IDs. Lists are sorted.
- The note printed after the report for corrupt runs is unchanged.

## Examples

- Profiles A (gitea `dpasare/alpha`) and B (gitea `dpasare/beta`) share slug
  `adore`, worktree root `worktrees` and prefix `adore-egress`. B has a
  `working` run `gitea-dpasare-beta-3` and a `handed-off` run
  `gitea-dpasare-beta-2`. A has a `cancelled` run `gitea-dpasare-alpha-5`, a
  `failed` run `gitea-dpasare-alpha-6`, and a container
  `adore-run-gitea-dpasare-alpha-9` with its worktree directory but no state.
  Cleanup for A removes the containers, proxies, networks and worktrees of
  runs 5 and 9; run 6 and all of B's resources remain.
- Under the same root, `gitea-dpasare-alpha-tools-4` and a folder `notes`
  remain after cleanup for A.
- A's run `gitea-dpasare-alpha-7` has an unreadable `state.json`: its
  worktree, container, proxy and network remain, and the report lists it under
  `corrupt_runs`.
- Truncation: for gitea `dpasare/2026_Networked_Intelligent_Lab_Orchestrator`
  with slug `adore`, runs 26 (`done`) and 27 (`handed-off`) share proxy
  `adore-run-gitea-dpasare-2026_Networked_Intelligent-egress-proxy` and network
  `adore-egress-adore-run-gitea-dpasare-2026_Networked_Intellige`. Cleanup
  removes run 26's container and worktree and keeps the shared proxy and
  network.

## Acceptance

- Automated tests cover every example above with a fake runtime.
- Existing cleanup tests still hold: failed-run resources are kept, a live
  lock is reported and kept, and the CLI prints the report keys.

## Assumptions and open decisions

- ADORE names executor containers and worktree directories only from the
  derived run ID; resources named any other way are not collected and need
  manual removal.
- Repository paths that differ only by `/` versus `-` (`a/b-c`, `a-b/c`) map
  to the same run IDs; this is pre-existing and outside this contract.
- Orphans of projects that no longer have a profile belong to no project's
  cleanup; the operator removes them manually.
- Proxy and network names are cut to 50 and 48 characters, so all runs of a
  project with a long repository path share one proxy name and one network
  name, and two projects whose executor names agree in those first characters
  share them too. Such a shared name belongs to every run it is derived from;
  cleanup keeps it whenever one of the current project's protected runs
  derives it. Unique proxy and network names are a separate naming change.
- A proxy or network whose run has no state, worktree or executor container
  left cannot be tied to a run ID and stays; the operator removes it manually.

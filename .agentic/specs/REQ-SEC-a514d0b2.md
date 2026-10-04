<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-SEC-a514d0b2 — Restrict web project deletion to confirmed archived projects

Also governs REQ-FUNC-bcaf01be (the CLI/engine removal it triggers).

## Behavior

1. `POST /api/v1/projects/{name}/delete` (administrator, CSRF) with
   `{"confirm_name": str, "idempotency_key": str(8-128)}`:
   - project resolved as for other project routes (404 `project_not_found`);
   - not archived -> 409 `project_not_archived`;
   - `confirm_name` not exactly the profile name -> 422
     `delete_confirmation_mismatch`;
   - queued/running web operation, unreadable run state (503
     `run_state_corrupt`) or a run whose lifecycle is not terminal or
     human-owned -> 409 `project_has_active_work`;
   - otherwise enqueue operation action `delete` (empty target), audit
     `project-delete-requested`, return the operation `{id, status}` (200).
   A repeated request while a delete is queued returns 409
   `project_has_active_work`.
2. Worker, for action `delete`: requires the actor to be an enabled
   administrator, the profile to exist, its project ID to match the operation
   and the profile to be **archived** (all other actions keep requiring it to
   be unarchived). Otherwise the operation fails with a reason and nothing is
   run. It runs `python -m adore profile delete <name> --force
   --remove-resources` with `ADORE_HOME` set, records succeeded/failed/
   uncertain like other operations, and audits `project-deleted` on success.
3. `GET /api/v1/operations/{id}` for a `delete` operation whose project no
   longer exists returns the operation to administrators (developers 404).
4. CLI `adore profile delete <name> --force --remove-resources`:
   - loads and validates the profile's configuration (invalid -> error,
     nothing deleted); takes the conductor lock (held -> error);
   - refuses (error, nothing deleted) when any run is neither terminal
     (`done`, `failed`, `cancelled`) nor human-owned (`handed-off`,
     `handoff-pending`), or when run state is corrupt;
   - for each run recorded in this project's state except human-owned runs,
     removes its executor container (with its egress proxy and network) and
     its worktree directory; it never sweeps by container-name prefix or the
     worktree root, which other projects on the host may share;
   - releases the lock, deletes `<home>/profiles/<name>/` (profile, config and
     default state), and leaves a `store_root` outside ADORE home untouched;
   - prints JSON: `{"deleted": name, "containers_removed": [...],
     "worktrees_removed": [...], "worktrees_retained": [...],
     "state_retained": path|null}` and exits 0; if removing the profile
     directory fails it prints the same report with `"deleted": null` and an
     `"error"` and exits non-zero.
   Without `--remove-resources`, `profile delete` behaves as before.

## Data / interface

- Error codes `project_not_archived`, `delete_confirmation_mismatch` are new
  and need EN/FR/DE/RO messages.
- Web store operation actions gain `delete`.
- Audit history, prices and grants in `web.db` are kept; they are bound to the
  immutable project ID, so a later project with the same name cannot inherit
  them.

## Examples

- Archived `alpha`, runs done/failed/handed-off, confirm `alpha` -> operation
  queued; worker removes containers and worktrees except the handed-off run's,
  deletes the profile; status `succeeded`; Projects no longer lists alpha.
- Unarchived `alpha` -> 409 `project_not_archived`.
- Confirm `Alpha` -> 422 `delete_confirmation_mismatch`.
- A run `working` -> 409 `project_has_active_work`.

## Acceptance

- API, worker and CLI tests for every case above; manual browser check of
  the confirmation flow.

## Assumptions and open decisions

- Human-owned worktrees and an external `store_root` are kept (task RULING-002);
  the operator removes them manually when no longer needed.

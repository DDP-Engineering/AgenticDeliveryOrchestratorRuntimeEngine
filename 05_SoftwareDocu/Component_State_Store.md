<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: State Store (`ador/state.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/ador/state.py` - file version 0.1.1.
> Design: Orchestrator_Design_And_Decisions.md section 8a.

## 1. Purpose

The local, **authoritative** run state. Labels and comments on the ticket are
only a human-facing reflection; what ADOR trusts across restarts, parks, and
resumes lives under `.<slug>/`. This component owns that tree, the
deterministic run identity, and the fail-closed handling of damaged state.

## 2. Responsibilities

- Layout per run: `.ador/runs/<run-id>/` with
  - `ticket.json` - the ticket snapshot taken at pickup,
  - `state.json` - the `RunState` (stage, lifecycle, comment ids, rounds,
    budget counters, park bookkeeping, resource names, timestamps),
  - `journal.jsonl` - append-only orchestrator events.
- `derive_run_id(platform, project, iid)` - deterministic, filesystem-safe,
  stable across restart/resume (never random; design 8a).
- `content_hash(title, description)` - drift detection: a changed hash on
  re-poll means the spec moved while the run was parked/in progress.
- Single-instance lock (`<root>/<slug>.lock`, exclusive create) and the
  global pause flag (`<root>/paused`) used by `ador pause` / `ador resume`.

Explicitly not owned: reflecting state to the ticket (forge adapters) and
deciding transitions (orchestrator).

## 3. Implementation Overview

- `RunState` dataclass; `from_dict` ignores unknown keys so older ADOR
  versions can read state written by newer ones (forward compatibility).
- All JSON writes are **atomic** (tmp file + `replace`), so a crash never
  leaves half a file.
- `save` stamps `created_at` on first save and refreshes `updated_at`.
- **Fail-closed policy** (Testing Rules in `AGENTS.md`):
  - corrupt/wrong-shape/key-incomplete `state.json` or `ticket.json` ->
    `StateError`; callers skip or escalate, never reinitialize;
  - `list_runs()` skips corrupt runs so operational commands keep working;
    `invalid_runs()` keeps them visible; nothing is silently deleted;
  - a corrupt **lock file** still counts as held - never start a second
    poller on damaged evidence;
  - `read_journal()` skips torn lines (journal appends are not atomic; a
    crash can tear the tail; the authority is `state.json`, not the journal).

## 4. Dependencies

- Internal: `ador.util.utc_now_iso`.
- External: Python standard library only (`json`, `hashlib`, `pathlib`,
  `shutil`, `os`).

## 5. Inputs And Outputs

- Inputs: store root + slug (from config), `RunState` objects, ticket
  mappings, journal events.
- Outputs: the persisted `.ador/` tree; loaded `RunState` / ticket / journal
  records; lock and pause status.

## 6. Data Contracts

- `run_id` = `<platform>-<project-with-dashes>-<iid>`; it names the worktree
  dir, the branch (`ador/<run-id>`), the container (`ador-run-<run-id>`), and
  the state dir - one identity for every per-run resource.
- Journal record shape: `{"ts": <iso>, "event": <name>, ...fields}`.
- Lock record shape: `{"pid": <int>, "acquired_at": <iso>}`; `lock_info()`
  returns `{}` when held-but-unreadable and `None` when free.
- The orchestrator run state is fully independent from the target repo's
  `.agentic` workflow run (design 8a); neither records the other's id.

## 7. Workflow Integration

Every poll pass reads and writes through this store: pickup snapshots the
ticket, each gate transition updates `state.json` and appends journal events,
park/resume rely on the recorded comment ids and `parked_at`, and metrics
(later phase) summarize the journal at terminal states. The CLI (`status`,
`runs`, `pause`, `resume`) is a thin view over it.

## 8. Usage

```python
from ador.state import RunState, StateStore, derive_run_id

store = StateStore(".ador", slug="ador")
run_id = derive_run_id("gitlab", "grp/proj", 14)
store.save(RunState(run_id=run_id, ticket_iid=14))
store.journal(run_id, "picked", ticket=14)
```

## 9. Validation And Tests

- `tests/test_state.py`: run-id stability, hash drift detection, save/load
  round-trip, forward-compatible loading, snapshot + journal ordering,
  listing/deletion, missing-run error, lock exclusivity, pause flag, and the
  corrupted-state suite (corrupt state/ticket JSON -> `StateError`, corrupt
  runs skipped-but-reported, torn journal tail, corrupt lock counts as held).
- Minimum validation after a change: `uv run --group dev pytest tests/test_state.py`.

## 10. Limitations And Future Work

- The lock is not stolen automatically on staleness; `ador cleanup` (later
  phase) will clear stale locks after checking the recorded pid.
- Single-orchestrator assumption: the lock protects one store on one host;
  multiple instances would need a shared lock (out of scope for v1).
- Retention policy for terminal-state run dirs (keep/purge) arrives with the
  reconciliation phase.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Clone Cleanup (`adore/clone_cleanup.py`)

## 1. Purpose

Decide whether a deleted project's local clone may be removed, so the clones that
enrollment makes under `<ADORE home>/repos` do not pile up after deletion.

## 2. Responsibilities

- `clone_decision`: removable only when the configured `repo_path` is absolute, not a
  symlink, resolves under `<ADORE home>/repos` (not the folder itself), is a git clone
  (`.git` folder) whose origin names the project's owner/repository, is not the clone
  path of another project and holds no other project's worktree root or state root
  (another project with a relative clone path, or an unreadable or invalid profile,
  counts as using it), has no entry under `.git/worktrees` and a clean
  `git status --porcelain`. Otherwise the first reason: `outside-repos` (also for any
  symlinked folder or Windows junction between `repos` and the clone), `missing`, `not-a-clone`,
  `origin-mismatch`, `shared`, `worktrees`, `uncommitted`, or `unknown` for a
  malformed configuration or an unreadable path.
- `project_clone_decision`: before the resource sweep, ignores linked worktrees
  (`linked_worktrees_ok`, the sweep removes ADORE's own) but keeps the clone with
  `worktrees` while a run the sweep keeps (handed-off, handoff-pending, or made by the
  local backend while the project now uses containers) still has its worktree folder, or
  while a linked worktree exists that is not one of this project's runs.

## 3. Workflow Integration

`GET /api/v1/projects/{name}/delete-preview` shows the decision in the Delete project
dialog (`web/src/DeleteCloneOption.tsx`, unticked option or the reason it stays).
`remove_clone: true` on the delete request rechecks it and queues the delete with target
`remove-clone`; the worker adds `--remove-clone`. `adore profile delete --remove-resources
--remove-clone` checks before the resource sweep (an unsafe clone deletes nothing), runs
`git worktree prune` and checks again after it, deletes the profile and then removes the
clone; a clone that became unsafe, or is still present after removal, is kept and
reported (`removal-failed`).

## 4. Validation And Tests

`tests/test_clone_cleanup.py` covers the removable case, every keep reason, symlinks, the
preview, the 409 refusal, the worker argument and CLI removal, refusal and retention. The
e2e `jobs.spec.ts` lifecycle test drives the dialog option.

## 5. Limitations

Local branches that were never pushed and files ignored by git are not checked (runs
push their branches to the forge; people work in worktrees, not in ADORE's clone). The
repository match compares owner/repository, not the host. Clones outside
`<ADORE home>/repos` are never removed.

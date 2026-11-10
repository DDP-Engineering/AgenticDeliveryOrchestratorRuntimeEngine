<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Host folder selection

## Routing

Clone destination, automatic/custom location and Choose folder requests start at
`adore/web/host_folders.py`, `web/src/HostFolderPicker.tsx` and `hostFolders.ts`.
Focused tests are `tests/test_host_folders.py`, `web/tests/hostFolders.test.mjs`
and `web/e2e/host-folders.spec.ts`. Actual Git clone/ownership/publication belongs
to web-interface.md and profiles.md, not to directory browsing.

## Purpose and boundaries

Offer administrator-only read-only navigation of the ADORE host filesystem.
Enrollment retains manual input, automatic default reset and final reviewed
creation; the dialog never creates a directory or reads file contents.

## Public interface

GET `/api/v1/host-folders?path=...`, admin-only/no-store, returns system, path,
parent, roots, folders [{name,path}] and truncated. Empty path selects account
home. Invalid/missing/file/linked/unreadable paths return typed HTTP 400; oversized
query returns 422. No authentication/developer authority returns 401/403.

## Invariants

Native absolute printable paths only, 4096-character bound, no traversal,
UNC/device, mapped Windows network or symlink/reparse navigation. At most 200 folders and a 2000-entry
scan, with truncated disclosure. Browser validates shape/paths/direct children,
bounds and uniqueness. Confirmation returns an exact existing directory; new
destinations are edited in the main clone-path input.
Requests are timed/abortable, stale/cancelled results ignored; modal restores focus.

## Change map

| Request | Start | Focused proof |
|---|---|---|
| Native path/listing/error contract | host_folders.py, web/app.py | test_host_folders.py |
| Automatic/custom clone selection | HostFolderPicker.tsx, EnrollmentWizard.tsx | host-folders.spec.ts, enrollment.spec.ts |
| Transport/name validation | hostFolders.ts | hostFolders.test.mjs |

## Key behaviors

REQ-FUNC-f47164f2 owns automatic/custom clone choice and bounded host selection.
Browser path entry navigates the ADORE server filesystem. The compact modal uses
a single address bar, starting locations, selectable rows and Select folder/Cancel.
Single click selects; double-click/Enter opens; arrows/Home/End move selection;
Back and Parent use successful read-only navigation. Pending/error/address-mismatch
state disables confirmation and stale results cannot modify history or draft.
A successful listing normalizes the requested address only if the operator has
left it in the address bar. The reviewed enrollment flow owns clone creation.

## Files

Exact source/tests above, setupCopy.ts for four locales and styles.css for modal
and narrow layouts. Component_Host_Folders.md documents schemas and limits;
Web_Interface.md and four-locale projects help explain operation.
02_Tools/verify_package.py exercises the endpoint in both native archives.

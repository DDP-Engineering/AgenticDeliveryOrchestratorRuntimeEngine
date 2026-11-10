<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Host folder selection

## 1. Purpose

Administrators select a clone destination on the computer running ADORE through
same-origin directory navigation. The browser never uploads a local folder.

## 2. Responsibilities

`adore/web/host_folders.py` validates native paths and lists directories only.
`HostFolderPicker.tsx` owns automatic/custom choice and a compact web modal with
Back/Parent navigation, an address bar, starting locations and selectable directory
rows. One click selects a row; double-click or Enter opens it; Select folder
confirms that exact existing directory (or the current directory when no row is selected). Existing enrollment
preview/publication owns clone validation, writes, ownership and rollback.

## 3. Implementation Overview

`list_host_folders(path=None)` defaults to the current account home. It reads at
most 2001 entries to detect the 2000-entry scan cap and returns at most 200 folder
records. Results are sorted within the bounded subset. Symlinks and Windows
reparse directories are omitted/refused; UNC/device and mapped Windows network paths, traversal and relative
paths fail closed. Folder names and paths are printable and bounded. Files are
not opened. No selection operation creates or changes a directory.

## 4. Dependencies

Python standard library, existing FastAPI administrator authorization, React
native dialog and fetch. The actual API process account supplies OS permissions.

## 5. Inputs And Outputs

Admin-only GET `/api/v1/host-folders?path=<absolute path>` returns no-store JSON:
`system`, `path`, nullable `parent`, `roots` (Windows drive roots/Linux root and
account home), `folders: [{name, path}]`, `truncated: bool`. Query length is at most
4096. Invalid/missing/file/linked/unreadable directories return value-free HTTP
400 `host_folder_unavailable`; oversized transport returns 422. Anonymous and
developer requests receive 401/403 before filesystem access.

## 6. Data Contracts

`hostFolders.ts` validates the full response shape, absolute native path family,
direct parent-child relationship, limits and duplicate entries. Existing directory
names retain their native form. Folder metadata and successful navigation history
stay in modal memory; only confirmation changes the clone draft. A new clone
destination can be typed in the main form and is validated by existing enrollment
review/create; directory selection itself never creates a folder.

## 7. Workflow Integration

After Read repository, Automatic location uses the proposed `<ADORE home>/repos/id`
and a read-only path field. Custom location enables manual text and Choose folder.
The modal starts at account home. Address entry/Enter, starting locations, Back
and Parent navigate; arrow/Home/End keys select/focus directory rows. The compact
footer contains Select folder and Cancel. Cancel/Escape/selection restore focus. An AbortController and generation guard prevent
late or cancelled reads from replacing navigation. A successful read normalizes
its requested path only if the address still matches it. Failed reads disable selection;
manual clone text and the automatic reset remain available. Creation still
requires exact review and existing clone/origin/AEGIS/branch checks.

## 9. Validation And Tests

`tests/test_host_folders.py`, frontend `tests/hostFolders.test.mjs`, and Chromium
`e2e/host-folders.spec.ts` exercise Windows/Linux names, administrator authority,
malformed and inaccessible paths, bounds, links, no writes, cancellation, mobile
and all four locales. `02_Tools/verify_package.py` verifies the packaged endpoint
on native Windows/Linux with inert fixtures and isolated data.

## 10. Limitations

Only existing, readable, non-linked directories can be browsed. New destinations
are entered in the main clone-path field; permissions are checked again at creation. Truncated listings
require a more specific manually entered path. Manual clone destinations retain
the normal configuration validation. Host filesystem operations use OS latency;
request cancellation/timeout bounds the browser wait, not a hung filesystem call.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Release Notes (`adore/release_notes.py`)

## 1. Purpose

Hold ADORE's user-facing release notes in one structured, four-locale file and
serve them to the web About > What's new window, while a repository check keeps
them short, user-oriented and aligned with `CHANGELOG.md`.

## 2. Responsibilities

- Define the document: `adore/release_notes.toml` (schema 1), one `[[release]]`
  per release with `Unreleased` first and released versions newest first, each
  dated like its `CHANGELOG.md` heading; `[[release.entry]]` items carry a
  category (`new`, `improved`, `fixed`) and a `topic` and `text` table in `en`,
  `fr`, `de` and `ro`.
- `parse_release_notes` / `load_release_notes`: enforce the shape the web API
  serves (`ReleaseNotesError` otherwise).
- `contract_issues`: the authoring contract - every locale present, topic at
  most 40 and text at most 100 characters, no backticks, file names, paths,
  endpoints, URLs, snake_case or UPPER_SNAKE names, REQ/TASK ids or CamelCase
  identifiers (product names listed in `PRODUCT_NAMES`, such as GitHub, GitLab
  and OpenCode, are allowed; add new ones there), at most 10 entries per
  category in a release, `Unreleased` first, released versions descending.

## 3. Implementation Overview

Standard-library only (`tomllib`, `re`). The file ships inside the `adore`
package, so the wheel and the runtime bundle carry it. `GET /api/v1/about`
returns `release_notes` (list of `{version, date, entries}`); an unreadable or
malformed file yields an empty list so About never fails, logs a warning on the
`adore.web` logger, and the repository check reports the defect instead.
Releases without entries are not shown. The web client (`src/releaseNotes.ts`) shows
the user's locale with English fallback, grouped New, Improved, Fixed and by
topic, and labels `Unreleased` as In development.

## 4. Dependencies

- `02_Tools/internal/check_release_notes.py` imports this module from its own checkout
  and adds the repository rules: released versions need a `## [x.y.z] - date`
  section in `CHANGELOG.md` with the same date, and the current `__version__`
  needs a release section. `--since <rev>` warns, without failing, when
  `CHANGELOG.md` changed since that revision but the release notes did not.
- The maintenance rule lives in `AGENTS.md` ("Release notes rules"): agents
  write the notes in the same change as a user-visible changelog entry and
  record `release-notes: added | updated | none (<reason>)` in the task journal.

## 5. Usage

```bash
python 02_Tools/internal/check_release_notes.py
python 02_Tools/internal/check_release_notes.py --since <task base>
```

At a release cut, rename `Unreleased` to the new version with the date of its
changelog heading; start a new `Unreleased` release with the next user-visible
note.

## 6. Validation And Tests

`tests/test_release_notes.py` runs the checker on the repository and on fixtures
for each contract rule (locales, category, lengths, each technical-reference
pattern, limits, ordering, dates, version form), the changelog cross-checks and
the `--since` warning, checks parser shape errors, the About payload and its
fail-soft path. `web/tests/
releaseNotes.test.mjs` covers grouping and the English fallback; the e2e
`shell.spec.ts` About test opens What's new.

## 7. Limitations And Future Work

Whether a change is user-visible stays a judgement made by the agent or
developer; the checker verifies only form and alignment, and the `--since`
warning is advisory. Translation quality is reviewed, not machine-checked.
The runtime packagers copy `adore/` whole, so bundles carry the file, but the
release-consistency bundle list does not yet require it: the released 0.13.0
artifacts predate it. Add `adore/release_notes.toml` to `REQUIRED_BUNDLE_FILES`
when the next release's artifacts are built.

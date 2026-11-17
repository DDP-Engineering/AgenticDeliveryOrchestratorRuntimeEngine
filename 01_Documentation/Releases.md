# Versions, changelog and release notes

## One release version

`04_Software/pyproject.toml` is authoritative. Change release versions with
`python 02_Tools/package/set_version.py VERSION`, not by editing declarations independently.
The script synchronizes `adore/__init__.py`, the editable package in `uv.lock`, current-version
manuals/indexes, package-name examples and the five presentation footers/metadata.
Release checks derive the expected version from pyproject; executor/proxy image tags have
independent content versions and are not changed with the application.

ADORE uses numeric `x.y.z` versions. Before 1.0.0, MINOR covers new capabilities and breaking
changes; PATCH covers fixes. From 1.0.0, MAJOR covers breaking public contracts, MINOR compatible
capabilities and PATCH fixes. Beta/updater channels are not implemented.
Stored-format identifiers are not release versions. The pre-release policy in AGENTS.md applies:
one current structure, web schema 1, no migrations/compatibility readers or automatic resets.

## CHANGELOG.md

- Keep `## [Unreleased]` first, then dated releases newest first; use only populated Added,
  Changed, Fixed and Removed sections. Read only Unreleased/current release during normal work.
- One concise entry per notable change, describing behavior rather than implementation history.
- A breaking stored-format change names what the operator deletes before starting the build.
- Existing release history stays intact. Do not load or duplicate it in agent context or component docs.

## User-facing notes and help

`04_Software/adore/release_notes.toml` supplies About > What's new. Keep its current TOML contract:
Unreleased first when present, then dated releases newest first. Internal refactoring, tests,
tooling and standalone documentation get no user-facing entry.

For a visible UI/CLI/settings change, add new/improved/fixed entries with topic and text in
`en`, `fr`, `de`, `ro`. Use the interface's terms; text is at most 100 characters, topic at most
40, with no paths, code/REQ/TASK identifiers or endpoints. At most 10 entries per category.
Merge related entries. Update affected in-app help in all four locales with matching structure;
its authoring rules live in `04_Software/web/src/help/README.md`.

With AEGIS, record help/release-note decisions in the task log. Without it, state the decision
in the handoff. The source checker verifies note shape, translations and changelog dates:

```text
python 02_Tools/package/release_checks/check_release_notes.py --since BASE_COMMIT
```

## Prepare a release

From the repository root, inspect the complete candidate and finish the user-authorized checks.
Keep unrelated local work. No command below commits, tags, pushes, deploys or runs tests.

```text
python 02_Tools/package/set_version.py --check
python 02_Tools/package/set_version.py X.Y.Z --dry-run
python 02_Tools/package/set_version.py X.Y.Z
python 02_Tools/package/release_checks/check_release_notes.py
```

Replace `X.Y.Z` with the intended version, which must be higher than the current one; use `--date YYYY-MM-DD` for an explicit
release date. The tool validates current metadata and all planned replacements before writing;
each file is replaced atomically. An IO failure is reported and may leave an incomplete cut:
inspect the listed source files and run `--check` after correcting it. There is no stored-data repair.

The script rolls Unreleased changelog entries into the dated release and stamps the matching
notes, then starts an empty Unreleased group. An internal-only release has no invented user notes.
It changes presentation text only; inspect slides if a longer version needs layout adjustment.
The working tree need not be clean, but do not edit release files concurrently with the tool.

Full suites run at the user's explicit gate; reuse valid proof for unchanged inputs.
Build and verify delivery only when requested, using [repository tools](../02_Tools/README.md).
Package names derive from the project version. A source version cut does not rebuild or relabel
existing archives. License text, REUSE metadata and bundled third-party notices remain in delivery.
Commit, tag, push and release publication require their own authorization.

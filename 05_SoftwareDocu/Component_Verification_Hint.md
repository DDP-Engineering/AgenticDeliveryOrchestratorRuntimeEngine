<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Component: Verification hint reader

## 1. Purpose

`04_Software/adore/verification_hint.py` supplies one editable verification default
for direct-repository enrollment and CLI init. It offers evidence, not a configured
command or a claim that tests pass.

## 2. Responsibilities

- Read names and bounded manifest contents only; no subprocess, network or writes.
- Ignore links outside the resolved clone and nonregular/oversized files, including
  command-selection lockfiles and wrappers. Only package JSON and Makefile need contents.
- Preserve deterministic table precedence and actual clone-relative provenance.
- Leave AEGIS exclusion, human choice, exact configuration validation and saving to callers.

## 3. Implementation overview

`suggest_verification_command(root: Path) -> tuple[str, str] | None` scans the root
first, then the same ordered table in immediate child directories. Any root match
wins. Exactly one matching child produces `cd <dir> && <command>` only for a name
matching `[A-Za-z0-9_][A-Za-z0-9._-]*`. Count matching children before this restriction;
multiple children, including a safe plus unsupported name, give no suggestion.
There is no deeper traversal or workspace/toolchain inference.

| Order | Eligible source | Command |
|---|---|---|
| 1 | `package.json` with real textual `scripts.test` | `pnpm test` with `pnpm-lock.yaml`, else `yarn test` with `yarn.lock`, else `npm test` |
| 2 | `pyproject.toml`, `pytest.ini`, `tox.ini` | `uv run pytest -q` with `uv.lock`, else `python -m pytest -q` |
| 3 | `go.mod` | `go test ./...` |
| 4 | `Cargo.toml` | `cargo test` |
| 5 | `pom.xml` | `mvn -q test` |
| 6 | `build.gradle`, `build.gradle.kts` | `./gradlew test` with `gradlew`, else `gradle test` |
| 7 | `*.sln`, `*.csproj` | `dotnet test` |
| 8 | `Makefile` with `test:` target | `make test` |

Within a row the listed source order wins; dotnet patterns use lexical filenames.
Malformed JSON/structure and npm's standard no-test-specified placeholder are not
JavaScript matches. No manifest content is validated as a runnable toolchain.

## 4. Dependencies

Python standard library only: `pathlib`, `stat`, `os`, `json`, `re`. No new runtime
or build dependency. CLI and API reuse the same public function.

## 5. Inputs and outputs / data contracts

Input is an existing clone root. Output is `(command, source)` or `None`. Source
is the actual eligible manifest path relative to the clone, with forward slashes,
including a child prefix, never the lockfile/wrapper that selected a variant.
Contained symlinks retain their candidate source spelling.

The byte limit is exactly 1048576, inclusive. Already oversized or external files
are never opened for contents. Content reads recheck file type/size and containment
and are bounded. Unexpected filesystem/encoding errors propagate rather than
silently returning a partial or empty scan; malformed package JSON has its explicit
parse-miss exception. CLI wraps access failures as field-addressed `WizardError`;
web preview uses its redacted setup-unavailable contract.

## 7. Workflow integration

CLI skips discovery for AEGIS presence and prepare-only. Web attaches a transient
`verification_hint` only to valid inspected direct previews, outside canonical
review/configuration digests. Applying it in the browser requires a new canonical
preview; explicit Create saves submitted text only. Settings never calls discovery.

## 9. Validation and tests

`04_Software/tests/test_verification_hint.py` exercises all eight table rows at
root and child, variants, deterministic source ties, row/root precedence, unique
and ambiguous children, unsupported names, no/deep match, malformed/placeholder
package evidence, external symlinks and inclusive size guards that forbid content
access. Repeatability and process/network/write guards prove the read-only seam;
access failures remain explicit. API, wizard and browser integration are covered
by `test_web_enrollment.py`, `test_wizard.py` and `web/e2e/enrollment.spec.ts`.

## 10. Limitations

This is an editable heuristic, not command validation, tool availability detection
or execution. Static containment/size checks do not establish snapshot isolation
against a concurrently hostile filesystem. No compatibility or stored schema is
introduced; there is nothing to migrate.

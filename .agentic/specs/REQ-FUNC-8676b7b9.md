<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-8676b7b9 — Ordered verification suggestion matching

## Status and authority

Active specification of the matching algorithm implemented for ticket #65, also
used by the Python, Go, Rust, Maven, Gradle, dotnet, Make and child-fallback
requirements in TASK-51bf134b. STATED authority: ticket #65 Decisions and
`00_Planning/2026-11-10_Direct_Workflow_Without_AEGIS/PLAN.md` section 4.5,
plus the owner's Q1–Q3 clarification recorded as RULING-001 through RULING-003
in TASK-51bf134b. This is an optional editable suggestion, not proof of an
installed tool, command validation or execution.

## Input and output

Input is the clone root path. Output is a pair `(command, source file)` or no
suggestion. The source identifies the actual matching manifest, not the
lockfile or wrapper that selected a command variant. For child matches it
identifies the manifest in that child. The public API is
`suggest_verification_command(root: Path) -> tuple[str, str] | None`, with
an actual eligible repository-relative source in forward-slash notation.
The source names the candidate repository path, not an external resolved target.

Discovery uses file names and relevant manifest contents only, never a
command, network request or write. Files larger than 1 MiB (1048576 bytes)
and links that leave the supplied repository are ignored. The same
containment and size limits apply to files that select command variants.
Only package.json and Makefile need their contents inspected by the table;
other manifest rows are presence-based, not toolchain/config validators.

## Ordered scan

1. Scan the clone root using the rows below in order; the first applicable
   row supplies the result and stops selection, irrespective of child files.
2. Only with no root match, inspect each first-level directory using the
   same ordered rows, without descending further.
3. Count matching first-level directories before applying the name restriction.
   Exactly one matching directory supplies its result only when its name fully
   matches `[A-Za-z0-9_][A-Za-z0-9._-]*`, with `cd <dir> && ` before the
   command and its repository-relative manifest as source. An otherwise matching
   sole child with an unsupported name supplies no suggestion.
4. Zero or several matching first-level directories supply no suggestion,
   including one safe-named and one unsupported-named match. Multiple matches
   inside one directory count as one matching directory; its first table row wins.
   Root suggestions are unaffected by child-name eligibility. No shell/backend
   parameter or shell-execution change is part of this helper.

| Order | Eligible evidence in the directory | Command |
|---|---|---|
| 1 | `package.json` with a real textual `scripts.test`, not npm's no-test-specified placeholder | `pnpm test` with eligible `pnpm-lock.yaml`, otherwise `yarn test` with eligible `yarn.lock`, otherwise `npm test` |
| 2 | `pyproject.toml`, `pytest.ini` or `tox.ini` | `uv run pytest -q` with `uv.lock`, otherwise `python -m pytest -q` |
| 3 | `go.mod` | `go test ./...` |
| 4 | `Cargo.toml` | `cargo test` |
| 5 | `pom.xml` | `mvn -q test` |
| 6 | `build.gradle` or `build.gradle.kts` | `./gradlew test` with `gradlew`, otherwise `gradle test` |
| 7 | `*.sln` or `*.csproj` | `dotnet test` |
| 8 | `Makefile` with a `test:` target | `make test` |

Within a matching row, select the first eligible source in these orders:
Python: `pyproject.toml`, `pytest.ini`, `tox.ini`; Gradle: `build.gradle`,
`build.gradle.kts`; dotnet: `*.sln` before `*.csproj`, lexical filename order
within each pattern. Containment and size rules apply before source selection.
Both eligible JavaScript lockfiles select pnpm. Do not inspect `packageManager`
or probe an executable, network or package-manager availability.

A malformed package.json or a missing/nontext scripts.test supplies no
JavaScript match and no parse exception to the caller. npm's standard
`echo "Error: no test specified" && exit 1` is a placeholder, not evidence of
tests. A directory with only that evidence therefore supplies no suggestion.
No extra ecosystem, test-runner, workspace, README or deeper-recursion rules
are part of this algorithm.

## Examples and acceptance oracles

| Repository evidence | Result |
|---|---|
| root package.json with `scripts.test = "vitest run"` | `npm test`, package.json source |
| same plus pnpm-lock.yaml | `pnpm test`, package.json source |
| same plus yarn.lock instead | `yarn test`, package.json source |
| same plus both eligible lockfiles | `pnpm test`, package.json source |
| root pyproject.toml, pytest.ini and tox.ini | `python -m pytest -q`, pyproject.toml source |
| root build.gradle and build.gradle.kts | `gradle test`, build.gradle source |
| root z.sln, a.sln and a.csproj | `dotnet test`, a.sln source |
| root pyproject.toml and uv.lock | `uv run pytest -q`, pyproject.toml source |
| root go.mod plus child Cargo.toml | `go test ./...`, root go.mod source |
| no root match, only service/go.mod | `cd service && go test ./...`, service/go.mod source |
| no root match, service/go.mod and ui/package.json with real tests | no suggestion |
| no root match, only service/deep/go.mod | no suggestion |
| no root match, only api & worker/go.mod | no suggestion |
| no root match, service/go.mod and api & worker/go.mod | no suggestion, despite one safe child name |
| malformed package.json as sole evidence | no suggestion and no error |
| sole matching manifest linked outside the clone | no suggestion and no external content read |
| sole matching manifest larger than 1048576 bytes | no suggestion and no content read |

`tests/test_verification_hint.py` supplies table-driven public-helper tests for every row at the root and in
a single child, all command variants, root/row precedence, no match,
ambiguous children and the explicitly required malformed/placeholder/link/
size negatives. Include both-lockfile precedence, all same-row source ties,
safe-name boundaries and ambiguity before name filtering from the clarification.
Process/network guards and before/after file snapshots exercise the read-only
boundary. Execution evidence is retained in the task journal.

## Authority and remaining limits

- STATED: only the supplied matching table and the owner's explicit Q1–Q3
  clarification are authorized. A needed additional matching rule remains a
  question in ADORE_QUESTIONS.md, not an invented heuristic.
- STATED: CLI use/edit/none choices and web clearing protection are authorized
  by the same clarification; their exact field/state flow is in the task Design.
- INFERRED (AGENTS.md fail-closed trust boundaries): unexpected filesystem
  access failures are not evidence of a match or an empty repository. Preserve
  the caller's error boundary rather than inventing a blanket error-to-miss
  rule. Malformed package evidence retains its explicit no-error exception.
- UNKNOWN: protection against a concurrently hostile clone replacing files
  during discovery is not established by static fixtures. The design bounds
  content access and verifies containment/size, but claims no hostile-filesystem
  snapshot guarantee. No toolchain, platform or live-command acceptance is implied.

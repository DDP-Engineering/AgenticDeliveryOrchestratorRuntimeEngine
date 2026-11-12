<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-8676b7b9 — Ordered verification suggestion matching

## Status and authority

Draft specification of the matching algorithm accepted for ticket #65, also
used by the Python, Go, Rust, Maven, Gradle, dotnet, Make and child-fallback
requirements in TASK-51bf134b. STATED authority: ticket #65 Decisions and
`00_Planning/2026-11-10_Direct_Workflow_Without_AEGIS/PLAN.md` section 4.5.
This is an optional suggestion, not command validation or execution.

## Input and output

Input is the clone root path. Output is a pair `(command, source file)` or no
suggestion. The source identifies the actual matching manifest, not the
lockfile or wrapper that selected a command variant. For child matches it
identifies the manifest in that child. The concrete callable name, source
path representation and preview transport names remain design choices.

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
3. Exactly one matching first-level directory supplies its result, with
   `cd <dir> && ` before the suggested command and its manifest as source.
4. Zero or several matching first-level directories supply no suggestion.
   Multiple matches inside one directory count as one matching directory;
   its first table row wins.

| Order | Eligible evidence in the directory | Command |
|---|---|---|
| 1 | `package.json` with a real textual `scripts.test`, not npm's no-test-specified placeholder | `npm test`; `pnpm test` with `pnpm-lock.yaml`; `yarn test` with `yarn.lock` |
| 2 | `pyproject.toml`, `pytest.ini` or `tox.ini` | `uv run pytest -q` with `uv.lock`, otherwise `python -m pytest -q` |
| 3 | `go.mod` | `go test ./...` |
| 4 | `Cargo.toml` | `cargo test` |
| 5 | `pom.xml` | `mvn -q test` |
| 6 | `build.gradle` or `build.gradle.kts` | `./gradlew test` with `gradlew`, otherwise `gradle test` |
| 7 | `*.sln` or `*.csproj` | `dotnet test` |
| 8 | `Makefile` with a `test:` target | `make test` |

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
| root pyproject.toml and uv.lock | `uv run pytest -q`, pyproject.toml source |
| root go.mod plus child Cargo.toml | `go test ./...`, root go.mod source |
| no root match, only service/go.mod | `cd service && go test ./...`, service/go.mod source |
| no root match, service/go.mod and ui/package.json with real tests | no suggestion |
| no root match, only service/deep/go.mod | no suggestion |
| malformed package.json as sole evidence | no suggestion and no error |
| sole matching manifest linked outside the clone | no suggestion and no external content read |
| sole matching manifest larger than 1048576 bytes | no suggestion and no content read |

Build adds table-driven public-helper tests for every row at the root and in
a single child, all command variants, root/row precedence, no match,
ambiguous children and the explicitly required malformed/placeholder/link/
size negatives. Process/network guards and before/after file snapshots prove
the read-only boundary. Test definitions are not execution evidence.

## Assumptions and open decisions

- STATED: only the supplied matching table is authorized. A needed rule beyond
  it is a question in ADORE_QUESTIONS.md and a blocked pause, not a heuristic.
- UNKNOWN: the ticket does not explicitly state provenance tie-breaking when
  several filenames in the same row match or command selection when both
  JavaScript lockfiles exist. No new tie-break rule is introduced here;
  design must stay within the supplied table or use the blocking-question
  procedure if an additional decision is necessary.
- UNKNOWN: exact safe rendering of a child directory in the command and CLI
  keep/edit/clear presentation belong to design, with no expansion of the
  matching table or execution authority.
- UNKNOWN: filesystem permission/encoding/concurrent-change outcomes beyond
  the stated malformed-JSON, size and external-link boundaries are not
  established by the ticket; do not silently promote an assumption to a
  matching or recovery rule.

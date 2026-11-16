# Code style

Rules for readable code; Ruff and TypeScript enforce the mechanical checks.
Licensing comes from `REUSE.toml`, `LICENSE.txt` and `LICENSES/`.

## Shared rules

- Use simple, direct code and explicit names. Avoid speculative abstractions and wrappers.
- Keep one responsibility per module; extract coherent parts of large files when touching them.
  Do not split files solely to satisfy an arbitrary line count.
- English for identifiers, comments, logs, tests and internal documents.
- Comments explain decisions or constraints; code and type hints explain mechanics.
  No commented-out code, file banners, section markers or end-of-file markers.
- Validate external input at its boundary and raise typed errors; never guess or accept partial data.
- Keep the core forge/executor agnostic and portable. Follow the pre-release data policy in AGENTS.md.
- Preserve third-party notices and managed AEGIS files. Prompt resources keep their loader-required
  legal prefix; generated standalone files and deployed Pi extensions keep required notices.
  Ordinary project files have no license header.

## Python

- PEP 8, explicit type hints on public interfaces, standard library where practical.
- One short module docstring. A callable needs a docstring when its contract is not obvious:
  describe important input constraints, outputs, side effects and typed failures.
  Use plain concise text; no mandatory Doxygen tags or parameter lists duplicating type hints.
- Keep meaningful existing contract explanations. Remove redundant file names and boilerplate.
- A shebang belongs on directly executable scripts. Python 3 source is UTF-8 without an encoding banner.
- Ruff configuration is `04_Software/ruff.toml`; run from `04_Software`.
  Preserve repository line-ending rules in `.gitattributes`.

## Frontend

- Strict TypeScript and shared typed transports; keep side effects at explicit boundaries.
- User-facing UI, help and release notes use `en`, `fr`, `de`, `ro` with matching terms.
- Reuse existing navigation, pagination, status and action components.
  Keep explanatory material in help rather than repeated helper paragraphs.
- Help authoring rules: `04_Software/web/src/help/README.md`.

## Tests and component documentation

- Test public behavior and trust boundaries with offline injected collaborators.
  Keep mutable test state isolated. Use `-n 0` for small selections; the default uses two workers.
- Fixture/authentication details: [test infrastructure](../05_SoftwareDocu/Component_Test_Infrastructure.md).
- Update the affected [component contract](../05_SoftwareDocu/README.md) rather than copying it into code
  or an AEGIS page. Keep only relevant sections of the component template.
- Release procedure and user-facing notes: [Releases](Releases.md).

Licensing metadata check (a repository check, not a product test):
`uvx --from "reuse[charset-normalizer]==6.0.0" reuse lint`.
The first invocation provisions the pinned checker; subsequent checks can use its cached environment.

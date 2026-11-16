# Component: Identity (`adore/identity.py`)

> Component documentation per `component_documentation_template.md`.
> Source: `04_Software/adore/identity.py`.
> System overview: [Operations guide](../01_Documentation/Operations_Guide.md#system-overview).

## 1. Purpose

Marker-based agent identity across the supported forges. ADORE identifies its
comments by a visible tag (`[ADORE]`) and a hidden HTML-comment marker rather
than relying on account authorship. Comments without its marker are eligible
as human evidence subject to the conductor's timestamp and system-note checks.
This component builds/parses the markers and derives slug-based resource names.

## 2. Responsibilities

- `AgentIdentity` (frozen dataclass around `name`/`slug`):
  - derived names: `tag` (`[ADORE]`), `store_root` (`.adore`),
    `questions_file` (`ADORE_QUESTIONS.md`), `branch(run_id)`
    (`adore/<run-id>`), `container_name(run_id)` (`adore-run-<run-id>`);
  - `make_marker(run_id, kind, **extra)` -> `<!-- adore:run=... kind=... -->`;
  - `parse_marker(body)` -> field mapping or `None`;
  - `is_own_comment(body)` -> marker present or not;
  - `status_comment(run_id, state, stage, updated)` -> the full single
    status-comment body (visible line + hidden marker).

Explicitly not owned: posting/editing comments (forge adapters) and deciding
*when* to post (orchestrator).

## 3. Implementation Overview

- The marker is an HTML comment, invisible when rendered on GitLab and
  GitHub: `<!-- <slug>:run=<run-id> kind=<kind> k=v ... -->`.
- `kind` values: `status` (the single edited status comment), `question`
  (clarification post), `delivery` (draft-MR notification).
- Parsing is slug-scoped (`<!-- adore:` only matches this agent) and
  DOTALL (a marker re-wrapped across lines still parses). When a body carries
  two markers, the first wins, deterministically.
- **Quoted lines are ignored** before matching: when a human replies by
  quoting ADORE's comment, the carried-over marker sits on blockquote (`>`)
  lines, so it does not count as ours - otherwise resume detection would miss
  the human's answer. A genuine ADORE comment always writes its marker on an
  unquoted line, so this never hides one.
- A malformed marker parses as "no marker" - the comment counts as human.
  That is the safe direction: at worst the executor re-evaluates and re-asks;
  it never mistakes its own comment for a human answer.

## 4. Dependencies

- Internal: none.
- External: Python standard library only (`re`, `dataclasses`).

## 5. Inputs And Outputs

- Inputs: the `[agent]` config values (`identity_from_config(name, slug)`),
  run-ids, comment bodies fetched by a forge adapter.
- Outputs: marker strings, parsed field mappings, derived resource names,
  formatted status-comment bodies.

## 6. Data Contracts

- Marker grammar: `<!-- <slug>:` + whitespace-separated `key=value` tokens
  (keys `[A-Za-z0-9_-]+`, values non-whitespace) + `-->`. `run` and `kind`
  are always present.
- Renaming the bot is a single `[agent]` config change; every derived
  identifier follows. Nothing else hard-codes "adore".

## 7. Workflow Integration

Used by the orchestrator for stamping every posted comment,
finding/editing its own status comment, and resume detection (a
comment newer than the question that lacks the marker and is not a system
note counts as a human answer). Comment ids recorded in `state.json` are the
second, independent identity signal.

## 8. Usage

```python
from adore.identity import AgentIdentity

ident = AgentIdentity(name="ADORE", slug="adore")
body = ident.status_comment("gitlab-x-14", "working", "build", "2026-11-15 14:02")
ident.is_own_comment(body)        # True
ident.parse_marker(body)["kind"]  # "status"
```

## 9. Validation And Tests

- `tests/test_identity.py`: derived names, marker round-trip, human comments
  carry no marker, slug-scoping against another agent's marker, status
  comment format, first-marker-wins, line-wrapped marker, malformed marker
  treated as human.
- Minimum validation after a change: `uv run --group dev pytest tests/test_identity.py`.

## 10. Limitations

- A marker quoted inside a code fence would still be detected as ours
  (acceptable: false "own comment" only delays resume by one reply).
- Saved comment IDs and clarification-resume decisions belong to run state
  and the conductor; this component supplies marker parsing only.

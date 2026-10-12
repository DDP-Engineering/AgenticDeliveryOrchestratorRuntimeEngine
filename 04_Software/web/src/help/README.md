<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Help content

The in-app help center (`/help`, header button **How ADORE works**) renders the
Markdown files in `content/<locale>/<topic>.md`. Every topic exists in `en`,
`fr`, `de` and `ro`; `tests/help.test.mjs` fails when a locale is missing or
drifts. Maintenance rule: AGENTS.md "Help content rules".

## Topics

| File | Topic |
|---|---|
| `overview.md` | What ADORE does (the help start page) |
| `interface.md` | Interface tour |
| `projects.md` | Adding a repository |
| `settings.md` | Project settings |
| `executors.md` | Executors and models |
| `tickets.md` | Tickets for automatic pickup |
| `jobs.md` | Job lifecycle |
| `statistics.md` | Statistics and costs |
| `administration.md` | Administration |
| `glossary.md` | Glossary |

## Markdown subset

Only these constructs are allowed; the test rejects anything else.

- Line 1: `# Title` (at most 40 characters), then a blank line and a short
  introduction paragraph.
- Sections: `## Heading {#id}` and `### Heading {#id}`. Every heading carries an
  explicit id (lowercase letters, digits, hyphens), unique in the file and
  identical in every locale, so links and the outline match across languages.
- Paragraphs: consecutive text lines; a blank line ends them.
- Lists: `- item` or `1. item`, one level, one line per item.
- Tables: a header row, a `|---|---|` separator and rows; no `|` inside cells.
- Notes: `> text` lines, shown as a highlighted note.
- Code blocks: fenced with three backticks, no language tag.
- Inline: `**bold**`, `` `code` `` and links `[text](target)`.
- Link targets: `/help/<topic>`, `/help/<topic>#<id>`, `#<id>` (same topic) or an
  interface address such as `/projects`, `/jobs`, `/metrics`, `/admin/users`,
  `/admin/status`, `/admin/audit`, `/account`, `/projects/new`,
  `/projects/import`. No external URLs, images or HTML.

## Writing

- Write for people using the web interface. Name screens, tabs, buttons and
  settings exactly as the interface shows them in that language (see
  `src/i18n.ts` and the `*Copy.ts` catalogs).
- Describe only behavior that exists; take facts from `01_Documentation/` and
  the code. Keep CLI detail out unless the web interface has no equivalent.
- Every locale has the same sections, tables, notes and link targets in the
  same order; only the language differs.

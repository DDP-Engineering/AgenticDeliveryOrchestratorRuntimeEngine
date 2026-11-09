<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Native Git isolation correction — delivery candidate

Status: validated, awaiting explicit local commit approval. No push, PR or merge.

Fresh executor containers use native Git discovery through a read-only Git pointer,
without inherited repository selectors. Independent/nested repositories remain
independent. Corrupt evidence fails closed; existing containers retain their
creation-time mode and installed dependencies. WSL options remain literal.

Candidate binding: `429505b5dfc07639dcd80a8190814da1e7ae0b1b2c0239dcaaa3fc2f359c3228` (27 paths).
Comparison base: `fe20f6b0c2df3491d69ae03c48d98f75b591169e`.
The immutable snapshot is retained at `refs/adore/validated/TASK-95ab438a`.
The real index, root branch, unrelated work and active issue25 are preserved.

Final configured strict check: exit0, 1604.14s; 2207 Python passed, 8 existing
skips, one upstream Starlette/httpx deprecation; Ruff passed; all226 Chromium
passed; 0 errors,181 nonpromoted advisories,22 notes. Both independent round4
verdicts approved. Disposable network-none Docker acceptance passed ordinary and
special-character paths, native independent/nested commits, unchanged host/main
Git state, UID1000 and same-ID warm reuse. Podman is covered offline only.

Deviations: WSL direct-argv parsing added after controlled shell-expansion failure;
two existing real-Git test fixtures replaced with offline doubles; finite global
browser budget raised20→30min after an incomplete run (individual limits and zero
retries unchanged); file bound28→30 and active work3→4h extended for owning docs
and repeat proof. Earlier failed/incomplete verification is not final evidence.

The proposed local commit contains exactly the paths below, with no separate
timeout-task files, Azure implementation, unrelated baseline work or credentials.
The private baseline ancestry must not be pushed automatically.

- `.agentic/context/environment.md`
- `.agentic/context/project.md`
- `.agentic/knowledge/isolation.md`
- `.agentic/knowledge/web-interface.md`
- `.agentic/requirements/functional/REQ-FUNC-0d0625e1.toml`
- `.agentic/requirements/reliability/REQ-REL-b8c5946a.toml`
- `.agentic/requirements/reliability/REQ-REL-e1ecfbd5.toml`
- `.agentic/specs/REQ-FUNC-0d0625e1.md`
- `.agentic/tasks/TASK-95ab438a.candidate.json`
- `.agentic/tasks/delivery_TASK-95ab438a.md`
- `.agentic/tasks/TASK-95ab438a.md`
- `.agentic/tasks/diagram_TASK-95ab438a.md`
- `01_Documentation/Configuration_Reference.md`
- `01_Documentation/Operations_Guide.md`
- `04_Software/adore/isolation.py`
- `04_Software/adore/release_notes.toml`
- `04_Software/adore/web/static/assets/index-BWQbhdHj.js`
- `04_Software/adore/web/static/assets/index-C6PbXIfO.js`
- `04_Software/adore/web/static/index.html`
- `04_Software/tests/test_container_git.py`
- `04_Software/tests/test_isolation.py`
- `04_Software/tests/test_release_notes.py`
- `04_Software/web/playwright.config.ts`
- `04_Software/web/src/help/content/de/executors.md`
- `04_Software/web/src/help/content/en/executors.md`
- `04_Software/web/src/help/content/fr/executors.md`
- `04_Software/web/src/help/content/ro/executors.md`
- `05_SoftwareDocu/Component_Isolation.md`
- `05_SoftwareDocu/Component_Web_Frontend.md`
- `CHANGELOG.md`

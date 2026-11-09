<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Published Web UX implementation baseline

Publication date: 2026-10-05. Coordination issue: [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4).
Parent: [epic #3](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/3).
Implementation starting branch: `task/adore-web-interface`.
The exact published source commit is recorded in both issues after remote verification.

## Implementation entry points

- [English implementation brief](Gitea_Issues/DESIGN_BRIEF.md): approved direction, product boundaries, dependency order and logo provenance. Current Gitea issue requirements govern implementation; this brief retains the approved archive's original bytes and historical baseline observations.
- [Published issue catalog](Gitea_Issues/README.md) and [publication snapshot](Gitea_Issues/published.json): links to the English epic and child requirements. Their recorded bodies and status are snapshots from backlog creation, not live issue state.
- [Approved transparent logo PNG](DDP_Engineering_logo_dark.png), 630 x 300, muted sage `#B8D1C4` for the `#102F29` navigation panel, and [native SVG adaptation](DDP_Engineering_logo_dark.svg).
- [Original extracted logo](DDP_Engineering_logo.png) and [extraction SVG](DDP_Engineering_logo.svg): source provenance retained. The SVGs embed raster data; they do not turn the original company mark into vector artwork.
- [Approved overview capture](proposal-overview-dark-logo.png), [import](proposal-import.png), [job](proposal-job.png), [configuration](proposal-configuration.png) and [statistics](proposal-statistics.png).
- [Illustrative HTML prototype](Prototip.html): open locally with the adjacent logo PNG. All projects, jobs, accounts, consumption values and actions are synthetic demonstrations. It performs no real orchestration and is a design reference distinct from the production React UI under `04_Software/web/`.

The existing Romanian proposal, README, variant note, prototype copy and captures are preserved as design history. New implementation specifications, documentation and acceptance copy are English. The variant note records a rejected image-generation experiment; no discarded generated-image trial is published.

## Archive integrity and provenance

The [epic reference archive](http://192.168.1.15:3001/attachments/a3006796-ce57-452a-8497-c1e38b102a09) was retrieved again using authenticated `tea api -l ddp`.
Its SHA-256 is `fd42635af2b704be1627c13477594fffe8d31c8f5c23ea1e2a644783400fafe2`.
The identical archive is retained as [ADORE_Web_UX_Reference.zip](Gitea_Issues/ADORE_Web_UX_Reference.zip).
All nine entries in [the approved manifest](Gitea_Issues/asset-manifest.json) matched both the extracted archive and local source bytes.
Manifest paths are archive-relative: `DESIGN_BRIEF.md` is in `Gitea_Issues/` in this checkout; the remaining entries are in this directory.
[The publication manifest](publication-manifest.json) records all preserved design-history files with paths relative to this directory, including the original archive and catalog. It excludes itself and this publication report.

The original company mark came from the user-supplied business-card layout at `D:/ProjectsDDP/DDP_Engineering/Carti de vizita/BunDeTipar3/`. The source layout SVG SHA-256 is `0fb248353b7844cc08a5e500593b81021cf9b1c862055ed2ca37e63989a1b9e3`. The deterministic luminance-to-alpha adaptation preserves the original geometry. Binary assets inherit this provenance; authored text carries the project legal header.

## Baseline reconciliation and verification

The initial working tree had only this untracked planning directory. Local branch HEAD was `6fed00cf899bd851c18d5ce3ef6ae5973abf809f`; a fresh fetch confirmed remote `task/adore-web-interface` at `450798e`, with no remote-only commits. The prepared tooling commit is preserved as an ancestor; publication uses a normal fast-forward push. No force push, merge, release bump or tag is required.

Clean dependency setup and frontend verification were performed in a separate clone of the prepared source commit, with no reused virtual environment or `node_modules`:

```text
cd 04_Software
uv sync --extra web --group dev
cd web
npm ci
npx playwright install chromium
npm run validate
cd ..
.venv/Scripts/python.exe -m pytest tests/test_web_asset_stamp.py -q
```

On POSIX, the final command uses `.venv/bin/python`. Setup may download dependencies; validation itself simulates external services and blocks browser requests outside the owned localhost test origin. See [frontend verification guidance](../../01_Documentation/Web_Interface.md#development-verification).

Environment: Windows, Node.js 24.15.0, npm 11.11.1, uv 0.11.3, clean-clone Python 3.12.13, Playwright 1.63.0 and Chromium.
Results: dependency setup succeeded; npm reported zero vulnerabilities; all 32 Node tests and 8 Chromium journeys passed, along with TypeScript checks, the isolated Vite build and all 3 asset-stamping tests. The approved PNG was decoded in Chromium: 630 x 300, 122001 fully transparent pixels, 16816 partially transparent pixels and 50183 opaque pixels. One publication correction was needed: directory-local Git attributes disable text normalization to preserve approved archive and historical bytes on every platform. The preserved historical variant note has an existing blank line at EOF; it was not rewritten for whitespace cleanup.
This publication validates the existing baseline, not the future redesign or novice acceptance. Live forge/container acceptance and accessibility audits remain outside this bootstrap scope. The harmless Node `NO_COLOR`/`FORCE_COLOR` warning did not affect verification. No environment blocker was observed. A fresh clone from the remote branch is checked after push; final commit and retrieval evidence are recorded in the issues.

This operation is bounded to four hours and at most three corrective attempts. No AEGIS task or stages apply to repository/documentation/tooling publication. Dependent implementation tickets remain held for explicit operator authorization.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# [Web UX] Publish the implementation baseline and approved design assets

## Tracking
Work item: BASE. Priority: P1. Parent: [EPIC #3](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/3).
Dependencies: None at this coordination/bootstrap step..
Implementation baseline: task/adore-web-interface; bootstrap records the remotely available commit. New specs/docs and acceptance copy are English.

## Problem and target behaviour
The approved UX reference files are local and untracked. Commit 6fed00c adds offline Playwright validation and clarifies AEGIS applicability, but the inspected remote web branch still points to 450798e. Other agents must have the same source and tools before taking dependent tickets.

## Scope
Reconcile the local and remote task/adore-web-interface branch without overwriting other work. Publish the prepared validation-tooling commit through the repository's authorized publication procedure. Save a concise English design brief, approved logo assets and reference prototype/captures in the design-history directory; preserve prior design history and provenance.
Provide a remotely accessible source commit for implementation. Keep the final dark-panel logo PNG (630x300, genuine alpha, #B8D1C4) and its native SVG adaptation; retain original logo source provenance. Do not publish discarded generated-image trials or credentials.

## Acceptance criteria
- [ ] A remote commit contains the offline web validation setup from 6fed00c and the project-owned AEGIS scope rule; document any reconciliation rather than force-pushing.
- [ ] The approved branding asset and English implementation brief can be retrieved by an agent in a fresh checkout or from the epic attachment.
- [ ] The prototype is labeled illustrative and is not installed as the product frontend.
- [ ] The implementation starting branch and exact source commit are recorded in the epic.
- [ ] A clean setup can run the documented frontend validation commands with simulated external services; environment limitations are recorded honestly.
- [ ] New authored text carries the legal header; binary artifacts retain provenance documentation.

## Verification and constraints
This is repository/documentation/tooling publication, not product implementation: no AEGIS task or stages. Inspect existing commit evidence before rerunning suites; rerun only what reconciliation or provisioning changes require. No release bump, tag, merge or unrelated refactor.
Obtain publication authority under the repository process before publishing; creating this issue does not supply additional Git publication authority.

## Code and documentation orientation
AGENTS.md; 00_Planning/2026-10-05_Web_UX_Redesign/; prepared commit 6fed00c; 04_Software/web/package.json and e2e/; 01_Documentation/Web_Interface.md; current frontend verification guidance.

## Execution bounds
Keep this operation to the stated planning/repository scope. Max four hours per session and three corrective attempts; record unresolved blockers. No product implementation, automatic pickup, merge or fabricated approval.


## Approved reference assets

- [English design brief, provenance manifest, logo variants and visual references](http://192.168.1.15:3001/attachments/a3006796-ce57-452a-8497-c1e38b102a09) — ADORE_Web_UX_Reference.zip.
- [Approved transparent DDP Engineering mark](http://192.168.1.15:3001/attachments/79f13809-2d28-47da-9870-6bd8007776f2) — 630x300 PNG; #B8D1C4 on #102F29 without a white panel.
- [Overview visual reference](http://192.168.1.15:3001/attachments/e9f32c44-3369-4589-b95f-1197b86a195a).

The archive is available through this Gitea issue rather than only the local untracked planning folder. Extract it and verify asset-manifest.json hashes. Historical screenshot copy is Romanian; implement English issue/specification copy and preserve supported localization.

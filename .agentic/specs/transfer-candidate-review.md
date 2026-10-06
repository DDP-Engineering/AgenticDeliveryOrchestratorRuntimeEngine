<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Candidate review — issue #10

Bound candidate SHA-256: `d40727cd3c0f3fedd90775efb878daad94e4036984f5ea1a0441120f460bd3d3`. Baseline/branch and every working-byte/deleted-blob digest are in `transfer-candidate-inventory.json`. Reporting files are explicitly excluded to avoid circular hashes. Reviews are separate primary-agent passes, not external reviewers or subagents. Round 3; two correction cycles of three authorized.

## Specification compliance: approved

Reviewed Frame, all three active requirements, spec/design, affected source/test/doc diffs, source parser contract and unchanged exact-TOML seam. Both methods transfer the complete 16-field allowlist into a fresh target with independent identity/ownership and stopped pickup. Fresh target environment/reference reconfirmation, visible source/default/effect mapping, exact source/candidate binding, source authority rechecks and guarded publication meet all eight issue criteria. Source users/grants/jobs/history/audit/pending/secrets/resource ownership are excluded. No later-ticket work, schema migration, dependency/version changes or planning edits. Component/operator/knowledge/project guidance matches the candidate; environment tooling remains accurate unchanged.

## Implementation quality: approved

Reviewed HTTP models/typed errors, parser/export trust boundaries, source-ID/config revision checks, session/CSRF/role refresh, bounded reads, ownership/symlink/repository collision checks, home/source/conductor lock order, late rechecks and rollback/replay. Reviewed UI memory/generation/submit guards, file reread, required reference gate, copied numeric domain handling, source and installed-default transport validation, localized copy and exact-TOML fallback. Public API tests exercise happy/negative security/ownership/source/rollback behavior; real isolated browser tests exercise both methods, changes, malformed/late transport and mobile/locales. Round-1 unchecked mapping defaults are corrected and the new failing-then-passing public browser regression proves rejection. The full-proof compatibility finding in shared English invalid-source guidance is corrected with the unchanged prior export assertion passing; second correction is confined to that message and regenerated bundle. No current actionable findings.

## Observed supporting proof

Latest combined export/transfer Chromium: 19 passed. Prior expanded API: 36 passed (latest bounded-read/routing changes covered by final full suite). Production build/typecheck and `uv run ruff check .`: exit 0. Generated index references the new stamped bundle; obsolete bundle removal is expected. Visual inspection: full desktop/source-copy screenshot plus native-size 390px top/bottom crops, light/dark readable text, wrapped paths/digests and explicit stopped action; automated no-horizontal-overflow/keyboard focus assertions passed. These are fixture screenshots, not participant or full-WCAG acceptance.

## Limits and advisories

Direct unmanaged host writes are detected at observed rechecks; no global filesystem transaction is claimed. Live credentials/forge/container readiness and participant acceptance remain operator work. Build reports a >500kB chunk warning; no functional verification is weakened. Existing TestClient and color-environment notices are informational. Historical AEGIS malformed-journal/tracked-fingerprint warnings concern other tasks. Oversized generated JS/JSON advisory scan limits are supplemented by source-diff review, deterministic build provenance and exact candidate hashes; fixtures use fake references, no credentials. Attempt 1 failed for the historical heartbeat test and shared English guidance regression. Failed evidence retained, heartbeat isolated unchanged passed; all 19 export/transfer scenarios pass after message correction. Final strict proof exit 0: 1049 Python passed/one skip, Ruff passed and frontend including 86 Chromium passed; zero errors, nine explained advisories. Current bound candidate remains unchanged.

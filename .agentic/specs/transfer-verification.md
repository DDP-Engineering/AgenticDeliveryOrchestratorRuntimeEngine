<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Issue #10 verification mapping

Candidate: `d40727cd3c0f3fedd90775efb878daad94e4036984f5ea1a0441120f460bd3d3`; see inventory and separate round-3 review.

| Criterion | Public evidence |
|---|---|
| 1 — Admin file and source copy, portable only | `test_transfer_roundtrip_independent_stopped_and_replay` both methods; browser file/project journeys |
| 2 — Independent ownership, stopped | Roundtrip IDs/state/worktree/metrics comparisons; stopped response/state; displayed paths |
| 3 — Excluded source data | Populated source secret/pending/history/grant fixtures remain unchanged; no target imports |
| 4 — Mapping/reconfirmation/invalid target | All16 nondefault rule comparisons; target boundary negatives; required checkbox; source/default/effect mapping; malformed default rejection |
| 5 — Exact source revision/re-review | Exact file bytes and comment-only config edits; immutable replacement/missing source negatives; real browser host/file edits and recovery |
| 6 — Failclosed/no partial/replay | Invalid package/schema/version/duplicate/secret cases; late source/ownership/audit rollback; repeated create and browser double click |
| 7 — Current Admin/CSRF/source access | All4 route Dev/CSRF/session denial; role revocation inside confirmation; browser controls denied |
| 8 — Exact TOML distinct/unchanged | Existing import API and browser regression suite; separately worded advanced action |

Evidence images under `transfer-evidence/`: latest successful isolated Chromium full-page file/project review and 390px light/dark. `inspection-*` images are lossless crops solely for visual review; PNG headers are technically unavailable. View inspection observed legible mapping, wrapped paths/digests, explicit exclusions and stopped creation. No participant/live/full-WCAG claim.

No children/subagents/executors. Fifteen authored paths plus three generated asset changes; workflow evidence separate. Versions/dependencies/setup untouched. Final canonical proof is saved in `.agentic/tasks/TASK-b93bf854.validation-final.json`.

## Final observed proof

`python -X utf8 .agentic/aegis.py check --task TASK-b93bf854 --strict --run --json`: exit 0, strict passed, zero errors, 9 advisory warnings/30 notes. Configured complete pytest: 1049 passed, one platform skip and existing TestClient warning; Ruff: passed; frontend helper/typecheck/build and 86 Chromium: passed. Production `npm run build` and separate `uv run ruff check .` also exit 0. Failed attempt remains retained; no test/assertion/command omitted or weakened.

Advisories: three historical tracked-fingerprint/malformed-other-journal warnings; six scanner coverage notices for PNG/binary/large generated/report content. Images were visually inspected and contain isolated fixture references; generated assets derive from reviewed sources. Source/package diff and exact hashes supplement the bounded scanner. Thirty notes are repository-wide manual-verification/historical observations; no manual acceptance was substituted for this task’s public tests. Build chunk >500kB and dependency/color warnings remain informational.

Final unchanged inventory checks: no digest mismatches or unexpected paths; local/remote branch remain baseline. Issue #10 and epic #3 remain open; no forge mutations, commits or pushes. Pending coordinator inventory verification/delivery instruction.

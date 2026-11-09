<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# W15 candidate review

Round6 review: the directly approved fifth corrective cycle increases only the suite-wide browser budget to480s and the matching AEGIS review bound to5; per-test limits,111 cases, one worker and zero retries remain. Final strict proof exit0:1145 Python passed/1existing skip, Ruff passed, npm validate passed including111 Chromium journeys;0errors/12explained advisories/29unrelated notes. Frozen candidate ready for coordinator delivery review.

Round4 invalidation is preserved in the task journal. Direct human RULING-003 authorizes a fourth narrow corrective cycle. Round5 reviews supersede the invalidated verdicts after persisted-project validation and negative read/restart/API proof.

Issue: live Gitea #19, `[Web UX] Record structured redacted change evidence and build useful audit history`.
Candidate: `23261bfa52caecc009238be067c6dc4917998b42d731159e4ea56cf6aabca155` on base `dd83612259daa0a34828f026093a19e90276ea76`; exact files/deletions and byte hashes: `audit-candidate-inventory.md`.
Scope: W15 only. No #16/#17/#20, planning edits, release, export invention, deployment, paid tool, executor, subagent, commit, push or issue closure.

Two distinct **same-agent** review lenses, authorized by task RULING-002. No independent reviewer is claimed. Round 6: specification compliance approved; implementation quality approved. Five corrective cycles used (maximum five, direct human RULING-004). Round1 final gate failed four Python regression assertions/fixtures and missing translated codes; all findings corrected with focused proof before renewed review. Round2 full Python and lint passed; browser failed from persisted locale-fixture preferences. Finally restores original explicit or en/system effective fallback preferences; 13 consecutive audit/dashboard journeys pass. Round3 full proof passed 1144 Python/111 Chromium cases, but supplemental inspection exposed oversized actor SQLite overflow. Final cycle bounds actor/offset at API and store boundaries; new public422/typed-store assertions pass. Earlier semantic corrections are recorded in the journal, with observed red/green proof. The final verification-budget correction changes no product contract. Both distinct same-agent lenses approve the refreshed tree. Both verdicts bind this material tree and require successful final full proof.

| Live criterion | Implemented contract and observed offline proof |
|---|---|
| 1. Structured evidence | Closed schema1 values in schema14; actor/time/resource/project/correlation/revisions/known diff. Account/config/access/enrollment/import/clone/pickup cases in test_web_audit_evidence.py; account create happy+audit-fault rollback. |
| 2. No secret leaks | Recursive closed keys/values, opaque server correlation, typed redacted failures and read validation. nested_secret_and_error_metadata; corrupt_audit_storage parameter cases; browser malformed-password rejection. |
| 3. Failure/crash/replay truth | Owning SQLite transactions; filesystem uncertain attempt and separate durable receipt; claimed worker terminal confirmation. access_update_rolls_back, operation_completion_fault, filesystem_apply_crash_retry, invalid_executor_exit_code, enrollment_rollback, completion_replay. |
| 4. Legacy unknown | Null recorded absence, no inferred actor name/diff/stable project; schema13 fixture preserves identities. legacy_rows, schema13_upgrade; Dev name-only exclusion. Superseded 2026-11-01: there are no legacy rows; an audit row without structured evidence is corrupt. |
| 5. Authorized server filters | SQL WHERE before COUNT/LIMIT, exact actor/project/action/half-open UTC. authorized_server_filters, admin_filters_counts_period, Dev global/unassigned/revoked/admin/financial exclusions; browser pages retain filters. |
| 6. Independent retention | System status Admin/CSRF policy with independent nullable bounds and actual deletion count. policy_evidence_and_pruning, retention_does_not_break_confirmation; existing RBAC/auditPolicy unit tests; browser separation/impact. |
| 7. Atomic audit upgrade | Existing initialization transaction, preserved users/grants/state, schema14 mandatory audit/index/receipt validation, no runtime migration. auth legacy upgrade fixtures, corrupt_audit_storage, bad_legacy_upgrade_rolls_back. Superseded 2026-11-01: REQ-DATA-196dcd48 is retired; the web store has one schema and refuses a database of another without upgrading it (REQ-DATA-a1d82c3b). |
| 8. Useful truthful UI | Who/What/When/Result, explicit unknown and prepared/discarded/uncertain labels, expandable redacted evidence, empty/error/retry, 10/25/50/All, existing project jobs retained. Five audit Chromium journeys; EN/FR/DE/RO, light/dark, 390px. |

Focused proof: 32 dedicated Python cases passed; four failed exact regression selectors now pass; 51 Node helper/catalog cases pass; five audit Chromium journeys plus eight consecutive dashboard journeys passed; whole `04_Software` Ruff passed; deployable static build passed. Screenshots inspected and preserved in `audit-evidence/`. Final proof is recorded truthfully in TASK-965eaba9 journal and `.agentic/tasks/TASK-965eaba9.verification.json` after execution (prior failed-gate evidence stays in audit-validation.log); focused results are not a substitute.

Semantics inspected: every changed component/diff, redaction, SQL parameters/current grants, legacy absence, transaction rollback and replay behavior, retention receipts, CSRF/role gates, source/config revisions, strict browser validation and stale unmount cancellation, portability, documentation/knowledge/architecture and generated asset license stamping. No unresolved in-scope finding. Final correction validates persisted project names using the existing new-write grammar; the negative fixture proves recent_audit, restart and authenticated API fail closed without returning its credential-bearing URL. Final code corrections use existing translated invalid_request/project_not_found codes for invalid filter or denied scope; fixture changes preserve fault injection and genuine pre14 schema shapes.

Accepted advisories: two existing tracked sidecars, two unrelated old journal format warnings; heuristic password literals are unchanged account SQL/hashed-password paths or offline fixture credentials; generated minified JS cannot be fully scanned by the heuristic. Source/value negative proof remains active. Build reports a bundle over 500kB; no code-splitting expansion in W15. Windows unprivileged-symlink test is skipped by its existing platform guard. Test client deprecation and NO_COLOR/FORCE_COLOR messages are dependency/tool warnings. No manual/live acceptance is claimed. Filesystem/SQLite cannot share an atomic commit: uncertain attempts are conservative evidence until reconciliation. Completed receipts retain minimal deduplication metadata independently of visible audit retention.

Delivery: freeze for coordinator verification. Commit/push/issue-close remain pending explicit coordinator delivery acceptance; no merge or PR requested by this delegation.

Final proof: `.agentic/tasks/TASK-965eaba9.verification.json`. Verification-only config is covered by direct human approval and full-suite execution; its missing product requirement path link is an accepted advisory, with no reduced coverage. Journal-only RULING-005 confirms direct human cycle/path approval in machine-readable form, preserving malformed prior entries as history.

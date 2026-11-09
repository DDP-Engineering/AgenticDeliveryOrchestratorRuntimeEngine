<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Published Gitea backlog

All issue requirements are English. Publication used the authenticated tea CLI. No implementation or AEGIS task was started. Native dependencies, labels and bodies were read back after creation.

| Work item | Issue | Priority | Dependencies |
| --- | --- | --- | --- |
| EPIC | [3](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/3) [Web UX] Deliver a self-explanatory ADORE operator interface | P1 | All child issues (#4 through #20) |
| BASE | [4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) [Web UX] Publish the implementation baseline and approved design assets | P1 | None |
| W01 | [5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5) [Web UX] Introduce the accessible dashboard shell, branding and plain-language vocabulary | P1 | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| W02 | [6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) [Web UX] Add stable display identity and safe paused-enrollment backend contracts | P1 | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| W03 | [7](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/7) [Web UX] Build guided project enrollment with explicit verification and review | P1 | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) |
| W04 | [8](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/8) [Web UX] Make exact host-specific TOML enrollment understandable and revision-safe | P1 | [W03 #7](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/7) |
| W05 | [9](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/9) [Web UX] Define and export a versioned portable project-settings package | P2 | [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) |
| W06 | [10](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/10) [Web UX] Implement portable settings import and settings-based project cloning | P2 | [W03 #7](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/7), [W05 #9](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/9) |
| W07 | [11](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/11) [Web UX] Expose an authorized global job read model with actionable evidence | P1 | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| W08 | [12](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/12) [Web UX] Rework project hubs, attention queues and job details around the next action | P1 | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W07 #11](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/11) |
| W09 | [13](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/13) [Web UX] Organize project settings by purpose and review candidate changes before applying | P1 | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5) |
| W10 | [14](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/14) [Web UX] Make statistics scope, per-job usage and measurement coverage consistent | P2 | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| W11 | [15](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/15) [Web UX] Present scoped statistics and per-job consumption with honest coverage | P2 | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W07 #11](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/11), [W10 #14](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/14) |
| W12 | [16](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/16) [Web UX] Specify message-count semantics and executor/forge source capabilities | P2 | [BASE #4](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/4) |
| W13 | [17](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/17) [Web UX] Collect and expose message counts from approved real evidence sources | P2 | [W12 #16](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/16), [W10 #14](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/14) |
| W14 | [18](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/18) [Web UX] Create users with explicit role and project access in one reviewed operation | P2 | [W01 #5](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/5), [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6) |
| W15 | [19](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/19) [Web UX] Record structured redacted change evidence and build useful audit history | P2 | [W02 #6](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/6), [W06 #10](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/10), [W09 #13](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/13), [W14 #18](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/18) |
| W16 | [20](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/20) [Web UX] Verify the integrated redesign with offline regression and novice-user acceptance | P1 | [W04 #8](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/8), [W06 #10](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/10), [W08 #12](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/12), [W09 #13](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/13), [W11 #15](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/15), [W13 #17](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/17), [W14 #18](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/18), [W15 #19](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/19) |

## Pickup gates

Implementation starts only after BASE is satisfied and the operator authorizes pickup. agent-hold prevents premature pickup while native blockers remain. The configured ready label is deliberately absent. EPIC, BASE and W12 carry no-agent because they are coordination, repository or standalone planning work. W12 also requires explicit owner approval of message semantics before W13. Native dependencies do not replace these authority gates.

## Remote design artifacts

## Approved reference assets

- [English design brief, provenance manifest, logo variants and visual references](http://192.168.1.15:3001/attachments/a3006796-ce57-452a-8497-c1e38b102a09) — ADORE_Web_UX_Reference.zip.
- [Approved transparent DDP Engineering mark](http://192.168.1.15:3001/attachments/79f13809-2d28-47da-9870-6bd8007776f2) — 630x300 PNG; #B8D1C4 on #102F29 without a white panel.
- [Overview visual reference](http://192.168.1.15:3001/attachments/e9f32c44-3369-4589-b95f-1197b86a195a).

The archive is available through this Gitea issue rather than only the local untracked planning folder. Extract it and verify asset-manifest.json hashes. Historical screenshot copy is Romanian; implement English issue/specification copy and preserve supported localization.

All three uploaded artifacts were downloaded through the authenticated tea CLI and matched the local SHA-256 values. No Git commit/push, product implementation or AEGIS task was performed during backlog creation.

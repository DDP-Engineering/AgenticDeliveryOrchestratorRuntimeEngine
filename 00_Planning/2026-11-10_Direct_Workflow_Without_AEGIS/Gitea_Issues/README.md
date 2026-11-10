<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Published Gitea backlog: repositories without AEGIS

Published 2026-11-10 with the authenticated `tea` CLI (`tea api`). Titles, labels,
bodies and native dependencies were read back after creation. The files in this
folder are the sources with the published links; once work starts, the live issue
is authoritative. Plan: [../PLAN.md](../PLAN.md).

ADORE implements these tickets on this repository with Pi on `gpt-6.1-sol` at
thinking `high`. Each ticket states its goal, decisions, scope, **Done when**
(unchecked `- [ ]` items) and **Validation** commands, plus when to ask in the
questions file.

None of them carries `agent-ready`, so ADORE does not pick them up by itself. The
epic and DW-07 carry `no-agent` and are never picked. Before adding `agent-ready`
to DW-01, finish the owner steps in plan section 6.1.

| Work item | Issue | Priority | Blocked by |
| --- | --- | --- | --- |
| EPIC | [#60](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/60) [Direct] Run tickets in repositories without AEGIS | P1 | #61 to #68 |
| DW-01 | [#61](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/61) [Direct] adore init probes AEGIS with the configured Python | P1 | - |
| DW-00 | [#68](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/68) [Direct] Read the agent prompts from files shipped with ADORE | P1 | #61 |
| DW-02 | [#62](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/62) [Direct] Direct workflow in the orchestrator, unverified candidates | P1 | #61, #68 |
| DW-03 | [#63](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/63) [Direct] Verification command and bounded fix attempts | P1 | #62 |
| DW-04 | [#64](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/64) [Direct] Enroll repositories without AEGIS in the web interface | P1 | #63 |
| DW-05 | [#65](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/65) [Direct] Suggest the verification command from repository files | P2 | #64 |
| DW-06 | [#66](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/66) [Direct] Show direct jobs clearly in Jobs | P2 | #64 |
| DW-07 | [#67](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/67) [Direct] Live acceptance and documentation audit | P1 | #61 to #66, #68 |

DW-05 and DW-06 may run in either order; everything else runs one at a time. DW-07
needs the owner present (real credentials and repositories).

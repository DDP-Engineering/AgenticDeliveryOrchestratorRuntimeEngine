<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Published Gitea backlog: Pi as the single coding agent

Published 2026-11-01 with the authenticated `tea` CLI (`tea api`). Titles, labels,
bodies and native dependencies were read back after creation. The files in this
folder are the sources with the published links; the live issue is authoritative
once work starts. Plan: [../PLAN.md](../PLAN.md).

The tickets are written for agentic implementation (Claude Code or Codex): each
states its decisions, scope, where to look, acceptance criteria, verification
commands and when to stop and ask. None carries ADORE's ready label, so ADORE does
not pick them up by itself.

| Work item | Issue | Priority | Blocked by |
| --- | --- | --- | --- |
| EPIC | [#50](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/50) [Pi] Make Pi the single, predefined coding agent of ADORE | P1 | #51 to #58 |
| PI-01 | [#51](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/51) Spike: confirm Pi 1.x headless contracts before integration | P1 | - |
| PI-02 | [#52](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/52) Run Pi through its RPC mode in the executor image | P1 | #51 |
| PI-03 | [#53](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/53) Remove OpenCode, Codex and Qwen Code support | P1 | #52 |
| PI-04 | [#54](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/54) Provider, model, API key and OpenAI-compatible endpoint setup | P1 | #53 |
| PI-05 | [#55](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/55) Sign in with ChatGPT from the ADORE web interface | P1 | #54 |
| PI-06 | [#56](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/56) Web search, page reading and downloads behind an internet switch | P2 | #52, #54 |
| PI-07 | [#57](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/57) Pi installed on the server through an ADORE-managed installation | P2 | #52, #53 |
| PI-08 | [#58](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/58) Live acceptance, documentation audit and backlog cleanup | P1 | #53 to #57 |

PI-01 and PI-08 need the owner present (real credentials). PI-06 and PI-07 can run
in parallel with PI-05.

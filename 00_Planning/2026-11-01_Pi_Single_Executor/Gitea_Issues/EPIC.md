<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# [Pi] Make Pi the single, predefined coding agent of ADORE

Labels: P1, change. Coordination only: implement the child tickets, not this one.

## Why

Configuring the coding agent is the hardest part of setting ADORE up: four agents
(OpenCode, Codex, Pi, Qwen Code), each with its own launch command, sign-in files,
output format and quirks. ADORE will ship one agent, Pi, fully predefined. The user
picks a provider and model, enters an API key or signs in with ChatGPT (or points
at LM Studio, Ollama or vLLM), switches internet access on or off, and chooses
container or server.

Plan with the evidence, target design and decisions:
`00_Planning/2026-11-01_Pi_Single_Executor/PLAN.md`.

## Decisions (do not reopen in child tickets)

- Pi is the only agent; OpenCode, Codex and Qwen Code are removed.
- ADORE drives Pi through RPC mode (`pi --mode rpc --no-session`), one process per stage.
- Pi and `pi-web-access` are pinned and shipped by ADORE (image and server install).
- API keys stay out of `config.toml`; one ChatGPT credential per host, used in place.
- No migrations: old executor configuration is refused with what to fix.
- The internal executor interface stays, with one implementation.
- Owner decisions (2026-11-01): internet access Off by default; one ChatGPT
  credential per server; Windows server installs in scope now; ADORE is free for
  now; work on branch `task/adore-web-interface`.

## Work items

| ID | Ticket | Depends on | Priority |
|---|---|---|---|
| PI-01 | [PI-01 #51](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/51) Spike: confirm Pi 1.x headless contracts | - | P1 |
| PI-02 | [PI-02 #52](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/52) Run Pi through its RPC mode in the executor image | PI-01 | P1 |
| PI-03 | [PI-03 #53](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/53) Remove OpenCode, Codex and Qwen Code support | PI-02 | P1 |
| PI-04 | [PI-04 #54](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/54) Provider, model, API key and OpenAI-compatible endpoint setup | PI-03 | P1 |
| PI-05 | [PI-05 #55](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/55) Sign in with ChatGPT from the web interface | PI-04 | P1 |
| PI-06 | [PI-06 #56](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/56) Web search, page reading and downloads behind an internet switch | PI-02, PI-04 | P2 |
| PI-07 | [PI-07 #57](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/57) Pi installed on the server through an ADORE-managed installation | PI-02, PI-03 | P2 |
| PI-08 | [PI-08 #58](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/58) Live acceptance, documentation audit and backlog cleanup | PI-03 to PI-07 | P1 |

PI-06 and PI-07 can run in parallel with PI-05. Native Gitea dependencies mirror
this table.

## Done when

- [ ] All child tickets are closed with their acceptance criteria met.
- [ ] A user sets up a project with only provider, model, credential, internet
      switch and location, in a container and on a server.
- [ ] Live acceptance (PI-08) passed for an API-key provider, an OpenAI-compatible
      local endpoint and a ChatGPT subscription.
- [ ] No OpenCode, Codex or Qwen Code code, configuration, tests or documentation
      remain, except changelog history and refusal messages.

## Existing tickets affected

Closed as superseded on 2026-11-01: #43, #45, #46 and #33 (by PI-03 #53), #44 and #32 (by PI-07 #57) and #34 (by PI-02 #52). Still open and related to PI-06: #26.

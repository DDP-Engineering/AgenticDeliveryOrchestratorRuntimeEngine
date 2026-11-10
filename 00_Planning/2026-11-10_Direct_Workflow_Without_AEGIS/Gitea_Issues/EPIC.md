<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# [Direct] Run tickets in repositories without AEGIS

Labels: P1, no-agent.

Coordination only. ADORE never picks this ticket (`no-agent`); it implements the
child tickets.

## Why

ADORE refuses every repository without AEGIS: enrollment answers
`repository_aegis_missing` and polling claims nothing. Many repositories ADORE
should serve have no AEGIS, and they should not receive it as a side effect of a
ticket. ADORE gets a second, smaller path for them, the **direct workflow**:

1. Pi implements the ticket in one bounded session.
2. ADORE checks that the session finished and runs one verification command.
3. The candidate goes to the same human approval and publication as today.

Plan with evidence, target design and decisions:
`00_Planning/2026-11-10_Direct_Workflow_Without_AEGIS/PLAN.md`.

## Decisions (do not reopen in child tickets)

- **Choosing the workflow.** ADORE decides per ticket from the run's worktree:
  - `.agentic/aegis.py` absent: direct workflow;
  - present: AEGIS workflow, probed as today;
  - present but unsupported or broken: refused as today, never a silent fallback.
- **No setting selects the workflow.** The run records it, and a resumed run keeps
  it.
- **AEGIS is left alone.** ADORE never installs, upgrades or edits AEGIS in a target
  repository.
- **A direct run reuses what exists.** It goes through the stages build → validate
  → done, with one Pi session per attempt. It uses the same isolation, egress,
  budgets, questions file, approval label, publication and review loop.
- **Done means:**
  - Pi ended normally;
  - no questions are open;
  - the worktree changed;
  - the verification command passed. When no command is configured, the approval
    comment says the candidate is unverified.
- **One new setting:** `[workflow] verify_command`, optional. ADORE suggests a value
  from repository files; a human confirms it.
- **No migrations.** A run record in the previous format is refused with what to
  delete.
- **How it is built.** ADORE implements this epic on this repository with Pi
  `gpt-6.1-sol` at thinking `high`, one ticket at a time, through its AEGIS
  workflow.

## Work items

| ID | Ticket | Depends on | Priority |
|---|---|---|---|
| DW-01 | [DW-01 #61](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/61) `adore init` probes AEGIS with the configured Python (smoke ticket) | - | P1 |
| DW-02 | [DW-02 #62](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/62) Direct workflow in the orchestrator, unverified candidates | DW-01 | P1 |
| DW-03 | [DW-03 #63](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/63) Verification command and bounded fix attempts | DW-02 | P1 |
| DW-04 | [DW-04 #64](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/64) Enroll repositories without AEGIS in the web interface | DW-03 | P1 |
| DW-05 | [DW-05 #65](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/65) Suggest the verification command from repository files | DW-04 | P2 |
| DW-06 | [DW-06 #66](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/66) Show direct jobs clearly in Jobs | DW-04 | P2 |
| DW-07 | [DW-07 #67](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/67) Live acceptance and documentation audit (owner) | DW-01 to DW-06 | P1 |

Native Gitea dependencies mirror this table. ADORE does not read them: add
`agent-ready` to one ticket at a time, after the previous PR is merged.

## Before the first ticket (owner)

These steps are in plan section 6:

- P1: make the AEGIS commands in `.agentic/aegis.toml` portable.
- P2: build a project image with Chromium for Playwright.
- P3: allow dependency registries through egress.
- P4: set provider, model `gpt-6.1-sol`, thinking `high`, the integration branch
  and the budgets.
- P5: dry-run the strict check in the image.

## Progress

- [ ] DW-01
- [ ] DW-02
- [ ] DW-03
- [ ] DW-04
- [ ] DW-05
- [ ] DW-06
- [ ] DW-07

## Done when

- [ ] All child tickets are closed with their Done-when items met.
- [ ] A repository without AEGIS is enrolled in the web interface, and one of its
      tickets reaches a draft PR with verification evidence. No AEGIS file appears
      in that repository.
- [ ] A repository with AEGIS behaves exactly as before, checked live in DW-07.
- [ ] No documentation, help or interface text says ADORE works only with
      repositories that have AEGIS, except where it describes the AEGIS workflow
      itself.

## Validation

- DW-07's live acceptance checklist is passed, with its evidence recorded on
  DW-07.
- This search finds only descriptions of the AEGIS workflow itself:

  ```
  git grep -n -i -E "already contain AEGIS|repository-installed AEGIS|Install AEGIS in|must carry an AEGIS" -- README.md 01_Documentation 04_Software/adore 04_Software/web/src
  ```

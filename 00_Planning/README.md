<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Planning

Architecture notes, design decisions, and the roadmap for ADORE, the Agentic
Delivery Orchestrator & Runtime Engine, belong here.

This folder is planning and project memory: the documents that describe why
ADORE is shaped the way it is, what it deliberately does not do, and what
remains open. AI agents must not update planning documents as routine
implementation maintenance. Update this folder only when the user explicitly
asks for a planning, strategy, decision-record, or TODO change.

Contents:

- [ADORE_Web_Interface_Plan.md](ADORE_Web_Interface_Plan.md) - draft web
  interface architecture, login and project access, configuration, metrics,
  deployment, phased delivery, and open product decisions.
- [2026-11-01_Pi_Single_Executor/PLAN.md](2026-11-01_Pi_Single_Executor/PLAN.md) -
  Pi as ADORE's single coding agent: decision, evidence, target design and the
  Gitea backlog (epic #50) for removing OpenCode, Codex and Qwen Code.
- `ADORE_System_Overview.md` - what ADORE is, the ADORE/AEGIS ownership
  boundary, the end-to-end run, runtime states, the safety and approval model,
  the components as implemented, the supported environment, and the known
  limits and open work of the current release.

Design detail lives with the implementation rather than here:

- `05_SoftwareDocu/Component_*.md` - one contract per component, updated in
  the same change as the code;
- `.agentic/knowledge/<component>.md` and `.agentic/context/` - the routes and
  current facts an agent reads before changing a component;
- `.agentic/requirements/` - the behavior register;
- `01_Documentation/` - operator guides and the configuration and CLI
  references;
- `CHANGELOG.md` - release history, including each AEGIS re-verification.

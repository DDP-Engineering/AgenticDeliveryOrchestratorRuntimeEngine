<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Planning

Architecture notes, requirements, design decisions, and roadmap for the Agentic
Delivery Orchestrator belong here.

This folder is for planning and project memory: documents used to design and
develop the current app, strategic choices, investigation records, and TODOs.
AI agents must not update planning documents as routine implementation
maintenance. Update this folder only when the user explicitly asks for a
planning, strategy, decision-record, or TODO change.

Planned contents:

- `Orchestrator_Architecture.md` - the orchestrator design: the thick-conductor
  state machine, forge adapter interface, executor launcher, isolation model,
  and the draft-MR delivery boundary.
- `Clarification_Flow.md` - the park-on-ambiguity design: how the orchestrator
  posts questions to the ticket, parks the run, and resumes it on a human reply.
- `Forge_And_Executor_Adapters.md` - the abstractions that keep GitLab/GitHub
  and opencode/pi/codex swappable.
- `Roadmap.md` - the crawl -> walk -> run adoption path and known trade-offs.
- Design references carried over from the initial proposal
  (`Agentic_Automation_Proposal.md`).

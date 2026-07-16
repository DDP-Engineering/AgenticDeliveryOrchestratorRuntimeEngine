<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Documentation

Project-level documentation for operating and configuring the Agentic Delivery
Orchestrator belongs here.

This folder is for project documentation intended to help people understand,
install, configure, operate, or present ADORE. It includes manuals, setup guides,
configuration references, user-facing behavior descriptions, operational
runbooks, and presentations. AI agents should update this folder whenever a
software interface, user-visible behavior, command, configuration contract, or
implementation-facing guide changes.

Current contents:

- `Operator_Cheat_Sheets/` - short visual operator cheat sheets for setup,
  tickets and labels, profiles and images, monitoring, steering, and recovery.
- `Step_By_Step_Setup.md` - step-by-step operator setup guide for Windows and
  Linux hosts.
- `Setup_And_Credentials.md` - host, forge, executor, and credential guidance.
- `Onboarding_New_Project.md` - runtime-project onboarding guide.
- `Configuration_Reference.md` - the `config.toml` keys, profiles,
  readiness, labels, isolation, delivery, review, reconcile, and metrics.
- `Code_Style.md` - code style, Python Doxygen conventions, and local
  file/function revision marker rules.

Planned contents:

- `Operator_Guide.md` - how to run the orchestrator, what the ticket lifecycle
  labels mean (`agent-ready`, `agent-working`, `agent-clarify`, `agent-mr`,
  `agent-failed`), and how to answer clarification questions.
- `Prompt_Reference.md` - the per-gate prompts the conductor sends to the
  executor.

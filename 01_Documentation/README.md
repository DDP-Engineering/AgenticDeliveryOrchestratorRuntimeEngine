<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Documentation

Project-level documentation for operating and configuring the Agentic Delivery
Orchestrator belongs here.

Planned contents:

- `Operator_Guide.md` - how to run the orchestrator, what the ticket lifecycle
  labels mean (`agent-ready`, `agent-working`, `agent-waiting`, `agent-mr`,
  `agent-failed`), and how to answer clarification questions.
- `Configuration_Reference.md` - the `config.toml` keys: forge selection,
  executor command templates, priority/readiness rules, run budgets, and
  isolation settings.
- `Prompt_Reference.md` - the per-gate prompts the conductor sends to the
  executor.

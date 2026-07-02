<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

Deployment, packaging, and release material for the Agentic Delivery
Orchestrator belong here.

Planned contents:

- `Deployment_Ubuntu22.md` - how to run the orchestrator on an Ubuntu 22 server
  (service/cron setup, container runtime, forge and model credentials).
- `Deployment_Windows11.md` - first-test setup on Windows 11.
- `Container.md` - the executor container image contents and build/publish steps.
- `Release_Notes.md` - notable release and change history.

Delivery model: the orchestrator is delivered as a Python package plus an
executor container image. Python 3.11+ is the only host runtime requirement for
the orchestrator itself; the executor and target-repo tooling run inside the
container.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Software Documentation

Implementation notes, internal contracts, and deeper technical documentation for
the orchestrator package belong here.

Planned contents:

- `State_Machine.md` - the run states and transitions (pick, isolate, gate loop,
  park/resume on clarification, deliver, retry, escalate) and the run budgets
  that bound them.
- `Forge_Adapter_Contract.md` - the methods every forge adapter implements
  (`list_ready`, `claim`, `post_comment`, `open_mr`, `set_state`) and their
  expected behavior.
- `Executor_Launcher_Contract.md` - how an executor is invoked per gate and how
  its result and any clarification signal are read back.
- `Idempotency_And_Recovery.md` - how the orchestrator recovers after a restart
  without double-posting comments or re-opening MRs.

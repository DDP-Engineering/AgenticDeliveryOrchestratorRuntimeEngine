<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Failure Recovery and Cleanup

Applies to ADORE 0.5.0 and AEGIS 0.5.x schema 1.

- Attempts `1/3` and `2/3`: read the edited incident; a fresh remediation
  session may run.
- Attempt `3/3`: no fourth launch. The terminal comment confirms container
  stop, preserved worktree/evidence and released slot.
- Questions: answer on the ticket and add `agent-answered`; no stage failure is
  consumed.
- Notification outage: restore forge access and poll until the outbox delivers.
  `adore retry` is refused while it remains pending.
- Target/candidate drift: expect approval removal, reintegration, validation,
  new presentation and fresh approval.

Commands:

```text
adore --profile <name> logs <run-id>
adore --profile <name> retry <run-id>
adore --profile <name> reset <run-id> --to <stage> --force
adore --profile <name> cleanup
```

Retry resets only the active stage counter and active-work clock. Reset changes
ADORE state but never edits an AEGIS task journal. Cleanup reports corrupt
state and never auto-deletes it. `delete --force` is irreversible.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Failure Recovery and Cleanup

Applies to ADORE 0.13.0 and AEGIS schema 1.

- `stage-continuation`: useful candidate changes plus appended work evidence;
  ADORE checkpoints and starts a fresh session at the same stage automatically.
  Failure counts are preserved; global run budgets still apply.
- `NO_STAGE_PROGRESS`: the same stage lacks either progress signal or its Log
  history was rewritten; this spends a failed attempt.
- `WORKTREE_PROGRESS`: observation failed; repair worktree/Git access before retry.
- Attempts `1/3` and `2/3`: read the edited incident; a fresh remediation
  session may run.
- Attempt `3/3`: no fourth launch. The terminal comment confirms container
  stop, preserved worktree/evidence and released slot.
- Questions: answer on the ticket and add `agent-answered`; no stage failure is
  consumed.
- Subscription/local cost stop: set `[budgets] max_cost_usd = 0`, validate the
  profile and retry. Recorded usage remains visible; other bounds still apply.
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
ADORE state but never edits an AEGIS task journal.

Reach for reset rather than retry after `FORBIDDEN_STAGE_TRANSITION`. That
failure means the journal reports a stage ADORE cannot legally reach from the
one it recorded, with no Log entry for the stages in between, so retry replays
the identical refusal. Read the journal, pick the stage the work genuinely
reached, `reset --to` it, then retry. The terminal comment names the command. Cleanup reports corrupt
state, sweeps orphan executor/proxy/network resources and worktree husks, and
never auto-deletes state. Failed runs are protected for retry; release one
with `cancel <run-id>` (retain audit state) or irreversible `delete <run-id>
--force`.

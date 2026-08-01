<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Recovery And Maintenance

Use this guide for a parked, failed, unwanted, or interrupted run. Start with
read-only inspection and choose the smallest action that restores the intended
state.

## 1. Inspect Before Acting

```bash
adore --profile <profile-name> status
adore --profile <profile-name> runs
adore --profile <profile-name> logs <run-id>
```

Inspect the ticket, run journal, current stage, and executor archive before
retrying or deleting anything. If `status` reports corrupt run state, ADORE
skips it; inspect the run directory manually before removal.

## 2. Resume a Clarification Park

When ADORE needs a human answer, it parks the run and preserves its worktree
and state.

1. Answer in a normal human comment on the ticket.
2. Add `agent-answered` if the profile uses label signaling.
3. Run one supervised poll.

```bash
adore --profile <profile-name> run --once
```

If no answer arrives before `[clarification] answer_timeout`, ADORE moves the
run to the configured terminal state, normally `failed`.

## 3. Use the Correct Recovery Command

| Situation | Command | Result |
| --- | --- | --- |
| Continue a failed or retryable run | `adore --profile <profile-name> retry <run-id>` | Re-arms retry flow without repeating completed gates. |
| Stop a run gracefully | `adore --profile <profile-name> cancel <run-id>` | Cancels the run and updates stored state. |
| Re-run from a deliberate stage | `adore --profile <profile-name> reset <run-id> --to <stage> --force` | Moves the stage pointer; run `retry` afterwards. |
| Permanently remove stored run state | `adore --profile <profile-name> delete <run-id> --force` | Irrecoverable removal. |
| Sweep stale resources | `adore --profile <profile-name> cleanup` | Removes resources no active valid run owns. |

`reset` requires `--force` because it can repeat work, spend model budget, and
change ticket history. `delete` is for deliberate disposal, not routine
cleanup.

### Runs abandoned by a crashed conductor

A run whose orchestrator process died mid-conduct (power loss, `SIGKILL`, a
systemd restart) stays `working` in the store. Because `working` runs count
against `[polling] max_concurrent_runs`, that used to stop all future pickup
silently - with the default of 1, one crash stopped the orchestrator with no
signal beyond `"at_capacity": true` in the poll summary.

The poller now reaps these itself. At the start of every poll pass, any
`working` run that this process is not currently conducting and whose last
state write is older than `[budgets] max_wall_clock_seconds +
per_gate_timeout_seconds` is **escalated to `failed`**, journaled as
`stale-working-detected`, and its ticket status comment updated. The slot is
free again in the same pass, so the next ticket is picked without operator
action.

You still decide what happens to the reaped run: read `adore logs <run-id>`,
then `adore retry <run-id>` to continue it from the stage where it stopped.
The threshold is derived from your own budgets, so a deployment that allows
long runs automatically waits longer before reaping. Nothing is deleted - the
worktree, state, and journal are all kept.

## 4. Clean Up Safely

Run cleanup after a host interruption, a closed or merged MR/PR, or an
intentional cancellation:

```bash
adore --profile <profile-name> cleanup
```

Cleanup can remove stale locks, containers, and worktrees. It reports corrupt
run state but does not automatically discard it. For a corrupt run:

1. Inspect its journal and archived executor output.
2. Confirm no active process owns the run.
3. Use `delete --force` only when removal is intentional.

## 5. Planned Maintenance

Before changing an image, credentials, profile configuration, labels, or the
host runtime:

```bash
adore --profile <profile-name> pause
adore --profile <profile-name> config validate
adore --profile <profile-name> run --dry-run
adore --profile <profile-name> resume
```

Pause only affects new pickup. Check `runs` and the target forge before taking
host actions that would interrupt an in-flight container or worktree.

For normal operation and metrics, return to
[Operations_Guide.md](Operations_Guide.md). For every command and safety flag,
see [CLI_Reference.md](CLI_Reference.md).

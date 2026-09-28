<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Transfer preserved runs to explicit human ownership at safe execution boundaries

When the operator requests human handoff, the runtime shall stop further autonomous execution at a safe boundary, attempt to publish a final recovery checkpoint, preserve the worktree and evidence in durable human ownership, and prevent polling, retry, reset and automatic cleanup from reclaiming that work.

## Contract

See TASK-4f1d55b2 Design for the exact state, ownership, concurrency and failure algorithm. Public interfaces: delivery.publish_checkpoints=false (strict boolean) and adore handoff RUN_ID. Checkpoints contain WIP labeling and never open a PR. Handoff is queued while a live conductor holds the lock and completes at the next safe boundary; handoff-pending persists before stop/Git mutations; handed-off is durable and automatic resume is refused. Remote races fail closed without overwriting developer commits.

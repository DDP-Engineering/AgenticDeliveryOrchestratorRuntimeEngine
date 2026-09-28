<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Publish explicit work-in-progress checkpoints with remote ownership protection

Where publish_checkpoints is enabled, the conductor shall publish durable work-in-progress commits to the ticket branch, expose the last verified remote checkpoint and stale failures, preserve local recovery evidence after bounded transport failure, and stop on unexpected remote ownership without granting delivery approval.

## Contract

See TASK-4f1d55b2 Design for the exact state, ownership, concurrency and failure algorithm. Public interfaces: delivery.publish_checkpoints=false (strict boolean) and adore handoff RUN_ID. Checkpoints contain WIP labeling and never open a PR. Handoff is queued while a live conductor holds the lock and completes at the next safe boundary; handoff-pending persists before stop/Git mutations; handed-off is durable and automatic resume is refused. Remote races fail closed without overwriting developer commits.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Setup and First Run

Applies to ADORE 0.13.0 and AEGIS schema 1.

1. Authenticate host `gh`, `glab`, or `tea`, then separately prove Git itself
   can reach the remote:

   ```text
   git ls-remote origin
   ```

   ADORE pushes the run branch with host Git and the host's own credentials;
   the platform CLI login does not cover that. A credential fault here surfaces
   only at publication, after a human has already approved the candidate, and
   that approval is discarded.

2. Verify Docker/Podman and the project executor image.
3. In the target clone run:

   ```text
   python .agentic/aegis.py --version
   python .agentic/aegis.py status --all --json
   ```

   Require a supported `aegis` version, schema `1`, and no unreadable journals.

4. Create and validate a profile:

   ```text
   adore init <profile>
   adore --profile <profile> config validate
   ```

   `init` also reports on the AEGIS companion, the target repository's
   `.gitignore`, and push access, with guidance for each. Act on what it flags
   before the first run rather than after it.

5. Confirm `[recovery]` is three stage attempts, three transient attempts and
   `[5, 30, 120]`; confirm `[delivery] approval_label="agent-approved"`.
   Confirm `[review] on_pipeline_failure` deliberately: the default `revise`
   lets a newly red pipeline on a published draft open a repair round without
   asking. Set it to `notify` while you are still proving the project.
6. Create every configured label in the repository before the first poll.
   ADORE applies and removes labels but never creates them, and the forge
   rejects a name that does not exist. The rejection lands at claim time,
   before ADORE can comment anywhere, so the ticket simply sits there still
   wearing its ready label while the reason goes only to the console and
   `adore.log`. See
   [Tickets, Readiness and Labels](Tickets_Readiness_And_Labels.md) for the
   full set.
7. Prepare one small `agent-ready` ticket with priority and acceptance criteria.
8. Preview and run one supervised poll:

   ```text
   adore --profile <profile> run --dry-run
   adore --profile <profile> run --once
   ```

9. At `awaiting-approval`, review evidence and freshly add `agent-approved`.
10. Run another poll and confirm a draft MR/PR opens. A human reviews and
    merges.

ADORE migrates no earlier run state; start from a fresh state root.

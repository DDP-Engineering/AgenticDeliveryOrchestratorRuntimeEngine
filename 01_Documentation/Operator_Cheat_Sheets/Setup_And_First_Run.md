<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Setup and First Run

Applies to ADORE 0.13.0 and AEGIS schema 1.

1. Authenticate host `gh`, `glab`, or `tea` and verify Git can push `origin`.
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

5. Confirm `[recovery]` is three stage attempts, three transient attempts and
   `[5, 30, 120]`; confirm `[delivery] approval_label="agent-approved"`.
6. Prepare one small `agent-ready` ticket with priority and acceptance criteria.
7. Preview and run one supervised poll:

   ```text
   adore --profile <profile> run --dry-run
   adore --profile <profile> run --once
   ```

8. At `awaiting-approval`, review evidence and freshly add `agent-approved`.
9. Run another poll and confirm a draft MR/PR opens. A human reviews and merges.

ADORE migrates no earlier run state; start from a fresh state root.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Runtime Software

This directory contains the portable Python implementation and offline tests
for ADORE.

Key components:

- `adore/aegis.py` - typed AEGIS schema-1 companion-CLI boundary;
- `adore/orchestrator.py` - task-journal conductor, bounded recovery, outbox,
  validation, approval, publication and review;
- `adore/state.py` - closed schema-1 state plus append-only JSONL audit;
- `adore/forge/` - GitHub/GitLab/Gitea tickets, comments, labels and draft
  MR/PR operations, deliberately without merge;
- `adore/isolation.py` - worktrees, local checkpoints, fingerprints,
  Docker/Podman lifecycle and executor command seam;
- `adore/executor/` - OpenCode, Pi, Codex and Qwen launchers;
- `adore/config.py`, `doctor.py`, `wizard.py`, `cli.py` - validated setup and
  operator surfaces;
- `tests/` - fully offline unit/contract suite.

Run locally:

```text
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check adore tests
```

Target repositories must carry unchanged `.agentic/aegis.py` from AEGIS 0.5 or
later within major 0 (a major bump is refused at probe) and return schema 1
from `status --all --json`. Executors own journal
transitions but never Git/forge publication. ADORE owns local commits, push and
draft MR/PR creation after fresh fingerprint-bound human approval. Neither the
executor nor ADORE merges.

See the [runtime integration guide](../01_Documentation/Integrating_A_Runtime_Project.md)
for the target-repository contract and onboarding sequence.

## Native local executor

Explicit local profiles run an installed authenticated CLI under the ADORE machine
and service account with dedicated worktrees and verified Windows Job/Linux cgroup
process ownership. Project tools remain user-owned. See [Local execution](../01_Documentation/Local_Execution.md).

# ADORE Runtime Software

This directory contains the portable Python implementation and offline tests
for ADORE.

Key components:

- `adore/aegis.py` - typed AEGIS schema-1 companion-CLI boundary;
- `adore/orchestrator.py` - task-journal conductor, bounded recovery, outbox,
  validation, approval, publication and review;
- `adore/state.py` - closed schema-1 state plus append-only JSONL audit;
- `adore/forge/` - GitHub, GitLab, Gitea and Azure DevOps Services tickets, comments, labels and draft
  MR/PR operations, deliberately without merge;
- `adore/isolation.py` - worktrees, local checkpoints, fingerprints,
  Docker/Podman lifecycle and executor command seam;
- `adore/executor/` - the Pi RPC launcher for container and managed native execution;
- `adore/config.py`, `doctor.py`, `wizard.py`, `cli.py` - validated setup and
  operator surfaces;
- `tests/` - fully offline unit/contract suite.

Prepare the source environment from the repository root:

```text
python 02_Tools/setup/setup_development_environment.py
python 02_Tools/build/build_web_assets.py
```

The setup command installs the locked Python web/development dependency groups
and frontend dependencies. Development dependencies are a dependency group,
not a `dev` package extra. See the [tools guide](../02_Tools/README.md) for
package creation and optional source-checkout services.

`config.example.toml` is the source template. A local `config.toml` and `.env`
are ignored by Git. Keep user data, worktrees and credentials out of commits.
The application sources, prompts, Pi helpers, container recipe assets and
compiled `adore/web/static/` bundle are required package inputs. Python/frontend
caches and browser-test reports can be regenerated.

Repositories with AEGIS use its installed companion and schema-1 contract;
`adore/aegis.py` defines the supported version range. Repositories without AEGIS
use the Direct build/validate/done workflow. An invalid installed companion is
refused. Pi owns agent work and AEGIS journal transitions. ADORE owns local
commits, push and draft or ready MR/PR creation under the configured approval
policy. Neither Pi nor ADORE merges.

See the [runtime integration guide](../01_Documentation/Operations_Guide.md#runtime-project-contract)
for the target-repository contract and onboarding sequence.

## Native local executor

Explicit local profiles run ADORE-managed Pi under the ADORE machine
and service account with dedicated worktrees and verified Windows Job/Linux cgroup
process ownership. Project tools remain user-owned. See [Local execution](../01_Documentation/Local_Execution.md).

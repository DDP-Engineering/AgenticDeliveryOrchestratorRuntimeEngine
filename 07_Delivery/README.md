<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

Runtime packages, release artifacts, and operator handoff material for the
Agentic Delivery Orchestrator & Runtime Engine belong here.

This folder is the delivery area. It contains generated release packages,
archives, checksums, and handoff artifacts produced from the repository tooling;
it is not the place for source code, planning notes, or component
documentation.

The current implemented packaging flow is a trimmed runtime bundle created by
the scripts in `02_Tools/`:

```powershell
.\02_Tools\package_runtime.ps1
```

```bash
bash 02_Tools/package_runtime.sh
```

The generated 0.6.0 bundle is named `adore-runtime-0.6.0.zip` on Windows or
`adore-runtime-0.6.0.tar.gz` on POSIX. It contains the runnable `04_Software`
package contents, deployment scripts under `deploy/`, and the canonical
operator documentation under `Documentation/`. It excludes development files,
test suites, virtual environments, worktrees, local `.adore` state, and
secrets.

Delivery model: ADORE is delivered as a Python package directory plus an executor
container image. Python 3.11+ and `uv` prepare the host-side `.venv` executable;
the executor and target-repo tooling run inside the container. Native Windows
single-file executables and Ubuntu `.deb` packages are not implemented yet.

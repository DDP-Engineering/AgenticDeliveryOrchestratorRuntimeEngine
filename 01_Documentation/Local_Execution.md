<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Local execution

Choose **Runs in → Installed on the server** during enrollment or in
**Settings → Agent and model** to run ADORE-managed Pi in a dedicated worktree
under the current ADORE service account. Container execution remains the default.
Pi has no permission prompts. Use a dedicated, least-privilege OS account:
a worktree and a process scope do not prevent access to files, credentials or
network destinations the account can reach.

## Install and verify

Install Node.js 22.23.4 or later in the 22.x line with its npm distribution.
Run these commands on the ADORE server under the same account and with the
same ADORE home as the service:

```text
adore pi install
adore pi verify
```

On Windows, use the packaged ADORE CLI wrapper if `adore` is not on PATH. The
service may set `ADORE_NODE` to the absolute path of `node.exe` or, on Linux,
`node`. ADORE otherwise finds Node on the service PATH. Project PATH overrides
never choose Node. ADORE invokes npm and Pi with that executable directly,
including paths with spaces; it does not run an npm shim or require a global Pi.

Installation requires registry access and write permission under
`<ADORE home>/tools/pi`. npm installs the build's Pi and web extension pins
there without lifecycle scripts or personal npm settings. ADORE checks Node,
the package versions and Pi's version before publishing the version directory.
On a build with a new Pi pin, run `adore pi install` again; the build selects its
own prefix and leaves other prefixes alone. `adore pi verify` checks the install
without making an AI request. A corrupt prefix is refused; move it aside and
install again.

## Project settings

```toml
[execution]
backend = "local"

[local]
account = "current"
path = "" # Empty uses the service PATH; otherwise supply tool directories.

[executor]
provider = "openai"
model = "your-model"
```

The launcher is fixed. Remove `[executor] command` and unsupported
`[local]` fields from server TOML. Use the selected provider's project
credential; ADORE never reads personal Pi sign-in. For an OpenAI-compatible
endpoint, use the address as seen from the server and configure a key only
when the endpoint needs one. For a ChatGPT subscription, select `provider = "chatgpt"` and sign in under
Settings → Agent and model. The native helper uses managed Node and Pi
without Docker. Each stage gets only a temporary access token and has a
maximum timeout of 3000 seconds. ADORE inside WSL2 uses the Linux setup,
its own service account and tools, and a delegated cgroup.

The operator supplies the project's tools, SDKs and libraries. Windows uses
Pi's PowerShell tool and an owned Job Object. On Linux, set the service's
`ADORE_LOCAL_CGROUP_ROOT` to an absolute, writable, delegated cgroup v2 root.
The service must itself run inside that delegated subtree and be able to create
child cgroups and use `cgroup.kill`. Setting the root path alone does not grant
permission to move processes from another subtree. There
is no fallback to unowned PID control. Set `workflow.aegis_python` to the native
Python executable if the default command is unavailable.

Container recipes, runtime options and system package installation permissions
do not apply locally. **Internet access for the agent** cannot restrict host
network access. When it is On and a search service is selected, Pi loads ADORE's
pinned web extension; Off disables that extension only.

## Isolation and recovery

Each stage uses Pi RPC over pipes inside the owned Job or cgroup. ADORE creates
a fresh agent directory outside the worktree, places any generated model and
web settings there, and loads only the ADORE guard and the selected managed web
extension. Personal and untrusted project extensions, skills, themes, templates
and MCP do not load; the repository's AEGIS instructions still apply. The guard
supplements credential filtering. It does not sandbox the account.

The supervisor releases the process only after recording its durable ownership.
Cancellation and timeout abort RPC and confirm that the native scope drains
before reusing it. Automatic resume requires the pinned native identity.
Explicit Retry can recheck tools and refresh verified environment evidence on
the same machine and account. Cleanup refuses corrupt or foreign ownership
and preserves the worktree when it cannot confirm scope drainage.

## Readiness and model checks

**Check host prerequisites** reports missing or incompatible Node, missing or
invalid Pi, the process scope and whether the selected provider credential is
configured. It does not contact the model. **Test AI connection** explicitly
runs a bounded RPC challenge in a temporary worktree and may incur charges.
The test requires a successful shell command and the exact final reply. Neither
check proves the project's toolchain or a complete job.

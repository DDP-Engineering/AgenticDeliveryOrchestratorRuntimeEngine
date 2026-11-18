# Component: Local execution

## Purpose and responsibilities

`04_Software/adore/local_execution.py` implements the native execution backend
for Windows and Linux. It runs the build's managed Pi under the server account
with owned process lifetime, pinned environment/tool identity and the same
conductor/executor contracts as container jobs.

`pi_installation.py` resolves server Node, pins/verifies npm packages and atomically
publishes a versioned managed prefix for source installations. Installation needs no model credential.
Offline user distributions select the application-owned _native_tools payload
through the bundled Python startup marker in offline archives. Online archives
omit the native payload and use the same managed installation as a source checkout;
host Node/npm must be prepared before `pi install` downloads Pi dependencies. Missing Node, Pi or search files are
refused with a complete-reextraction instruction; host tools are never selected
for an incomplete delivery. Bundled pi install/verify perform offline checks.
The controlled native PATH prepends bundled Node/npm and fd/ripgrep; project
SDKs and Git/forge tools remain external operator requirements.
The current pin is Pi 1.5.2 with pi-web-access 0.46.0, using Node 22.23.4 or
later in the 22.x line. `adore pi install` installs and verifies that exact Pi
release under the service account's ADORE home; it does not rewrite project or
job data. `adore pi verify` checks the current pinned installation offline.
`local_process.py` and `local_child.py` assign the child to its owned scope and
record its durable lease before releasing project argv. The controller owns
interruption and final drainage.

## Launch flow and data contracts

`local_policy` fingerprints machine/account, sanitized environment and the exact
Node/Pi file identities. `LocalBackend` provisions a run-owned control receipt and
binds `LocalTarget` against the saved identity. Native plans have no container
image or preparation steps. Unknown/corrupt policy, plan, receipt or scope evidence
is refused; no stored format is filled in or converted.

`LocalTarget.pi_session` creates a fresh settings directory outside the worktree,
writes only ADORE-generated model/web settings and lends owned binary pipes to
the shared Pi RPC launcher. The job's explicit Pi session file lives separately
in private IO storage and survives settings cleanup, RPC restarts, Retry and
clarification/review continuations. Disposable probes remain ephemeral. Windows forwards explicit standard handles through
the supervisor and offers Pi's PowerShell tool. Linux execs exact native Node
inside the delegated process scope. Normal exit, timeout and cancellation require
confirmed process-tree drainage. See [Executor launcher](Component_Executor_Launcher.md).

AEGIS CLI calls use the native run_files exchange with bounded strict UTF-8 and
validated JSON. Python child streams use ADORE-owned PYTHONIOENCODING=utf-8.
Invalid bytes cannot be replaced into successful protocol evidence. Paths may
contain spaces; native argv is not an implicit shell-command authority.

Direct uses the same owned Pi RPC path. The agent chooses repository checks;
there is no native verification-only shell operation or independent configured
verification command. See [Orchestrator](Component_Orchestrator.md).

## Environment and credentials

Server configuration supplies managed Node and Linux delegation. Project `[local]`
selects the current account and optional tools PATH. Personal Pi settings/auth,
ambient Node options and unrelated credentials are excluded from the fresh agent
configuration. Provider/model credentials enter the bound environment explicitly.
Native readiness validates local tools and stored credential status without a
model call. Explicit model diagnostics use the same owned native scope.

ChatGPT projects share the ADORE-owned sign-in with container projects for the
same home. The trusted helper uses verified managed Node/Pi and returns only a
temporary access token to the bound stage/probe, never the refresh credential.
Stage limits retain the shared subscription ceiling. See
[ChatGPT sign-in](Component_ChatGPT_Sign_In.md).

## Resource ownership and cleanup

Windows Jobs and Linux delegated cgroup v2 provide process lifetime ownership.
WSL2 uses the Linux backend inside its distribution. They do not sandbox the
filesystem, credentials or network: Pi has the server account's host permissions.
Container internet settings cannot restrict a native host process.

Retry revalidates the pinned resource and effective native policy before effects.
Stable identity changes require a fresh job. Explicit cleanup after drift uses
`LocalBackend.for_cleanup` without resolving current installed tools, then checks
the saved resource/policy against the receipt and verifies host/account, state-root
path and leases. It drains only verified owned scopes before unlinking the receipt.
Missing receipts are idempotent only without an active-process record. This grants
no Retry or execution exception.

Managed installation uses a dedicated bounded tools lock, unique verified staging
prefix and atomic immutable publication. Reading/verifying a published install
needs no installation lock. Run controls, scopes, IO and temporary Pi settings
remain per run; project settings never mutate the process-global environment.
See [Resource locks](Component_Resource_Locks.md).

## Evidence and validation coverage

Native RPC retains literal bounded session stdout, including agent-printed secret
values. Operational tails, stderr, questions and model diagnostics remain masked.
Authorized no-store session reads exclude system messages; old recordings are not
rewritten. See [Web jobs](Component_Web_Jobs.md).

Existing `04_Software/tests/test_pi_installation.py`, `test_local_execution.py`,
`test_native_chatgpt.py`, `test_retry_revalidation.py`, `test_drift_recovery.py`
and `test_shared_resources.py` exercise injected install/process/protocol and
ownership failures. Operators provision native prerequisites explicitly; this
component does not wrap missing process ownership with a weaker launch mode.

LocalBackend is imported directly from adore.local_execution. The shared execution
module owns only backend contracts; it provides no lazy adapter alias.

Project setting ranges/defaults share `adore/setting_limits.json` and the current
[configuration contract](Component_Config.md#shared-setting-domains). Native execution
uses the current process account; `local.account` is not a selectable setting. No stored
plan conversion or automatic reset is performed.

# Component: Azure CLI bridge

## Purpose and ownership

`04_Software/adore/azure_cli.py` supplies shell-free host launcher resolution and
one-shot Azure REST requests. It has only standard-library imports at module
load; no Azure dependency is added to ADORE. The installed official Azure CLI
and `azure-devops` extension remain prerequisites and own authentication.
The bridge neither reads credential files itself nor implements another token store.

## Responsibilities and execution

- `azure_python` resolves the selected host PATH installation. Windows MSI/ZIP
  uses `../python.exe` relative to `wbin/az.cmd` or `bin/az.cmd`; pip can also
  use an adjacent interpreter. POSIX uses the installed az Python shebang,
  including `/usr/bin/env python`. Unknown shell launchers and missing runtimes
  fail explicitly rather than selecting an unrelated Python installation.
- `windows_azure_argv`, called by `util.run_command`, converts Windows Azure
  commands into `[python, -IBm, azure.cli, ...original arguments]`. No cmd.exe,
  PowerShell or `shell=True` is involved. Other tools/platforms keep their argv.
  Logical argv, cwd, effective environment, output capture and timeout behavior
  remain the common runner's responsibility.
- `AzureDevOpsForge` serializes each REST request into an automatically cleaned
  private JSON file. The injected runner launches the bridge with that file's
  path, not human payloads or credentials in command text. The application
  Python starts an isolated Azure CLI Python child with a 55-second timeout,
  within the runner's 60-second limit. Timeout kills and waits for that child.
- `sdk_request` loads the already installed extension using Azure CLI's own
  extension discovery and uses its `get_connection` authentication/service-area
  discovery. It calls the official SDK client's `_send` with an immutable
  Microsoft resource-location GUID. It does not use `az devops invoke`'s
  name/version resolver, whose results can depend on metadata ordering.
- Boards comments use the precise `7.1-preview.4` API version. JSON Patch media
  type, explicit project/repository routes, query parameters, request bodies and
  response-header continuation tokens survive the transport unchanged.

The GUID table comes from Microsoft's v7.1 Work Item Tracking and Git clients:
[official SDK source](https://github.com/microsoft/azure-devops-python-api/tree/dev/azure-devops/azure/devops/v7_1).
It distinguishes Work Item reads/updates from type-based creation, query text
from stored-query routes, repository PRs from project-level PR routes, and current
comments from legacy revision comments. No completion or policy-bypass route exists.

## Failure and security boundaries

Only GET, POST and PATCH, known location IDs and explicitly scoped cloud requests
are accepted. Missing/ambiguous service discovery, missing extensions, CLI launch
failure, API errors, unexpected JSON shapes and child timeouts become value-free
child errors, then typed forge errors. SDK exception text, child stderr, tokens
and human content are never forwarded by the bridge. `AzureDevOpsForge` still owns
strict final JSON validation and resource identity checks.

Python runs isolated (`-I`) and receives literal argv; embedded quotes, spaces,
newlines, Unicode, percent signs and shell metacharacters are not interpreted.
Host credential environment remains on the host and is not passed to executors.
No persistence format, migration, installation hook or product dependency is added.

## Validation

`tests/test_azure_cli.py` covers all location families against the public Microsoft
CLI recording subset in `tests/fixtures/azure_resource_locations.json`, retaining
same-name competitors and testing both metadata orders. It drives Work Item
GET/PATCH and PR creation from the public Forge adapter through bridge dispatch,
with the SDK transport mocked rather than calling Azure. It also covers invalid
scope/locations, malformed responses, sanitized SDK/timeout failures, MSI/ZIP and
POSIX discovery, and Windows doctor/argument-preservation behavior with process
creation mocked. Existing adapter and web tests cover serialization, scoped
readiness and fail-closed response normalization.

An optional test in that same file uses the **real** Microsoft SDK URL builder,
GUID resolver and API-version negotiator, while mocking HTTP, credentials and
account discovery. It skips when the host-tool libraries are absent and never
installs dependencies itself. It was also run in a temporary isolated verification
runtime with Azure CLI core 2.80.0 and the official extension 1.0.2 wheel: 72
location/method/order combinations passed, including the exact comment preview
revision. These are verification-only libraries, not application dependencies.

Live Windows process creation and Azure tenancy acceptance remain operator-owned;
these offline simulations do not claim either was executed.

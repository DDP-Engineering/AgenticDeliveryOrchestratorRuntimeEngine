# Azure DevOps Services

ADORE's `azure_devops` provider conducts Azure Boards Work Items and Azure Repos
Git Pull Requests through the same bounded orchestration as the other providers.
It supports **Services (cloud) only**, not Azure DevOps Server/on-premises. Use
canonical organization URLs `https://dev.azure.com/ORGANIZATION`; legacy
organization aliases must be entered in canonical form.

## Host installation and unattended authentication

Install Git, [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli),
and the official extension on the machine/account running ADORE (not in the Pi
executor):

```text
az extension add --name azure-devops
az extension show --name azure-devops --output json
```

On Windows Azure CLI is available through `winget install Microsoft.AzureCLI`.
ADORE resolves the standard MSI/ZIP `az.cmd` launcher to its bundled Python and
runs it directly, without cmd.exe or shell expansion of labels, paths or text.
A missing embedded interpreter requires repairing the Azure CLI installation.
On Linux, the installed `az` must expose its Python entry script (the official
package and ordinary pip installations do); arbitrary shell wrappers are refused.
REST requests address exact Microsoft resource-location IDs through the official
extension's SDK in that same runtime, avoiding ambiguous resource-name lookup.
No Azure Python libraries need to be installed in ADORE's environment, and sign-in
continues to use the extension's host-account authentication.
On Linux use Microsoft's distribution-specific installation instructions. ADORE
neither installs these tools nor signs in on your behalf. Portable archives
include the adapter, this guide and the configuration example, **not Azure CLI,
the extension or credentials**. The package manifest names external forge tools.
Deployment preflight accepts `az` only with its official extension. No new Python
runtime dependency is required.

Use a dedicated account with least-privilege project/repository/area access.
For unattended operation provide `AZURE_DEVOPS_EXT_PAT` from a private service
secret environment, or sign in as that same OS account using:

```text
az devops login --organization https://dev.azure.com/contoso
```

Enter the PAT privately at the prompt, never as an argument, in a public profile,
an answer file, browser settings or a ticket. Do not put it in executor
`env_keys`, container runtime environment or local environment. Azure credentials
are host-only. ADORE refuses explicit executor forwarding of Azure credential
variables. Git clone/push authentication (for example Git Credential Manager or
SSH) is configured separately by the operator. Azure CLI may prefer an existing
Microsoft Entra sign-in; use a dedicated service-account CLI context so identity
selection is deliberate. Do not rely on interactive sessions that expire during
unattended operation. Rotate credentials externally and recheck host prerequisites.

Grant PAT **Code (read/write)** and **Work Items (read/write)**, plus the account's
repository permissions to contribute, create branches and Pull Requests, and
area permissions to read/edit Work Items and create tags. Existing tag use alone
may not grant tag creation. Read-only prerequisite checks confirm repository and
Boards query access, not future write privileges. No permission to bypass branch
policies, complete PRs or administer the organization is needed. ADORE never
merges, enables auto-complete, votes on behalf of a reviewer or bypasses policies.

## Explicit scope and configuration

Copy [the complete Azure example](../04_Software/config.azure-devops.example.toml)
and adjust paths, executor model and resource names. Validate with
`adore -c config.toml config validate`, then inspect with `run --dry-run` before
an operator-authorized supervised `run --once`.

Required `[platform]` values:

| Setting | Source and meaning |
| --- | --- |
| `kind = "azure_devops"` | Canonical provider identifier in CLI, profiles and GUI. |
| `organization` | Organization URL, e.g. `https://dev.azure.com/contoso`. |
| `project` | Exact Azure project name from the Repos URL, e.g. `Payments`. |
| `repo` | Repository **name**, e.g. `backend`, not `owner/repo`, a URL or a GUID. |
| `area_path` | Exact repository-owned Boards Area Path, e.g. literal TOML `'Payments\Backend'`. |
| `work_item_types` | Allowed literal process type names. Default: Bug, Task, Issue, User Story, Product Backlog Item, Requirement. |
| `closed_states` | Literal terminal state names. Default: Closed, Done, Removed. |

`platform.login` remains Gitea-only and must be empty. Reviewers are optional Azure
identity GUIDs (one per line in Settings; comma-separated in the setup wizard).
They are Azure account IDs, not display names or GitHub-style handles.

Boards is **project-wide, not repository-wide**. Reserve a distinct child area
for each repository in Azure Project settings → Project configuration → Areas.
The project root itself is refused. ADORE queries **exact equality**, not UNDER;
child areas are excluded. Never share that exact area across repository profiles.
Organization/project are explicit on every REST request; Git routes also bind
the repository. No `az devops configure` global defaults are used. Returned Work
Items and PRs are checked against configured scope before use; mismatches raise
a typed error instead of conducting another repository's ticket. A person moving
a claimed Work Item to another area causes a scope error requiring intervention.

`adore init PROFILE` offers Azure DevOps Services and prompts for the required
scope. Noninteractive `--answers FILE` accepts `kind`, `repo`, `organization`,
`project` and `area_path` in addition to the usual wizard answers. Use single
quoted TOML for Area Paths to retain backslashes.

In the GUI, **Add project → Read repository** recognizes canonical Azure HTTPS
and `git@ssh.dev.azure.com:v3/ORG/PROJECT/REPO` addresses. It fills organization,
project and repository. Enter the repository-owned Area Path, confirm identity
and target branch, choose the executor separately, review and check prerequisites.
Imports accept the same TOML configuration. New projects start stopped. Admins
use reviewed preview/apply for settings; runtime-affecting changes require paused
pickup and no active work. Developers retain read-only visibility and existing
project/job authorization rules. The normal GUI never asks for an Azure token;
its Repository access guidance directs the administrator to external host setup.

## Work Item authoring and signaling

Describe one bounded change with acceptance criteria. HTML Description and
`Microsoft.VSTS.Common.AcceptanceCriteria` are normalized to readable text;
acceptance criteria receive a heading recognized by the common readiness gate.
Native type and state are included in executor context. Active states are those
not listed in `closed_states`; types not in `work_item_types` are not eligible.
Configure both lists for your inherited/custom process **before enabling pickup**;
ADORE does not assume Scrum, Agile, Basic or CMMI share all names and never
changes native state automatically.

| Signal | Azure resource | Owner |
| --- | --- | --- |
| `agent-ready`, `agent-hold`, `no-agent` | Work Item tags | Human pickup/hold/exclusion. Hold/exclude always win. |
| `P1`, `P2`, `P3`, `bug`, kind/quick labels | Work Item tags | Human priority/type/workflow hints. |
| `agent-working`, `agent-clarify`, `agent-mr`, `agent-failed`, `agent-done` | Work Item tags | ADORE status; do not use these as approval. |
| `agent-answered` | Work Item tag, with discussion answer | Human clarification resume. |
| `agent-approved` | Work Item tag | Fresh human approval of the exact presented candidate/target. |
| `agent-revise` | **PR label** | Human review/revision request; removed from the PR after consumption. |

All names follow the project's existing label settings. Native Azure Priority is
informational: it **does not replace P1/P2/P3 tags** or satisfy priority readiness.
Native type does not invent `bug`/kind tags; use explicit tags when those workflow
hints matter. Semicolons cannot occur in tag names. Tags are read/modify/written
with a revision test, preserving unrelated human tags; conflicts fail rather
than blindly overwriting concurrent changes.

Azure does not need a GitHub-style repository label catalog. The label helper
verifies repository/Boards access and reports names as available **on attachment**;
it creates no dummy Work Item/PR and claims no labels were provisioned. Work Item
tags and PR label attachments remain separate even where Azure shares tag names.

## Runtime, restart and review

CLI and web workers use the same adapter/configuration; `--once` retains web
polling/backoff semantics. Common priorities, readiness, limits, clarification,
candidate-bound approval, review rounds and restart reconciliation are unchanged.
The status comment is edited in place. Hidden markers remain in comment text for
outbox replay. PR comments include all discussion/inline threads, oldest first;
a durable composite integer encodes thread and comment ID so edits after restart
do not target a different thread's comment with the same local ID.

Publication creates or adopts the branch's active PR, links its source Work Item
idempotently, and refreshes approved evidence on revisions. Azure states map:
`active → opened`, `completed → merged`, `abandoned → closed`. `isDraft` is a
required boolean; draft/ready follows `delivery.draft`. After a **human** merge,
normal leased Git branch cleanup follows `delivery.remove_source_branch`.

The latest PR iteration's status contexts provide advisory CI: succeeded/success, failed or error/failed,
pending/running, notApplicable/none; unrecognized or unreadable data/unknown.
No statuses means none, not success. A pipeline which publishes no PR status is
not inferred from an unrelated project build. ADORE never gates or authorizes a
merge from these observations. Status reporting uses the latest context result.

WIQL uses increasing IDs with 200-item pages; Boards comments follow continuation
tokens, and PR search uses bounded pages. At 50 pages the adapter refuses an
incomplete result. Requests time out at 60 seconds (readiness uses its shorter
shared deadline); malformed/duplicate JSON, wrong scope, invalid IDs and API/CLI
errors become `ForgeError`/`ForgeResponseError`. Raw CLI output is not included
in Azure error messages. An inaccessible or deleted ID may be indistinguishable
from denied access through `az`: it is an explicit forge failure, never guessed
to be a successful deletion or silently re-created. Restore access or use the
existing operator cancel/delete recovery boundary.

## Troubleshooting

- Missing CLI/extension: install both under the service account's PATH, then check prerequisites.
- Expired/missing sign-in: refresh the private PAT or account login externally; verify the service account and organization, not your desktop account.
- Permission denied: check PAT scopes **and** repository/Area Path ACLs, tag creation and reviewer identity membership. Read access does not prove write access.
- No eligible Work Items: inspect exact project/area/type/state values, ready/hold/exclude tags, priority and acceptance settings. Subareas intentionally do not match.
- Tag conflict: reread the Work Item; retry explicitly after concurrent human edits settle. Do not replace the whole tag set manually.
- PR revision not triggered: put the revise label on the PR, not only a Boards tag.
- CI unknown: grant status-read access or configure the pipeline to publish PR status. Unknown is never a pass.
- Repeated scope/JSON/page-bound failures: stop pickup, retain run evidence and correct configuration or CLI/API access before retrying.

## Bounded operator-authorized live acceptance (not an automated test)

Offline tests do not prove live Azure tenancy, ACLs or installed extension behavior.
Live acceptance has **not been executed by the implementation agent**. An operator
must authorize a disposable Services project and service credentials explicitly.
Bound each exercise to one repository, one exact area, at most three Work Items,
one active job/PR and a 30-minute/20-iteration/5 USD/20-file run limit.

1. Read-only phase (5 minutes): check extension, sign-in, exact repository, remote target branch and scoped Work Item listing in CLI and GUI. Put another repository's ready Work Item in a sibling area and confirm it never appears. Confirm hold/exclude and invalid scope fail safely.
2. Signaling phase (5 minutes): authorize writes to the disposable Work Item only. Check status edits, preservation of a human tag, question/answer resume and candidate-bound approval. Restart once after an acknowledged status write; confirm a single status comment remains.
3. Publication phase (10 minutes): authorize one branch push and draft PR only. Verify target, reviewer IDs, Work Item association and no auto-complete/bypass settings. Restart around publication and confirm adoption, not a duplicate PR. Repeat as ready only with separate authorization and the same finite bound.
4. Review phase (5 minutes): leave one inline review thread and apply the revise **PR label**. Confirm one bounded review round, evidence refresh, label consumption and advisory CI (including no pipeline/unknown). Abandon the PR to check closed mapping if merge is not authorized.
5. Human-only completion phase (5 minutes): **only if separately authorized**, a human merges. Observe done and leased branch cleanup with cleanup enabled, then separately verify retention with cleanup disabled. ADORE and the implementation agent never merge. Cancel/delete disposable jobs and remove test resources explicitly.

Record observed versions, outcomes and any failures outside product configuration;
never retain credentials in reports. Do not infer live acceptance from offline
runner fixtures or from merely building a portable archive.

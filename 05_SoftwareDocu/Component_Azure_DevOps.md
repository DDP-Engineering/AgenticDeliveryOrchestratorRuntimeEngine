<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Azure DevOps Services Adapter

## 1. Purpose

`adore/forge/azure_devops.py` implements the existing Forge contract for cloud
Azure Boards and Azure Repos. Canonical provider ID: `azure_devops`. Server is
not supported. No new Python dependency or alternate orchestration loop exists.

## 2. Responsibilities

The adapter owns scoped CLI requests, strict response normalization, Work Item
tag edits, Boards/PR comment identity, PR publication/association and advisory CI.
It does not own ticket ranking, hold/exclude, budgets, candidate approval,
notification replay, backoff, review rounds, Git checkpoints or branch cleanup.
Those remain in the common orchestrator/selection/polling/state components.
There is no completion, auto-complete, policy bypass or merge method.

## 3. Implementation Overview

All REST requests use `az devops invoke`, an injected runner, a 60-second timeout
and strict duplicate-rejecting JSON parsing. Organization/project route arguments
are explicit; Git requests add repositoryId. Temporary JSON request files are
mode 0600 inside automatically cleaned private directories, including JSON Patch
payloads. Exceptions omit raw CLI streams, arguments and human content.
Dedicated `az repos pr work-item add` and `pr label remove` bind organization and
disable Git auto-detection; their preceding repository-scoped reads establish PR
identity. Mutating responses must acknowledge the expected IDs/settings.

WIQL uses exact project/area/type/state predicates and ID keyset pages of 200;
Boards comment pages follow continuation tokens. PR source lookup uses explicit
status/source criteria and skip/top. A 50-page ceiling fails closed without a
partial result; nonadvancing/duplicate results are refused.

## 4. Dependencies

- `Forge`, `Ticket`, `Comment`, `MergeRequest` and typed forge errors.
- `CommandRunner`, `CommandResult`, strict JSON, standard-library HTMLParser.
- External host `az`, official `azure-devops` extension and service-account auth.
- Host Git remains responsible for local and publication Git operations.

## 5. Inputs And Outputs

Platform configuration supplies organization, project, repository **name**, exact
repository-owned child Area Path, allowed native type names and terminal states.
The factory receives all scope fields identically from orchestrator construction
and the web ticket service. Wizard and GUI enrollment bind the same configuration.
HTML Description/AcceptanceCriteria become readable text; acceptance receives a
common readiness heading. Native type/state/priority remain contextual text;
ADORE priority/kind/readiness signals are configured tags, not synthesized labels.

## 6. Data Contracts

- Work Items must have the configured exact project and area, positive integer ID,
  text title/type/state and string semicolon-delimited tags. Excluded native types
  and terminal native states normalize to closed. Custom process names are lists,
  not inferred process-template enums.
- PR repository/project names must match. Active/completed/abandoned normalize to
  opened/merged/closed; draft is a strict boolean. PR labels come from their own
  resource, never from Work Item tags. Returned web URLs are constructed only
  from validated cloud scope and positive IDs.
- Tag updates read current tags, retain unrelated names and test `/rev` in the
  same JSON Patch. A conflict is a typed failure, never a blind retry/overwrite.
- Boards comments use native IDs and preserve literal markers. PR IDs encode
  `(threadId << 32) | commentId`; decoding is stateless across restart. Deleted
  PR comments are excluded and system comments remain flagged.
- `link_ticket` is idempotent: read current Work Item references, add only when
  absent. The common Forge default is a no-op for providers using body references.
  The conductor calls it before entering review for creation, adoption and retry.
- Current-iteration PR CI contexts map succeeded/failed/error/pending/notApplicable
  to success/failed/failed/running/none. Unknown, malformed or inaccessible data
  returns unknown and never raises; no status is not a success.
- Missing/inaccessible resources which `az` cannot distinguish remain typed errors;
  no free-text 404 heuristic can interpret denied access as a confirmed deletion.

No durable store/schema or migration path was introduced. Composite comment IDs
fit existing integer fields. Host Azure auth is external; the GUI never sends a
PAT. Existing origin/token connection storage intentionally refuses this provider.

## 7. Workflow Integration

Doctor requires both CLI and named extension; authentication checks read the exact
repository and a scoped WIQL page. They prove read/query access, not future write
privileges. Label provisioning reports `mode=azure_on_attachment`, verified names
and empty created/existing/failed lists after the access check. No placeholder
Work Item/PR is created. The web renders this distinctly from a provisioned catalog.

GUI organization/project/Area Path are explicit enrollment fields. Process type
and terminal-state lists are complete reviewed settings collections, using the
existing candidate revision, administrator authorization and pause/apply rules.
Executor configuration remains separate. Repository URL parsing recognizes cloud
HTTPS and Azure v3 SSH, retaining organization/project for clone identity checks.

## 8. Usage

See [Azure DevOps Services](../01_Documentation/Azure_DevOps_Services.md) and
`04_Software/config.azure-devops.example.toml`. Runtime packaging copies the guide
and example to the bundle root (separate from the three compact guides under
`Documentation/`) and names external forge prerequisites in its manifest. Azure tools
and credentials are intentionally not shipped to the executor.

## 9. Validation And Tests

`tests/test_azure_devops.py` covers public adapter operations, bad JSON, CLI/API
failure, scope confusion, paging, tag revision conflicts, HTML normalization,
PR state, review threads, comment restart identity, Work Item association replay,
CI uncertainty and the never-merge payload boundary. `test_web_azure_devops.py`
covers CLI wizard answers, GUI enrollment/config metadata and scoped host checks.
`web/tests/azureDevops.test.mjs` covers four-locale terminology and settings domain
validation. Existing forge, orchestrator, selection, polling, RBAC, config and
frontend suites provide regressions. Live acceptance is explicitly operator-owned
and bounded in the user guide; offline fixtures are not live acceptance evidence.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Software component documentation

This folder describes the implementation that exists in the checkout. It is the
entry point for component ownership, data contracts, dependencies and recovery
boundaries. User manuals and operating procedures are in
[01_Documentation](../01_Documentation/README.md); automation instructions are in
[02_Tools](../02_Tools/README.md).

## Maintaining these documents

Use the [component template](component_documentation_template.md), keeping only
relevant sections. Update a component document with its implementation change.
Describe current behavior verified in code; do not append implementation history,
acceptance handoffs, old plans or speculative backlogs. Planning belongs in
00_Planning only when explicitly requested.

Each distinct implementation contract has one owner below. Link to it rather than
copying the same workflow, API or UI details into several files. Exact setting
names, CLI arguments and image pins remain in their canonical references/code.
The API's generated OpenAPI describes exact HTTP route shapes.

Every stored format has one current schema. Unsupported stores are refused with
operator deletion guidance, never migrated or silently recreated. Components
must document their actual refusal/recovery boundaries.

## Core configuration and storage

| Component | Scope |
|---|---|
| [Branding](Component_Branding.md) | Product constants, paths, images and package identity |
| [Config](Component_Config.md) | Typed TOML, defaults, validation and execution policy |
| [Config Edit](Component_Config_Edit.md) | Shared configuration-edit locking and atomic publication |
| [Profiles](Component_Profiles.md) | Project metadata, immutable identity and config selection |
| [State Store](Component_State_Store.md) | Current run schema, dispatch, journals and lifecycle locks |
| [Identity](Component_Identity.md) | Run naming and forge comment markers |
| [Util](Component_Util.md) | Bounded command runner, strict parsing and platform helpers |
| [Resource Locks](Component_Resource_Locks.md) | Cross-process resource locking and atomic writes |

## Workflow and execution

| Component | Scope |
|---|---|
| [Orchestrator](Component_Orchestrator.md) | Admission, Direct/AEGIS conduction, approval and publication |
| [Polling](Component_Polling.md) | Bounded adaptive polling cadence |
| [Forge Adapters](Component_Forge_Adapters.md) | GitLab/GitHub/Gitea command adapters and strict output validation |
| [AEGIS Client](Component_Aegis_Client.md) | Companion CLI protocol, task evidence and typed refusals |
| [Prompts](Component_Prompts.md) | Fixed licensed resource catalog and literal rendering |
| [Preparation](Component_Preparation.md) | Closed execution plans and reviewed recipe resolution |
| [Execution](Component_Execution.md) | Backend interface, immutable resources and preparation runner |
| [Isolation](Component_Isolation.md) | Git worktrees, checkpoints, container mounts and egress |
| [Local Execution](Component_Local_Execution.md) | Managed native Pi, process ownership and cleanup |
| [Executor Launcher](Component_Executor_Launcher.md) | Fresh Pi RPC sessions, bounded recordings and archives |
| [Instructions](Component_Instructions.md) | Durable queued/live messages and acknowledged delivery |
| [Package Permissions](Component_Package_Permissions.md) | Explicit container package-manager authority |

## Enrollment, credentials and environments

| Component | Scope |
|---|---|
| [Wizard](Component_Wizard.md) | CLI guided configuration and prepare-only candidates |
| [Doctor](Component_Doctor.md) | Host tools, repository/AEGIS and managed Pi readiness |
| [Repository Source](Component_Repository_Source.md) | Repository URL validation and owned enrollment clone |
| [Repository Auth](Component_Repository_Auth.md) | Selected host forge login and scoped Git credentials |
| [Executor Configuration](Component_Executor_Configuration.md) | Reviewed agent/model settings and evidence binding |
| [Model Connection](Component_Model_Connection.md) | Explicit model and shell challenge diagnostics |
| [ChatGPT Sign In](Component_ChatGPT_Sign_In.md) | Server-owned sign-in and launch-only access tokens |
| [Executor Discovery](Component_Executor_Discovery.md) | Bounded read-only host Pi inventory |
| [Host Folders](Component_Host_Folders.md) | Administrator server-folder navigation and path validation |
| [Project Images](Component_Project_Images.md) | External project image preparation and ADORE recipe ownership |
| [Executor Recipes](Component_Executor_Recipes.md) | Reviewed image-source catalog and closed dependency graph |
| [Build Bundle](Component_Build_Bundle.md) | Immutable Git build definitions and exact source-bundle export |
| [Portable Settings](Component_Portable_Settings.md) | Current-version settings projection and transfer API |
| [Clone Cleanup](Component_Clone_Cleanup.md) | Verified optional removal of an ADORE-owned clone |

## Web control plane

| Component | Scope |
|---|---|
| [Web API](Component_Web_API.md) | HTTP authorization, route responsibilities and mutation boundaries |
| [Web Identity](Component_Web_Identity.md) | SQLite accounts, sessions, grants, audit and operation ownership |
| [Web Jobs](Component_Web_Jobs.md) | Strict authorized job, budget, diagnostics and session reads |
| [Web Frontend](Component_Web_Frontend.md) | Current pages, three-tab job view, sessions and UI request state |
| [Web Worker](Component_Web_Worker.md) | Supervisor, project workers and bounded run dispatch |
| [Configuration Worker](Component_Configuration_Worker.md) | Independent slow configuration and diagnostic operations |
| [Worker Processes](Component_Worker_Processes.md) | Gated process trees, ancestry and confirmed stop |
| [Project Capacity](Component_Project_Capacity.md) | Current admission ceiling, occupancy and status projection |

## Reporting, application metadata and delivery

| Component | Scope |
|---|---|
| [CLI](Component_CLI.md) | Command wiring, structured results and worker-bound execution |
| [Metrics](Component_Metrics.md) | Run summaries, measured usage, estimates and reporting locks |
| [Process Log](Component_Process_Log.md) | Run/project output attribution and bounded rotating logs |
| [Release Notes](Component_Release_Notes.md) | Translated user release notes and About payload |
| [Packaging](Component_Packaging.md) | Setup/build/package tool ownership and source services |
| [Portable Distribution](Component_Portable_Distribution.md) | Bundled Python, launchers, archive integrity and data home |

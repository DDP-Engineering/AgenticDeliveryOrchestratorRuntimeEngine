<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE documentation

These guides describe the current implementation. Source code and the CLI's
`--help` define exact runtime contracts; component details live in
[05_SoftwareDocu](../05_SoftwareDocu/README.md).

## Using the application

| Guide | Purpose |
|---|---|
| [User guide](User_Guide.md) | Start the packaged application and follow normal work. |
| [Administrator guide](Administrator_Guide.md) | Prepare the application host, accounts and backups. |
| [Troubleshooting](Troubleshooting.md) | Resolve startup, prerequisite and job problems. |

These three source files sit beside the technical guides. Portable distributions
copy only them into Documentation, with User_Guide.md named README.md in the
package. The index and engineering references remain repository documentation.

## Technical and operator guides

| Guide | Purpose |
|---|---|
| [Getting started](Getting_Started.md) | Install from a package or source and enroll the first project. |
| [Operations](Operations_Guide.md) | System overview, AEGIS/Direct workflows, approval, review, recovery and maintenance. |
| [Web interface](Web_Interface.md) | Current navigation, scoped Jobs/Tickets, sessions, settings and administration. |
| [CLI reference](CLI_Reference.md) | Commands, selectors, intervention flags and exit codes. |
| [Configuration reference](Configuration_Reference.md) | Current settings, defaults, limits and save rules. |
| [Security and credentials](Security_And_Credentials.md) | Authentication, secrets, isolation and agent package-installation authority. |
| [Code style](Code_Style.md) | Implementation and source documentation conventions. |

## Specialized contracts

| Guide | Purpose |
|---|---|
| [Container preparation](Container_Preparation.md) | Reviewed recipe grammar, pinned plans, step evidence and explicit reprepare. |
| [Local execution](Local_Execution.md) | Managed Pi, Windows Jobs, Linux cgroups and native recovery. |
| [Project executor images](Project_Executor_Images.md) | External builds, retained definitions, source ZIPs and image selection. |
| [Portable project settings](Portable_Project_Settings.md) | Closed working-rule export and transfer format. |

[Operator quick reference](Operator_Quick_Reference.md) provides task-oriented
reminders and the five current presentations. [Deployment tools](../02_Tools/deploy/README.md)
document service installation; source automation belongs under 02_Tools.

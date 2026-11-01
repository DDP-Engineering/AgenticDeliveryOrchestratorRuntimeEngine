<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Documentation

This is the operator and administrator documentation for **Agentic Delivery
Orchestrator & Runtime Engine (ADORE)**. It describes the product generically:
replace placeholders such as `<profile-name>` and `<runtime-project>` with your
own names. No guide assumes a particular target repository.

## Start Here

Follow these guides in order when introducing ADORE to a host or a project:

1. [Getting_Started.md](Getting_Started.md) - understand the operating model,
   prepare a host, install the runtime, create a profile, and complete a safe
   first poll.
2. [Security_And_Credentials.md](Security_And_Credentials.md) - set up forge
   access, executor credentials, secret handling, and the human merge boundary.
3. [Integrating_A_Runtime_Project.md](Integrating_A_Runtime_Project.md) - add a
   runtime project, its image, state, readiness rules, and ticket-label contract.
4. [Operations_Guide.md](Operations_Guide.md) - run, monitor, steer, review,
   and schedule normal ADORE work.
5. [Recovery_And_Maintenance.md](Recovery_And_Maintenance.md) - diagnose,
   retry, reset, cancel, delete, and clean up runs safely.

## Reference Guides

- [Configuration_Reference.md](Configuration_Reference.md) - every
  `config.toml` setting, profile resolution, defaults, and validation rules.
- [CLI_Reference.md](CLI_Reference.md) - the complete command-line interface,
  command syntax, safety flags, and exit codes.
- [Web_Interface.md](Web_Interface.md) - optional browser interface, accounts,
  RBAC, metrics, offline installation, and worker operations.

## Quick References

[Operator_Cheat_Sheets/](Operator_Cheat_Sheets/README.md) contains concise,
task-oriented reminders. The full guides above are authoritative when a cheat
sheet and a reference need different levels of detail.

## Maintainer Reference

[Code_Style.md](Code_Style.md) is internal engineering guidance for people who
implement ADORE. It is not part of the operator documentation path.

- [Container preparation](Container_Preparation.md): recipe grammar, review, execution evidence and recovery.

## Native local execution

Native execution setup, security and recovery are documented in Local_Execution.md.

See [Local execution](Local_Execution.md) for platform prerequisites, configuration,
authentication, process ownership and acceptance coverage.

- [Project executor images](Project_Executor_Images.md): external image build and verification, image selection in ADORE, and pending-candidate recovery.

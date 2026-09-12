<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Operator Cheat Sheets

Applies to ADORE 0.13.0 and AEGIS schema 1. ADORE migrates no earlier run
state.

- [Setup and First Run](Setup_And_First_Run.md)
- [Tickets, Readiness and Labels](Tickets_Readiness_And_Labels.md)
- [Monitoring and Steering](Monitoring_And_Steering.md)
- [Profiles and Container Images](Profiles_And_Container_Images.md)
- [Failure Recovery and Cleanup](Failure_Recovery_And_Cleanup.md)

The core operator invariant is simple: ADORE either progresses, parks on an
explicit human question/approval, or fails loudly with durable local and forge
evidence. It never merges.

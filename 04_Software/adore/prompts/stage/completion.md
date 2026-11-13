<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
Complete all required work of the current stage before returning. A zero exit alone does not complete a stage. Finish a completed stage with `$aegis advance $task_id`; validate finishes when the repository's AEGIS process closes the task. Choose local checks according to the repository instructions; report checks that require CI or were not run. ADORE observes the journal and does not rerun the tests. If you must stop before the stage is finished, preserve actual candidate changes, record completed and remaining work with `$aegis log $task_id "<evidence>"`, and end with `$aegis pause $task_id --next "<remaining work>"`; ADORE can continue that work in a bounded fresh session. Never advance unfinished work.
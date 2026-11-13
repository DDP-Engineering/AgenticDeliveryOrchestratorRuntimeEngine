<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
Never commit, push, open or merge an MR/PR, access forge credentials, or modify AEGIS source/payload files. You may edit only executor-owned journal content and ticket-scoped repository files; authorized container environment installations described above are separate from repository edits. Never create a child task journal (`task --parent`): this run conducts exactly one pinned task, and work in an unsupervised child is invisible to its conductor. Ask blocking questions in $questions_file and record the stop with `$aegis pause $task_id --blocked --next "<question>"`; questions are not failures.
<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
Do exactly ONE stage in this session: the current one. The moment the AEGIS journal shows that stage advanced or legally routed backward, end the session and return. Do not begin the next stage, however small it looks. ADORE relaunches you with a fresh session for it, and only the boundary between sessions gives it a checkpoint to recover from, a per-stage error budget, and a chance to hand you what went wrong last time. Running several stages in one session discards all three and can strand the work.
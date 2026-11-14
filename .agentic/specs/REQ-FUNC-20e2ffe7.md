<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
# Live session protocol

STATED: #93 extends #92 with three-second complete-line polling, current unfinished work and session_ended handoff. Existing grouped source items and numeric byte cursors remain.

A launch-owned `io/live.json` schema 1 contains random `id` (live-hex), exact planned `archive_id`, and `start_at`. The planned archive name determines stage/attempt. PiExecutor publishes it after clearing old output, around the RPC/archive lifetime, and removes it on every normal/exceptional return. Only working run state plus this marker and the existing held StateStore agent-session kernel lock yields a live session; retained output alone never does. No older stored format reader is introduced.

Live metadata extends archive metadata with `live: true`, `archive_id`, null end/outcome/exit, and recorded start time. GET sessions/{live-id} accepts cursor, limit and optional continuity; subsequent nonzero cursors require continuity. Live pages include session, items, next_cursor (including unchanged zero), continuity, a nullable thinking hint and session_ended:false. Stable source identity plus SHA-256 of bytes preceding cursor binds continuation; mtime is not launch identity. Prefix proof is bounded by the existing 64 MiB file ceiling. Item scanning retains 4 MiB per page, 256 KiB per record, 16 KiB per text, grouped parts and maximum 200 source items. Partial tails return their starting cursor. Append during reads is allowed only beyond the captured size; source replacement or prefix rewrite invalidates the response atomically.

Ended replies contain session_ended:true, archive_id, items:[], next_cursor:null. The UI discards pending results after selection/view/visibility generation changes, refreshes the list, follows a new live attempt only when following live, or reloads the ended archive from zero so the final completed records are present without duplication. User-selected history remains selected during unrelated job refreshes. The nullable thinking hint changes only at message/agent boundaries; unfinished tools use existing completed tool_call/tool_result ids and names, not text deltas. UI keeps current unfinished state across cursor pages. Between launches, following live discovers the next launch through list reads; explicit history selection stops following.

All reads reuse authenticated ownership, no-store and role restrictions. Unsafe/corrupt markers or cursor syntax use existing typed evidence errors. A well-formed missing live id, finished run, replacement or continuity mismatch returns session_ended. No instruction sending, migration, provider call or new setting.

Live continuity verification uses a fresh unbuffered descriptor, independent of parser
read-ahead. EOF before the captured size ends the changed session without retry loops.

Owner #91 persistence policy: raw bounded RPC stdout is separate from sanitized
operational tails. Package launches archive that same literal file without rewriting
it; known credentials are visible through authorized live/archive session reads.

Raw archive absence is a failure; operational tails never substitute for recordings.
Archive source identity/size and destination link/reparse boundaries are guarded.

An accepted archive retains loaded pages and EOF across visibility changes; it never
auto-pages or resets to page one. An unaccepted initial history read can resume/retry.

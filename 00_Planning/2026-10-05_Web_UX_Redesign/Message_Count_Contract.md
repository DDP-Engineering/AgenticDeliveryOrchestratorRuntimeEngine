<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Message measurement proposal (W12 / issue #16)

**Status: recommended proposal; NOT owner-approved; NOT implemented.** Prepared
2026-10-06 against `3167322753c859c8b97ac7df6c38c42e9eeba19e` on
`task/adore-web-interface`. [Issue #16](http://192.168.1.15:3001/dpasare/AgenticDeliveryOrchestratorRuntimeEngine/issues/16)
requires the repository owner's explicit approval of the definition and source
scope before collection implementation in #17. Routine delivery authority,
dependency completion, labels and agent review do not supply this approval.

## Recommended definition

Expose **Executor conversation messages** and **Forge comments** separately.
Never display an implicit mixed total or convert launches, tokens or usage events
into messages. The following are distinct quantities:

| Quantity | Unit and recommended treatment |
| --- | --- |
| Executor conversation message | One finalized logical message with a proven stable identity in a particular physical executor launch. Main subtotal includes `human` and `assistant` roles. `human` means a user-role input, including an orchestrator-supplied gate prompt; it does not prove a person typed it. |
| Tool message | One finalized tool-role result message, reported separately. A tool invocation embedded in an assistant message does not create another assistant message. A source reporting tool operations without logical message boundaries cannot supply this count. |
| Model call | One provider inference request, including a fresh retry request. It needs its own evidence; a turn, completion, message or tool operation is not proof of one model call. Unavailable in the inspected normalized runtime contracts. |
| Executor launch | One physical headless invocation. An attempt can produce zero, one or many messages and model calls. Launch evidence already exists, independently of message evidence. |
| Usage event | One measured consumption/coverage record, normally aggregated per launch by ADORE. Stream updates, turn usage and journal observation records are not conversation units. |
| Forge comment | One persisted non-system authored comment object on an associated issue or MR/PR, including non-empty submitted review bodies and inline review comments. The initial issue/PR description, labels, reactions, bodyless approvals and system notes are excluded. |

Streaming chunks, deltas, starts, usage summaries, system/developer instructions
and synthesized archive rows are excluded from conversation counts. Failed or
unfinished messages are excluded, with incomplete coverage recorded. A valid
finalized empty message still counts if its source explicitly proves a message
object. Role mapping and finality must be pinned per supported output version;
unknown roles or ambiguous multipart boundaries cannot be guessed.

Re-reading the same launch is replay and adds nothing. A fresh retry or revision
launch contains new conversation instances even if its prompt text is identical.
Rehydrated conversation history within one launch is counted only once by its
logical message identity. Resending a forge comment in a gate prompt counts as
part of that input message, never as another forge comment. No content comparison
or hashing of message bodies is needed for identity.

## Current capability evidence

The matrix describes **ADORE's current adapter contract at the pinned commit**,
not everything an external product might offer. No external API capability or
installed CLI version is inferred. No executor was run for this proposal.
Local source and offline fixture contents are sufficient to establish the gaps;
these fixtures were inspected, not executed in this documentation task.

| Source | Actual captured/normalized evidence | Message capability and gaps |
| --- | --- | --- |
| OpenCode (`opencode`) | Launcher archives raw `output.jsonl`; usage parser reads `part.tokens.input/output` and `part.cost`; fixture `test_usage_extraction_from_event_stream` supplies `step_finish` usage objects. Component documentation records historical `step_start/tool_use/step_finish` output. | No normalized message parser, stable message identity, role, finality or message timestamp contract. Usage/tool event presence alone supplies no approved conversation count. Raw archives are only potential evidence pending a version-pinned metadata parser. |
| Pi / pi.dev (`pi`) | `PiExecutor` reads final `turn_end.message.usage` (`input/output/cacheRead/cacheWrite`). Fixture `test_pi_counts_completed_turn_usage_once` duplicates usage in `message_update/message_end`, then supplies two final turns. Embedded cost is not billed cost. | Partial stream structure is evidenced, but the fixture has no stable message ID, role or source timestamp. Two turns prove usage handling, not two messages or two model calls. Conversation counts unavailable. |
| Codex (`codex`) | `CodexExecutor` reads nested/top-level `input_tokens/output_tokens`, optional `cost_usd`. Fixture `test_codex_parses_usage_from_json` has `thread.started.thread_id` and `turn.completed.usage`. Schema comments call usage provisional. | A thread ID is not a message ID. Fixture supplies no finalized message objects, role or timestamp. Counts unavailable; optional cost fixture is no claim that every Codex release emits billing. |
| Qwen Code (`qwen`) | `build_executor` and config selection support Qwen; fixture `test_factory_selects_qwen_and_bans_yolo` proves selection. Shared launcher archives output; Qwen has no specialized usage parser. | No proven usage or conversation metadata contract. Counts unavailable. Included because actual source supports this fourth executor even though the short issue orientation names three. |
| GitLab (`glab`) | `list_comments` / `list_mr_comments` read issue/MR notes; note ID, author username, body, `created_at`, and `system` normalize to `Comment`. MR notes include diff notes. Posts return an ID; edits return no new comment. | Partial count candidates for issue/MR non-system objects. No durable complete message ledger, guaranteed valid dates, deletion history or completion marker. Bound pagination can stop at 50 pages without proving exhaustion. Missing dates stay gaps. |
| GitHub (`gh`) | Issue comments plus PR conversation, submitted reviews and inline diff comments; `created_at` falls back to `submitted_at`. Empty review/inline bodies are filtered. `Comment.system=False`. Posts return an ID. | Partial candidates. Common `Comment` drops the originating endpoint/surface, so equal numeric IDs across review/comment namespaces cannot safely be deduplicated after flattening. System timeline events are outside these endpoints. Pagination is bounded, not completeness proof. |
| Gitea (`tea`) | Issue comments plus PR conversation and submitted reviews with per-review inline comments; `created_at` falls back to `submitted_at`; login/username normalized; `system=False`. Empty review/inline bodies filtered. Posts return an ID. | Partial candidates with the same lost-surface identity and date gaps. `_get_paged` uses total-count header or page size with a 50-page bound. This is not continuous or historically complete capture. |

Source anchors: [launcher](../../04_Software/adore/executor/launcher.py),
[GateRun](../../04_Software/adore/executor/base.py),
[executor fixtures](../../04_Software/tests/test_executor.py),
[configuration selection](../../04_Software/adore/config.py),
[forge model](../../04_Software/adore/forge/base.py),
[GitLab](../../04_Software/adore/forge/gitlab.py),
[GitHub](../../04_Software/adore/forge/github.py),
[Gitea](../../04_Software/adore/forge/gitea.py),
[forge fixtures](../../04_Software/tests/test_forge.py).
The GitHub/Gitea `test_*_mr_comments_include_review_bodies_and_inline_comments`
fixtures yield three normalized objects each; this proves accessible surfaces,
not ongoing collection. Other fixtures use dates such as `t1/t2`, demonstrating
that current normalization is not timestamp validation.

[Executor component guidance](../../05_SoftwareDocu/Component_Executor_Launcher.md)
contains stale session fallback/self-heal examples. Current `GateRun` and launcher
run fresh sessions and have no session field; source takes precedence. This
proposal neither fixes that historical documentation nor changes its contract.

## Forge direction, association and authority

Define `observed_comments` as all unique eligible objects observed through an
authorized adapter read. This set includes ADORE's own posted comments when read
back. Define `posted_by_adore` only where a successful **create**, its returned
source ID and a durable run-owned delivery record can be reconciled. An edit,
attempted POST, transport retry or marker replay is not another creation.
Define `received_external` only where trusted source author identity proves the
object was not created by the configured ADORE identity. A display name or a
marker alone cannot authenticate an external author. Unknown authors/direction
contribute to `direction_unknown`, never silently to received or posted.

`observed_comments` overlaps `posted_by_adore`; do not add them. External received
and verified posted sets are disjoint when identity is proven. Account-authored
comments without proven ADORE delivery provenance remain direction-unknown.
Run associations may overlap: the same ticket comment seen by two runs counts
once at project level and once in each applicable per-run view. Project totals
are a union of source IDs, not a sum of run rows; multi-project totals are a union
of authorized project-qualified identities. A related forge object must be
explicitly linked by retained run/ticket/MR evidence, never by matching text.

[Orchestrator notification evidence](../../04_Software/adore/orchestrator.py)
records `notification-delivered` with `kind/surface/resource/comment_id`.
The outbox can deliver an edit or recover an already-posted marker. Consequently
that journal entry alone proves neither a new creation nor the original forge
creation time. Current journal reads cannot recover full inbound history.
Forge comments remain the authority for human approval on the validated candidate;
measurement metadata never grants approval, readiness, merge or execution rights.

The unit is an observed creation, not the number of comments still visible now.
A later remote deletion does not subtract a previously observed creation;
unobserved deleted objects remain unknown. A privacy purge removes retained
metadata and marks coverage expired. A scan can be complete for currently visible
objects while creation-history coverage remains partial. Declare capture start
and supported surfaces explicitly; no initial scan implies complete history.

## Proposed count-only evidence contract

This is a future schema proposal, not an existing state or endpoint. Use a
separately versioned metadata ledger (`message_schema=1`) without migrating
ADORE schema-1 run state. Store these fields only:

| Field | Validation and meaning |
| --- | --- |
| `project_id`, `run_id` | Immutable authorized association from ADORE, not body text or CLI-supplied project names. Run-level observations require both. Forge source object identity is project-level; separate association records link it to one or more immutable runs. |
| `source`, `source_version`, `source_namespace`, `source_id` | Allowlisted executor/forge and pinned parser schema. Executor identity includes physical launch ID plus logical message ID. Forge namespace includes platform instance, repository, resource kind/number and native endpoint category; review ID is included where needed for inline identity. Stable non-empty native ID required; archive line index, body hash and thread ID alone are insufficient. |
| `event_id` | Deterministic identity of the canonical source object; namespaced by project. Immutable on replay. Separate observation/association IDs may link the same forge object to runs without creating another counted object. |
| `observed_at` | Required valid timezone-aware UTC ingestion instant. Not the event's occurrence time. |
| `occurred_at` | Valid source creation/finalization instant normalized to UTC, or null with `timestamp_status=missing/invalid/ambiguous`. Never substitute run start/end, archive `meta.created_at`, notification delivery or read time. |
| `role`, `category`, `direction` | Allowlisted proven role/category and independently proven direction. Executor roles: human/assistant/tool; forge category: issue conversation, MR/PR conversation, review body, inline comment. Exclusion of system notes occurs before count normalization. Unknown mapping yields an unsupported-source gap. |
| `launch_id`, `revision_round` | Executor association only, from durable launch/run evidence. Revision is a dimension, not a multiplier. |
| `coverage` | Per source, role, interval and run: complete/partial/unavailable/disabled/expired/error, with reason and snapshot/cursor. Complete requires proven boundaries, finality, source exhaustion and no timestamp/identity gaps, limited to the declared monitored scope. |

Identifiers have bounded lengths (proposed maximum 256 characters per source
identity component), counts are non-negative integers, and ingested objects are
bounded per scan. #17 must select scan/object/byte limits within the operator's
run budgets and reject over-limit batches without successful partial commits.
An unsupported role is a capability gap; an invalid value in a supported
versioned schema is corrupt input. These are different outcomes.

New capture must read exact retained bytes through a strict bounded parser. Missing
native IDs, mismatched run/project, conflicting identity fields, unknown schema,
malformed JSON, invalid observation dates or invalid types reject the batch with
a typed `MetricsError`/`ForgeError` at the relevant boundary. Booleans are not
integer IDs or counts. Never reset a ledger or silently drop corrupt records.
Valid identifiable legacy objects with missing/invalid occurrence dates may be
kept as explicitly unallocated metadata; versioned new records with malformed
date syntax fail closed. A source lacking identities is unavailable, not a
new source of invented events. Unknown event types invalidate completeness even
if recognized independent objects provide a partial subtotal.

Identical canonical replay is a no-op. Reused ID with incompatible immutable
fields fails closed. Forge body edits do not affect identity/count and require
no body retention. A creation timestamp conflict is corruption, not a late
arrival. Proven association additions and first resolution of a declared legacy
timestamp gap are explicit revisions with provenance; they do not mutate the
original observation. Ledger cursors/digests must detect rewritten/truncated
evidence; rebuild never erases evidence or recounts a replay as new traffic.

The existing [StateStore journal reader](../../04_Software/adore/state.py)
skips malformed JSON lines and the launcher usage parsers are tolerant. Neither
is sufficient proof of complete new message capture. Required strict message
parsing belongs to a separately approved implementation; no runtime change is
made here. Existing usage IDs `<run_id>:<attempt>` identify launch consumption,
not messages.

## Aggregation, unavailable values and proposed API

Reuse #14's authorized immutable project set, half-open UTC interval `[from,to)`,
IANA timezone and day/week/month buckets. Inclusive local dates resolve each
midnight independently, including 23/25-hour days. Both bounds omitted mean
all-time retained evidence. Attribute messages at `occurred_at`, regardless of
the job's lifecycle dates; null occurrence dates are lifetime/unallocated only.
Late arrivals recompute their original period and mark a new snapshot with
`as_of`; they are never moved to the ingestion period. Old exported snapshots
remain labeled by their own `as_of`, rather than silently rewritten.

Expose per category/role/direction `count` (complete value or null),
`observed_count` (deduplicated lower bound), `status`, `reason`, `as_of`, monitored
boundaries and unallocated count. Known zero requires complete verified coverage
of an empty selected interval. Zero observed objects under partial/unavailable
coverage is not a known zero total. No evidence means `count=null`,
`observed_count=null`, `status=unavailable`; a completed scan with gaps can report
`count=null`, `observed_count=0`, `status=partial`. If one selected source is
unavailable, a multi-source complete total is null; keep proven component
subtotals and role-specific coverage. Missing tool coverage need not invalidate
a separately proven human/assistant subtotal.

Proposed additive `message_counts` projection in existing scoped statistics and
job read models uses separate `executor_conversation` and `forge_comments`
objects, `lifetime/in_period/unallocated`, source/coverage and composite job
identity. Example of a partial future projection (synthetic):

```json
{"message_counts":{"executor_conversation":{"count":null,"observed_count":3,"status":"partial","reason":"human role unavailable"},"forge_comments":{"count":null,"observed_count":2,"status":"partial","reason":"historical coverage unknown"}}}
```

The proposed field does not exist today. No `/api` path, database table or
configuration key is installed by this document. #17 must settle exact wire
schema and contract tests under AEGIS after owner approval. Additive nullable
fields preserve existing token/launch semantics; strict older consumers need
compatibility review. No version bump or state migration is justified by this
planning change. Preserve #15's **Messages: Not available** until real approved
capture exists. Use clear labels, separate tool traffic and coverage text; retain
the approved transparent DDP mark #B8D1C4 on #102F29.

Server authorization applies before aggregation and export. Developers see only
assigned projects; revoked access removes all nested evidence. All financial
fields and coverage remain Admin-only as in #14; counts never proxy cost or
approval authority. Browser refresh uses local projections, not fresh forge
requests. Sources must be approved and collection bounded by operational budgets.

## Privacy and retention recommendation

Extract metadata from already authorized local outputs and adapter responses;
never scrape conversations or collect bodies just for counts. Existing forge
flows necessarily read bodies for operational decisions, but the new ledger
retains neither bodies, prompts, tool arguments/results, author display names,
credentials nor body hashes. Persist only an identity classification needed for
direction; use existing configured identity rather than another user directory.
Raw archive paths/output stay server-side under their existing access controls.

Recommend 90 days of count-only metadata from observation time, with deduplication
keys/tombstones retained for the same window. Purge is explicit, scoped and
records the retention cutoff; purge must also prevent older replay from restoring
expired objects. After cutoff, all-time means retained evidence with expired
coverage, never historical completeness. New associations to expired objects
cannot recover counts without a separately authorized backfill. Raw archive and
runtime cleanup policies are unchanged; the retention value is proposed and
requires owner approval. A longer history is useful but increases retained
activity metadata and must also retain identities for replay safety.

## Synthetic acceptance examples (hand calculated)

These are normalized hypothetical fixtures, not claims about current CLI output.
All positive cases assume verified complete scoped capture except where stated.
`H/A/T` mean finalized human/assistant/tool messages; executor main count is H+A.

| Case | Input | Expected result |
| --- | --- | --- |
| Clear path/tool traffic | Launch L1: H:h1, A:a1 carrying two tool calls, T:t1, T:t2, A:a2; stream contains ten deltas for a1. | H=1, A=2, main=3, tool=2; one launch. Deltas add 0; model calls unavailable. |
| Retry/revision | Previous L1 plus fresh L2 with same text but new IDs H:h1/A:a1, then revision L3 H:h1/A:a1. | Launch-qualified identity gives H=3, A=4, main=7, tool=2, launches=3. Failed attempt L1's finalized messages still count; unfinished extra output does not. |
| Replay | L1 is read three times and a1 has start/update/final events with same logical ID. | Main remains 3 and tool 2. Conflicting finalized role for a1 rejects batch; previous snapshot remains, status error. |
| Cross-period/late | Europe/Bucharest Oct 6 interval is `[2026-10-05T21:00Z,2026-10-06T21:00Z)`. Same job has H at Oct 5 20:59Z, A at Oct 5 21:00Z, A at Oct 6 20:59Z, T at Oct 6 21:00Z. One A arrives Oct 8. | Lifetime main=3/tool=1; Oct 6 main=2/tool=0. Late arrival corrects Oct 6, adds nothing to Oct 8; exact upper-bound T belongs to Oct 7. |
| DST repeated hour | Bucharest Oct 25 interval `[2026-10-24T21:00Z,2026-10-25T22:00Z)` is 25h. A at Oct 25 00:30Z and A at 01:30Z have different IDs; both local 03:30 with different offsets. | Oct 25 A=2. Naive `2026-10-25T03:30` is ambiguous and unallocated for legacy evidence, rejected in a new versioned event; never deduplicate by clock text. |
| Forge echo/edit | Issue human c1; verified ADORE-created c2, read back twice; edit c2 once; same notification retried; one external non-empty review r1 and inline i1; system note s1 and bodyless approval r2. | Observed=4 (c1,c2,r1,i1), received_external=3, posted_by_adore=1. Edit/replay/system/approval add 0; do not report observed+posted=5. Only partial historical coverage if these are a current scan. |
| ID collision/overlap | Review id 7 and issue comment id 7; comment c1 associated with runs R1 and R2. | Distinct namespaces give 2 objects; c1 project count=1, per-run count=1 each. Flattened objects lacking namespace cannot prove collision-safe aggregate: unavailable/partial, never guess. |
| Missing/invalid dates | Three legacy identifiable comments: one valid in period, one no date, one `t1`. | Observed lifetime=3, in-period observed=1, unallocated=2; period count=null/status partial. New record with `observed_at=t1`, naive or date-only occurrence rejects batch. |
| Partial capabilities | One pinned parser proves A=3; H/T unavailable; another executor emits only usage. | Assistant observed=3; main count=null, observed_count=3/status partial. Other executor count=null/observed_count=null/unavailable. Two usage events do not add 2 messages. |
| Zero/missing/error | Exhaustive verified empty scoped stream; then compare absent archive, truncated scan and malformed record. | First count=0/complete. Missing archive null/unavailable; truncated scan null/partial with known observed subtotal; malformed new source null/error with no successful new snapshot. |

DST date boundaries may also span 23 hours (Bucharest March 29, 2026:
`[2026-03-28T22:00Z,2026-03-29T21:00Z)`). Counts use UTC instants and local bucket
labels, not a fixed 24-hour duration. [Scoped analytics source](../../04_Software/adore/web/analytics.py),
[metrics source](../../04_Software/adore/metrics.py),
[scope fixtures](../../04_Software/tests/test_web_scoped_metrics.py),
[operator guidance](../../01_Documentation/Web_Interface.md) and
[metrics component](../../05_SoftwareDocu/Component_Metrics.md) define the reused
scope/redaction rules; they provide no current conversation count.

## Concrete owner decision required in issue #16

Recommended approval wording (a request, **not evidence of approval**):

> Approve this proposal's separate executor conversation (human + assistant),
> separately reported tool messages, and forge observed/received-external/
> posted-by-ADORE sets with no mixed total; include retries/revisions as fresh
> launch-qualified messages, use only version-pinned count-only metadata from
> existing authorized archives/forge adapters, keep unavailable/partial results
> honest, and retain metadata for 90 days. Permit #17 to implement only proven
> source mappings, leaving unsupported roles/sources unavailable.

The owner may instead include tools in the main executor subtotal (larger totals
dominated by tool traffic), exclude orchestrator prompts (less comparable and
requiring provenance beyond user role), narrow forge scope to ticket conversation
(less review coverage), or choose longer retention (more history/privacy cost).
Any different choice needs an explicit recorded revision before implementation.
Even recommended approval does not authorize scraping, paid proof runs, live
acceptance, complete historical backfill or a claim of external CLI capabilities.

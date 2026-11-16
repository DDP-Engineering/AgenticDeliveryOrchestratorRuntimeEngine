# Component: Instructions (`adore/instructions.py`)

## 1. Purpose

Durably carry authenticated operator instructions from the web interface to the
existing Pi stdin owner without a second writer or agent loop.

## 2. Responsibilities

InstructionInbox owns physical, bounded current-schema files and atomic receipts.
InstructionDelivery captures prompt fallback and matches live command acknowledgements.
The API owns grants/lifecycle, the conductor owns journals and notification replay,
and Pi owns steering/follow-up scheduling and the tools already in progress.

## 3. Implementation Overview

Enqueue validates literal Unicode text and authenticated author metadata. A separate
short crash-released StateStore kernel lock serializes same-directory temporary,
fsync and replacement writes. Readers validate complete regular single-link files,
all ancestor directories, reparse points, byte bounds, duplicate JSON keys and schema.
Malformed records remain untouched and unsent with value-free filename notices.

InstructionDelivery snapshots queued records for insertion after the human thread.
Only a matching accepted initial prompt consumes this snapshot; later arrivals use
steer/follow_up from the existing RPC loop. Each command is attempted once per session.
False, missing or mismatched acknowledgements preserve Queued for the next session.

## 4. Dependencies

Python standard library, StateStore kernel locks and the shipped PromptCatalog.
No new package, web transport, setting or agent process is introduced.

## 5. Inputs And Outputs

`InstructionInbox(run_dir).enqueue(user, text, mode)` returns the queued record.
`read()` returns sorted valid records and value-free notices. `acknowledge(id, how)`
persists an idempotent receipt; `reject(id)` retains the queue with pi_rejected.
InstructionDelivery exposes suffix, poll, prompt_accepted and command_response to
conductor/launcher/RPC. Its local callbacks never perform forge I/O during Pi execution.

## 6. Data Contracts

Each `runs/<run_id>/instructions/<UUID-hex>.json` has schema 1, id, user {id,username},
created_at, mode now/after, exact text, delivery null or {at,how}, and last_error.
Text contains 1..4000 Unicode characters without NUL. Retention is 256 records per run,
32 KiB per record (8 MiB maximum record data); explicit run delete removes the inbox.
Unknown shapes remain refused with affected-file deletion guidance. No migrations.
Delivery means Pi acknowledged receipt, not execution or completion. Prompt composition
and process spawn are insufficient evidence. Unencodable author/text is refused.

## 7. Workflow Integration

The conductor reconciles persisted receipts into deterministic instruction notification
ids before appending one instruction-delivered journal event. Existing marker lookup,
outbox backoff and replay copy the exact text once to the source ticket. A forge error
keeps its outbox record and cannot undo Pi receipt or fail the active job.

## 8. Usage

In Agent sessions, queue text below the live/empty session using Send now or Send when
finished. Only a working job accepts new text. The four-locale composer polls receipt
states and fences responses to the requested project/run; the existing saved header,
scopes, Jobs/Tickets/Projects and cancellation behavior remain intact.

## 9. Validation And Tests

`tests/test_instructions.py` covers atomic reopening, trust boundaries, retention,
links/reparse points, malformed metadata, duplicate keys and receipt matching.
`test_pi_rpc.py` exercises fake Pi live commands and initial-prompt failure boundaries.
`test_orchestrator.py` exercises public conduction/restart and fake-forge replay.
`test_web_jobs.py` covers API grants, CSRF, literal payloads and non-working refusal.
`web/tests/instructions.test.mjs` and LA-03 browser journeys cover identity, copy and UI.

## 10. Limitations

Pi acceptance and local persistence cannot form one transaction. A process crash after
remote acceptance but before its local receipt can cause a queued retry; no successful
acknowledgement is invented. Ticket comments are sent/replayed after the RPC session,
independently of the live receipt. Real Pi/forge/runtime and Linux link acceptance are
operator-owned; existing contract tests use isolated offline fakes.

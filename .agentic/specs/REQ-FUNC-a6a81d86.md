<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project executor image definition and build

## Define and data authority

A container project's profile directory owns `image-build/`, outside its checkout.
`draft.json` holds schema 1, immutable project ID, UTF-8 Dockerfile, checks and
network/time/memory policy plus deterministic content revision. Text/upload is
at most 65536 UTF-8 bytes and 1024 lines, no NUL/control/invalid Unicode. At most
32 shell-free check strings, each 512 bytes, are accepted using the existing
required-tool command semantics. Dockerfile template carries the legal header,
extends the installed canonical ADORE base and finishes as `USER adore`.

Initial context has exactly the reviewed Dockerfile; local/server paths and all
COPY/ADD, ONBUILD, syntax-front-end downloads, RUN mounts/network overrides and
external stages are unsupported before runtime launch, with actionable evidence.
Single base FROM is the canonical installed ADORE base; pin its actual image ID
in the operation's execution Dockerfile. Original author text stays exportable;
revision and exact execution-context SHA are recorded separately. This explicit
supported grammar is an input/compatibility boundary, never a Dockerfile sandbox.
Known provider/forge secret values and credential-shaped literal assignments/URLs
are rejected before retention; guidance forbids embedding arbitrary secrets.

Draft/operation records are closed, atomic, bounded and strict UTF-8/JSON; links,
foreign project IDs, unexpected files/path traversal and corrupt records fail
closed. Operations are UUIDs, tags `adore-built-<project-id>:<operation-uuid>`;
operator-supplied tags/context paths are not accepted. At most 10 retained
operations per project; new requests reject once retention is full. Export is
admin-only bounded Dockerfile/evidence/log, never .env or credential stores.
Successful contexts are removed after confirmed owned cleanup; bounded verification IO is retained; images
remain managed evidence and are never deleted/pruned/published by this feature.

## Durable runtime operation

Reuse WebStore/CommandWorker's queue, immutable project identity, actor recheck,
single-worker lock and operation completion/audit. Add image-build action whose
run_id is the artifact operation UUID. No second conductor or preparation parser/
runner. A build requires a current container profile, stopped monitoring and no
active work/unfinished operation, with one config/draft revision captured before
enqueue. Worker rechecks role/project/profile/state and holds the existing
conductor lock. Draft/config changes make evidence stale, never ready to apply.

Phases: queued -> inspecting -> building -> verifying -> verified; explicit
failed/cancelled/uncertain/interrupted states cannot be applied or auto-replayed.
Cancelled before claim runs no runtime commands. During a build, durable cancel
signal interrupts only this operation's fresh or verified native process scope;
no recovered PID-only kill. Reuse LocalProcessController's Windows Jobs/Linux
delegated cgroup control and bounded strict stream drains. Linux worker build
client control requires operator-delegated `ADORE_BUILD_CGROUP_ROOT`; no fallback
to uncontained process groups. Windows-to-WSL runtime argv retains configured
wrapper/path translation and sends a controlled Linux environment. Unconfirmed
native/remote control keeps explicit uncertain evidence and owned resources for
operator reconciliation, never reports verified/cancelled success.

Support Linux-container Docker with its explicit legacy builder
(`DOCKER_BUILDKIT=0`) and Podman OCI build, including strictly shaped configured
WSL wrappers. Check runtime identity and enforceable CPU/memory capability;
unsupported builder/remote context/platform/restrictions fail actionably, never
silently weaken bounds or install a builder. Newer BuildKit per-step resource
capability is not assumed. Build options use argv, per-operation minimal context,
unique tag/labels, force-rm, one-CPU quota and selected 512..4096 MiB memory/swap
bounds. At most 160 retained native launches per operation, with 512 KiB record limits.
Owned cleanup gets a separate 30-second window. Timeout default 600 seconds,
accepted 30..1800; verification commands at
most 30 seconds each within one shared deadline. Retain <=65536 bytes per stdout/
stderr stream with known-secret/bearer redaction, discard excess while draining.
Status returns phase and available retained log, no invented progress percentage.

Networking is explicit `none` (default) or `default` (admin download authorization).
Base is locally available/pinned, pull is never; no credentials, build secrets,
SSH forwarding, Docker sockets/privileged flags, checkout or host-home contexts.
Image build downloads are separate from executor/preparation egress. None fails
on unavailable packages; default permits administrator-reviewed Dockerfile
network downloads. Controlled runtime environment uses only needed OS/PATH/local
runtime transport plus isolated HOME/DOCKER_CONFIG/registry-auth paths. Existing
remote TLS/context credentials are unsupported; no automatic auth forwarding.

## Verification and cleanup

Resolve built managed tag via ContainerBackend.image_identity; strict inspect
validates exact image ID, project/operation labels and non-root adore user.
Persist a unique verification container and actual resource ID before checks.
Run selected installed executor --version plus draft project tool
checks (the candidate required_tool_checks) through shared backend's existing bound commands in that container, no
model/provider credentials, no recipe or library setup. Verify image identity
again after checks; owned removal validates resource IDs. Failures preserve live
config, original source and typed evidence; cleanup touches only exact owned
context/verification/process identities, never inventory-wide prune. Restart
marks interrupted queue work uncertain, reconciles only verified leases/resources
and never replays build/tool side effects. Lost/corrupt control retains evidence
and reports reconciliation failure.

## Review and apply

Build review uses existing config/pending, stores immutable image ID plus declared
checks in one candidate and returns current active/proposed values. Binding covers
project/operation UUID, draft/config revisions, runtime/base/result image IDs,
context fingerprint and verification. Candidate applies through existing
config/apply locks, admin/project/CSRF, idle/paused/no-pending-operation and exact
base/candidate revision checks. Reinspect runtime, labels/image ID, latest draft
and operation before apply. `preparation.preview_plan` resolves current exact Git
recipe; image conflicts/stale source fail. User explicitly reviews a consistent
recipe/profile selection separately; target-repository YAML is never rewritten.
Existing image edits remain compatible. Failed/uncertain/cancelled operations
cannot create or apply candidates. Stale candidates require fresh review/build.

## GUI and proof

One localized panel inside Settings' Isolated environment group. Existing image
choice preserves existing single-setting review and shows the current image with
an action that opens/focuses its inline editor. Backend and image controls lead
the group; other environment settings remain in a collapsed advanced disclosure.
Selected styling identifies the active choice. Definition
guidance explains RUN commands between USER root and USER adore, successful tool
checks and explicit save/build/use. Source/check fields show 16/six resizable lines;
switches preserve unsaved text. An expandable compiler example displays RUN and
gcc/make checks plus explicit download-policy instructions without changing data.
Source and checks align on wide screens and stack on narrower screens; downloads
is beside checks, time/memory bounds in a disclosure. Spaced action and result
panels explain saving before building and show actionable failures with saved
bounded output loaded on entry. Define image offers edit/paste/text import, tool checks alongside source, explicit Build and verify,
phase/log/error/cancel, source/evidence export and Use image review through existing
PendingReview. Technical tag/context/policy detail is Advanced. Distinguish ADORE
server from browser, Dockerfile system tools from per-worktree recipe libraries,
and tool verification from model/full readiness. Developers see saved evidence
read-only; local profiles show existing native tooling responsibility notice and
no build actions. No new top-level navigation/enrollment steps or catalogue.

Focused injected public tests and bounded offline browser journeys cover success,
all input/runtime/identity/authorization/stale/failure/cancel/restart/cleanup
boundaries plus existing-image/local regression. Full Python/frontend suites,
aggregate strict --run, full epic #23 and live runtime/provider/forge acceptance
remain deferred by explicit instruction. No dependencies or release assignment.

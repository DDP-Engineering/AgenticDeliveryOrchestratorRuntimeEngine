/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { safeEvidenceLink, readJobPage, readJobDetail, activityAge, commandAllowed } from "../src/jobModel.ts";
import { parseRoute, formatRoute } from "../src/routes.ts";
import { messages } from "../src/i18n.ts";

const id = "a".repeat(32), snapshot = "b".repeat(64);
const job = () => ({ project_id: id, project_name: "alpha", project_display_name: "Alpha",
  project_archived: false, run_id: "one", ticket_iid: 1, ticket_title: null,
  ticket_url: null, mr_url: null, lifecycle: "working", stage: "build", status_group: "active",
  outcome: "", stage_failures: 0, review_rounds: 0, created_at: null, updated_at: null, last_activity_at: null,
  waiting: { availability: "unknown", reason: null, next_action: null, responsible_role: null,
    responsible_person: null, evidence_url: null, source: null },
  evidence_url: `/api/v1/jobs/${id}/one`, consumption: { availability: "unknown" },
  coverage: { ticket: "missing", journal: "missing", title: "unknown", last_activity: "unknown" } });
const page = () => ({ items: [job()], total: 1, counts: { working: 1 }, groups: { active: 1, waiting: 0, review: 0, terminal: 0 },
  limit: 10, offset: 0, complete: true, snapshot, snapshot_semantics: "optimistic-source-revision" });

test("complete projection preserves unknowns and composite identity", () => {
  assert.equal(readJobPage(page(), [id]).items[0].ticket_title, null);
  const detail = readJobDetail({ job: { ...job(), timeline: [{ ts: null, event: "gate-started", stage: "build" }] },
    complete: true, snapshot }, id, "one");
  assert.deepEqual(detail.timeline.map(row => row.stage), ["build"]);
  assert.equal(activityAge(null, 0), "unknown");
  assert.equal(activityAge("2026-10-05T00:00:00Z", Date.parse("2026-10-05T00:16:00Z")), "old");
  assert.equal(activityAge("2026-10-05T00:00:00Z", Date.parse("2026-10-05T00:01:00Z")), "recent");
});

test("a stage this build does not conduct fails closed", () => {
  assert.throws(() => readJobDetail({ job: { ...job(), stage: "deliver" }, complete: true, snapshot }, id, "one"));
  assert.throws(() => readJobDetail({ job: { ...job(),
    timeline: [{ ts: null, event: "stage-launch", stage: "deliver" }] }, complete: true, snapshot }, id, "one"));
  for (const locale of ["en", "fr", "de", "ro"]) assert.equal(messages[locale].deliverStage, undefined, locale);
});

test("incomplete malformed unauthorized and colliding duplicates fail closed", () => {
  for (const mutate of [p => p.total = -1, p => p.counts.working = NaN,
    p => p.snapshot = "bad", p => p.items[0].status_group = "terminal",
    p => p.counts.working = 3, p => p.items[0].project_id = "c".repeat(32),
    p => p.items[0].last_activity_at = "bad", p => p.items.push(job()),
    p => p.items[0].lifecycle = "merged", p => p.items[0].stage = "arbitrary",
    p => p.items[0].ticket_url = "javascript:alert(1)",
    p => p.items[0].waiting.next_action = "approve_in_browser"]) {
    const p = page(); mutate(p); assert.throws(() => readJobPage(p, [id]));
  }
  assert.throws(() => readJobPage({ ...page(), complete: false }, [id]), /incomplete/);
  assert.throws(() => readJobDetail({ job: { ...job(), timeline: [{ event: "ok", stage: "speculate", ts: null }] }, complete: true, snapshot }, id, "one"));
  assert.throws(() => readJobDetail({ job: { ...job(), timeline: [] }, complete: true, snapshot }, id, "other"));
  const p = page(); p.items.push({ ...job(), project_id: "c".repeat(32), evidence_url: `/api/v1/jobs/${"c".repeat(32)}/one` }); p.total = 2; p.counts.working = 2; p.groups.active = 2;
  assert.equal(readJobPage(p, [id, "c".repeat(32)]).items.length, 2);
});

test("links accept actual comment anchors and reject credential or executable locations", () => {
  for (const link of ["https://forge.example/org/repo/issues/1#issuecomment-7", "http://forge.example/org/repo/issues/1#note_9"]) assert.equal(safeEvidenceLink(link), link);
  for (const link of ["javascript:alert(1)", "//forge.example/path", "https://user:secret@forge.example/path",
    "https://forge.example/%0aevil", "https://forge.example/%5cevil", "https://forge.example/path?token=secret",
    "https://forge.example/path#javascript:evil"]) assert.equal(safeEvidenceLink(link), null);
});

test("command contracts protect final or human owned jobs and old routes survive", () => {
  assert.equal(commandAllowed(job(), "cancel"), true);
  assert.equal(commandAllowed({ ...job(), lifecycle: "failed" }, "retry"), true);
  for (const lifecycle of ["done", "cancelled", "failed", "stale", "handoff-pending", "handed-off"]) assert.equal(commandAllowed({ ...job(), lifecycle }, "cancel"), false);
  assert.equal(commandAllowed({ ...job(), project_archived: true, lifecycle: "failed" }, "retry"), false);
  for (const tab of ["overview", "configuration", "access", "jobs", "statistics", "history"]) {
    const route = { view: "projectDetails", project: id, tab };
    assert.deepEqual(parseRoute(formatRoute(route)), route);
  }
});

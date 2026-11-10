/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { safeEvidenceLink, readJobPage, readJobDetail, activityAge, commandAllowed, stableExecutionDrift } from "../src/jobModel.ts";
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
  budget: {availability:"observed",reason:null,launches:0,max_launches:20,active_seconds:0,max_active_seconds:3600,config_revision:snapshot},
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

test("Overview accepts only authorized, unique unreadable project IDs with no returned jobs", () => {
  const unreadable = "c".repeat(32), authorized = [id, unreadable];
  const partial = { ...page(), unreadable_projects: [unreadable] };
  assert.deepEqual(readJobPage(partial, authorized, true).unreadable_projects, [unreadable]);
  assert.throws(() => readJobPage(partial, authorized));
  for (const value of [null, [id], [unreadable, unreadable], ["d".repeat(32)], "alpha"]) {
    assert.throws(() => readJobPage({ ...page(), unreadable_projects: value }, authorized, true));
  }
  assert.throws(() => readJobPage({ ...page(), items: [], unreadable_projects: [id] }, [id], true));
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


test("stable execution drift routes to confirmed restart and keeps volatile Retry", () => {
  const failed = { ...job(), lifecycle: "failed", state_revision: "a".repeat(64),
    outcome: "INFRASTRUCTURE_EXHAUSTED: execution profile drift; restore pinned settings or start a fresh run" };
  assert.equal(stableExecutionDrift(failed), true);
  assert.equal(commandAllowed(failed, "retry"), false);
  assert.equal(commandAllowed(failed, "restart"), true);
  assert.equal(commandAllowed({ ...failed, project_archived: true }, "restart"), false);
  assert.equal(commandAllowed({ ...failed, state_revision: undefined }, "restart"), false);
  assert.equal(commandAllowed({ ...failed, lifecycle: "working" }, "restart"), false);
  assert.equal(commandAllowed({ ...failed, outcome: "RETRY_REVALIDATION_FAILED: local environment drifted" }, "retry"), true);
  assert.throws(() => readJobPage({ ...page(), items: [{ ...job(), state_revision: "wrong" }] }, [id]));
});


test("retained old branches are localized as successful recovery evidence", async () => {
  const { operationResultText } = await import("../src/ticketCopy.ts");
  const { recoveryCopy } = await import("../src/recoveryCopy.ts");
  for (const locale of ["en", "fr", "de", "ro"]) {
    assert.equal(operationResultText("restart:retained", locale), recoveryCopy[locale].retained);
    assert.notEqual(operationResultText("restart:retained", locale), recoveryCopy[locale].failed);
  }
});


test("budget observations validate counts, limits and revision before display", () => {
  const budget = {availability:"observed",reason:null,launches:9,max_launches:20,active_seconds:90,max_active_seconds:3600,config_revision:snapshot};
  const detail = value => readJobDetail({job:{...job(),budget:value,timeline:[]},complete:true,snapshot},id,"one");
  assert.equal(detail(budget).budget.launches,9);
  assert.throws(()=>detail(undefined));
  for (const value of [{...budget,launches:-1},{...budget,launches:true},
    {...budget,max_launches:0},{...budget,active_seconds:Infinity},
    {...budget,max_active_seconds:1.5},{...budget,config_revision:"bad"}]) {
    assert.throws(()=>detail(value));
  }
});


test("unavailable current limits preserve trustworthy saved job consumption", () => {
  const budget = {availability:"unavailable",reason:"config_missing",launches:9,active_seconds:90,
    max_launches:null,max_active_seconds:null,config_revision:null};
  const detail = value => readJobDetail({job:{...job(),budget:value,timeline:[]},complete:true,snapshot},id,"one");
  assert.deepEqual(detail(budget).budget,budget);
  for (const value of [{...budget,reason:"invented"},{...budget,max_launches:20},
    {...budget,config_revision:snapshot},{...budget,launches:-1},
    {...budget,active_seconds:NaN},{...budget,availability:"unknown"}]) assert.throws(()=>detail(value));
});


test("normal lifecycle guidance and failure labels exist in all four locales", async () => {
  const { jobGuidance, jobCopy } = await import("../src/jobCopy.ts");
  for (const locale of ["en", "fr", "de", "ro"]) {
    for (const lifecycle of ["working", "parked-clarification", "failed"]) {
      const guidance = jobGuidance(locale, lifecycle);
      assert.ok(guidance.reason && guidance.where && guidance.follows);
      assert.notEqual(guidance.reason, jobCopy[locale].reasonUnknown);
      assert.notEqual(guidance.where, jobCopy[locale].evidenceMissing);
      assert.notEqual(guidance.follows, jobCopy[locale].unknown);
    }
    assert.ok(jobCopy[locale].stageFailures.includes("{count}"));
  }
});

test("executor output transport is identity bound and closed to arbitrary transcripts", async () => {
  const { readExecutorOutput } = await import("../src/jobModel.ts");
  const evidence = {project_id:id,run_id:"one",availability:"observed",stdout:"ModuleNotFoundError: No module named 'yaml'\npytest: 1 failed, 2 passed",
    stderr:"diagnostic: credential\n[other output withheld]",exit_code:1,timed_out:false};
  assert.equal(readExecutorOutput(evidence,id,"one").exit_code,1);
  assert.equal(readExecutorOutput({...evidence,availability:"missing",stdout:null,stderr:null,exit_code:null,timed_out:null},id,"one").availability,"missing");
  for (const change of [{project_id:"c".repeat(32)},{run_id:"foreign"},{stdout:"PRIVATE_REASONING"},
    {stderr:"api_key=PRIVATE_KEY"},{stdout:"ModuleNotFoundError: No module named 'ghp_ABCDEFGHIJKLMNOPQRST'"},{exit_code:true},{timed_out:0},{stdout:"response\n".repeat(10000)},
    {availability:"missing"},{extra:"PRIVATE_CONFIG"}]) {
    assert.throws(()=>readExecutorOutput({...evidence,...change},id,"one"));
  }
});

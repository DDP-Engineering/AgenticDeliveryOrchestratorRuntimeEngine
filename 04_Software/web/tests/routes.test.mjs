/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { formatRoute, normalizeRoute, parseRoute } from "../src/routes.ts";

const ID = "88efed3d79945faab27a52d1a11f219b";

test("reporting selections survive statistics and job deep links", () => {
  const reporting = { from: "2026-10-25", through: "2026-10-25", timezone: "Europe/Bucharest", granularity: "week" };
  for (const view of ["metrics", "jobs"]) {
    const route = { view, project: ID, reporting };
    const url = new URL(formatRoute(route), "http://localhost");
    assert.deepEqual(parseRoute(url.pathname, url.search), route);
    assert.equal(url.searchParams.get("timezone"), "Europe/Bucharest");
  }
  assert.equal(parseRoute("/metrics", "?granularity=bad"), null);
  assert.equal(parseRoute("/metrics", "?from=not-a-date"), null);
});

// Every route in the URL scheme, as [url, route] pairs that must round-trip.
const table = [
  ["/", { view: "overview" }],
  [`/?project=${ID}`, { view: "overview", project: ID }],
  ["/projects", { view: "projects" }],
  ["/projects/new", { view: "createProject" }],
  ["/projects/import", { view: "importProject" }],
  [`/projects/${ID}`, { view: "projectDetails", project: ID, tab: "overview" }],
  [`/projects/${ID}/configuration`, { view: "projectDetails", project: ID, tab: "configuration" }],
  [`/projects/${ID}/access`, { view: "projectDetails", project: ID, tab: "access" }],
  [`/projects/${ID}/jobs`, { view: "projectDetails", project: ID, tab: "jobs" }],
  [`/projects/${ID}/jobs?run=run-26`, { view: "projectDetails", project: ID, tab: "jobs", run: "run-26" }],
  [`/projects/${ID}/jobs?view=jobs`, { view: "projectDetails", project: ID, tab: "jobs", jobsView: "jobs" }],
  [`/projects/${ID}/statistics`, { view: "projectDetails", project: ID, tab: "statistics" }],
  [`/projects/${ID}/statistics?tab=usage&from=2026-10-01&granularity=week`, { view: "projectDetails", project: ID, tab: "statistics", metricsTab: "usage", reporting: { from: "2026-10-01", through: "", timezone: "UTC", granularity: "week" } }],
  ["/jobs", { view: "jobs" }],
  [`/jobs?project=${ID}`, { view: "jobs", project: ID }],
  [`/jobs?project=${ID}&run=run-26`, { view: "jobs", project: ID, run: "run-26" }],
  ["/metrics", { view: "metrics" }],
  [`/metrics?project=${ID}&tab=usage`, { view: "metrics", project: ID, tab: "usage" }],
  ["/admin/status", { view: "administration" }],
  ["/admin/users", { view: "adminUsers" }],
  ["/admin/audit", { view: "adminAudit" }],
  ["/account", { view: "settings" }],
];

test("every route parses from and formats to its URL", () => {
  for (const [url, route] of table) {
    const [path, query = ""] = url.split("?");
    assert.deepEqual(parseRoute(path, query ? `?${query}` : ""), route, url);
    assert.equal(formatRoute(route), url, JSON.stringify(route));
  }
});

test("trailing slashes and unknown query parameters are ignored", () => {
  assert.deepEqual(parseRoute("/projects/", ""), { view: "projects" });
  assert.deepEqual(parseRoute("/jobs", `?project=${ID}&sort=desc`), { view: "jobs", project: ID });
  assert.deepEqual(parseRoute("/metrics", "?tab=bogus"), { view: "metrics" });
});

test("unknown or malformed paths are not routes", () => {
  for (const path of ["/nope", "/projects/a/b/c", "/projects/bad%20id", "/admin", "/Projects", "/projects/x/settings"]) {
    assert.equal(parseRoute(path, ""), null, path);
  }
});

test("normalization replaces unknown and role-restricted routes", () => {
  assert.deepEqual(normalizeRoute(null, { isAdmin: true }), { route: { view: "overview" }, replaced: true });
  for (const view of ["createProject", "importProject", "administration", "adminUsers", "adminAudit"]) {
    assert.deepEqual(normalizeRoute({ view }, { isAdmin: false }), { route: { view: "overview" }, replaced: true }, view);
    assert.deepEqual(normalizeRoute({ view }, { isAdmin: true }), { route: { view }, replaced: false }, view);
  }
  assert.deepEqual(
    normalizeRoute({ view: "projectDetails", project: ID, tab: "prices" }, { isAdmin: false }),
    { route: { view: "projectDetails", project: ID, tab: "configuration" }, replaced: true });
  assert.deepEqual(
    normalizeRoute({ view: "projectDetails", project: ID, tab: "access" }, { isAdmin: false }),
    { route: { view: "projectDetails", project: ID, tab: "overview" }, replaced: true });
  assert.deepEqual(
    normalizeRoute({ view: "metrics", tab: "projects" }, { isAdmin: false }),
    { route: { view: "metrics", tab: "summary" }, replaced: true });
  assert.deepEqual(normalizeRoute({ view: "settings" }, { isAdmin: false }), { route: { view: "settings" }, replaced: false });
});

test("identifiers follow the API alphabet and a run needs its project", () => {
  assert.equal(formatRoute({ view: "projectDetails", project: "demo.v2", tab: "overview" }), "/projects/demo.v2");
  assert.deepEqual(parseRoute("/projects/demo.v2", ""), { view: "projectDetails", project: "demo.v2", tab: "overview" });
  // Run IDs use the API's [A-Za-z0-9._-] alphabet; anything else is dropped, not guessed.
  assert.deepEqual(parseRoute("/jobs", `?project=${ID}&run=run+1`), { view: "jobs", project: ID });
  assert.deepEqual(parseRoute("/jobs", "?run=run-26"), { view: "jobs" });
  assert.equal(formatRoute({ view: "jobs", run: "run-26" }), "/jobs");
});

test("legacy executor links redirect to Settings for both roles", () => {
 for (const isAdmin of [true,false]) assert.deepEqual(normalizeRoute(parseRoute(`/projects/${ID}/executor`),{isAdmin}),{route:{view:"projectDetails",project:ID,tab:"configuration"},replaced:true});
});

test("project tab queries are kept only where they belong and validated", () => {
  assert.deepEqual(parseRoute(`/projects/${ID}/jobs`, "?run=run+1"), { view: "projectDetails", project: ID, tab: "jobs" });
  assert.deepEqual(parseRoute(`/projects/${ID}/jobs`, "?view=tickets"), { view: "projectDetails", project: ID, tab: "jobs" });
  assert.deepEqual(parseRoute(`/projects/${ID}/jobs`, "?view=jobs&run=run-26"), { view: "projectDetails", project: ID, tab: "jobs", run: "run-26" });
  assert.equal(formatRoute({ view: "projectDetails", project: ID, tab: "jobs", jobsView: "jobs", run: "run-26" }), `/projects/${ID}/jobs?run=run-26`);
  assert.deepEqual(parseRoute(`/projects/${ID}/statistics`, "?view=jobs"), { view: "projectDetails", project: ID, tab: "statistics" });
  assert.deepEqual(parseRoute(`/projects/${ID}/configuration`, "?run=run-26&tab=usage"), { view: "projectDetails", project: ID, tab: "configuration" });
  assert.deepEqual(parseRoute(`/projects/${ID}/statistics`, "?tab=projects"), { view: "projectDetails", project: ID, tab: "statistics" });
  assert.equal(parseRoute(`/projects/${ID}/statistics`, "?from=10/01/2026"), null);
  assert.equal(formatRoute({ view: "projectDetails", project: ID, tab: "history", run: "run-26" }), `/projects/${ID}/history`);
  for (const isAdmin of [true, false]) for (const tab of ["jobs", "statistics"]) assert.deepEqual(
    normalizeRoute({ view: "projectDetails", project: ID, tab }, { isAdmin }), { route: { view: "projectDetails", project: ID, tab }, replaced: false });
});

test("legacy price links open Settings, where prices live, for both roles", () => {
  for (const isAdmin of [true, false]) assert.deepEqual(
    normalizeRoute(parseRoute(`/projects/${ID}/prices`), { isAdmin }),
    { route: { view: "projectDetails", project: ID, tab: "configuration" }, replaced: true }, String(isAdmin));
});

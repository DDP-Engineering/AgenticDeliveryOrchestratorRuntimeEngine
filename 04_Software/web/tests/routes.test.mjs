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

// Every route in the URL scheme, as [url, route] pairs that must round-trip.
const table = [
  ["/", { view: "overview" }],
  [`/?project=${ID}`, { view: "overview", project: ID }],
  ["/projects", { view: "projects" }],
  ["/projects/new", { view: "createProject" }],
  ["/projects/import", { view: "importProject" }],
  [`/projects/${ID}`, { view: "projectDetails", project: ID, tab: "overview" }],
  [`/projects/${ID}/configuration`, { view: "projectDetails", project: ID, tab: "configuration" }],
  [`/projects/${ID}/prices`, { view: "projectDetails", project: ID, tab: "prices" }],
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

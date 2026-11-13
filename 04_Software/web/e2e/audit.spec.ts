/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { revalidateVisiblePage } from "./polling";
import { auditCopy } from "../src/auditCopy";
import { messages, type Locale } from "../src/i18n";
import { test, expect } from "@playwright/test";

test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
});

test("change evidence is scannable, server filtered and retention stays in administration", async ({ page }) => {
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Change history", exact: true }).click();
  await expect(page.getByLabel("Actor ID", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Change type", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Audit retention" })).toHaveCount(0);
  await expect(page.getByRole("columnheader", { name: "Result", exact: true })).toBeVisible();
  await page.getByRole("cell").getByText("Evidence", { exact: true }).first().click();
  await expect(page.getByText("Before value not recorded", { exact: true }).first()).toBeVisible();
  await expect(page.locator(".audit-evidence dd").first()).toHaveCSS("white-space", "normal");
  await page.screenshot({ path: test.info().outputPath("audit-desktop.png"), fullPage: true });
  const request = page.waitForRequest(request => request.url().includes("/audit-page?") && request.url().includes("action=missing-event"));
  await page.getByLabel("Change type", { exact: true }).fill("missing-event");
  await page.getByRole("button", { name: "Apply filters", exact: true }).click();
  await request;
  await expect(page.getByText("No changes match these filters.", { exact: true })).toBeVisible();
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "System status", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Audit retention" })).toBeVisible();
  await expect(page.getByText(/jobs, run journals and identity data are kept/)).toBeVisible();
  await expect(page.getByText(/Deleting audit events does not delete jobs|Saved limits appear below/)).toHaveCount(0);
  // Current limits are named, not just zeros in the form.
  const limits = page.locator(".audit-limits");
  await expect(limits.locator("div").filter({ has: page.getByText("Keep for days", { exact: true }) })).toContainText("Unlimited");
  await expect(limits.locator("div").filter({ has: page.getByText("Audit data limit (MiB)", { exact: true }) })).toContainText("Unlimited");
  await expect(page.locator(".audit-policy-form input[name=retention_days]")).toHaveValue("0");
  // Worker and storage are compact indicators in one row; one shared volume is one line.
  const row = page.locator(".system-status-row");
  await expect(row.getByText("Control worker", { exact: true })).toBeVisible();
  await expect(row.getByText("Storage", { exact: true })).toBeVisible();
  await expect(page.getByText(/Shows whether the command worker|Shows free space where ADORE/)).toHaveCount(0);
  await expect(page.getByText(/share this volume/)).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Volume", exact: true })).toHaveCount(0);
  // Separate disks get one table row each, in server order (home first), with what they hold.
  const gib = 1024 ** 3, volume = (scope: string, project: string | null, id: string, free: number) => ({ scope, project, free_bytes: free * gib, total_bytes: 100 * gib, low: free < 1, volume_id: id });
  await page.route("**/api/v1/system/storage", route => route.fulfill({ json: { threshold_bytes: gib, low: true, volumes: [
    volume("home", null, "100", 40), volume("project", "alpha", "9", 0.5), volume("project", "beta", "100", 40)] } }));
  await page.reload();
  const rows = page.locator("table").filter({ has: page.getByRole("columnheader", { name: "Volume", exact: true }) }).locator("tbody tr");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toContainText("ADORE home, beta");
  await expect(rows.nth(1)).toContainText("alpha");
  await expect(rows.nth(1)).toContainText("Low disk space");
  await expect(page.getByText(/share this volume/)).toHaveCount(0);
});

test("expanding evidence keeps the columns still and shortens identifiers", async ({ page }) => {
  const correlation = "ab".repeat(32), base = "cd".repeat(32);
  await page.route("**/api/v1/audit-page?*", async route => {
    const value = await (await route.fetch()).json();
    Object.assign(value.items[0], { operation_id: null, correlation, base_revision: base, candidate_revision: null });
    await route.fulfill({ json: value });
  });
  await page.goto("/admin/audit");
  const headers = page.locator(".audit-evidence thead th");
  await expect(headers).toHaveCount(5);
  const before = await headers.evaluateAll(cells => cells.map(cell => Math.round(cell.getBoundingClientRect().left)));
  await page.getByRole("cell").getByText("Evidence", { exact: true }).first().click();
  const detail = page.locator(".audit-detail-row").first();
  await expect(detail).toBeVisible();
  expect(await headers.evaluateAll(cells => cells.map(cell => Math.round(cell.getBoundingClientRect().left)))).toEqual(before);
  await expect(detail.locator(`code[title="${correlation}"]`)).toHaveText(correlation.slice(0, 12));
  await expect(detail.locator(`code[title="${base}"]`)).toHaveText(base.slice(0, 12));
  await expect(detail).not.toContainText("Candidate revision");
  await expect(detail).not.toContainText(correlation);
  // At phone width the fixed table keeps readable columns and scrolls inside its container.
  await page.setViewportSize({ width: 390, height: 844 });
  expect(Math.min(...await headers.evaluateAll(cells => cells.map(cell => cell.getBoundingClientRect().width)))).toBeGreaterThanOrEqual(90);
  expect(await page.locator(".audit-evidence .table-scroll").evaluate(node => node.scrollWidth > node.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
});

for (const view of ["global", "project"] as const) {
test(`${view} change history background reads keep the active filters and open evidence`, async ({ page }) => {
  await page.clock.install();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const project = view === "project" ? projects.find((item: { name: string }) => item.name === "alpha").id : "";
  await page.goto(project ? `/projects/${project}/history` : "/admin/audit");
  const panel = page.locator(".audit-evidence");
  const baseline = await (await page.request.get("/api/v1/audit-page?limit=10&offset=0")).json();
  const event = baseline.items[0];
  const expectedProjectId = project || event.project_id;
  let actor = event.actor;
  let projectId = expectedProjectId;
  let query = new URLSearchParams();
  await page.route("**/api/v1/audit-page?*", route => {
    query = new URL(route.request().url()).searchParams;
    return route.fulfill({ json: { ...baseline, items: [{ ...event, actor, project_id: projectId }], total: 1 } });
  });
  const action = page.getByLabel("Change type", { exact: true });
  await action.fill(event.action);
  await page.getByRole("button", { name: "Apply filters", exact: true }).click();
  await expect(panel.getByRole("status")).toContainText("1 ");
  const evidence = panel.getByRole("button", { name: /Evidence/ });
  await evidence.click();
  await action.fill("unapplied-filter");
  actor = "updated_actor";
  await page.clock.fastForward(15000);
  await expect(panel.getByRole("cell").filter({ hasText: actor })).toBeVisible();
  await expect(evidence).toHaveAttribute("aria-expanded", "true");
  await expect(action).toHaveValue("unapplied-filter");
  expect(query.get("action")).toBe(event.action);
  expect(query.get("project_id")).toBe(project || null);
  await expect(panel.getByRole("button", { name: "Refresh", exact: true })).toHaveCount(1);
  if (project) projectId = "0".repeat(32);
  else actor = "invalid actor!";
  await revalidateVisiblePage(page);
  await expect(panel.getByRole("alert")).toContainText("Could not load data");
  await expect(panel.getByRole("table")).toHaveCount(0);
  actor = "recovered_actor";
  projectId = expectedProjectId;
  await page.clock.fastForward(15000);
  await expect(panel.getByRole("cell").filter({ hasText: actor })).toBeVisible();
});
}

for (const view of ["global", "project"] as const) {
test(`${view} change history manual refresh retains paged evidence and draft focus`, async ({ page }) => {
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const project = projects.find((item: { name: string }) => item.name === "alpha").id;
  const baseline = await (await page.request.get("/api/v1/audit-page?limit=10&offset=0")).json();
  const event = { ...baseline.items[0], project_id: project, actor: "continuity_actor" };
  await page.clock.install();
  let hold = false, reads = 0, release = () => {}, actor = event.actor;
  const queries: string[] = [];
  await page.route("**/api/v1/audit-page?*", async route => {
    reads++;
    const query = new URL(route.request().url()).searchParams;
    queries.push(query.toString());
    const offset = Number(query.get("offset")), size = query.get("limit") === "all" ? 70 : Number(query.get("limit"));
    const value = { items: Array.from({ length: Math.min(size, 70 - offset) }, (_, index) => ({ ...event, id: offset + index + 1, actor })), total: 70, offset, limit: query.get("limit") === "all" ? null : size };
    if (hold) await new Promise<void>(resolve => { release = resolve; });
    await route.fulfill({ json: value }).catch(() => undefined);
  });
  try {
    await page.goto(view === "project" ? `/projects/${project}/history` : "/admin/audit");
    const panel = page.locator(".audit-evidence"), feedback = panel.locator(".refresh-feedback");
    const action = panel.getByLabel("Change type", { exact: true });
    await action.fill(event.action); await panel.getByRole("button", { name: "Apply filters", exact: true }).click();
    const size = panel.getByRole("combobox", { name: "Rows per page", exact: true });
    await size.selectOption("25");
    await expect(panel.locator("tbody tr")).toHaveCount(25);
    await panel.getByRole("button", { name: "Next", exact: true }).click();
    await expect.poll(() => new URLSearchParams(queries.at(-1)).get("offset")).toBe("25");
    await expect(feedback).toHaveAttribute("data-refreshing", "false");
    const evidence = panel.getByRole("button", { name: /Evidence/ }).first();
    await evidence.click(); await action.fill("unapplied-filter");
    const row = await panel.locator("tbody tr").first().elementHandle();
    const input = await action.elementHandle();
    const lastSuccess = await feedback.locator("time").getAttribute("datetime");
    const query = queries.at(-1), before = reads;
    hold = true;
    await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect.poll(() => reads).toBe(before + 1);
    await feedback.getByRole("button", { name: "Refresh", exact: true }).focus(); await page.keyboard.press("Enter");
    await action.focus();
    const scroll = await page.evaluate(() => ({ x: scrollX, y: scrollY }));
    await page.clock.runFor(2000); await revalidateVisiblePage(page);
    expect(reads).toBe(before + 1); expect(queries.at(-1)).toBe(query);
    await expect(panel.getByRole("table")).toBeVisible(); await expect(evidence).toHaveAttribute("aria-expanded", "true");
    await expect(size).toHaveValue("25"); await expect(action).toHaveValue("unapplied-filter"); await expect(action).toBeFocused();
    await expect(panel.getByText(auditCopy.en.loading, { exact: true })).toHaveCount(0);
    await expect(feedback.locator("time")).toHaveAttribute("datetime", lastSuccess!);
    hold = false; release();
    await expect(feedback).toHaveAttribute("data-refreshing", "false");
    expect(await row!.evaluate(node => node === document.querySelector(".audit-evidence tbody tr"))).toBe(true);
    expect(await input!.evaluate(node => node === document.activeElement)).toBe(true);
    expect(await page.evaluate(() => ({ x: scrollX, y: scrollY }))).toEqual(scroll);
    await expect(feedback.locator("time")).not.toHaveAttribute("datetime", lastSuccess!);
    // Changed background evidence updates the same surviving row without a loading panel.
    actor = "changed_actor"; hold = true;
    await page.clock.fastForward(15000); await expect.poll(() => reads).toBe(before + 2);
    await expect(panel.locator("tbody")).not.toContainText(actor);
    await expect(evidence).toHaveAttribute("aria-expanded", "true");
    hold = false; release();
    await expect(panel.locator("tbody tr").first()).toContainText(actor);
    expect(await row!.evaluate(node => node === document.querySelector(".audit-evidence tbody tr"))).toBe(true);
    await expect(action).toBeFocused(); await expect(size).toHaveValue("25");
    await expect(evidence).toHaveAttribute("aria-expanded", "true");
    expect(new URLSearchParams(queries.at(-1)).get("offset")).toBe("25");
  } finally { release(); }
});
}

for (const failure of ["transport", "deadline", "malformed", "denied"] as const) {
test(`change history ${failure} refresh has honest freshness and recovery`, async ({ page }) => {
  await page.clock.install();
  await page.goto("/admin/audit");
  const panel = page.locator(".audit-evidence"), feedback = panel.locator(".refresh-feedback");
  await expect(panel.getByRole("table")).toBeVisible();
  const lastSuccess = await feedback.locator("time").getAttribute("datetime");
  let release = () => {};
  await page.route("**/api/v1/audit-page?*", async route => {
    if (failure === "transport") await route.abort("failed");
    else if (failure === "deadline") {
      await new Promise<void>(resolve => { release = resolve; });
      await route.fulfill({ json: { items: [], total: 0, offset: 0, limit: 10 } }).catch(() => undefined);
    } else if (failure === "malformed") await route.fulfill({ contentType: "application/json", body: "{" });
    else await route.fulfill({ status: 403, json: { detail: { code: "forbidden" } } });
  });
  try {
    await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    if (failure === "deadline") await page.clock.runFor(10000);
    const informational = failure === "transport" || failure === "deadline";
    if (informational) {
      await expect(feedback.getByRole("status")).toContainText("Refresh failed");
      await expect(panel.getByRole("table")).toBeVisible();
      await expect(feedback.locator("time")).toHaveAttribute("datetime", lastSuccess!);
    } else {
      await expect(panel.getByRole("alert")).toContainText("Could not load data");
      await expect(panel.getByRole("table")).toHaveCount(0); await expect(feedback.locator("time")).toHaveCount(0);
      await expect(feedback.getByRole("status")).toHaveCount(0);
    }
    await page.unroute("**/api/v1/audit-page?*");
    await page.clock.runFor(1000);
    await feedback.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(panel.getByRole("table")).toBeVisible(); await expect(feedback.getByRole("status")).toHaveCount(0);
    await expect(feedback.locator("time")).not.toHaveAttribute("datetime", lastSuccess!);
    release();
    await expect(panel.getByRole("table")).toBeVisible();
  } finally { release(); }
});
}

test("change history query ownership cancels old reads and pauses hidden scheduling", async ({ page }) => {
  const baseline = await (await page.request.get("/api/v1/audit-page?limit=10&offset=0")).json();
  await page.clock.install();
  let hold = false, reads = 0;
  const releases: Array<() => void> = [];
  await page.route("**/api/v1/audit-page?*", async route => {
    reads++;
    const action = new URL(route.request().url()).searchParams.get("action");
    const value = { ...baseline, items: [{ ...baseline.items[0], actor: action ? "replacement_actor" : "original_actor" }], total: 1 };
    if (hold) await new Promise<void>(resolve => { releases.push(resolve); });
    await route.fulfill({ json: value }).catch(() => undefined);
  });
  try {
    await page.goto("/admin/audit");
    const panel = page.locator(".audit-evidence"), feedback = panel.locator(".refresh-feedback");
    await expect(panel.getByRole("cell").filter({ hasText: "original_actor" })).toBeVisible();
    const before = reads;
    // Hidden intervals do not read. One visible return joins repeated visible events.
    await page.evaluate(() => {
      Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await page.clock.fastForward(45000); expect(reads).toBe(before);
    hold = true;
    await page.evaluate(() => {
      Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
      document.dispatchEvent(new Event("visibilitychange")); document.dispatchEvent(new Event("visibilitychange"));
    });
    await expect.poll(() => reads).toBe(before + 1);
    await expect.poll(() => releases.length).toBe(1);
    const oldCancelled = page.waitForEvent("requestfailed", request => request.url().includes("/audit-page?") && !request.url().includes("action="));
    await panel.getByLabel("Change type", { exact: true }).fill("replacement-event");
    await panel.getByRole("button", { name: "Apply filters", exact: true }).click();
    await oldCancelled;
    await expect.poll(() => releases.length).toBe(2);
    await expect(panel.getByRole("table")).toHaveCount(0); await expect(feedback.locator("time")).toHaveCount(0);
    releases[0](); await expect(panel.getByText("original_actor", { exact: true })).toHaveCount(0);
    hold = false; releases[1]();
    await expect(panel.getByRole("cell").filter({ hasText: "replacement_actor" })).toBeVisible();
    // Leaving the view aborts its current read and prevents a late publication/retry.
    hold = true;
    await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect.poll(() => releases.length).toBe(3);
    const leaving = page.waitForEvent("requestfailed", request => request.url().includes("/audit-page?"));
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await leaving;
    const exitedReads = reads; releases[2](); await page.clock.fastForward(45000);
    expect(reads).toBe(exitedReads); await expect(panel).toHaveCount(0);
  } finally { releases.forEach(release => release()); }
});

test("removed audit events cannot regain an old expanded disclosure", async ({ page }) => {
  const baseline = await (await page.request.get("/api/v1/audit-page?limit=10&offset=0")).json();
  let items = [baseline.items[0]];
  await page.route("**/api/v1/audit-page?*", route => route.fulfill({ json: { ...baseline, items, total: items.length } }));
  await page.goto("/admin/audit");
  const panel = page.locator(".audit-evidence"), feedback = panel.locator(".refresh-feedback");
  await panel.getByRole("button", { name: /Evidence/ }).click();
  await expect(panel.locator(".audit-detail-row")).toBeVisible();
  items = []; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(panel.getByText("No changes match these filters.", { exact: true })).toBeVisible();
  await expect(panel.locator(".audit-detail-row")).toHaveCount(0);
  items = [baseline.items[0]]; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(panel.getByRole("button", { name: /Evidence/ })).toHaveAttribute("aria-expanded", "false");
});

test("project change history background recovers from a stalled read", async ({ page }) => {
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const project = projects.find((item: { name: string }) => item.name === "alpha").id;
  const baseline = await (await page.request.get("/api/v1/audit-page?limit=10&offset=0")).json();
  await page.clock.install();
  let reads = 0;
  let release = () => {};
  const stalled = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/audit-page?*", async route => {
    if (++reads === 1) {
      await stalled;
      await route.abort().catch(() => undefined);
      return;
    }
    await route.fulfill({ json: { ...baseline, items: [{ ...baseline.items[0], project_id: project }], total: 1 } });
  });
  try {
    await page.goto(`/projects/${project}/history`);
    await expect.poll(() => reads).toBe(1);
    const panel = page.locator(".audit-evidence");
    await page.clock.fastForward(10000);
    await expect(panel.getByRole("alert")).toContainText("Could not load data");
    await page.clock.fastForward(15000);
    await expect(panel.getByRole("status")).toContainText("1 ");
  } finally { release(); }
});

test("malformed or failed projections hide evidence and retry recovers", async ({ page }) => {
  await page.goto("/admin/audit");
  await expect(page.getByRole("columnheader", { name: "Result", exact: true })).toBeVisible();
  const good = await page.request.get("/api/v1/audit-page?limit=10&offset=0");
  const malformed = await good.json();
  malformed.items[0].before = { password: "injected-private-secret" };
  await page.route("**/api/v1/audit-page?*", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(malformed) }));
  await page.locator(".audit-evidence").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(page.locator(".audit-evidence table")).toHaveCount(0);
  await expect(page.locator(".audit-evidence")).not.toContainText("injected-private-secret");
  await page.unroute("**/api/v1/audit-page?*");
  await page.route("**/api/v1/audit-page?*", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":{"code":"web_store_corrupt"}}' }));
  await page.locator(".audit-evidence").getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await page.unroute("**/api/v1/audit-page?*");
  await page.locator(".audit-evidence").getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("columnheader", { name: "Result", exact: true })).toBeVisible();
});

test("server pages retain filters and show truthful account diffs", async ({ page }) => {
  const me = await (await page.request.get("/api/v1/me")).json();
  for (let index = 0; index < 12; index++) {
    const created = await page.request.post("/api/v1/users/with-access", { headers: { "X-CSRF-Token": me.csrf }, data: {
      username: `audit_fixture_${index}`, password: "audit-private-password", role: "developer", project_ids: [], allow_no_projects: true,
    } });
    expect(created.ok()).toBeTruthy();
  }
  await page.goto("/admin/audit");
  await page.getByLabel("Change type", { exact: true }).fill("user-created");
  await page.getByRole("button", { name: "Apply filters", exact: true }).click();
  await expect(page.locator(".audit-evidence tbody tr")).toHaveCount(10);
  await page.getByRole("cell").getByText("Evidence", { exact: true }).first().click();
  await expect(page.locator(".audit-evidence")).toContainText('"exists":false');
  await expect(page.locator(".audit-evidence")).not.toContainText("audit-private-password");
  const continuation = page.waitForRequest(request => request.url().includes("/audit-page?") && request.url().includes("offset=10") && request.url().includes("action=user-created"));
  await page.locator(".audit-evidence").getByRole("button", { name: "Next", exact: true }).click();
  await continuation;
  await expect(page.locator(".audit-evidence tbody tr")).toHaveCount(2);
  await page.getByLabel("From (UTC)", { exact: true }).fill("2099-01-01T00:00");
  await page.getByRole("button", { name: "Apply filters", exact: true }).click();
  await expect(page.getByText("No changes match these filters.", { exact: true })).toBeVisible();
});

test("Dev reads only assigned project changes and cannot enter administrator history", async ({ page }) => {
  const me = await (await page.request.get("/api/v1/me")).json();
  await page.request.delete("/api/v1/session", { headers: { "X-CSRF-Token": me.csrf } });
  await page.request.post("/api/v1/session", { data: { username: "developer", password: "test-password" } });
  const projects = await (await page.request.get("/api/v1/projects")).json();
  expect(projects.every((project: { name: string }) => project.name === "alpha")).toBeTruthy();
  await page.goto(`/projects/${projects[0].id}/history`);
  await expect(page.getByRole("region", { name: "Change evidence", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Change history", exact: true })).toHaveCount(0);
  expect((await page.request.get("/api/v1/audit-page")).status()).toBe(403);
  expect((await page.request.get(`/api/v1/audit-page?project_id=${"0".repeat(32)}`)).status()).toBe(403);
  await expect(page.locator(".audit-evidence")).not.toContainText("audit_fixture_");
});

test("localized change evidence remains usable at 390px in both themes", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const me = await (await page.request.get("/api/v1/me")).json();
  const originalPreferences = await (await page.request.get("/api/v1/me/preferences")).json();
  try {
    for (const locale of ["en", "fr", "de", "ro"] as Locale[]) {
      for (const theme of ["light", "dark"]) {
        const updated = await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } });
        expect(updated.ok()).toBeTruthy();
        await page.goto("/admin/audit");
        await expect(page.getByLabel(auditCopy[locale].actor, { exact: true })).toBeVisible();
        await expect(page.getByRole("button", { name: auditCopy[locale].apply, exact: true })).toBeVisible();
        const feedback = page.locator(".audit-evidence .refresh-feedback");
        await expect(feedback.locator("time")).toHaveCount(1);
        await page.route("**/api/v1/audit-page?*", route => route.abort("failed"));
        await feedback.getByRole("button", { name: messages[locale].refresh, exact: true }).click();
        await expect(feedback.getByRole("status")).toHaveText(messages[locale].refreshStale);
        await expect(page.locator(".audit-evidence table")).toBeVisible();
        await feedback.getByRole("button", { name: messages[locale].retry, exact: true }).focus();
        await page.unroute("**/api/v1/audit-page?*");
        await page.keyboard.press("Enter");
        await expect(feedback.getByRole("status")).toHaveCount(0);
        await expect(feedback.getByRole("button", { name: messages[locale].refresh, exact: true })).toBeFocused();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
      }
    }
    await page.screenshot({ path: test.info().outputPath("audit-mobile-ro-dark.png"), fullPage: true });
  } finally {
    const restored = await page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": me.csrf }, data: {
        language: originalPreferences.language ?? "en",
        theme: originalPreferences.theme ?? "system",
      },
    });
    expect(restored.ok()).toBeTruthy();
  }
});


test("typed History targets and outcomes appear in four locales", async ({ page }) => {
  const me = await (await page.request.get("/api/v1/me")).json();
  const original = await (await page.request.get("/api/v1/me/preferences")).json();
  await page.route("**/api/v1/audit-page?*", async route => {
    const make = (id: number, action: string, type: string, target: string, result: string, phase: string) => ({
      id, actor_id: action === "job-deleted" ? null : 1, actor: action === "job-deleted" ? null : "admin",
      action, project: "alpha", project_id: "a".repeat(32), resource_type: type, resource_id: target,
      created_at: "2026-11-08T10:00:00+00:00", phase, result, before: null, after: null,
      operation_id: action === "job-deleted" ? null : id, base_revision: null, candidate_revision: null, correlation: null,
    });
    await route.fulfill({ json: { items: [make(1, "ticket-start-prepared", "ticket", "46", "prepared", "prepare"),
      make(2, "operation-finished", "job", "job-46", "rejected", "apply"),
      make(3, "operation-finished", "job", "job-47", "failed", "apply"),
      make(4, "job-deleted", "job", "job-48", "applied", "apply")], total: 4, offset: 0, limit: 10 } });
  });
  try {
    for (const locale of ["en", "fr", "de", "ro"] as Locale[]) {
      expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale } })).ok()).toBeTruthy();
      await page.goto("/admin/audit");
      const rows = page.locator(".audit-evidence tbody tr");
      await expect(rows).toHaveCount(4);
      await expect(rows.nth(0)).toContainText(`${auditCopy[locale].ticket} 46`);
      await expect(rows.nth(0)).toContainText(auditCopy[locale].prepared);
      await expect(rows.nth(1)).toContainText(auditCopy[locale].rejected);
      await expect(rows.nth(2)).toContainText(auditCopy[locale].failed);
      await expect(rows.nth(3)).toContainText(auditCopy[locale].cli);
      await expect(rows.nth(3)).toContainText(`${auditCopy[locale].job} job-48`);
      await expect(rows.nth(3)).toContainText(auditCopy[locale].applied);
    }
  } finally {
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: original.language ?? "en" } });
  }
});

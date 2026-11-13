/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage, trackScopeReads } from "./polling";

const deferred = () => { let resolve!: () => void; const promise = new Promise<void>(done => { resolve = done; }); return { promise, resolve }; };
const monitoring = (page: Page) => page.getByRole("button", { name: /^(Activate|Pause) monitoring$/ });
async function directory(page: Page) { return (await (await page.request.get("/api/v1/projects")).json()) as Array<any>; }

test.beforeEach(async ({ context, request, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  expect((await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
});
test.afterEach(async ({ page, request }) => {
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});

for (const view of ["Statistics", "History", "Jobs"] as const) test(`App result supersedes held ${view} evidence without removing its view`, async ({ page }) => {
  const operation = deferred(), evidence = deferred();
  const id = (await directory(page)).find(project => project.name === "alpha").id;
  let polled = 0;
  for (const action of ["pause", "resume"]) await page.route(`**/operations/${action}`, route => route.fulfill({ json: { id: 7780, status: "pending" } }));
  await page.route("**/operations/7780", async route => { polled++; await operation.promise; await route.fulfill({ json: { id: 7780, status: "succeeded" } }).catch(() => {}); });
  await page.goto(`/projects/${id}`); await monitoring(page).click();
  await expect.poll(() => polled).toBe(1);
  await page.getByRole("tab", { name: view, exact: true }).click();
  if (view === "Jobs") await page.getByRole("tab", { name: "Jobs", exact: true }).last().click();
  const surface = page.locator(view === "Statistics" ? ".statistics-evidence" : view === "History" ? ".audit-evidence" : ".action-jobs-table");
  await expect(surface).toBeVisible();
  if (view === "History") {
    // The audit panel exists during its first read; visibility alone is not a
    // validated baseline, and visible-return correctly joins in-flight work.
    await expect(page.locator(".audit-evidence .refresh-feedback time")).toHaveCount(1);
    await expect(page.locator(".jobs-list-refresh .refresh-feedback time")).toHaveCount(1);
  }
  await expect(page.locator('.refresh-feedback[data-refreshing="true"]')).toHaveCount(0);
  const node = await surface.elementHandle();
  if (view === "Statistics") await page.getByText("Export CSV", { exact: true }).click();
  const patterns = view === "Statistics" ? ["**/api/v1/projects/*/metrics?*", "**/api/v1/projects/*/usage?*"] :
    view === "History" ? ["**/api/v1/audit-page?*", "**/api/v1/jobs-page?*"] : ["**/api/v1/jobs-page?*", "**/api/v1/projects/*/usage?*"];
  const counts = patterns.map(() => 0), cancelled = patterns.map(() => 0);
  page.on("requestfailed", request => {
    const url = request.url();
    const index = view === "Statistics" ? url.includes("/metrics?") ? 0 : url.includes("/usage?") ? 1 : -1 :
      view === "History" ? url.includes("/audit-page?") ? 0 : url.includes("/jobs-page?") ? 1 : -1 :
      url.includes("/jobs-page?") ? 0 : url.includes("/usage?") ? 1 : -1;
    if (index >= 0) cancelled[index]++;
  });
  for (const [index, pattern] of patterns.entries()) await page.route(pattern, async route => {
    const count = ++counts[index]; const response = await route.fetch();
    if (count === 1) await evidence.promise;
    await route.fulfill({ response }).catch(() => {});
  });
  try {
    await revalidateVisiblePage(page);
    await expect.poll(() => counts).toEqual([1, 1]);
    operation.resolve();
    await expect.poll(() => cancelled).toEqual([1, 1]);
    await expect.poll(() => counts).toEqual([2, 2]);
    await expect(surface).toBeVisible();
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
    if (view === "Statistics") await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
    evidence.resolve();
    await expect(surface).toBeVisible();
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
  } finally { operation.resolve(); evidence.resolve(); }
});

for (const ownCommand of [false, true]) test(`App result preserves open job detail and ${ownCommand ? "its pending command barrier" : "requires both post-result authority reads"}`, async ({ page }) => {
  const external = deferred(), command = deferred(), detailRead = deferred();
  const id = (await directory(page)).find(project => project.name === "alpha").id;
  let observed = 0, commandReads = 0, lists = 0, details = 0, writes = 0;
  for (const action of ["pause", "resume"]) await page.route(`**/operations/${action}`, route => route.fulfill({ json: { id: 7785, status: "pending" } }));
  await page.route("**/operations/7785", async route => { observed++; await external.promise; await route.fulfill({ json: { id: 7785, status: "succeeded" } }).catch(() => {}); });
  await page.route("**/operations/7786", async route => { commandReads++; await command.promise; await route.fulfill({ json: { id: 7786, status: "succeeded" } }).catch(() => {}); });
  await page.route("**/operations/cancel", route => { writes++; return route.fulfill({ json: { id: 7786, status: "pending" } }); });
  await page.goto(`/projects/${id}`); await monitoring(page).click(); await expect.poll(() => observed).toBe(1);
  await page.getByRole("tab", { name: "Jobs", exact: true }).click();
  await page.getByRole("tab", { name: "Jobs", exact: true }).last().click();
  await page.getByRole("combobox", { name: "Rows per page", exact: true }).selectOption("all");
  await page.locator('.action-jobs-table a[href*="ux-working"]').click();
  const detail = page.locator(".detail-panel"), cancel = detail.getByRole("button", { name: "Cancel", exact: true });
  await expect(cancel).toBeEnabled();
  const node = await detail.elementHandle();
  await detail.locator("details").first().locator(":scope > summary").click();
  await page.route("**/api/v1/jobs-page?*", async route => { lists++; const response = await route.fetch(); await route.fulfill({ response }).catch(() => {}); });
  await page.route("**/api/v1/jobs/*/ux-working", async route => { details++; const response = await route.fetch(); await detailRead.promise; await route.fulfill({ response }).catch(() => {}); });
  try {
    if (ownCommand) {
      page.once("dialog", dialog => dialog.accept()); await cancel.click();
      await expect.poll(() => commandReads).toBe(1);
    }
    const metadata = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
    external.resolve(); await (await metadata).finished();
    await expect(page.locator("div.notice").filter({ hasText: "#7785" })).toContainText("succeeded");
    if (ownCommand) {
      expect({ lists, details }).toEqual({ lists: 0, details: 0 });
      await expect(cancel).toBeDisabled();
      await revalidateVisiblePage(page);
      expect({ lists, details }).toEqual({ lists: 0, details: 0 });
      command.resolve();
      await expect(page.locator(".command-result")).toContainText("#7786");
    }
    await expect.poll(() => lists).toBe(1); await expect.poll(() => details).toBe(1);
    await expect(page.locator(".jobs-list-refresh .refresh-feedback")).toHaveAttribute("data-refreshing", "false");
    // A valid list alone cannot authorize commands while detail is pre-result.
    await expect(cancel).toBeDisabled();
    await cancel.evaluate((button: HTMLButtonElement) => button.click());
    expect(writes).toBe(ownCommand ? 1 : 0);
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
    await expect(detail.locator("details").first()).toHaveAttribute("open", "");
    detailRead.resolve();
    await expect(cancel).toBeEnabled();
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
  } finally { external.resolve(); command.resolve(); detailRead.resolve(); }
});

for (const action of ["monitoring", "archive", "delete"] as const) test(`App held ${action} submission cannot publish across project navigation`, async ({ page }) => {
  const items = await directory(page), alpha = items.find(project => project.name === "alpha"), beta = items.find(project => project.id !== alpha.id);
  if (action === "delete") {
    alpha.archived = true; alpha.paused = true;
    await page.route("**/api/v1/projects", route => route.fulfill({ json: items }));
  }
  const held = deferred(); let submitted = 0, cancelled = 0, tracked = 0;
  const suffix = action === "monitoring" ? /\/operations\/(pause|resume)$/ : action === "archive" ? /\/archive$/ : /\/delete$/;
  await page.route("**/api/v1/projects/**", async route => {
    if (!suffix.test(route.request().url())) return route.continue();
    submitted++; await held.promise;
    await route.fulfill({ json: action !== "archive" ? { id: 7781, status: "pending" } : { ...alpha, archived: true } }).catch(() => {});
  });
  await page.route("**/operations/7781", route => { tracked++; return route.fulfill({ json: { id: 7781, status: "succeeded" } }); });
  page.on("requestfailed", request => { if (suffix.test(request.url())) cancelled++; });
  await page.goto(`/projects/${alpha.id}`);
  if (action === "monitoring") await monitoring(page).click();
  else if (action === "archive") await page.getByRole("button", { name: "Archive project", exact: true }).click();
  else {
    await page.getByRole("button", { name: "Delete project", exact: true }).click();
    await page.getByRole("dialog").locator("input:not([type=checkbox])").fill(alpha.name);
    await page.getByRole("dialog").getByRole("button", { name: "Delete project", exact: true }).click();
  }
  await expect.poll(() => submitted).toBe(1);
  try {
    if (action === "delete") await page.getByRole("dialog").getByRole("button", { name: "Cancel", exact: true }).click();
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await page.getByRole("link", { name: beta.display_name, exact: true }).click();
    await expect.poll(() => cancelled).toBe(1);
    held.resolve();
    await expect(page.locator("div.notice")).toHaveCount(0);
    expect(tracked).toBe(0);
    await expect(monitoring(page)).toBeEnabled();
  } finally { held.resolve(); }
});

for (const transition of ["archived", "removed", "failed"] as const) test(`App ${transition} project metadata cancels old submission authority`, async ({ page }) => {
  const items = await directory(page), alpha = items.find(project => project.name === "alpha"), held = deferred();
  let writes = 0, cancelled = 0, metadataReads = 0;
  for (const action of ["pause", "resume"]) await page.route(`**/operations/${action}`, async route => {
    writes++; await held.promise;
    await route.fulfill({ status: 503, json: { detail: { code: "arbitrary_old_error" } } }).catch(() => {});
  });
  page.on("requestfailed", request => { if (/\/operations\/(pause|resume)$/.test(request.url())) cancelled++; });
  await page.goto(`/projects/${alpha.id}`); await monitoring(page).click(); await expect.poll(() => writes).toBe(1);
  if (transition === "archived") alpha.archived = true;
  const changed = transition === "removed" ? items.filter(project => project.id !== alpha.id) : items;
  await page.route("**/api/v1/projects", route => {
    metadataReads++;
    return transition === "failed" ? route.fulfill({ status: 503, json: { detail: { code: "config_corrupt" } } }) : route.fulfill({ json: changed });
  });
  try {
    await revalidateVisiblePage(page); await expect.poll(() => cancelled).toBe(1);
    if (transition === "removed") {
      await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();
      await expect(page.getByRole("alert")).toContainText("The project was not found");
      await expect.poll(() => metadataReads).toBe(2); // new directory context owns one initial read
    }
    held.resolve();
    await expect(page.locator("div.notice")).toHaveCount(0);
    await expect(monitoring(page)).toHaveCount(0);
    await expect(page.getByText(/arbitrary_old_error/)).toHaveCount(0);
    expect(writes).toBe(1); expect(metadataReads).toBe(transition === "removed" ? 2 : 1);
  } finally { held.resolve(); }
});

for (const view of ["overview", "summary", "jobs"] as const) test(`Live removed project leaves no ${view} detail or orphaned selector authority`, async ({ page }) => {
  const items = await directory(page), alpha = items.find(project => project.name === "alpha");
  await page.goto(view === "overview" ? `/overview?project=${alpha.id}` : view === "summary" ? `/projects/${alpha.id}` : `/jobs?project=${alpha.id}&run=ux-working`);
  const surface = page.locator(view === "jobs" ? ".detail-panel" : ".overview-jobs-table").first();
  await expect(surface).toBeVisible();
  await page.route("**/api/v1/projects", route => route.fulfill({ json: items.filter(project => project.id !== alpha.id) }));
  await revalidateVisiblePage(page);
  if (view === "summary") {
    await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();
    await expect(page.getByRole("alert")).toContainText("The project was not found");
  }
  await expect(page.locator(".detail-panel")).toHaveCount(0);
  await expect(page.locator(`select option[value="${alpha.id}"]`)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Cancel", exact: true })).toHaveCount(0);
  await expect(monitoring(page)).toHaveCount(0);
});

test("Live archived project retains job detail while revoking operational controls", async ({ page }) => {
  const items = await directory(page), alpha = items.find(project => project.name === "alpha");
  await page.goto(`/jobs?project=${alpha.id}&run=ux-working`);
  const detail = page.locator(".detail-panel"), cancel = detail.getByRole("button", { name: "Cancel", exact: true });
  await expect(cancel).toBeEnabled(); const node = await detail.elementHandle();
  alpha.archived = true;
  await page.route("**/api/v1/projects", route => route.fulfill({ json: items }));
  await revalidateVisiblePage(page);
  await expect(cancel).toBeDisabled();
  expect(await node!.evaluate(element => element.isConnected)).toBe(true);
  let writes = 0;
  page.on("request", request => { if (request.method() === "POST" && request.url().includes("/operations/")) writes++; });
  await cancel.evaluate((button: HTMLButtonElement) => button.click()); expect(writes).toBe(0);
});

test("App archive success notice is scoped and can be explicitly dismissed", async ({ page }) => {
  const now = Date.now();
  await page.clock.install({ time: new Date(now) });
  await page.clock.pauseAt(new Date(now + 1000));
  const items = await directory(page), alpha = items.find(project => project.name === "alpha");
  await page.goto(`/projects/${alpha.id}`);
  await expect(monitoring(page)).toBeVisible();
  await page.route("**/api/v1/projects/*/archive", route => route.fulfill({ json: { ...alpha, archived: true } }));
  await page.getByRole("button", { name: "Archive project", exact: true }).click();
  const notice = page.locator("div.notice");
  await expect(notice).toContainText("Project archived");
  await notice.getByRole("button", { name: "Close", exact: true }).click();
  await expect(notice).toHaveCount(0);
});

test("App malformed archive result cannot announce success and still revalidates metadata", async ({ page }) => {
  const settleScope = trackScopeReads(page);
  const items = await directory(page), alpha = items.find(project => project.name === "alpha");
  await page.goto(`/projects/${alpha.id}`);
  await expect(monitoring(page)).toBeVisible(); await settleScope();
  let reads = 0;
  await page.route("**/api/v1/projects", route => { reads++; return route.fulfill({ json: items }); });
  await page.route("**/api/v1/projects/*/archive", route => route.fulfill({ json: { ...alpha, archived: "yes" } }));
  await page.getByRole("button", { name: "Archive project", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("unexpected response");
  await expect(page.locator("div.notice")).toHaveCount(0);
  await expect.poll(() => reads).toBe(1);
  await expect(monitoring(page)).toBeEnabled();
});

test("App delete review keeps unchanged draft but latches changed project authority invalid", async ({ page }) => {
  const items = await directory(page), alpha = items.find(project => project.name === "alpha");
  alpha.archived = true; alpha.paused = true;
  await page.route("**/api/v1/projects", route => route.fulfill({ json: items }));
  let writes = 0;
  await page.route("**/api/v1/projects/*/delete", route => { writes++; return route.fulfill({ json: { id: 7782, status: "succeeded" } }); });
  await page.goto(`/projects/${alpha.id}`);
  await page.getByRole("button", { name: "Delete project", exact: true }).click();
  const dialog = page.getByRole("dialog"), input = dialog.locator("input:not([type=checkbox])"), submit = dialog.getByRole("button", { name: "Delete project", exact: true });
  await input.fill(alpha.name); await input.focus();
  await revalidateVisiblePage(page);
  await expect(input).toHaveValue(alpha.name); await expect(input).toBeFocused(); await expect(submit).toBeEnabled();
  alpha.name = "alpha-renamed";
  await revalidateVisiblePage(page);
  await expect(dialog).toBeVisible(); await expect(submit).toBeDisabled();
  await expect(input).toHaveValue("alpha");
  alpha.name = "alpha";
  await revalidateVisiblePage(page);
  await expect(submit).toBeDisabled();
  await submit.evaluate((button: HTMLButtonElement) => button.click());
  expect(writes).toBe(0);
});

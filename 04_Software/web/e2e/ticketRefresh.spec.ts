/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage } from "./polling";

const deferred = () => { let resolve!: () => void; const promise = new Promise<void>(done => { resolve = done; }); return { promise, resolve }; };
const hidden = (page: Page) => page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }); document.dispatchEvent(new Event("visibilitychange")); });
const row = (page: Page, iid: number) => page.locator("tr.ticket-row").filter({ has: page.getByRole("cell", { name: `#${iid}`, exact: true }) });
const notice = (page: Page) => page.locator(".ticket-notice");
const ticket = (iid: number) => ({ iid, title: `Quiet ticket ${iid}`, description: "Retained ticket body", labels: ["agent-ready", "P2"], author: "author", web_url: "https://forge.invalid/issues/" + iid,
  updated_at: "2026-11-01T10:00:00Z", startable: true, reason: null, job: null, can_start: true, blocked_by: null, adds_ready_label: false, needs_priority: false });

async function open(page: Page, global = false) {
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const project = projects.find((item: { name: string }) => item.name === "alpha");
  let ticketReads = 0, commentReads = 0;
  await page.route("**/api/v1/projects/*/tickets", route => {
    ticketReads++;
    return route.fulfill({ json: { read_at: "2026-11-01T10:00:00Z", truncated: false, ready_label: "agent-ready", priority_labels: ["P2"], tickets: route.request().url().includes(`/${project.id}/`) ? [ticket(21), ticket(22)] : [] } });
  });
  await page.route("**/api/v1/projects/*/tickets/*/comments", route => { commentReads++; return route.fulfill({ json: { iid: Number(route.request().url().split("/").at(-2)), comments: [{ author: "author", created_at: "2026-11-01T10:00:00Z", body: "Retained comment" }] } }); });
  await page.goto(global ? "/jobs" : `/projects/${project.id}/jobs`);
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  await expect(row(page, 21)).toBeVisible();
  await row(page, 21).getByRole("button", { name: "Details", exact: true }).click();
  await expect(page.locator(".ticket-comments")).toContainText("Retained comment");
  return { project, projects, counts: () => [ticketReads, commentReads] };
}

test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
});

for (const global of [false, true]) test(`Tickets ${global ? "global" : "project"} operation reads coalesce and revalidate metadata without forge rereads`, async ({ page }) => {
  await page.clock.install();
  const fixture = await open(page, global), counts = fixture.counts();
  const first = deferred(), second = deferred(); let reads = 0, metadata = 0;
  await page.route("**/api/v1/projects", route => { metadata++; return route.fulfill({ json: fixture.projects }); });
  await page.route("**/tickets/21/start", route => route.fulfill({ json: { operation_id: 7710, status: "pending", labels_added: [] } }));
  await page.route("**/operations/7710", async route => {
    const index = ++reads;
    await (index === 1 ? first.promise : second.promise);
    await route.fulfill({ json: { id: 7710, status: index === 1 ? "running" : "succeeded" } }).catch(() => {});
  });
  await row(page, 21).getByRole("button", { name: "Start", exact: true }).click();
  await expect.poll(() => reads).toBe(1);
  const control = page.getByRole("combobox", { name: "Body display", exact: true });
  await control.focus(); const node = await control.elementHandle();
  try {
    await page.clock.runFor(6000); await revalidateVisiblePage(page);
    expect(reads).toBe(1);
    await hidden(page); await page.clock.runFor(10000); expect(reads).toBe(1);
    first.resolve(); await expect(notice(page)).toContainText("running");
    expect(reads).toBe(1); // A status change is not a new owner/immediate read.
    await revalidateVisiblePage(page); await expect.poll(() => reads).toBe(2);
    await expect(control).toBeFocused();
    await hidden(page); const beforeResult = metadata;
    second.resolve(); await expect(notice(page)).toContainText("· finished");
    await expect.poll(() => metadata).toBe(beforeResult + 1);
    expect(fixture.counts()).toEqual(counts);
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
    await expect(control).toBeFocused();
    await expect(page.locator(".ticket-comments")).toContainText("Retained comment");
    await page.clock.runFor(10000); expect(reads).toBe(2);
  } finally { first.resolve(); second.resolve(); }
});

for (const action of ["start", "stop"] as const) test(`Tickets immediate ${action} result revalidates metadata without operation or forge polling`, async ({ page }) => {
  await page.clock.install(); const fixture = await open(page), counts = fixture.counts();
  let metadata = 0, operationReads = 0;
  await page.route("**/api/v1/projects", route => { metadata++; return route.fulfill({ json: fixture.projects }); });
  await page.route("**/api/v1/operations/*", route => { operationReads++; return route.fulfill({ json: { id: 7714, status: "succeeded" } }); });
  await page.route(`**/tickets/21/${action}`, route => route.fulfill({ json: action === "start"
    ? { operation_id: 7714, status: "succeeded", labels_added: [] }
    : { cancel_operation_id: null, ready_label: "removed", ready_label_error: null } }));
  await row(page, 21).getByRole("button", { name: action === "start" ? "Start" : "Stop", exact: true }).click();
  if (action === "stop") await page.getByRole("button", { name: "Stop ticket", exact: true }).click();
  await expect.poll(() => metadata).toBe(1);
  await expect(notice(page)).toContainText(action === "start" ? "· finished" : "Ready label removed.");
  await hidden(page); await page.clock.runFor(10000);
  expect(metadata).toBe(1); expect(operationReads).toBe(0); expect(fixture.counts()).toEqual(counts);
});

test("Tickets operation deadline releases its slot, ignores expired success and cancels on exit", async ({ page }) => {
  await page.clock.install(); await open(page);
  const expired = deferred(), current = deferred(); let reads = 0, cancelled = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/operations/7711")) cancelled++; });
  await page.route("**/tickets/21/start", route => route.fulfill({ json: { operation_id: 7711, status: "pending", labels_added: [] } }));
  await page.route("**/operations/7711", async route => { const index = ++reads; await (index === 1 ? expired.promise : current.promise); await route.fulfill({ json: { id: 7711, status: "succeeded" } }).catch(() => {}); });
  await row(page, 21).getByRole("button", { name: "Start", exact: true }).click();
  await expect.poll(() => reads).toBe(1);
  try {
    await hidden(page); await page.clock.runFor(30001);
    await expect(notice(page).getByRole("alert")).toBeVisible();
    await expect(notice(page)).toContainText("· queued");
    await expect.poll(() => cancelled).toBe(1);
    await revalidateVisiblePage(page); await expect.poll(() => reads).toBe(2);
    expired.resolve(); await expect(notice(page)).toContainText("· queued");
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await expect.poll(() => cancelled).toBe(2);
    await page.clock.runFor(10000); expect(reads).toBe(2);
  } finally { expired.resolve(); current.resolve(); }
});

test("Tickets malformed operation identity is not completion and valid retry does not reread forge", async ({ page }) => {
  await page.clock.install(); const fixture = await open(page), counts = fixture.counts(); let reads = 0;
  await page.route("**/tickets/21/start", route => route.fulfill({ json: { operation_id: 7712, status: "pending", labels_added: [] } }));
  await page.route("**/operations/7712", route => { reads++; return route.fulfill({ json: { id: 7713, status: "succeeded" } }); });
  await row(page, 21).getByRole("button", { name: "Start", exact: true }).click();
  await expect(notice(page).getByRole("alert")).toBeVisible(); await expect(notice(page)).toContainText("· queued");
  await page.route("**/operations/7712", route => { reads++; return route.fulfill({ json: { id: 7712, status: "failed", reason: "at_capacity" } }); });
  await page.clock.runFor(2000);
  await expect(notice(page)).toContainText("all execution slots are busy");
  await expect(notice(page).getByRole("alert")).toHaveCount(0);
  expect(reads).toBe(2); expect(fixture.counts()).toEqual(counts);
});

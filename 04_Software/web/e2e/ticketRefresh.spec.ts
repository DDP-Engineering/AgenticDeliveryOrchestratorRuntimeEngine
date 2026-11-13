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

async function open(page: Page, global = false, review = false, readLabel = "Read tickets", detailsLabel = "Details") {
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const project = projects.find((item: { name: string }) => item.name === "alpha");
  let ticketReads = 0, commentReads = 0;
  await page.route("**/api/v1/projects/*/tickets", route => {
    ticketReads++;
    return route.fulfill({ json: { read_at: "2026-11-01T10:00:00Z", truncated: false, ready_label: "agent-ready", priority_labels: ["P2"], tickets: route.request().url().includes(`/${project.id}/`) ? [{ ...ticket(21), ...(review ? { labels: [], startable: false, reason: "missing_ready_label", adds_ready_label: true } : {}) }, ticket(22)] : [] } });
  });
  await page.route("**/api/v1/projects/*/tickets/*/comments", route => { commentReads++; return route.fulfill({ json: { iid: Number(route.request().url().split("/").at(-2)), comments: [{ author: "author", created_at: "2026-11-01T10:00:00Z", body: "Retained comment" }] } }); });
  await page.goto(global ? "/jobs" : `/projects/${project.id}/jobs`);
  await page.getByRole("button", { name: readLabel, exact: true }).click();
  await expect(row(page, 21)).toBeVisible();
  await row(page, 21).getByRole("button", { name: detailsLabel, exact: true }).click();
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

for (const action of ["start", "stop"] as const) test(`Tickets ${action} review survives unchanged metadata but latches changed authority invalid`, async ({ page }) => {
  await page.clock.install(); const fixture = await open(page, false, action === "start"), counts = fixture.counts();
  let projects = fixture.projects, writes = 0;
  await page.route("**/api/v1/projects", route => route.fulfill({ json: projects }));
  await page.route(`**/tickets/21/${action}`, route => { writes++; return route.abort(); });
  await row(page, 21).getByRole("button", { name: action === "start" ? "Start" : "Stop", exact: true }).click();
  const dialog = page.getByRole("alertdialog"), submit = dialog.getByRole("button", { name: action === "start" ? "Add labels and start" : "Stop ticket", exact: true });
  await submit.focus(); const node = await submit.elementHandle();
  await revalidateVisiblePage(page);
  await expect(submit).toBeEnabled(); await expect(submit).toBeFocused();
  expect(await node!.evaluate(element => element.isConnected)).toBe(true);
  projects = fixture.projects.map((item: { id: string }) => item.id === fixture.project.id ? { ...item, archived: true } : item);
  await revalidateVisiblePage(page);
  await expect(submit).toBeDisabled();
  await expect(dialog.getByRole("alert")).toContainText("Read tickets again");
  await expect(page.locator(".ticket-comments")).toContainText("Retained comment");
  projects = fixture.projects;
  await revalidateVisiblePage(page);
  await expect(submit).toBeDisabled(); // Restoring an identity cannot restore an old review.
  expect(writes).toBe(0); expect(fixture.counts()).toEqual(counts);
  await dialog.getByRole("button", { name: action === "start" ? "Cancel" : "Keep running", exact: true }).click();
  await expect(row(page, 21).getByRole("button", { name: action === "start" ? "Start" : "Stop", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  await expect(row(page, 21).getByRole("button", { name: action === "start" ? "Start" : "Stop", exact: true })).toBeEnabled();
});

test("Tickets removed global project cancels comments and never restores captured bodies", async ({ page }) => {
  await page.clock.install(); const fixture = await open(page, true), counts = fixture.counts();
  const held = deferred(); let reads = 0, cancelled = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/tickets/22/comments")) cancelled++; });
  await page.route("**/tickets/22/comments", async route => { reads++; await held.promise; await route.fulfill({ json: { iid: 22, comments: [{ author: "old", created_at: "now", body: "Obsolete private comment" }] } }).catch(() => {}); });
  await row(page, 22).getByRole("button", { name: "Details", exact: true }).click(); await expect.poll(() => reads).toBe(1);
  try {
    await page.route("**/api/v1/projects", route => route.fulfill({ json: fixture.projects.filter((item: { id: string }) => item.id !== fixture.project.id) }));
    await revalidateVisiblePage(page);
    await expect(row(page, 21)).toHaveCount(0); await expect(row(page, 22)).toHaveCount(0);
    await expect(page.locator(".ticket-workspace").getByRole("status")).toContainText("The project was not found, or you do not have access to it.");
    await expect.poll(() => cancelled).toBe(1);
    held.resolve();
    await page.route("**/api/v1/projects", route => route.fulfill({ json: fixture.projects }));
    await revalidateVisiblePage(page);
    await expect(row(page, 21)).toHaveCount(0); await expect(page.getByText("Obsolete private comment")).toHaveCount(0);
    expect(fixture.counts()).toEqual(counts);
    await page.getByRole("button", { name: "Read tickets", exact: true }).click(); await expect(row(page, 21)).toBeVisible();
  } finally { held.resolve(); }
});

test("Tickets explicit list reads cancel on navigation without late publication", async ({ page }) => {
  await page.clock.install(); await open(page);
  const held = deferred(); let reads = 0, cancelled = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/tickets")) cancelled++; });
  await page.route("**/api/v1/projects/*/tickets", async route => { reads++; await held.promise; await route.fulfill({ json: {} }).catch(() => {}); });
  await page.getByRole("button", { name: "Read tickets", exact: true }).click(); await expect.poll(() => reads).toBe(1);
  try {
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await expect.poll(() => cancelled).toBe(1);
    held.resolve(); await page.clock.runFor(5000);
    await expect(page.locator(".ticket-workspace")).toHaveCount(0); expect(reads).toBe(1);
  } finally { held.resolve(); }
});

test("Tickets changed authority cancels submission and ignores its late result", async ({ page }) => {
  await page.clock.install(); const fixture = await open(page);
  const held = deferred(); let writes = 0, cancelled = 0, metadata = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/tickets/21/start")) cancelled++; });
  await page.route("**/tickets/21/start", async route => { writes++; await held.promise; await route.fulfill({ json: { operation_id: 7799, status: "succeeded", labels_added: [] } }).catch(() => {}); });
  await row(page, 21).getByRole("button", { name: "Start", exact: true }).click(); await expect.poll(() => writes).toBe(1);
  try {
    await page.route("**/api/v1/projects", route => { metadata++; return route.fulfill({ json: fixture.projects.map((item: { id: string }) => item.id === fixture.project.id ? { ...item, archived: true } : item) }); });
    await revalidateVisiblePage(page); await expect.poll(() => cancelled).toBe(1);
    held.resolve(); await page.clock.runFor(1000);
    await expect(notice(page)).toHaveCount(0); expect(metadata).toBe(1);
    await expect(row(page, 21).getByRole("button", { name: "Start", exact: true })).toBeDisabled();
  } finally { held.resolve(); }
});

test("Tickets explicit reads have finite deadlines and comments coalesce until explicit recovery", async ({ page }) => {
  await page.clock.install(); const fixture = await open(page), counts = fixture.counts();
  const listHold = deferred(), commentHold = deferred(); let listReads = 0, comments = 0;
  await page.route("**/api/v1/projects/*/tickets", async route => { listReads++; await listHold.promise; await route.fulfill({ json: {} }).catch(() => {}); });
  await page.getByRole("button", { name: "Read tickets", exact: true }).click(); await expect.poll(() => listReads).toBe(1);
  try {
    await hidden(page); await page.clock.runFor(30001);
    await expect(page.locator(".ticket-workspace .alert")).toBeVisible(); await expect(row(page, 21)).toHaveCount(0);
    listHold.resolve();
    await page.unroute("**/api/v1/projects/*/tickets"); // Restore the original successful explicit fixture.
    await page.route("**/api/v1/projects/*/tickets", route => route.fulfill({ json: { read_at: "2026-11-01T11:00:00Z", truncated: false, ready_label: "agent-ready", priority_labels: ["P2"], tickets: [ticket(21), ticket(22)] } }));
    await page.getByRole("button", { name: "Read tickets", exact: true }).click(); await expect(row(page, 21)).toBeVisible();
    await page.route("**/tickets/21/comments", async route => { comments++; await commentHold.promise; await route.fulfill({ json: { iid: 21, comments: [] } }).catch(() => {}); });
    const details = row(page, 21).getByRole("button", { name: "Details", exact: true });
    await details.click(); await expect.poll(() => comments).toBe(1);
    await row(page, 21).getByRole("button", { name: "Hide details", exact: true }).click(); await details.click(); expect(comments).toBe(1);
    await page.clock.runFor(30001); await expect(page.locator(".ticket-detail .alert")).toBeVisible();
    commentHold.resolve();
    await page.route("**/tickets/21/comments", route => { comments++; return route.fulfill({ json: { iid: 21, comments: [{ author: "new", created_at: "now", body: "Explicit recovery" }] } }); });
    await row(page, 21).getByRole("button", { name: "Hide details", exact: true }).click(); await details.click();
    await expect(page.locator(".ticket-comments")).toContainText("Explicit recovery"); expect(comments).toBe(2);
    await page.clock.runFor(10000); expect(listReads).toBe(1); expect(fixture.counts()).toEqual(counts);
  } finally { listHold.resolve(); commentHold.resolve(); }
});

test("Tickets reject corrupt explicit evidence at the list and comment boundary", async ({ page }) => {
  await open(page);
  await page.route("**/tickets/22/comments", route => route.fulfill({ json: { iid: 99, comments: [{ author: "other", created_at: "now", body: "Foreign comment" }] } }));
  await row(page, 22).getByRole("button", { name: "Details", exact: true }).click();
  await expect(page.locator(".ticket-detail .alert")).toBeVisible();
  await expect(page.getByText("Foreign comment")).toHaveCount(0);
  await expect(row(page, 21).getByRole("button", { name: "Start", exact: true })).toBeEnabled();
  await page.route("**/api/v1/projects/*/tickets", route => route.fulfill({ json: { read_at: "now", truncated: false, ready_label: "agent-ready", priority_labels: ["P2"], tickets: [{ ...ticket(21), can_start: "yes" }] } }));
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  await expect(page.locator(".ticket-workspace > section > .alert")).toBeVisible();
  await expect(page.locator("tr.ticket-row")).toHaveCount(0);
  await expect(page.getByText("Retained ticket body")).toHaveCount(0);
});

test("Tickets changed-review feedback is localized and keyboard accessible in both narrow themes", async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 390, height: 850 });
  let language = "en", theme = "light";
  await page.route("**/api/v1/me/preferences", route => route.fulfill({ json: { language, theme, ticket_body_mode: "rendered" } }));
  for (const labels of [
    ["en", "Read tickets", "Details", "Start", "Add labels and start", "Project authority changed", "Cancel"],
    ["fr", "Lire les tickets", "Détails", "Démarrer", "Ajouter les étiquettes et démarrer", "Les droits du projet ont changé", "Annuler"],
    ["de", "Tickets lesen", "Details", "Starten", "Labels hinzufügen und starten", "Die Projektberechtigung hat sich geändert", "Abbrechen"],
    ["ro", "Citește tichetele", "Detalii", "Pornește", "Adaugă etichetele și pornește", "Drepturile proiectului s-au schimbat", "Renunță"],
  ]) for (theme of ["light", "dark"]) {
    language = labels[0];
    await page.unroute("**/api/v1/projects");
    const fixture = await open(page, false, true, labels[1], labels[2]);
    await row(page, 21).getByRole("button", { name: labels[3], exact: true }).click();
    const dialog = page.getByRole("alertdialog"), submit = dialog.getByRole("button", { name: labels[4], exact: true });
    await page.route("**/api/v1/projects", route => route.fulfill({ json: fixture.projects.map((item: { id: string }) => item.id === fixture.project.id ? { ...item, archived: true } : item) }));
    await revalidateVisiblePage(page);
    await expect(dialog.getByRole("alert")).toContainText(labels[5]); await expect(submit).toBeDisabled();
    const cancel = dialog.getByRole("button", { name: labels[6], exact: true }); await cancel.focus(); await expect(cancel).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await cancel.press("Enter"); await expect(dialog).toHaveCount(0);
  }
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

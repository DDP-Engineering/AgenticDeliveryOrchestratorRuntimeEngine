/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage } from "./polling";
import { messages } from "../src/i18n";

async function hidden(page: Page) {
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }); document.dispatchEvent(new Event("visibilitychange")); });
}

const deferred = () => { let resolve!: () => void; const promise = new Promise<void>(done => { resolve = done; }); return { promise, resolve }; };
const grants = (granted = false) => ({ developers: [{ id: 9001, username: "access_target", disabled: false, granted }] });
const confirmation = (page: Page) => page.getByRole("region", { name: "Review access change", exact: true });
const apply = (page: Page) => confirmation(page).getByRole("button", { name: "Apply reviewed access", exact: true });
const grant = (page: Page) => page.getByRole("button", { name: "Grant access: access_target", exact: true });

test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
});

async function access(page: Page) {
  await page.route("**/api/v1/projects/*/access", route => route.fulfill({ json: grants() }));
  await page.goto("/projects/alpha/access");
  await expect(grant(page)).toBeVisible();
}

test("Access held reads coalesce, preserve review focus and stop on navigation", async ({ page }) => {
  await page.clock.install();
  await access(page);
  await grant(page).click();
  const button = await apply(page).elementHandle();
  await apply(page).focus();
  const held = deferred(); let reads = 0, cancelled = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/access")) cancelled++; });
  await page.route("**/api/v1/projects/*/access", async route => { reads++; await held.promise; await route.fulfill({ json: grants() }).catch(() => {}); });
  try {
    await revalidateVisiblePage(page);
    await expect.poll(() => reads).toBe(1);
    await page.clock.runFor(15000);
    await revalidateVisiblePage(page);
    expect(reads).toBe(1);
    await expect(confirmation(page)).toBeVisible();
    await expect(apply(page)).toBeFocused();
    expect(await button!.evaluate(node => node.isConnected)).toBe(true);
    await page.getByRole("tab", { name: "Summary", exact: true }).click();
    await expect.poll(() => cancelled).toBe(1);
    await page.clock.runFor(45000);
    expect(reads).toBe(1);
  } finally { held.resolve(); }
});

test("Access changed authority invalidates review without closing it or reviving on old values", async ({ page }) => {
  await access(page);
  await grant(page).click();
  await page.route("**/api/v1/projects/*/access", route => route.fulfill({ json: grants(true) }));
  await revalidateVisiblePage(page);
  await expect(confirmation(page)).toBeVisible();
  await expect(apply(page)).toBeDisabled();
  await expect(page.getByText("This review is no longer current. Correct the choices and review again.", { exact: true })).toBeVisible();
  await page.route("**/api/v1/projects/*/access", route => route.fulfill({ json: grants() }));
  await revalidateVisiblePage(page);
  await expect(apply(page)).toBeDisabled();
  await confirmation(page).getByRole("button", { name: "Correct access", exact: true }).click();
  await grant(page).click();
  await expect(apply(page)).toBeEnabled();
});

test("Access live project archival invalidates an unchanged grant review", async ({ page }) => {
  await access(page); await grant(page).click();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  projects.find((project: { name: string }) => project.name === "alpha").archived = true;
  await page.route("**/api/v1/projects", route => route.fulfill({ json: projects }));
  await revalidateVisiblePage(page);
  await expect(apply(page)).toBeDisabled();
  await expect(confirmation(page)).toBeVisible();
  await expect(page.getByText("This review is no longer current. Correct the choices and review again.", { exact: true })).toBeVisible();
});

for (const failure of ["transport", "malformed"] as const) test(`Access ${failure} post-write read withholds grants and dependent authority`, async ({ page }) => {
  await access(page);
  let reads = 0, writes = 0;
  await page.route("**/api/v1/projects/*/access/9001", route => {
    writes++; expect(route.request().postDataJSON()).toEqual({ granted: true });
    return route.fulfill({ json: { id: 9001, granted: true } });
  });
  await page.route("**/api/v1/projects/*/access", route => {
    reads++;
    return failure === "transport" ? route.abort("failed") : route.fulfill({ json: { developers: [{ ...grants().developers[0], granted: "yes" }] } });
  });
  await grant(page).click(); await apply(page).click();
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(grant(page)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Remove access: access_target", exact: true })).toHaveCount(0);
  expect(writes).toBe(1); expect(reads).toBe(1);
});

test("Access deadline fails closed, releases read slot and rejects expired completion", async ({ page }) => {
  await page.clock.install(); await access(page);
  await grant(page).click();
  const held = deferred(); let reads = 0;
  await page.route("**/api/v1/projects/*/access", async route => { reads++; await held.promise; await route.fulfill({ json: grants(true) }).catch(() => {}); });
  try {
    const metadata = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
    await revalidateVisiblePage(page); await expect.poll(() => reads).toBe(1);
    await (await metadata).finished();
    await hidden(page);
    await page.clock.runFor(30001);
    await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
    await expect(apply(page)).toBeDisabled();
    await page.route("**/api/v1/projects/*/access", route => route.fulfill({ json: grants() }));
    await revalidateVisiblePage(page);
    await expect(grant(page)).toBeVisible();
    held.resolve();
    await expect(apply(page)).toBeDisabled();
    await expect(page.getByRole("button", { name: "Remove access: access_target", exact: true })).toHaveCount(0);
  } finally { held.resolve(); }
});

test("App monitoring status coalesces through running, expires safely and cancels on navigation", async ({ page }) => {
  await page.clock.install();
  await page.route("**/operations/resume", route => route.fulfill({ json: { id: 7702, status: "pending" } }));
  await page.route("**/operations/pause", route => route.fulfill({ json: { id: 7702, status: "pending" } }));
  const first = deferred(), second = deferred(); let reads = 0, cancelled = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/operations/7702")) cancelled++; });
  await page.route("**/operations/7702", async route => {
    const index = ++reads;
    await (index === 1 ? first.promise : second.promise);
    await route.fulfill({ json: { id: 7702, status: "running", action: "resume" } }).catch(() => {});
  });
  await page.goto("/projects/alpha");
  await page.getByRole("button", { name: /^(Activate|Pause) monitoring$/ }).click();
  await expect.poll(() => reads).toBe(1);
  try {
    await page.clock.runFor(6000);
    expect(reads).toBe(1);
    first.resolve();
    await expect(page.getByRole("status").filter({ hasText: "#7702" })).toContainText("running");
    expect(reads).toBe(1); // pending -> running is not a new owner/extra immediate read
    await page.clock.runFor(2000); await expect.poll(() => reads).toBe(2);
    await hidden(page); await page.clock.runFor(30001);
    await expect(page.getByRole("alert").filter({ hasText: "The ADORE server cannot be reached" })).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "#7702" })).toContainText("running");
    const metadata = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
    await revalidateVisiblePage(page); await (await metadata).finished();
    await expect.poll(() => reads).toBe(3);
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await expect.poll(() => cancelled).toBe(2);
    await page.clock.runFor(6000); expect(reads).toBe(3);
  } finally { first.resolve(); second.resolve(); }
});

test("System status holds values, coalesces bounded reads and rejects malformed replacements", async ({ page }) => {
  await page.clock.install();
  const storage = { threshold_bytes: 1024, low: false, volumes: [{ scope: "home", project: null, free_bytes: 4096, total_bytes: 8192, low: false, volume_id: "test-volume" }] };
  await page.route("**/api/v1/ready", route => route.fulfill({ json: { status: "ready", worker: "ready", activity: "idle" } }));
  await page.route("**/api/v1/system/storage", route => route.fulfill({ json: storage }));
  await page.goto("/admin/status");
  const worker = page.locator(".system-indicator").filter({ hasText: "Control worker" });
  const disk = page.locator(".system-indicator").filter({ hasText: "Storage" });
  await expect(worker).toContainText("Ready"); await expect(disk).toContainText(messages.en.storageHealthy);
  const node = await worker.elementHandle();
  const held = deferred(); let workerReads = 0, storageReads = 0;
  await page.route("**/api/v1/ready", async route => { workerReads++; await held.promise; await route.fulfill({ json: { status: "ready", worker: false, activity: "idle" } }).catch(() => {}); });
  await page.route("**/api/v1/system/storage", async route => { storageReads++; await held.promise; await route.fulfill({ json: { ...storage, low: "no" } }).catch(() => {}); });
  try {
    await revalidateVisiblePage(page);
    await expect.poll(() => workerReads).toBe(1); await expect.poll(() => storageReads).toBe(1);
    await page.clock.runFor(15000);
    expect(workerReads).toBe(1); expect(storageReads).toBe(1);
    await expect(worker).toContainText("Ready"); await expect(disk).toContainText(messages.en.storageHealthy);
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
    held.resolve();
    await expect(worker).toContainText(messages.en.workerCheckFailed);
    await expect(disk).toContainText(messages.en.storageCheckFailed);
  } finally { held.resolve(); }
  await page.route("**/api/v1/ready", route => route.fulfill({ json: { status: "ready", worker: "ready", activity: "busy" } }));
  await page.route("**/api/v1/system/storage", route => route.fulfill({ json: { ...storage, low: true } }));
  await revalidateVisiblePage(page);
  await expect(worker).toContainText(messages.en.workerBusy); await expect(disk).toContainText(messages.en.storageLow);
  expect(await node!.evaluate(element => element.isConnected)).toBe(true);
  const expired = deferred(); let reads = 0, cancelled = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/ready") || request.url().endsWith("/system/storage")) cancelled++; });
  await page.route("**/api/v1/ready", async route => { reads++; await expired.promise; await route.fulfill({ json: { status: "ready", worker: "ready", activity: "idle" } }).catch(() => {}); });
  await page.route("**/api/v1/system/storage", async route => { reads++; await expired.promise; await route.fulfill({ json: storage }).catch(() => {}); });
  try {
    await hidden(page); await page.clock.runFor(45000); expect(reads).toBe(0);
    await revalidateVisiblePage(page); await expect.poll(() => reads).toBe(2);
    await hidden(page); await page.clock.runFor(30001);
    await expect(worker).toContainText(messages.en.workerCheckFailed); await expect(disk).toContainText(messages.en.storageCheckFailed);
    await expect.poll(() => cancelled).toBe(2);
  } finally { expired.resolve(); }
});

for (const view of ["access", "configuration", "dirty configuration"] as const) test(`App operation completion preserves ${view} local state and rereads after result`, async ({ page }) => {
  const held = deferred(); let polled = 0, reads = 0;
  await page.route("**/operations/resume", route => route.fulfill({ json: { id: 7701, status: "pending" } }));
  await page.route("**/operations/pause", route => route.fulfill({ json: { id: 7701, status: "pending" } }));
  await page.route("**/operations/7701", async route => { polled++; await held.promise; await route.fulfill({ json: { id: 7701, status: "succeeded", action: "resume" } }).catch(() => {}); });
  await page.route("**/api/v1/projects/*/access", route => { reads++; return route.fulfill({ json: grants() }); });
  await page.goto("/projects/alpha");
  await page.getByRole("button", { name: /^(Activate|Pause) monitoring$/ }).click();
  await expect.poll(() => polled).toBe(1);
  try {
    await page.getByRole("tab", { name: view === "access" ? "Access" : "Settings", exact: true }).click();
    if (view === "access") {
      await grant(page).click(); await apply(page).focus();
      const node = await apply(page).elementHandle();
      held.resolve();
      await expect.poll(() => reads).toBe(2);
      await expect(apply(page)).toBeVisible(); await expect(apply(page)).toBeFocused();
      expect(await node!.evaluate(element => element.isConnected)).toBe(true);
    } else {
      const category = page.locator("#project-settings > .setting-groups > details").first();
      await category.locator("summary").click();
      const node = await category.elementHandle();
      let draft = page.locator("#unused");
      if (view === "dirty configuration") {
        const implementation = page.locator("details[data-setting-purpose=implementation]");
        await implementation.locator(":scope > summary").click();
        await implementation.getByRole("button", { name: "Edit Maximum executor launches per job", exact: true }).click();
        draft = implementation.getByLabel("Maximum executor launches per job", { exact: true });
        await draft.fill("123");
      }
      held.resolve();
      await expect(page.getByRole("status").filter({ hasText: "#7701" })).toContainText("succeeded");
      await expect(category).toHaveAttribute("open", "");
      expect(await node!.evaluate(element => element.isConnected)).toBe(true);
      if (view === "dirty configuration") await expect(draft).toHaveValue("123");
    }
  } finally { held.resolve(); }
});

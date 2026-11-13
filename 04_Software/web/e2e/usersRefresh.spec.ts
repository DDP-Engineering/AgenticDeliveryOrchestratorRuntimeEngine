/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage } from "./polling";
import { userCopy } from "../src/userCopy";
import { messages, type Locale } from "../src/i18n";

const deferred = () => { let resolve!: () => void; const promise = new Promise<void>(done => { resolve = done; }); return { promise, resolve }; };
const targetRow = (page: Page) => page.locator(".user-row").filter({ has: page.getByText("refresh_target", { exact: true }) });
const refresh = (page: Page) => page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true });

test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
});

async function fixture(page: Page) {
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((p: { name: string }) => p.name === "alpha");
  const accounts = [{ id: 9001, username: "refresh_target", role: "developer", disabled: false, project_ids: [alpha.id], projects: ["alpha"] }];
  await page.route("**/api/v1/users", route => route.fulfill({ json: accounts }));
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Users", exact: true }).click();
  await expect(targetRow(page)).toBeVisible();
  return { accounts, projects };
}

async function review(page: Page) {
  const row = targetRow(page);
  await row.getByText("Assigned projects", { exact: true }).click();
  await row.getByRole("checkbox", { name: /beta/ }).check();
  await row.getByRole("button", { name: "Save", exact: true }).click();
  return row.getByRole("region", { name: "Review access change", exact: true });
}

test("Users manual refresh retains rows review focus and successful completion time without polling", async ({ page }) => {
  const { accounts } = await fixture(page);
  await page.clock.install();
  const confirmation = await review(page);
  const apply = confirmation.getByRole("button", { name: "Apply reviewed access", exact: true });
  const savedRow = await targetRow(page).elementHandle();
  const stamp = page.locator(".refresh-stamp");
  const originalTime = await stamp.locator("time").getAttribute("datetime");
  const held = deferred(), started = deferred();
  let reads = 0;
  await page.route("**/api/v1/users", async route => { reads++; started.resolve(); await held.promise; await route.fulfill({ json: accounts }); });
  await refresh(page).click();
  await started.promise;
  try {
    await expect(refresh(page)).toHaveAttribute("aria-disabled", "true");
    await refresh(page).press("Enter");
    await apply.focus();
    await page.clock.runFor(15000);
    expect(reads).toBe(1);
    await expect(confirmation).toBeVisible();
    await expect(apply).toBeFocused();
    expect(await savedRow!.evaluate(node => node.isConnected)).toBe(true);
    await expect(stamp.locator("time")).toHaveAttribute("datetime", originalTime!);
    await expect(page.getByText("Loading data…", { exact: true })).toHaveCount(0);
  } finally { held.resolve(); }
  await expect(refresh(page)).toHaveAttribute("aria-disabled", "false");
  await expect(stamp.locator("time")).not.toHaveAttribute("datetime", originalTime!);
  await expect(confirmation).toBeVisible();
  await expect(apply).toBeFocused();
  expect(await savedRow!.evaluate(node => node.isConnected)).toBe(true);
  await page.clock.runFor(45000);
  expect(reads).toBe(1);
});

for (const failure of ["transport", "malformed"] as const) test(`Users ${failure} refresh hides authority but retains unrelated reset draft`, async ({ page }) => {
  await fixture(page);
  const held = deferred(), started = deferred();
  await page.route("**/api/v1/users", async route => {
    started.resolve(); await held.promise;
    if (failure === "transport") await route.abort("failed");
    else await route.fulfill({ json: [{ id: 9001, username: "unsafe", role: "developer", disabled: false, project_ids: "alpha" }] });
  });
  await refresh(page).click(); await started.promise;
  await targetRow(page).getByRole("button", { name: "Reset password", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Reset password for refresh_target", exact: true });
  const password = dialog.getByLabel("New password", { exact: true });
  await password.fill("retained-draft-password");
  await dialog.getByLabel("Repeat new password", { exact: true }).fill("retained-draft-password");
  const field = await password.elementHandle();
  held.resolve();
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(targetRow(page)).toHaveCount(0);
  await expect(dialog).toBeVisible();
  await expect(password).toHaveValue("retained-draft-password");
  expect(await field!.evaluate(node => node.isConnected)).toBe(true);
  await expect(dialog.getByRole("button", { name: "Save", exact: true })).toBeDisabled();
  await expect(page.locator(".refresh-stamp")).toBeEmpty();
});

test("Users changed account authority invalidates a review without erasing its local selection", async ({ page }) => {
  const { accounts } = await fixture(page);
  const confirmation = await review(page);
  accounts[0].disabled = true;
  await refresh(page).click();
  await expect(targetRow(page)).toContainText("Disable");
  await expect(confirmation).toBeVisible();
  await expect(confirmation.getByRole("button", { name: "Apply reviewed access", exact: true })).toBeDisabled();
  await confirmation.getByRole("button", { name: "Correct access", exact: true }).click();
  await expect(targetRow(page).getByRole("checkbox", { name: /beta/ })).toBeChecked();
});

test("Users removed reset target cannot submit and Add user rechecks reviewed project availability", async ({ page }) => {
  const { accounts, projects } = await fixture(page);
  const held = deferred(), started = deferred();
  await page.route("**/api/v1/users", async route => { started.resolve(); await held.promise; await route.fulfill({ json: [] }); });
  await refresh(page).click(); await started.promise;
  await targetRow(page).getByRole("button", { name: "Reset password", exact: true }).click();
  const reset = page.getByRole("dialog");
  await reset.getByLabel("New password", { exact: true }).fill("retained-draft-password");
  held.resolve();
  await expect(targetRow(page)).toHaveCount(0);
  await expect(reset.getByRole("button", { name: "Save", exact: true })).toBeDisabled();
  await reset.getByRole("button", { name: "Close", exact: true }).click();
  await page.unroute("**/api/v1/users");
  await page.route("**/api/v1/users", route => route.fulfill({ json: accounts }));
  await refresh(page).click();
  await page.getByRole("button", { name: "Add user", exact: true }).click();
  const add = page.getByRole("dialog");
  await add.getByLabel("Username", { exact: true }).fill("unsubmitted-review");
  await add.getByLabel("Password", { exact: true }).fill("retained-draft-password");
  await add.getByLabel("Repeat new password", { exact: true }).fill("retained-draft-password");
  await add.getByRole("button", { name: "Continue to access", exact: true }).click();
  await add.getByRole("checkbox", { name: /alpha/ }).check();
  await add.getByRole("button", { name: "Review account", exact: true }).click();
  const changed = projects.map((p: { name: string }) => p.name === "alpha" ? { ...p, archived: true } : p);
  await page.route(/\/api\/v1\/projects(?:\?overview=true)?$/, route => route.fulfill({ json: changed }));
  await revalidateVisiblePage(page);
  await expect(add.getByRole("button", { name: "Create reviewed account", exact: true })).toBeDisabled();
  await expect(add.getByRole("heading", { name: "Review account", exact: true })).toBeVisible();
  await add.getByRole("button", { name: "Correct access", exact: true }).click();
  await expect(add.getByRole("checkbox", { name: /alpha/ })).toHaveCount(0);
  await add.getByRole("checkbox", { name: /beta/ }).check();
  await add.getByRole("button", { name: "Review account", exact: true }).click();
  await expect(add.getByRole("button", { name: "Create reviewed account", exact: true })).toBeEnabled();
});

test("Users cancels pre-write reads and publishes only post-write authority without remounting the row", async ({ page }) => {
  const { accounts } = await fixture(page);
  const held = deferred(), started = deferred();
  let reads = 0;
  await page.route("**/api/v1/users", async route => {
    reads++;
    const snapshot = structuredClone(accounts);
    if (reads === 1) { started.resolve(); await held.promise; }
    await route.fulfill({ json: snapshot }).catch(() => {});
  });
  await page.route("**/api/v1/users/9001/disable", async route => { accounts[0].disabled = true; await route.fulfill({ json: { ok: true } }); });
  await refresh(page).click(); await started.promise;
  const node = await targetRow(page).elementHandle();
  await targetRow(page).getByRole("button", { name: "Disable", exact: true }).click();
  await expect(targetRow(page).getByRole("button", { name: "Enable", exact: true })).toBeVisible();
  expect(reads).toBe(2);
  expect(await node!.evaluate(element => element.isConnected)).toBe(true);
  held.resolve();
  await expect(targetRow(page).getByRole("button", { name: "Enable", exact: true })).toBeVisible();
});

test("Users initial deadline releases retry and rejects expired completions", async ({ page }) => {
  await fixture(page);
  await page.clock.install();
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  const held = deferred(), started = deferred();
  await page.route("**/api/v1/users", async route => { started.resolve(); await held.promise; await route.fulfill({ json: [] }).catch(() => {}); });
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Users", exact: true }).click();
  await started.promise;
  await expect(targetRow(page)).toHaveCount(0);
  await expect(page.locator(".refresh-stamp")).toBeEmpty();
  await page.clock.runFor(30001);
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(refresh(page)).toHaveAttribute("aria-disabled", "false");
  await page.unroute("**/api/v1/users");
  await page.route("**/api/v1/users", route => route.fulfill({ json: [{ id: 9002, username: "current", role: "admin", disabled: false, project_ids: [], projects: [] }] }));
  await refresh(page).click();
  await expect(page.getByText("current", { exact: true })).toBeVisible();
  held.resolve();
  await expect(page.getByText("current", { exact: true })).toBeVisible();
});


test("Users navigation aborts held manual ownership and old data cannot replace a new visit", async ({ page }) => {
  const { accounts } = await fixture(page);
  const held = deferred(), started = deferred();
  let reads = 0;
  await page.route("**/api/v1/users", async route => {
    reads++;
    if (reads === 1) { started.resolve(); await held.promise; }
    await route.fulfill({ json: reads === 1 ? [] : accounts }).catch(() => {});
  });
  const aborted = page.waitForEvent("requestfailed", req => new URL(req.url()).pathname === "/api/v1/users");
  await refresh(page).click(); await started.promise;
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  await aborted;
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Users", exact: true }).click();
  await expect(targetRow(page)).toBeVisible();
  held.resolve();
  await expect(targetRow(page)).toBeVisible();
  expect(reads).toBe(2);
});


test("Users refresh and changed review feedback work in four locales and both narrow themes", async ({ page }) => {
  const { accounts } = await fixture(page);
  const me = await (await page.request.get("/api/v1/me")).json();
  try {
    for (const locale of ["en", "fr", "de", "ro"] as Locale[]) for (const theme of ["light", "dark"]) {
      const text = messages[locale], copy = userCopy[locale];
      await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } });
      await page.reload();
      await page.setViewportSize({ width: 390, height: 844 });
      const row = targetRow(page);
      await row.getByText(text.assignedProjects, { exact: true }).click();
      await row.getByRole("checkbox", { name: /beta/ }).check();
      await row.getByRole("button", { name: text.save, exact: true }).click();
      const confirmation = row.getByRole("region", { name: copy.reviewAccess, exact: true });
      accounts[0].disabled = !accounts[0].disabled;
      await page.locator(".topbar").getByRole("button", { name: text.refresh, exact: true }).click();
      await expect(confirmation.getByRole("button", { name: copy.apply, exact: true })).toBeDisabled();
      await expect(row.getByRole("alert")).toHaveText(copy.reviewChanged);
      await expect(page.locator(".refresh-stamp time")).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    }
  } finally {
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } });
  }
});

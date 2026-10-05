/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";

async function openSettings(page: Page, user = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(user);
  await page.getByLabel("Password", { exact: false }).fill(user === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  await page.goto(`/projects/${projects.find((item: { name: string }) => item.name === "alpha").id}/configuration`);
  await expect(page.getByRole("heading", { name: "Project settings", exact: true })).toBeVisible();
}

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

test("explicit portable preview downloads exact active bytes with purpose and exclusions", async ({ page }) => {
  await openSettings(page);
  const panel = page.locator(".portable-settings");
  const download = panel.getByRole("button", { name: "Download portable JSON", exact: true });
  await expect(download).toBeDisabled();
  await expect(panel).toContainText("pending changes are excluded");
  await expect(panel).toContainText("all credential/endpoint references");
  await expect(panel).toContainText("does not authenticate");
  await expect(panel).toContainText("not available in this screen");
  const active = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const pending = await (await page.request.get("/api/v1/projects/alpha/config/pending")).text();
  const expected = await (await page.request.get("/api/v1/projects/alpha/config/portable-settings")).text();
  await panel.getByRole("button", { name: "Preview active rules", exact: true }).click();
  await expect(panel.locator("pre")).toContainText('"max_iterations"');
  const event = page.waitForEvent("download");
  await download.click();
  const file = await event;
  expect(file.suggestedFilename()).toBe("adore-project-settings.json");
  expect(await readFile((await file.path())!, "utf8")).toBe(expected);
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(active.revision);
  expect(await (await page.request.get("/api/v1/projects/alpha/config/pending")).text()).toBe(pending);
});

test("failed empty malformed and changed reads clear preview and allow retry", async ({ page }) => {
  await openSettings(page);
  const panel = page.locator(".portable-settings");
  const preview = panel.getByRole("button", { name: "Preview active rules", exact: true });
  const download = panel.getByRole("button", { name: "Download portable JSON", exact: true });
  for (const body of ["", "null", "{}", '{"kind":"adore-project-settings"}']) {
    await page.route("**/config/portable-settings*", route => route.fulfill({ status: 200, contentType: "application/json", body }));
    await preview.click();
    await expect(panel.getByRole("alert")).toBeVisible();
    await expect(download).toBeDisabled();
    await expect(panel.locator("pre")).toHaveCount(0);
    await page.unroute("**/config/portable-settings*");
  }
  await preview.click(); await expect(download).toBeEnabled();
  await page.route("**/config/portable-settings?*", route => route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ detail: { code: "portable_settings_changed" } }) }));
  await download.click();
  await expect(panel.getByRole("alert")).toContainText("Preview the active settings again");
  await expect(download).toBeDisabled();
  await expect(panel.locator("pre")).toHaveCount(0);
  await page.unroute("**/config/portable-settings?*");
  await preview.click(); await expect(download).toBeEnabled();
});

test("corrupt source and network feedback never offer an export", async ({ page }) => {
  await openSettings(page);
  const panel = page.locator(".portable-settings");
  await page.route("**/config/portable-settings*", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: { code: "portable_settings_invalid" } }) }));
  await panel.getByRole("button", { name: "Preview active rules" }).click();
  await expect(panel.getByRole("alert")).toContainText("Correct it on the ADORE host");
  await page.unroute("**/config/portable-settings*");
  await page.route("**/config/portable-settings*", route => route.abort("failed"));
  await panel.getByRole("button", { name: "Preview active rules" }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(panel.getByRole("button", { name: "Download portable JSON" })).toBeDisabled();
});

test("Dev cannot see export and direct requests reveal no project metadata", async ({ page }) => {
  await openSettings(page, "developer");
  await expect(page.locator(".portable-settings")).toHaveCount(0);
  for (const project of ["alpha", "beta", "absent"]) {
    const response = await page.request.get(`/api/v1/projects/${project}/config/portable-settings?download=true`);
    expect(response.status()).toBe(403);
    expect(await response.json()).toEqual({ detail: { code: "admin_required" } });
  }
});

test("late preview is cancelled on project navigation and duplicate clicks issue one read", async ({ page }) => {
  await openSettings(page);
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let reads = 0;
  await page.route("**/config/portable-settings*", async route => {
    reads += 1; const response = await route.fetch(); await held;
    await route.fulfill({ response }).catch(() => {});
  });
  const panel = page.locator(".portable-settings");
  await panel.getByRole("button", { name: "Preview active rules" }).click();
  await expect(panel.getByRole("button", { name: "Preview active rules" })).toBeDisabled();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  await page.goto(`/projects/${projects.find((item: { name: string }) => item.name === "beta").id}/configuration`);
  release();
  await expect(page.locator(".portable-settings pre")).toHaveCount(0);
  await expect(page.locator(".portable-settings").getByRole("button", { name: "Download portable JSON" })).toBeDisabled();
  expect(reads).toBe(1);
});

test("keyboard 390px themes and four locales keep purpose and controls usable", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openSettings(page);
  const session = await (await page.request.get("/api/v1/me")).json();
  for (const theme of ["light", "dark"]) {
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { theme, language: "en" } });
    await page.reload();
    const panel = page.locator(".portable-settings");
    const preview = panel.getByRole("button", { name: "Preview active rules" });
    await preview.focus(); await page.keyboard.press("Enter");
    await expect(panel.getByRole("button", { name: "Download portable JSON" })).toBeEnabled();
    await page.keyboard.press("Tab");
    await expect(panel.getByRole("button", { name: "Download portable JSON" })).toBeFocused();
    await panel.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await panel.screenshot({ path: info.outputPath(`portable-${theme}-390.png`) });
  }
  for (const [locale, title] of [["en", "Export portable settings"], ["fr", "Exporter les paramètres portables"], ["de", "Portable Einstellungen exportieren"], ["ro", "Exportă setările portabile"]]) {
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: locale } });
    await page.reload();
    await expect(page.locator(".portable-settings").getByRole("heading", { name: title })).toBeVisible();
    await expect(page.locator(".portable-settings p").first()).not.toBeEmpty();
  }
  await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: "en", theme: "light" } });
});

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
  await expect(page.locator(".shell")).toBeVisible();
  const session = await (await page.request.get("/api/v1/me")).json();
  await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: "en", theme: "light" } });
  const projects = await (await page.request.get("/api/v1/projects")).json();
  await page.goto(`/projects/${projects.find((item: { name: string }) => item.name === "alpha").id}/configuration`);
  await expect(page.getByRole("heading", { name: "Project settings", exact: true })).toBeVisible();
}

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

test.afterEach(async ({ page }) => {
  const response = await page.request.get("/api/v1/me");
  if (response.ok()) {
    const session = await response.json();
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: "en", theme: "light" } });
  }
});

test("raw configuration preview and download are original and Settings stays compact", async ({ page }) => {
  await openSettings(page);
  const panel = page.locator("#project-settings");
  await expect(page.locator(".portable-settings, #project-config-editor")).toHaveCount(0);
  await expect(panel.getByText("Set for this project", { exact: true })).toHaveCount(0);
  await expect(panel.getByText(/Prepare one setting at a time/)).toHaveCount(0);
  const original = await page.request.get("/api/v1/projects/alpha/config/raw");
  expect(original.status()).toBe(200);
  const expected = await original.body();
  const download = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Download raw configuration", exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("config.toml");
  expect(await readFile((await file.path())!)).toEqual(expected);
  const preview = panel.getByRole("button", { name: "Preview raw configuration", exact: true });
  await preview.click();
  const dialog = page.getByRole("dialog", { name: "Preview raw configuration", exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator("pre")).toHaveText(expected.toString("utf8"), { useInnerText: false });
  await expect(dialog.getByRole("button", { name: "Close", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(preview).toBeFocused();
  await expect(page.locator(".raw-config-actions pre")).toHaveCount(0);
});

test("raw configuration failures and malformed transports expose no preview", async ({ page }) => {
  await openSettings(page);
  const preview = page.getByRole("button", { name: "Preview raw configuration", exact: true });
  for (const response of [
    { status: 503, contentType: "application/json", body: JSON.stringify({ detail: { code: "config_corrupt" } }) },
    { status: 200, contentType: "text/html", body: "<script>window.rawInjected = true</script>" },
    { status: 200, contentType: "text/plain", body: "" },
  ]) {
    await page.route("**/config/raw*", route => route.fulfill(response));
    await preview.click();
    await expect(page.locator(".raw-config-actions [role=alert]")).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.unroute("**/config/raw*");
  }
  await preview.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
});

test("raw configuration inline secrets render as text and are cleared on scope change", async ({ page }) => {
  await openSettings(page);
  const original = '# inline fixture\r\n[private]\r\nvalue="<script>window.rawInjected=true</script>"\r\n';
  await page.route("**/config/raw*", route => route.fulfill({ contentType: "text/plain", body: original }));
  await page.getByRole("button", { name: "Preview raw configuration", exact: true }).click();
  const dialog = page.getByRole("dialog");
  expect(await dialog.locator("pre").textContent()).toBe(original);
  expect(await page.evaluate(() => "rawInjected" in window)).toBe(false);
  await page.keyboard.press("Escape");
  let release!: () => void;
  let captured!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const started = new Promise<void>(resolve => { captured = resolve; });
  await page.unroute("**/config/raw*");
  await page.route("**/config/raw*", async route => { captured(); await held; await route.fulfill({ contentType: "text/plain", body: original }).catch(() => undefined); });
  await page.getByRole("button", { name: "Preview raw configuration", exact: true }).click();
  await started;
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Overview", exact: true }).click();
  release();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(await page.evaluate(() => Object.values(localStorage).some(value => value.includes("rawInjected")))).toBe(false);
});

test("developer cannot view or download original unredacted configuration", async ({ page }) => {
  await openSettings(page, "developer");
  await expect(page.locator(".raw-config-actions")).toHaveCount(0);
  for (const project of ["alpha", "beta"]) {
    expect((await page.request.get(`/api/v1/projects/${project}/config/raw?download=true`)).status()).toBe(403);
  }
});

for (const [locale, preview] of [
  ["en", "Preview raw configuration"], ["fr", "Voir la configuration brute"],
  ["de", "Originalkonfiguration anzeigen"], ["ro", "Previzualizare configurație originală"],
]) {
  test(`raw configuration controls support ${locale} at 390px`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openSettings(page);
    const me = await (await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme: "dark" } });
    await page.reload();
    await page.getByRole("button", { name: preview, exact: true }).click();
    const dialog = page.getByRole("dialog", { name: preview, exact: true });
    await expect(dialog).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
  });
}

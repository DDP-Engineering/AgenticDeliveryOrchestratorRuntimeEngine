/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect } from "@playwright/test";

test("factory reminder persists in four languages and links to password change", async ({ page, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.setViewportSize({ width: 390, height: 850 });
  await page.goto("/");
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin");
  await page.locator('form button[type="submit"]').click();
  const notice = page.locator('main p.notice').filter({ has: page.locator('a[href="/account"]') });
  await expect(notice).toContainText("initial administrator password");
  await notice.getByRole("link").click();
  for (const [locale, text] of [["fr", "mot de passe initial"], ["de", "ursprüngliche Administratorkennwort"], ["ro", "Parola inițială"], ["en", "initial administrator password"]]) {
    await page.locator("main select").first().selectOption(locale);
    await page.reload();
    await expect(notice).toContainText(text);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  }
  await expect(page).toHaveURL(/account/);
  // API tests exercise the real password change in an isolated store. Stub only
  // this UI transition so this serial suite keeps its shared fixture credentials.
  const current = await (await page.request.get("/api/v1/me")).json();
  current.user.factory_password = false;
  await page.route("**/api/v1/me/password", route => route.fulfill({ json: { ok: true } }));
  await page.route("**/api/v1/session", route => route.request().method() === "POST" ? route.fulfill({ json: current }) : route.continue());
  await page.route("**/api/v1/me", route => route.fulfill({ json: current }));
  await page.locator('input[name="current"]').fill("admin");
  await page.locator('input[name="replacement"]').fill("new-long-password");
  await page.locator('input[name="confirmation"]').fill("new-long-password");
  await page.locator('input[name="replacement"]').locator("xpath=ancestor::form").getByRole("button", { name: "Save", exact: true }).click();
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("new-long-password");
  await page.locator('form button[type="submit"]').click();
  await expect(notice).toHaveCount(0);
  await page.reload();
  await expect(notice).toHaveCount(0);
});

test("a delayed session refresh cannot restore a signed-out session", async ({ page, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/");
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin");
  await page.locator('form button[type="submit"]').click();
  await expect(page.locator('a[href="/account"]').first()).toBeVisible();
  let release!: () => void, started!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const waiting = new Promise<void>(resolve => { started = resolve; });
  await page.route("**/api/v1/me", async route => {
    const response = await route.fetch();
    started();
    await held;
    await route.fulfill({ response });
  });
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await waiting;
  await page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
  release();
  await expect(page.locator('input[name="username"]')).toBeVisible();
  await expect(page.locator('a[href="/account"]')).toHaveCount(0);
});

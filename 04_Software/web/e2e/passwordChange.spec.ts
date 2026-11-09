/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect } from "@playwright/test";

test("account password change reveals fields and rejects mismatched confirmation", async ({ page, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.setViewportSize({ width: 390, height: 850 });
  await page.goto("/");
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin");
  await page.locator('form button[type="submit"]').click();
  await page.locator('main a[href="/account"]').click();
  const form = page.locator('input[name="current"]').locator('xpath=ancestor::form');
  const current = form.locator('input[name="current"]');
  const replacement = form.locator('input[name="replacement"]');
  const confirmation = form.locator('input[name="confirmation"]');
  await expect(form).toContainText("At least 8 characters.");
  for (const field of [current, replacement, confirmation]) await expect(field).toHaveAttribute("type", "password");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await current.fill("admin");
  await replacement.fill("new-long-password");
  await confirmation.fill("mismatch-password");
  await form.getByRole("button", { name: "Show current password" }).click();
  await expect(current).toHaveAttribute("type", "text");
  await expect(replacement).toHaveAttribute("type", "password");
  await form.getByRole("button", { name: "Hide current password" }).click();
  await expect(current).toHaveAttribute("type", "password");
  await form.getByRole("button", { name: "Show new password", exact: true }).click();
  await expect(replacement).toHaveAttribute("type", "text");
  await form.getByRole("button", { name: "Hide new password" }).click();
  await expect(replacement).toHaveAttribute("type", "password");
  await form.getByRole("button", { name: "Show repeated password" }).click();
  await expect(confirmation).toHaveAttribute("type", "text");
  await form.getByRole("button", { name: "Hide repeated password" }).click();
  await expect(confirmation).toHaveAttribute("type", "password");
  let submitted = 0;
  await page.route("**/api/v1/me/password", route => {
    submitted++;
    expect(route.request().postDataJSON()).toEqual({ current: "admin", replacement: "new-long-password" });
    return route.fulfill({ json: { ok: true } });
  });
  await form.getByRole("button", { name: "Save", exact: true }).click();
  await expect(form).toContainText("Passwords do not match");
  expect(submitted).toBe(0);
  await page.getByRole("button", { name: /Menu/ }).click();
  await page.getByRole("navigation").getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("button", { name: /Menu/ }).click();
  await page.getByRole("navigation").getByRole("link", { name: "My account", exact: true }).click();
  await expect(form.getByRole("alert")).toHaveCount(0);
  await current.fill("admin");
  await replacement.fill("new-long-password");
  await confirmation.fill("new-long-password");
  await form.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.locator('input[name="username"]')).toBeVisible();
  expect(submitted).toBe(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});


test("required password change uses the same confirmation and visibility controls", async ({ page, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.route("**/api/v1/session", async route => {
    if (route.request().method() !== "POST") return route.continue();
    const response = await route.fetch();
    const data = await response.json();
    data.user.password_change_required = true;
    await route.fulfill({ response, json: data });
  });
  await page.goto("/");
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin");
  await page.locator('form button[type="submit"]').click();
  const form = page.locator('input[name="current"]').locator('xpath=ancestor::form');
  await expect(form).toContainText("At least 8 characters.");
  await expect(form.locator('input[name="current"]')).toBeFocused();
  await form.locator('input[name="current"]').fill("admin");
  await form.locator('input[name="replacement"]').fill("new-long-password");
  await form.locator('input[name="confirmation"]').fill("different-password");
  await form.getByRole("button", { name: "Show repeated password" }).click();
  await expect(form.locator('input[name="confirmation"]')).toHaveAttribute("type", "text");
  let submitted = 0;
  await page.route("**/api/v1/me/password", route => { submitted++; return route.fulfill({ json: { ok: true } }); });
  await form.getByRole("button", { name: "Change password", exact: true }).click();
  await expect(form).toContainText("Passwords do not match");
  expect(submitted).toBe(0);
  await form.locator('input[name="confirmation"]').fill("new-long-password");
  await form.getByRole("button", { name: "Change password", exact: true }).click();
  await expect(page.locator('input[name="username"]')).toBeVisible();
  expect(submitted).toBe(1);
});


test("password guidance and controls are localized", async ({ page, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/");
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin");
  await page.locator('form button[type="submit"]').click();
  await page.locator('main a[href="/account"]').click();
  const form = page.locator('input[name="current"]').locator('xpath=ancestor::form');
  try {
    for (const [locale, rule, confirmation, reveal] of [
    ["en", "At least 8 characters.", "Repeat new password", "Show current password"],
    ["fr", "Au moins 8 caractères.", "Confirmer le nouveau mot de passe", "Afficher le mot de passe actuel"],
    ["de", "Mindestens 8 Zeichen.", "Neues Passwort wiederholen", "Aktuelles Passwort anzeigen"],
    ["ro", "Cel puțin 8 caractere.", "Repetă parola nouă", "Arată parola curentă"],
  ]) {
    await page.locator("main select").first().selectOption(locale);
    await expect(form).toContainText(rule);
    await expect(form.getByLabel(confirmation)).toBeVisible();
    await expect(form.getByRole("button", { name: reveal })).toBeVisible();
    }
  } finally {
    await page.locator("main select").first().selectOption("en");
  }
});

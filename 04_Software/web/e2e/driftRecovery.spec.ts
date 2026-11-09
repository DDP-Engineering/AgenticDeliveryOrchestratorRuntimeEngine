/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect } from "@playwright/test";
import { recoveryCopy } from "../src/recoveryCopy";

test.beforeEach(async ({ request, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  expect((await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});
test.afterEach(async ({ request, page }) => {
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});

for (const locale of ["en", "fr", "de", "ro"] as const) {
  test(`confirmed drift recovery and stale refusal in ${locale}`, async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Username", { exact: false }).fill("admin");
    await page.getByLabel("Password", { exact: false }).fill("admin");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.locator(".shell")).toBeVisible();
    const session = await (await page.request.get("/api/v1/me")).json();
    expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: locale } })).ok()).toBe(true);
    await page.route("**/api/v1/jobs/*/ux-failed", async route => {
      const response = await route.fetch();
      const body = await response.json();
      body.job.outcome = "INFRASTRUCTURE_EXHAUSTED: execution profile drift; restore pinned settings or start a fresh run";
      await route.fulfill({ response, json: body });
    });
    let submits = 0;
    await page.route("**/operations/restart", async route => {
      submits++;
      const body = route.request().postDataJSON();
      expect(body.confirmed).toBe(true);
      expect(body.state_revision).toMatch(/^[a-f0-9]{64}$/);
      expect(body.run_id).toBe("ux-failed");
      await route.fulfill({ status: 409, json: { detail: { code: "job_snapshot_changed" } } });
    });
    await page.goto("/jobs?project=alpha&run=ux-failed");
    const detail = page.locator(".detail-panel");
    const restart = detail.getByRole("button", { name: recoveryCopy[locale].restart, exact: true });
    await expect(restart).toBeVisible();
    await expect(detail).toContainText(recoveryCopy[locale].drift);
    await expect(detail.locator(".button-row button")).toHaveCount(0);
    page.once("dialog", async dialog => {
      expect(dialog.message()).toContain(recoveryCopy[locale].confirm.replace("{ticket}", "42"));
      await dialog.dismiss();
    });
    await restart.click();
    expect(submits).toBe(0);
    page.once("dialog", dialog => dialog.accept());
    await restart.focus(); await page.keyboard.press("Enter");
    await expect.poll(() => submits).toBe(1);
    await expect(page.locator(".job-workspace [role=alert]")).toBeVisible();
    await expect(restart).toBeEnabled();
    await expect(detail).toContainText(recoveryCopy[locale].drift);
    if (locale === "ro") {
      await page.setViewportSize({ width: 390, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
    // Keep the shared fixture's account preference deterministic for later journeys.
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: "en" } });
  });
}

test("retained unproven old branch is a visible successful recovery", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".shell")).toBeVisible();
  await page.route("**/operations/restart", route => route.fulfill({ json: {
    id: 991, status: "succeeded", result: "restart:retained",
  } }));
  await page.goto("/jobs?project=alpha&run=ux-failed");
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: recoveryCopy.en.restart, exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: recoveryCopy.en.retained })).toBeVisible();
});

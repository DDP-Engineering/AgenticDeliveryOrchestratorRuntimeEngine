import { test, expect } from "@playwright/test";
import { recoveryCopy } from "../src/recoveryCopy";

test.beforeEach(async ({ request, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  await context.route("**/workflow-selection", route => route.fulfill({ json: { default: "direct", aegis_available: false } }));
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
      expect(body.workflow).toBe("direct");
      expect(body.state_revision).toMatch(/^[a-f0-9]{64}$/);
      expect(body.run_id).toBe("ux-failed");
      await route.fulfill({ status: 409, json: { detail: { code: "job_snapshot_changed" } } });
    });
    await page.goto("/jobs?project=alpha&run=ux-failed");
    const detail = page.locator(".detail-panel");
    await detail.locator(".job-actions summary").click();
    const restart = detail.getByRole("button", { name: recoveryCopy[locale].restartDirect, exact: true });
    await expect(restart).toBeVisible();
    await expect(detail).toContainText(recoveryCopy[locale].drift);
    await expect(detail.locator(".button-row button")).toHaveCount(0);
    await expect(detail.getByRole("button", { name: recoveryCopy[locale].restartAegis, exact: true })).toBeDisabled();
    await expect(detail.locator(".job-action-menu .field-hint")).toHaveCount(0);
    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    const firstDialog = page.waitForEvent("dialog");
    const firstClick = restart.click();
    const cancelled = await firstDialog;
    expect(cancelled.message()).toContain(recoveryCopy[locale].confirm.replace("{ticket}", "42"));
    expect(cancelled.message()).toContain(recoveryCopy[locale].restartDirect);
    await cancelled.dismiss(); await firstClick;
    expect(submits).toBe(0);
    await restart.focus();
    const secondDialog = page.waitForEvent("dialog");
    const keyboardClick = page.keyboard.press("Enter");
    await (await secondDialog).accept(); await keyboardClick;
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

test("compact recovery keeps Retry pinned and selects AEGIS for a fresh job", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".shell")).toBeVisible();
  await page.route("**/workflow-selection", route => route.fulfill({ json: { default: "aegis", aegis_available: true } }));
  let retries = 0;
  await page.route("**/operations/retry", route => {
    const body = route.request().postDataJSON();
    expect(body.workflow).toBeUndefined();
    expect(body.run_id).toBe("ux-failed");
    retries++;
    return route.fulfill({ json: { id: 990, status: "succeeded", result: "retried" } });
  });
  await page.route("**/operations/restart", route => {
    expect(route.request().postDataJSON().workflow).toBe("aegis");
    return route.fulfill({ json: { id: 991, status: "succeeded", result: "restart:retained" } });
  });
  await page.goto("/jobs?project=alpha&run=ux-failed");
  await page.locator(".detail-panel .job-actions summary").click();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect.poll(() => retries).toBe(1);
  const prompt = page.waitForEvent("dialog");
  const click = page.getByRole("button", { name: recoveryCopy.en.restartAegis, exact: true }).click();
  const confirmation = await prompt;
  expect(confirmation.message()).toContain(recoveryCopy.en.restartAegis);
  await confirmation.accept(); await click;
  await expect(page.getByRole("status").filter({ hasText: recoveryCopy.en.retained })).toBeVisible();
});

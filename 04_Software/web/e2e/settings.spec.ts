/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";

async function openSettings(page: Page, name = "alpha", user = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(user);
  await page.getByLabel("Password", { exact: false }).fill(user === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  await page.goto(`/projects/${projects.find((item: { name: string }) => item.name === name).id}/configuration`);
  await expect(page.getByRole("heading", { name: "Project settings", exact: true })).toBeVisible();
}

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

test.afterEach(async ({ page }) => {
  const me = await page.request.get("/api/v1/me");
  if (me.ok()) {
    const session = await me.json();
    if (session.user.role === "admin") await page.request.delete("/api/v1/projects/alpha/config/pending", { headers: { "X-CSRF-Token": session.csrf } });
  }
});

test("purpose guidance, correction, exact safe review/copy and candidate-only discard", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await openSettings(page);
  for (const category of ["Repository and tickets", "Agent and model", "Isolated environment", "Rules and approvals", "Limits and recovery", "Measurement and notifications", "Advanced"]) await expect(page.locator("#project-settings > .setting-groups > details > summary").filter({ hasText: category })).toBeVisible();
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  await page.getByRole("button", { name: "Edit Repository owner and name", exact: true }).click();
  const editor = page.locator(".setting-editor");
  await expect(editor.getByRole("textbox")).toHaveAttribute("aria-describedby", "help-platform.repo");
  await editor.getByRole("textbox").fill("");
  await editor.getByRole("button", { name: "Prepare candidate" }).click();
  await expect(page.getByRole("alert")).toContainText("invalid");
  await expect(editor.getByRole("textbox")).toHaveValue("");
  await editor.getByRole("textbox").fill("offline/reviewed-repository");
  await editor.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  await expect(review.getByRole("heading", { name: "Pending configuration", exact: true })).toBeFocused();
  await expect(review).toContainText("Affected project: alpha");
  await expect(review).toContainText(String(before.config.platform.repo));
  await expect(review).toContainText("offline/reviewed-repository");
  await expect(review).toContainText("Prepared by: not recorded");
  await expect(review).toContainText("Stop project pickup");
  await expect(page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true })).toBeDisabled();
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  await review.getByRole("button", { name: "Copy safe review" }).click();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain("offline/reviewed-repository");
  expect(copied).not.toContain("OPENCODE_CONFIG_CONTENT");
  await review.getByRole("button", { name: "Discard change", exact: true }).click();
  await expect(review).toHaveCount(0);
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  expect(await (await page.request.get("/api/v1/projects/alpha/config/pending")).json()).toBeNull();
  await expect(page.getByRole("button", { name: "Edit Repository owner and name", exact: true })).toBeFocused();
});

test("server blocked apply preserves review and active configuration", async ({ page }) => {
  await openSettings(page);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  await page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true }).click();
  const editor = page.locator(".setting-editor");
  await editor.getByRole("spinbutton").fill("12");
  await editor.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  await expect(review).toBeVisible();
  const pending = await (await page.request.get("/api/v1/projects/alpha/config/pending")).json();
  await page.route("**/config/apply", route => {
    expect(route.request().postDataJSON()).toEqual({ candidate_revision: pending.candidate_revision, base_revision: pending.base_revision });
    return route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ detail: { code: "project_has_active_work" } }) });
  });
  await review.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Pause pickup");
  await expect(review).toBeVisible();
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  await review.getByRole("button", { name: "Discard change", exact: true }).click();
});

test("late prepare cannot populate another project and repeated clicks prepare once", async ({ page }) => {
  await openSettings(page);
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let count = 0;
  await page.route("**/projects/*/config/pending", async route => {
    if (route.request().method() !== "POST") return route.continue();
    count += 1;
    const response = await route.fetch();
    await held;
    await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true }).click();
  await page.locator(".setting-editor").getByRole("spinbutton").fill("13");
  const prepare = page.locator(".setting-editor").getByRole("button", { name: "Prepare candidate" });
  await prepare.click();
  await expect(prepare).toBeDisabled();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const beta = projects.find((item: { name: string }) => item.name === "beta");
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("link", { name: "beta", exact: true }).click();
  await page.getByRole("tab", { name: "Settings", exact: true }).click();
  release();
  await expect(page.locator(".candidate-review")).toHaveCount(0);
  expect(count).toBe(1);
  expect(beta).toBeTruthy();
  const csrf = (await (await page.request.get("/api/v1/me")).json()).csrf;
  await page.request.delete("/api/v1/projects/alpha/config/pending", { headers: { "X-CSRF-Token": csrf } });
});

test("endpoint review compares complete supported connection without credential values", async ({ page }, info) => {
  await openSettings(page);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const form = page.locator(".config-form");
  await form.locator('[name="model"]').fill("local/settings-review");
  await form.locator('[name="endpoint"]').fill("https://model.local/v1");
  await form.locator('[name="auth_env"]').selectOption("OPENAI_API_KEY");
  await form.locator('[name="timeout_seconds"]').fill("45");
  await form.locator('[name="ca_file"]').fill("/etc/ssl/model-ca.pem");
  await form.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  for (const value of ["https://model.local/v1", "local/settings-review", "openai-chat-completions", "OPENAI_API_KEY", "45", "/etc/ssl/model-ca.pem", "Not recorded"]) await expect(review).toContainText(value);
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  await page.setViewportSize({ width: 390, height: 844 });
  await review.screenshot({ path: info.outputPath("settings-endpoint-review-390.png") });
  await review.getByRole("button", { name: "Discard change", exact: true }).click();
});

test("Dev redacted purpose view remains read-only at 390px in both themes", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openSettings(page, "alpha", "developer");
  await expect(page.getByRole("button", { name: /^Edit / })).toHaveCount(0);
  expect(await page.locator("#project-settings").innerText()).not.toContain("Job cost cap");
  expect(await page.locator("#project-settings").innerText()).not.toContain("OPENCODE_CONFIG_CONTENT");
  await page.locator("#project-settings > .setting-groups > details > summary").first().focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("Space");
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const id = projects.find((item: { name: string }) => item.name === "alpha").id;
  for (const theme of ["light", "dark"]) {
    await page.getByRole("button", { name: /Menu/ }).click();
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "My account", exact: true }).click();
    await page.getByLabel("Theme", { exact: true }).selectOption(theme);
    await page.goto(`/projects/${id}/configuration`);
    await expect(page.locator("#project-settings")).toBeVisible();
    await page.locator("#project-settings").scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({ path: info.outputPath(`settings-${theme}-390.png`), fullPage: false });
  }
});


test("purpose guidance and single-setting flow preserve four locales", async ({ page }) => {
  await openSettings(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const id = projects.find((item: { name: string }) => item.name === "alpha").id;
  const expected = { en: "Repository and tickets", fr: "Dépôt et tickets", de: "Repository und Tickets", ro: "Depozit și tichete" };
  for (const locale of ["fr", "de", "ro", "en"] as const) {
    await page.goto("/account");
    const saved = page.waitForResponse(response => response.url().endsWith("/me/preferences") && response.request().method() !== "GET");
    await page.locator(".form-stack select").first().selectOption(locale);
    await saved;
    await page.goto(`/projects/${id}/configuration`);
    await expect(page.locator("#project-settings > .setting-groups > details > summary").first()).toContainText(expected[locale]);
    await expect(page.locator(".setting-essential").first()).toBeVisible();
  }
});


test("unpaused identity candidate is blocked in the browser without an apply request", async ({ page }) => {
  await page.route("**/api/v1/projects", async route => {
    const response = await route.fetch();
    const items = await response.json();
    for (const item of items) if (item.name === "alpha") { item.paused = false; item.pickup_state = "active"; }
    await route.fulfill({ response, json: items });
  });
  await openSettings(page);
  await page.getByRole("button", { name: "Edit Repository owner and name", exact: true }).click();
  await page.locator(".setting-editor").getByRole("textbox").fill("offline/paused-required");
  await page.locator(".setting-editor").getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  await expect(review).toBeVisible();
  await expect(review.getByRole("button", { name: "Apply change", exact: true })).toBeDisabled();
  await expect(review).toContainText("Stop project pickup");
  await review.getByRole("button", { name: "Discard change", exact: true }).click();
});

test("stale base and malformed restored candidate cannot enable Apply", async ({ page }) => {
  await openSettings(page);
  await page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true }).click();
  await page.locator(".setting-editor").getByRole("spinbutton").fill("17");
  await page.locator(".setting-editor").getByRole("button", { name: "Prepare candidate" }).click();
  await expect(page.locator(".candidate-review")).toBeVisible();
  await page.route("**/projects/*/config", async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), revision: "0".repeat(64) } });
  });
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".candidate-review")).toContainText("active configuration changed");
  await expect(page.locator(".candidate-review").getByRole("button", { name: "Apply change", exact: true })).toBeDisabled();
  await page.unroute("**/projects/*/config");
  await page.route("**/projects/*/config/pending", async route => {
    if (route.request().method() !== "GET") return route.continue();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ candidate_revision: "broken" }) });
  });
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator("#project-config-editor")).toContainText("could not be verified");
  await expect(page.getByRole("button", { name: "Apply change", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Discard change", exact: true }).click();
  await expect(page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true })).toBeEnabled();
});


for (const user of ["admin", "developer"]) {
 test(`project settings keep defaults and single guidance for ${user}`, async ({ page }) => {
  await openSettings(page, "alpha", user);
  const panel = page.locator("#project-settings");
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const identity = projects.find((item: {name:string}) => item.name === "alpha").id;
  const configuration = await (await page.request.get(`/api/v1/projects/${identity}/config`)).json();
  await expect(panel.locator(".setting-row")).toHaveCount(configuration.settings.length);
  await expect(panel.locator(".setting-actions details")).toHaveCount(0);
  await expect(panel.getByRole("checkbox")).toHaveCount(0);
  await expect(panel.locator(".setting-essential")).toHaveCount(configuration.settings.length);
  await expect(panel.locator(".setting-badge").filter({hasText:"Default"}).first()).toBeVisible();
  await expect(panel.getByRole("heading", {name:"Audit retention",exact:true})).toHaveCount(0);
  if (user === "developer") await expect(panel.getByRole("button")).toHaveCount(0);
  else {
   await page.goto("/admin/status");
   await expect(page.locator(".audit-policy-form")).toBeVisible();
  }
 });
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { enrollmentCopy } from "../src/enrollmentCopy";
import { messages, type Locale } from "../src/i18n";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

async function enter(page: Page, username = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(username);
  await page.getByLabel("Password", { exact: false }).fill(username === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await page.goto("/projects/new");
}

test("guided enrollment begins with a supported method and visible step navigation", async ({ page }) => {
  await enter(page);
  await expect(page.getByRole("heading", { name: "Enrollment method", exact: true })).toBeVisible();
  await expect(page.getByText("Existing repository clone", { exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Enrollment steps" })).toBeVisible();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Repository and identity", exact: true })).toBeFocused();
  await expect(page.getByText(/already exist on the ADORE server/)).toBeVisible();
});

async function fixture(page: Page, mode = "failed") {
  const response = await page.request.post("/__e2e__/enrollment?mode=" + mode,
    { headers: { "X-ADORE-E2E": "local-test" } });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).clone as string;
}
async function repository(page: Page, name = "e2e-valid") {
  const clone = await fixture(page);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Display name", { exact: false }).fill("Offline service");
  await page.getByLabel("Stable project ID", { exact: false }).fill(name);
  await page.getByLabel("Forge", { exact: false }).selectOption("gitea");
  await page.getByLabel("Repository", { exact: false }).fill("offline/service");
  await page.getByLabel("Gitea tea login", { exact: false }).fill("fixture");
  await page.getByLabel("Local clone path", { exact: false }).fill(clone);
  return clone;
}
async function environment(page: Page) {
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel(/^Model \*/).fill("openai/fixture-model");
  await page.getByLabel("Executor image", { exact: false }).fill("fixture-image:local");
  await page.getByLabel("Credential environment references", { exact: false }).fill("LOCAL_API_KEY");
}
async function verification(page: Page, name = "e2e-valid") {
  const clone = await repository(page, name);
  await environment(page);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Reviewers", { exact: false }).fill("fixture-reviewer");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Verification", exact: true })).toBeFocused();
  return clone;
}
const validate = async (page: Page) => {
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await expect(page.getByText("Structural setup valid", { exact: true })).toBeVisible();
};

test("complete reviewed draft creates once with stopped pickup and honest failed/partial checks", async ({ page }, info) => {
  let previewBody: Record<string, unknown> = {};
  let submitted: Record<string, unknown> = {};
  let creates = 0;
  page.on("request", request => {
    if (request.url().endsWith("/setup-preview")) previewBody = request.postDataJSON();
  });
  await page.route("**/setup-create", async route => {
    creates++; submitted = route.request().postDataJSON();
    await new Promise(resolve => setTimeout(resolve, 250));
    await route.continue();
  });
  await enter(page);
  const clone = await verification(page);
  await expect(page.getByText(/Unverified — no environment/)).toBeVisible();
  await validate(page);
  await page.getByRole("button", { name: "Check environment", exact: true }).click();
  await expect(page.getByText(/Failed — correct/).first()).toBeVisible();
  await fixture(page, "partial");
  await page.getByRole("button", { name: "Recheck environment", exact: true }).click();
  await expect(page.getByText(/Partial — some prerequisites/)).toBeVisible();
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Review and create", exact: true })).toBeFocused();
  await expect(page.locator(".enrollment-review")).toContainText(["Offline service", "LOCAL_API_KEY"]);
  await expect(page.getByText(clone, { exact: true })).toHaveCount(2);
  await page.screenshot({ path: info.outputPath("enrollment-review-desktop.png"), fullPage: true });
  await page.getByRole("button", { name: "Create project with pickup stopped", exact: true }).evaluate(node => {
    (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click();
  });
  await expect(page.getByRole("heading", { name: "Enrollment complete", exact: true })).toBeFocused();
  expect(creates).toBe(1);
  const { revision, ...submittedDraft } = submitted;
  expect(revision).toMatch(/^[0-9a-f]{64}$/);
  expect(submittedDraft).toEqual(previewBody);
  await expect(page.getByText(/Activation is a separate administrator action/)).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const created = projects.find((item: { name: string }) => item.name === "e2e-valid");
  expect(created.paused).toBe(true); expect(created.pickup_state).toBe("stopped");
});

test("field summary focus, malformed fields, collision and invalid server clone/runtime recover", async ({ page }) => {
  await enter(page);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await page.getByRole("button", { name: /Stable project ID — Correct/ }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Stable project ID", { exact: false })).toBeFocused();
  await page.getByLabel("Display name", { exact: false }).fill("Service");
  await page.getByLabel("Stable project ID", { exact: false }).fill("BAD ID");
  await page.getByLabel("Repository", { exact: false }).fill("https://unsupported/repository");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Stable project ID", { exact: false })).toHaveAttribute("aria-invalid", "true");
  await page.getByLabel("Stable project ID", { exact: false }).fill("alpha");
  await page.getByLabel("Repository", { exact: false }).fill("offline/service");
  await page.getByLabel("Local clone path", { exact: false }).fill(await fixture(page));
  await environment(page);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Reviewers", { exact: false }).fill("fixture-reviewer");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("project_exists");
  await page.getByRole("button", { name: /Stable project ID — Correct/ }).click();
  await page.getByLabel("Stable project ID", { exact: false }).fill("e2e-corrections");
  await page.getByLabel("Local clone path", { exact: false }).fill("/missing-offline-clone");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Container runtime", { exact: false }).fill("invalid-runtime");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("setup_field_invalid");
  await page.getByRole("button", { name: /Local clone path — Correct/ }).click();
  await expect(page.getByLabel("Local clone path", { exact: false })).toBeFocused();
  await page.getByLabel("Local clone path", { exact: false }).fill(await fixture(page));
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await page.getByRole("button", { name: /Container runtime — Correct/ }).click();
  await expect(page.getByLabel("Container runtime", { exact: false })).toBeFocused();
  await page.getByLabel("Container runtime", { exact: false }).fill("docker");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await validate(page);
});

test("Back and review changes retain values and invalidate dependent checks", async ({ page }) => {
  await enter(page); await verification(page, "e2e-back");
  await validate(page);
  await page.getByRole("button", { name: "Check environment", exact: true }).click();
  await expect(page.getByText(/Failed — correct/).first()).toBeVisible();
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  await page.getByRole("button", { name: "Change — Repository and identity", exact: true }).click();
  await expect(page.getByLabel("Display name", { exact: false })).toHaveValue("Offline service");
  await page.getByLabel("Display name", { exact: false }).fill("Changed display");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Executor image", { exact: false })).toHaveValue("fixture-image:local");
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(page.getByLabel("Display name", { exact: false })).toHaveValue("Changed display");
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByText(/Stale — the draft changed/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Review candidate", exact: true })).toBeDisabled();
  await validate(page);
  await expect(page.getByText(/Unverified — no environment/)).toBeVisible();
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  await expect(page.locator(".enrollment-review")).toContainText(["Changed display"]);
});

test("pending preview becomes stale on upstream edit; corrupt or stale readiness cannot claim success", async ({ page }) => {
  await enter(page); await verification(page, "e2e-stale");
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/setup-preview", async route => { await gate; await route.continue(); });
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByLabel("Maximum executor launches", { exact: false }).fill("8");
  release();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("button", { name: "Review candidate", exact: true })).toBeDisabled();
  await page.unroute("**/setup-preview");
  await validate(page);
  await page.route("**/setup-check", route => route.fulfill({ status: 409, contentType: "application/json",
    body: JSON.stringify({ detail: { code: "stale_config_revision" } }) }));
  await page.getByRole("button", { name: "Check environment", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await expect(page.getByText(/Unverified — no environment/)).toBeVisible();
  await page.unroute("**/setup-check");
  await page.route("**/setup-check", async route => {
    const response = await route.fetch();
    const value = await response.json();
    await route.fulfill({ json: { ...value, status: "verified", checks: { ...value.checks, git: false } } });
  });
  await page.getByRole("button", { name: "Check environment", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(/unexpected_response|unexpected response/i);
  await expect(page.getByText(/Verified — the reported/)).toHaveCount(0);
});

test("draft loss warning protects shell, history and refresh; draft never enters browser storage", async ({ page }) => {
  await enter(page); await repository(page, "e2e-memory");
  page.once("dialog", dialog => dialog.dismiss());
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  await expect(page.getByLabel("Stable project ID", { exact: false })).toHaveValue("e2e-memory");
  const historyDialog = page.waitForEvent("dialog");
  await page.evaluate(() => history.back());
  await (await historyDialog).dismiss();
  await expect(page).toHaveURL(/\/projects\/new$/);
  await expect(page.getByLabel("Stable project ID", { exact: false })).toHaveValue("e2e-memory");
  const keys = await page.evaluate(() => ({ local: { ...localStorage }, session: { ...sessionStorage } }));
  expect(JSON.stringify(keys)).not.toContain("e2e-memory");
  let refreshWarned = false;
  page.once("dialog", dialog => { refreshWarned = dialog.type() === "beforeunload"; return dialog.accept(); });
  await page.reload();
  expect(refreshWarned).toBe(true);
  await expect(page.getByRole("heading", { name: "Enrollment method", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Stable project ID", { exact: false })).toHaveValue("");
});

test("Dev is denied setup routes and sees no enrollment controls", async ({ page }) => {
  await enter(page, "developer");
  await expect(page.getByRole("heading", { name: "Enrollment method", exact: true })).toHaveCount(0);
  const me = await (await page.request.get("/api/v1/me")).json();
  for (const route of ["setup-preview", "setup-check", "setup-create"]) {
    const response = await page.request.post("/api/v1/projects/" + route, {
      headers: { "X-CSRF-Token": me.csrf }, data: { name: "denied" } });
    expect(response.status()).toBe(403);
  }
});

test("390px keyboard guidance and review wrap in both themes", async ({ page }, info) => {
  await enter(page); await verification(page, "e2e-mobile");
  await validate(page); await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  for (const theme of ["light", "dark"]) {
    await page.evaluate(value => document.documentElement.dataset.theme = value, theme);
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    const change = page.getByRole("button", { name: "Change — Working environment", exact: true });
    await change.focus(); await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Working environment", exact: true })).toBeFocused();
    await expect(page.getByLabel("Executor image", { exact: false })).toHaveValue("fixture-image:local");
    await page.screenshot({ path: info.outputPath("enrollment-environment-" + theme + "-390.png"), fullPage: true });
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.getByRole("button", { name: "Review candidate", exact: true }).click();
    await page.screenshot({ path: info.outputPath("enrollment-review-" + theme + "-390.png"), fullPage: true });
  }
});

test("failed creation requires a deliberate new review and never automatically resubmits", async ({ page }) => {
  await enter(page); await verification(page, "e2e-create-failure"); await validate(page);
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  let attempts = 0;
  await page.route("**/setup-create", route => {
    attempts++;
    return route.fulfill({ status: 503, contentType: "application/json",
      body: JSON.stringify({ detail: { code: "project_creation_failed" } }) });
  });
  await page.getByRole("button", { name: "Create project with pickup stopped", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await expect(page.getByRole("heading", { name: "Enrollment complete", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Create project with pickup stopped", exact: true })).toHaveCount(0);
  expect(attempts).toBe(1);
  await page.getByRole("alert").getByRole("button", { name: "Validate setup", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Verification", exact: true })).toBeFocused();
});

for (const locale of ["en", "fr", "de", "ro"] as Locale[]) {
  test("enrollment guidance preserves locale " + locale, async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Username", { exact: false }).fill("admin");
    await page.getByLabel("Password", { exact: false }).fill("admin");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
    const me = await (await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": me.csrf }, data: { language: locale } });
    await page.goto("/projects/new");
    await expect(page.getByRole("heading", { name: enrollmentCopy[locale].steps[0], exact: true })).toBeVisible();
    await expect(page.getByText(enrollmentCopy[locale].intro, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: enrollmentCopy[locale].continue, exact: true }).click();
    await expect(page.getByText(enrollmentCopy[locale].clone, { exact: true })).toBeVisible();
    await expect(page.getByLabel(messages[locale].clonePath, { exact: false })).toBeVisible();
    // Leave the shared fixture account in the baseline language.
    await page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": me.csrf }, data: { language: "en" } });
  });
}

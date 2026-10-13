/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { dirname, join } from "node:path";
import { enrollmentCopy } from "../src/enrollmentCopy";
import { type Locale } from "../src/i18n";

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

test("guided enrollment begins at repository and identity with visible step navigation", async ({ page }) => {
  await enter(page);
  await expect(page.getByRole("heading", { name: "Repository and identity", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Enrollment method", exact: true })).toHaveCount(0);
  const steps = page.getByRole("navigation", { name: "Enrollment steps" });
  await expect(steps.getByRole("listitem")).toHaveText(["1. Repository and identity", "2. Agent and model",
    "3. Eligibility, reviewers and limits", "4. Verification", "5. Review and create"]);
  await expect(steps.locator('[aria-current="step"]')).toHaveText("1. Repository and identity");
  await expect(page.getByRole("button", { name: "Back", exact: true })).toHaveCount(0);
  await expect(page.getByText(/git clone/)).toBeVisible();
  await expect(page.getByLabel("Stable project ID", { exact: false })).toHaveCount(0);
  // One flow: a repository URL; there is no existing-clone mode.
  await expect(page.getByRole("button", { name: "Use an existing clone on this server", exact: true })).toHaveCount(0);
});

test("enrollment reads a repository URL, derives the ID and clones at creation", async ({ page }) => {
  await enter(page);
  const home = dirname(await fixture(page, "partial"));
  const proceed = page.getByRole("button", { name: "Continue", exact: true });
  const url = page.getByLabel("Repository URL", { exact: false });
  // Without a successful read the wizard cannot continue.
  await expect(proceed).toBeDisabled();
  await expect(url).toHaveAttribute("placeholder", "e.g. https://github.com/owner/repository");
  await url.fill("ssh://git@unreachable.e2e.invalid:2222/team/url-service.git");
  await page.getByRole("button", { name: "Read repository", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(/could not read this repository/);
  await expect(proceed).toBeDisabled();
  await url.fill("ssh://git@forge.e2e.invalid:2222/team/url-service.git");
  await expect(proceed).toBeDisabled();
  await page.getByRole("button", { name: "Read repository", exact: true }).click();
  await expect(proceed).toBeEnabled();
  const detected = page.getByRole("region", { name: "Detected from the repository" });
  await expect(detected).toContainText("team/url-service");
  await expect(detected).toContainText("url-service");
  // The clone folder is prefilled and can be changed.
  const clonePath = page.getByLabel("Local clone path", { exact: false });
  await expect(clonePath).toHaveValue(/repos[\\/]url-service$/);
  const custom = join(home, "repos", "custom-url-service");
  await clonePath.fill(custom);
  await expect(page.locator("#enrollment-clone-note")).toContainText("You can change the folder.");
  await expect(page.getByLabel("Forge", { exact: false })).toHaveValue("gitea");
  await expect(page.getByLabel("Gitea tea login", { exact: false })).toHaveValue("fixture");
  await expect(page.getByLabel("Target branch", { exact: false })).toHaveValue("main");
  await expect(page.getByLabel("Display name", { exact: false })).toHaveValue("url-service");
  await environment(page);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Reviewers", { exact: false }).fill("fixture-reviewer");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await validate(page);
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  await expect(page.locator(".enrollment-review").first()).toContainText("ssh://git@forge.e2e.invalid:2222/team/url-service.git");
  await expect(page.locator(".enrollment-review").first()).toContainText(custom);
  await page.getByRole("button", { name: "Create project with pickup stopped", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Enrollment complete", exact: true })).toBeFocused();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const created = projects.find((item: { name: string }) => item.name === "url-service");
  expect(created.paused).toBe(true);
});

test("guided enrollment delegates environment setup to the server operator",async({page})=>{
  await enter(page);await repository(page,"external-env");
  await page.getByRole("button",{name:"Continue",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Agent and model",exact:true})).toBeVisible();
  await expect(page.getByLabel("Execution backend",{exact:false})).toHaveCount(0);
  await expect(page.getByLabel("Executor image",{exact:false})).toHaveCount(0);
  await expect(page.getByLabel("Container runtime",{exact:false})).toHaveCount(0);
  await expect(page.getByText(/environment is prepared externally/)).toBeVisible();
});

async function fixture(page: Page, mode = "failed") {
  const response = await page.request.post("/__e2e__/enrollment?mode=" + mode,
    { headers: { "X-ADORE-E2E": "local-test" } });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).clone as string;
}
async function repository(page: Page, name = "e2e-valid") {
  await fixture(page);
  // The project ID is derived from the repository name; the clone path is the proposed one.
  await page.getByLabel("Repository URL", { exact: false }).fill(`ssh://git@forge.e2e.invalid:2222/offline/${name}.git`);
  await page.getByRole("button", { name: "Read repository", exact: true }).click();
  await expect(page.getByRole("region", { name: "Detected from the repository" })).toBeVisible();
  await page.getByLabel("Display name", { exact: false }).fill("Offline service");
  return await page.getByLabel("Local clone path", { exact: false }).inputValue();
}
async function environment(page: Page) {
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel(/^Model \*/).fill("openai/fixture-model");
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

test("complete reviewed draft creates once with stopped pickup and honest failed checks", async ({ page }, info) => {
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
  await expect(page.getByText(/Failed — correct/).first()).toBeVisible();
  await expect(page.getByText("git", {exact:true}).locator("..")).toContainText("Passed");
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

test("field summary focus, malformed fields, collision and invalid server clone recover", async ({ page }) => {
  let previewName = "";
  page.on("request", request => { if (request.url().endsWith("/setup-preview")) previewName = request.postDataJSON().name; });
  await enter(page);
  await fixture(page);
  await expect(page.getByRole("button", { name: "Continue", exact: true })).toBeDisabled();
  // A taken ID is never offered: the repository alpha derives alpha-2.
  await page.getByLabel("Repository URL", { exact: false }).fill("ssh://git@forge.e2e.invalid:2222/offline/alpha.git");
  await page.getByRole("button", { name: "Read repository", exact: true }).click();
  await expect(page.getByRole("region", { name: "Detected from the repository" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Detected from the repository" })).toContainText("alpha-2");
  const clonePath = page.getByLabel("Local clone path", { exact: false });
  const proposed = await clonePath.inputValue();
  await page.getByLabel("Display name", { exact: false }).fill("");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await page.getByRole("button", { name: /^Display name — Correct/ }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Display name", { exact: false })).toBeFocused();
  await page.getByLabel("Display name", { exact: false }).fill("Service");
  await clonePath.fill("relative/clone");
  await environment(page);
  // Reviewers are optional.
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Reviewers", { exact: false })).toHaveValue("");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button",{name:"Validate setup",exact:true}).click();
  await expect(page.getByRole("alert")).toContainText("setup_field_invalid");
  expect(previewName).toBe("alpha-2");
  await page.getByRole("button",{name:/Local clone path — Correct/}).click();
  await expect(page.getByLabel("Local clone path",{exact:false})).toBeFocused();
  await page.getByLabel("Local clone path",{exact:false}).fill(proposed);
  for(let i=0;i<3;i++) await page.getByRole("button",{name:"Continue",exact:true}).click();
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
  await expect(page.getByLabel("Executor image", { exact: false })).toHaveCount(0);
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
  await expect(page.getByLabel("Repository URL", { exact: false })).toHaveValue(/offline\/e2e-memory/);
  const historyDialog = page.waitForEvent("dialog");
  await page.evaluate(() => history.back());
  await (await historyDialog).dismiss();
  await expect(page).toHaveURL(/\/projects\/new$/);
  await expect(page.getByLabel("Repository URL", { exact: false })).toHaveValue(/offline\/e2e-memory/);
  const keys = await page.evaluate(() => ({ local: { ...localStorage }, session: { ...sessionStorage } }));
  expect(JSON.stringify(keys)).not.toContain("e2e-memory");
  let refreshWarned = false;
  page.once("dialog", dialog => { refreshWarned = dialog.type() === "beforeunload"; return dialog.accept(); });
  await page.reload();
  expect(refreshWarned).toBe(true);
  await expect(page.getByRole("heading", { name: "Repository and identity", exact: true })).toBeVisible();
  await expect(page.getByLabel("Repository URL", { exact: false })).toHaveValue("");
});

test("Dev is denied setup routes and sees no enrollment controls", async ({ page }) => {
  await enter(page, "developer");
  await expect(page.getByRole("heading", { name: "Repository and identity", exact: true })).toHaveCount(0);
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
    const change = page.getByRole("button", { name: "Change — Agent and model", exact: true });
    await change.focus(); await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Agent and model", exact: true })).toBeFocused();
    await expect(page.getByLabel("Executor image", { exact: false })).toHaveCount(0);
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
    await expect(page.getByText(enrollmentCopy[locale].urlHelp, { exact: true })).toBeVisible();
    await expect(page.getByLabel(enrollmentCopy[locale].url, { exact: false })).toBeVisible();
    // Leave the shared fixture account in the baseline language.
    await page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": me.csrf }, data: { language: "en" } });
  });
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { branchNamingCopy } from "../src/settingsCopy";

async function openSettings(page: Page, name = "alpha", user = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(user);
  await page.getByLabel("Password", { exact: false }).fill(user === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  await page.goto(`/projects/${projects.find((item: { name: string }) => item.name === name).id}/configuration`);
  await expect(page.getByRole("heading", { name: "Project settings", exact: true })).toBeVisible();
  await expect(page.locator("#project-settings > .setting-groups > details[open]")).toHaveCount(0);
  for (const summary of await page.locator("#project-settings > .setting-groups > details > summary").all()) await summary.click();
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

test("branch naming previews invalid drafts and applies both fields through exact review", async ({ page }) => {
  await openSettings(page);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const preview = page.getByRole("region", { name: "Example job branch", exact: true });
  await expect(preview).toContainText("No naming rule configured.");
  const template = page.locator('[id="setting-worktree.branch_template"]');
  await template.getByRole("button", { name: "Edit Job branch name template", exact: true }).click();
  const text = template.getByRole("textbox", { name: "Job branch name template", exact: true });
  await text.fill("feature/{unknown}-{iid}");
  await expect(preview).toContainText("Use only {slug}, {iid} and {run_id}");
  await expect(template.getByRole("button", { name: "Prepare candidate" })).toBeDisabled();
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  await text.fill("feature/{slug}-{iid}");
  await expect(preview).toContainText(`feature/${before.config.agent.slug}-1`);
  await expect(template.getByRole("button", { name: "Prepare candidate" })).toBeEnabled();
  await template.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  await expect(review).toContainText("Job branch name template");
  await expect(preview).toContainText(`feature/${before.config.agent.slug}-1`);
  await review.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(review).toHaveCount(0);
  await page.locator('[data-setting-purpose="repository"] > summary').click();
  const rule = page.locator('[id="setting-worktree.branch_rule"]');
  await rule.getByRole("button", { name: "Edit Optional branch name rule", exact: true }).click();
  const regex = rule.getByRole("textbox", { name: "Optional branch name rule", exact: true });
  await regex.fill("[");
  await expect(preview).toContainText("not a valid Python regular expression");
  await expect(rule.getByRole("button", { name: "Prepare candidate" })).toBeDisabled();
  await regex.fill("^bugfix/");
  await expect(preview).toContainText("does not match the rule");
  await regex.fill("^(?P<prefix>feature)/.*$");
  await expect(preview).toContainText("This example matches the rule.");
  await rule.getByRole("button", { name: "Prepare candidate" }).click();
  await expect(review).toContainText("Optional branch name rule");
  await review.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(review).toHaveCount(0);
  const applied = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  expect(applied.config.worktree.branch_template).toBe("feature/{slug}-{iid}");
  expect(applied.config.worktree.branch_rule).toBe("^(?P<prefix>feature)/.*$");
  // Restore the isolated profile through the same reviewed workflow, rule first.
  for (const [key, value] of [["worktree.branch_rule", before.config.worktree.branch_rule], ["worktree.branch_template", before.config.worktree.branch_template]]) {
    await page.locator('[data-setting-purpose="repository"] > summary').click();
    const row = page.locator(`[id="setting-${key}"]`);
    await row.getByRole("button").click();
    await row.getByRole("textbox").fill(value);
    await expect(row.getByRole("button", { name: "Prepare candidate" })).toBeEnabled();
    await row.getByRole("button", { name: "Prepare candidate" }).click();
    await review.getByRole("button", { name: "Apply change", exact: true }).click();
    await expect(review).toHaveCount(0);
  }
});

test("branch preview rejects corrupt and late responses before preparing a candidate", async ({ page }) => {
  await openSettings(page);
  const row = page.locator('[id="setting-worktree.branch_template"]');
  await row.getByRole("button").click();
  const editor = row.getByRole("textbox");
  const preview = page.getByRole("region", { name: "Example job branch", exact: true });
  await page.route("**/config/branch-preview", route => route.fulfill({ json: { valid: true } }));
  await editor.fill("feature/{iid}");
  await expect(preview).toContainText("Preview unavailable");
  await expect(row.getByRole("button", { name: "Prepare candidate" })).toBeDisabled();
  await page.unroute("**/config/branch-preview");
  await page.route("**/config/branch-preview", async route => {
    const response = await route.fetch();
    if (route.request().postDataJSON().template === "slow/{iid}") await new Promise(resolve => setTimeout(resolve, 700));
    await route.fulfill({ response });
  });
  const slow = page.waitForRequest(request => request.url().endsWith("/config/branch-preview") && request.postDataJSON().template === "slow/{iid}");
  await editor.fill("slow/{iid}");
  await slow;
  await editor.fill("latest/{iid}");
  await expect(preview).toContainText("latest/1");
  await page.waitForTimeout(900);
  await expect(preview).not.toContainText("slow/1");
  await expect(row.getByRole("button", { name: "Prepare candidate" })).toBeEnabled();
});

test("branch naming is read-only for developers and wraps on narrow screens", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openSettings(page, "alpha", "developer");
  const preview = page.getByRole("region", { name: "Example job branch", exact: true });
  await expect(preview).toContainText("No naming rule configured.");
  for (const key of ["worktree.branch_template", "worktree.branch_rule"]) await expect(page.locator(`[id="setting-${key}"]`).getByRole("button")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
});

test("ticket labels separate actions from collapsed status edits and retain inactive config", async ({ page }) => {
  await openSettings(page);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const panel = page.locator("#project-settings");
  await expect(panel.getByText("Ready for pickup label", { exact: true })).toBeVisible();
  await expect(panel.getByText("Clarification answered label", { exact: true })).not.toBeVisible();
  for (const key of ["labels.executor.prefix", "readiness.max_scope_hint"]) {
    expect(before.settings.some((item: { key: string }) => item.key === key)).toBe(true);
    await expect(panel.locator(`[id="help-${key}"]`)).toHaveCount(0);
  }
  const statuses = panel.locator(".status-label-settings");
  await expect(statuses).not.toHaveAttribute("open");
  await expect(statuses.locator(".setting-row")).toHaveCount(6);
  await expect(statuses.locator(".setting-row").first()).not.toBeVisible();
  await statuses.locator("summary").click();
  for (const name of ["clarify", "done", "failed", "review", "working"]) {
    await expect(statuses.getByText(`Job status: ${name} label`, { exact: true })).toBeVisible();
  }
  const row = statuses.locator(".setting-row").filter({ has: page.getByText("Job status: working label", { exact: true }) });
  await row.getByRole("button", { name: "Edit Job status: working label", exact: true }).click();
  await row.getByRole("textbox", { name: "Job status: working label", exact: true }).fill("agent-running");
  await row.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  await expect(review).toContainText("Job status: working label");
  await expect(review).toContainText("agent-running");
  await expect(review).toContainText("human publication approval");
  const unchanged = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  expect(unchanged.revision).toBe(before.revision);
  expect(unchanged.config.labels.executor.prefix).toBe(before.config.labels.executor.prefix);
  expect(unchanged.config.readiness.max_scope_hint).toBe(before.config.readiness.max_scope_hint);
  await review.getByRole("button", { name: "Discard change", exact: true }).click();
});

for (const user of ["admin", "developer"]) {
 test(`pickup defaults and revision limits preserve ${user} settings authority`, async ({ page }) => {
  await openSettings(page, "alpha", user);
  const panel = page.locator("#project-settings");
  const groups = panel.locator(":scope > .setting-groups > details");
  const limits = groups.filter({ hasText: "PR/MR and review" });
  const rules = groups.filter({ hasText: "Tickets" });
  const row = limits.locator(".setting-row").filter({ has: page.getByText("Maximum revision rounds", { exact: true }) });
  await expect(row).toHaveCount(1);
  await expect(rules.getByText("Maximum revision rounds", { exact: true })).toHaveCount(0);
  await expect(row).toContainText("5");
  await expect(row).toContainText("Initial implementation does not count");
  await expect(row).toContainText("REVIEW_LIMIT");
  const acceptance = rules.locator(".setting-row").filter({ has: page.getByText("Require ticket acceptance criteria", { exact: true }) });
  await expect(acceptance).toContainText("false");
  await expect(panel.locator('[id="help-readiness.require_known_component"]')).toHaveCount(0);
  if (user === "developer") {
   await expect(row.getByRole("button")).toHaveCount(0);
  } else {
   await row.getByRole("button", { name: "Edit Maximum revision rounds", exact: true }).click();
   await expect(row.getByRole("spinbutton", { name: "Maximum revision rounds", exact: true })).toHaveAttribute("min", "1");
   await row.getByRole("spinbutton", { name: "Maximum revision rounds", exact: true }).fill("6");
   await row.getByRole("button", { name: "Prepare candidate" }).click();
   const review = page.locator(".candidate-review");
   await expect(review).toContainText("Maximum revision rounds");
   await expect(review).toContainText("REVIEW_LIMIT");
   await review.getByRole("button", { name: "Discard change", exact: true }).click();
  }
 });
}

test("ticket labels stay read-only for developers in the narrow status disclosure", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openSettings(page, "alpha", "developer");
  const statuses = page.locator(".status-label-settings");
  await expect(statuses).not.toHaveAttribute("open");
  await statuses.locator("summary").click();
  await expect(statuses.locator(".setting-row")).toHaveCount(6);
  await expect(statuses.locator(".setting-row").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /^Edit / })).toHaveCount(0);
  await expect(page.locator('[id="help-labels.executor.prefix"], [id="help-readiness.max_scope_hint"]')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
});

test("merged branch cleanup help applies to every forge", async ({ page }) => {
  await openSettings(page);
  const row = page.locator(".setting-row").filter({ has: page.getByText("Remove branch after human merge", { exact: true }) });
  await row.getByRole("button", { name: "Edit Remove branch after human merge", exact: true }).click();
  await expect(row).toContainText("GitHub, GitLab and Gitea");
  await expect(row).toContainText("published commit");
  await expect(row).toContainText("When false");
});

test("request review from edits one account per line through reviewed apply", async ({ page }) => {
  await openSettings(page);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const row = page.locator(".setting-row").filter({ has: page.getByText("Request review from", { exact: true }) });
  await expect(row).toContainText("one account per line");
  await row.getByRole("button", { name: "Edit Request review from", exact: true }).click();
  const editor = row.getByRole("textbox", { name: "Request review from", exact: true });
  await expect(editor).toHaveValue(before.config.delivery.reviewers.join("\n"));
  await expect(editor).toHaveAttribute("rows", "6");
  await editor.fill("alice\nbob.smith");
  await row.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  await expect(review).toContainText("Request review from");
  await expect(review).toContainText("alice");
  await expect(review).toContainText("bob.smith");
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  await review.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(review).toHaveCount(0);
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).config.delivery.reviewers).toEqual(["alice", "bob.smith"]);
  // Restore the independent test profile using the same reviewed workflow.
  await page.locator("#project-settings > .setting-groups > details > summary").filter({ hasText: "PR/MR and review" }).click();
  await row.getByRole("button", { name: "Edit Request review from", exact: true }).click();
  await editor.fill(before.config.delivery.reviewers.join("\n"));
  await row.getByRole("button", { name: "Prepare candidate" }).click();
  await review.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(review).toHaveCount(0);
});

test("publication state offers draft and ready with explicit reviewed apply", async ({ page }) => {
  await openSettings(page);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const row = page.locator(".setting-row").filter({ has: page.getByText("PR/MR state at publication", { exact: true }) });
  await expect(row).toContainText("Draft");
  await row.getByRole("button", { name: "Edit PR/MR state at publication", exact: true }).click();
  const editor = row.getByRole("combobox");
  await expect(editor.getByRole("option", { name: "Draft", exact: true })).toHaveAttribute("value", "true");
  await editor.selectOption({ label: "Ready for review" });
  await row.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  await expect(review).toContainText("Draft");
  await expect(review).toContainText("Ready for review");
  await expect(review).toContainText("fresh human publication approval");
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  await review.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(review).toHaveCount(0);
  await expect(row.locator("code")).toHaveText("Ready for review");
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).config.delivery.draft).toBe(false);
  // Restore the independent test profile through the same reviewed UI.
  await page.locator("#project-settings > .setting-groups > details > summary").filter({ hasText: "PR/MR and review" }).click();
  await row.getByRole("button", { name: "Edit PR/MR state at publication", exact: true }).click();
  await row.getByRole("combobox").selectOption({ label: "Draft" });
  await row.getByRole("button", { name: "Prepare candidate" }).click();
  await review.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(row.locator("code")).toHaveText("Draft");
});

test("purpose guidance, correction, exact safe review/copy and candidate-only discard", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await openSettings(page);
  for (const category of ["Repository", "Tickets", "Implementation", "PR/MR and review", "Statistics", "Technical details"]) await expect(page.locator("#project-settings > .setting-groups > details > summary").filter({ hasText: category })).toBeVisible();
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
  await page.getByRole("tab", { name: "Executor configuration", exact: true }).click();
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const form = page.locator(".config-form");
  const model = await form.locator('[name="model"]').inputValue();
  await form.locator('[name="endpoint"]').fill("https://model.local/v1");
  await form.locator('[name="auth_env"]').selectOption("OPENAI_API_KEY");
  await form.locator('[name="timeout_seconds"]').fill("45");
  await form.locator('[name="ca_file"]').fill("/etc/ssl/model-ca.pem");
  await form.getByRole("button", { name: "Prepare candidate" }).click();
  const review = page.locator(".candidate-review");
  for (const value of ["https://model.local/v1", model, "openai-chat-completions", "OPENAI_API_KEY", "45", "/etc/ssl/model-ca.pem", "Not recorded"]) await expect(review).toContainText(value);
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
  const expected = { en: "Repository", fr: "Dépôt", de: "Repository", ro: "Repository" };
  const labelNames = {
    en: ["Ready for pickup label", "Clarification answered label", "Status labels"],
    fr: ["Étiquette de disponibilité pour la prise en charge", "Étiquette de réponse à une clarification", "Étiquettes de statut"],
    de: ["Label für aufnahmebereite Tickets", "Label für beantwortete Rückfragen", "Statuslabels"],
    ro: ["Eticheta pentru preluare", "Eticheta de răspuns la clarificări", "Etichete de stare"],
  };
  for (const locale of ["fr", "de", "ro", "en"] as const) {
    await page.goto("/account");
    const saved = page.waitForResponse(response => response.url().endsWith("/me/preferences") && response.request().method() !== "GET");
    await page.locator(".form-stack select").first().selectOption(locale);
    await saved;
    await page.goto(`/projects/${id}/configuration`);
    await expect(page.locator("#project-settings > .setting-groups > details > summary").first()).toContainText(expected[locale]);
    await page.locator("#project-settings > .setting-groups > details > summary").first().click();
    await expect(page.locator(".setting-essential").first()).toBeVisible();
    await expect(page.locator('[id="setting-worktree.branch_template"] strong')).toHaveText(branchNamingCopy[locale].template);
    await expect(page.locator('[id="setting-worktree.branch_rule"] strong')).toHaveText(branchNamingCopy[locale].rule);
    await expect(page.getByRole("region", { name: branchNamingCopy[locale].preview })).toContainText(branchNamingCopy[locale].noRule);
    const statuses = page.locator(".status-label-settings");
    const rules = page.locator("#project-settings > .setting-groups > details").filter({ has: statuses });
    await rules.locator("summary").first().click();
    await expect(page.getByText(labelNames[locale][0], { exact: true })).toBeVisible();
    await expect(page.getByText(labelNames[locale][1], { exact: true })).not.toBeVisible();
    await expect(statuses.locator("summary")).toContainText(labelNames[locale][2]);
    await expect(statuses).not.toHaveAttribute("open");
    await statuses.locator("summary").click();
    await expect(statuses.locator(".setting-row")).toHaveCount(6);
    await expect(statuses.locator(".setting-row").first()).toBeVisible();
    await expect(page.getByText(labelNames[locale][1], { exact: true })).toBeVisible();
    await expect(page.locator('[id="help-labels.executor.prefix"], [id="help-readiness.max_scope_hint"]')).toHaveCount(0);
    await expect(page.locator('[id="setting-polling.mode"], [id="help-polling.mode"]')).toHaveCount(0);
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
  await expect(page.locator("#project-settings")).toContainText("could not be verified");
  await expect(page.getByRole("button", { name: "Apply change", exact: true })).toHaveCount(0);
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:/Implementation/i}).click();
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
  await expect(panel.locator('[id="help-state.channel"]')).toHaveCount(0);
  await expect(panel.getByText("State reporting channel", {exact:true})).toHaveCount(0);
  const stateFolder = panel.locator(".setting-row").filter({has:page.getByText("Durable job state folder", {exact:true})});
  await expect(stateFolder).toBeVisible();
  await expect(stateFolder).toContainText(configuration.config.state.store_root);
  await expect(stateFolder.getByRole("button")).toHaveCount(0);
  const hidden = ["state.channel", "labels.executor.prefix", "readiness.max_scope_hint", "labels.selection.type_feature", "review.trigger", "review.review_reminder_after", "clarification.reminder_after", "clarification.timeout_state", "metrics.capture_resource", "reconcile.on_ticket_closed", "reconcile.on_ticket_deleted", "reconcile.on_trigger_removed", "executor.mode"];
  const shown = configuration.settings.filter((s:{key:string}) => !hidden.includes(s.key) && !["executor.", "container.", "execution.", "local."].some(prefix => s.key.startsWith(prefix)) && (!s.key.startsWith("worktree.") || ["worktree.repo_path", "worktree.root", "worktree.branch_template", "worktree.branch_rule"].includes(s.key)));
  await expect(panel.locator(".setting-row")).toHaveCount(shown.length);
  await expect(panel.locator(".setting-actions details")).toHaveCount(0);
  await expect(panel.getByRole("checkbox")).toHaveCount(0);
  await expect(panel.locator(".setting-essential")).toHaveCount(shown.length);
  expect((await (await page.request.get(`/api/v1/projects/${identity}/config`)).json()).revision).toBe(configuration.revision);
  await expect(panel.locator(".setting-badge").filter({hasText:"Default"}).first()).toBeVisible();
  await expect(panel.getByRole("heading", {name:"Audit retention",exact:true})).toHaveCount(0);
  if (user === "developer") await expect(panel.getByRole("button")).toHaveCount(0);
  else {
   const row = panel.locator(".setting-row").filter({has:page.getByText("Repository owner and name", {exact:true})});
   const heading = row.locator(".setting-value-heading");
   await expect(heading.getByRole("button", {name:"Edit Repository owner and name",exact:true})).toBeVisible();
   await expect(row.locator(".setting-actions")).toHaveCount(0);
   for (const width of [1280, 390]) {
    await page.setViewportSize({width,height:844});
    const description = await row.locator(":scope > div").nth(0).boundingBox();
    const value = await row.locator(":scope > div").nth(1).boundingBox();
    expect(Math.abs(description!.width - value!.width)).toBeLessThan(2);
    if (width === 1280) expect(value!.x - description!.x - description!.width).toBeGreaterThanOrEqual(24);
    else expect(Math.abs(description!.x - value!.x)).toBeLessThan(2);
    const label = await heading.locator("small").boundingBox();
    const edit = await heading.getByRole("button").boundingBox();
    expect(Math.abs(label!.y + label!.height / 2 - edit!.y - edit!.height / 2)).toBeLessThan(3);
    expect(edit!.x).toBeGreaterThan(label!.x);
   }
   await heading.getByRole("button").click();
   await expect(row.getByRole("textbox", {name:"Repository owner and name",exact:true})).toBeVisible();
   await row.getByRole("button", {name:"Cancel",exact:true}).click();
   await expect(heading.getByRole("button")).toBeVisible();
   await page.goto("/admin/status");
   await expect(page.locator(".audit-policy-form")).toBeVisible();
  }
 });
}


test("environment recipe selection is external", async ({page}) => {
  await openSettings(page);
  await expect(page.getByRole("button",{name:"Edit Reviewed preparation recipe",exact:true})).toHaveCount(0);
  await expect(page.locator(".project-image")).toHaveCount(0);
});

for (const user of ["admin", "developer"]) {
 test(`Git flow categories, branch reference and topic disclosures preserve ${user} authority`, async ({page}) => {
  await openSettings(page, "alpha", user);
  const panel = page.locator("#project-settings");
  const groups = panel.locator(":scope > .setting-groups > details");
  expect(await groups.locator(":scope > summary").allTextContents()).toEqual([
   expect.stringMatching(/^Repository /), expect.stringMatching(/^Tickets /), expect.stringMatching(/^Implementation /),
   expect.stringMatching(/^PR\/MR and review /), expect.stringMatching(/^Statistics /), expect.stringMatching(/^Technical details /),
  ]);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  expect(before.config.polling.mode).toBe("loop");
  const category = (name:string) => groups.filter({has: page.locator(`summary`).filter({hasText: new RegExp(`^${name} \\(`)})});
  const placements = {
   Repository: ["platform.repo", "agent.email", "delivery.target_branch", "worktree.branch_template", "worktree.branch_rule"],
   Tickets: ["labels.control.hold", "labels.control.exclude", "polling.poll_interval_seconds", "polling.poll_jitter_seconds", "polling.poll_backoff", "readiness.require_acceptance_criteria"],
   Implementation: ["budgets.max_cost_usd", "polling.max_concurrent_runs", "delivery.publish_checkpoints", "clarification.max_rounds", "recovery.max_stage_failures"],
   "PR/MR and review": ["review.max_review_rounds", "review.revise_label", "delivery.reviewers"],
   Statistics: ["metrics.enabled", "metrics.capture_tokens", "metrics.db_path"],
   "Technical details": ["state.store_root", "agent.slug", "worktree.repo_path", "worktree.root", "workflow.aegis_python"],
  };
  for (const [name, keys] of Object.entries(placements)) for (const key of keys) {
   if (user === "developer" && key === "budgets.max_cost_usd") continue;
   await expect(category(name).locator(`[id="setting-${key}"]`)).toHaveCount(1);
   await expect(panel.locator(`[id="setting-${key}"]`)).toHaveCount(1);
  }
  await expect(panel.locator('[id="setting-polling.mode"], [id="help-polling.mode"]')).toHaveCount(0);
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).config.polling.mode).toBe(before.config.polling.mode);
  for (const key of ["review.trigger", "review.review_reminder_after", "metrics.capture_resource", "clarification.reminder_after", "clarification.timeout_state", "reconcile.on_ticket_closed", "labels.selection.type_feature", "execution.backend", "container.image"]) await expect(panel.locator(`[id="help-${key}"]`)).toHaveCount(0);
  for (const key of ["worktree.repo_path", "worktree.root", "agent.slug", "workflow.aegis_python"]) await expect(panel.locator(`[id="setting-${key}"]`).getByRole("button")).toHaveCount(0);
  for (const topic of ["clarification", "recovery", "stageLimits", "statisticsFiles"]) {
   const disclosure = panel.locator(`[data-setting-topic="${topic}"]`);
   await expect(disclosure).not.toHaveAttribute("open");
   await disclosure.locator(":scope > summary").click();
   await expect(disclosure.locator(".setting-row").first()).toBeVisible();
  }
  const repository = category("Repository");
  await repository.locator(":scope > summary").click();
  await expect(repository).not.toHaveAttribute("open");
  await category("PR/MR and review").getByRole("link", {name:"View in Repository",exact:true}).click();
  await expect(repository).toHaveAttribute("open", "");
  await expect(panel.locator('[id="setting-delivery.target_branch"]')).toBeFocused();
  expect((await (await page.request.get("/api/v1/projects/alpha/config")).json()).revision).toBe(before.revision);
  if (user === "developer") {
   await expect(panel.getByRole("button")).toHaveCount(0);
   await expect(panel.locator('[id="setting-budgets.max_cost_usd"]')).toHaveCount(0);
  } else await expect(panel.getByRole("button", {name:"Edit Target branch",exact:true})).toHaveCount(1);
 });
}

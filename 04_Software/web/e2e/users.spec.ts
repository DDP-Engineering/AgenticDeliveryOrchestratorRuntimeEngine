/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { userCopy } from "../src/userCopy";
import { messages, type Locale } from "../src/i18n";

test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("navigation", { name: "Primary navigation", exact: true })
    .getByRole("link", { name: "Users", exact: true }).click();
});

async function identity(page: Page, username: string) {
  const creation = page.getByRole("region", { name: "Add user", exact: true });
  await creation.getByLabel("Username", { exact: true }).fill(username);
  await creation.getByLabel("Password", { exact: true }).fill("review-secret-password");
  await creation.getByRole("button", { name: "Continue to access", exact: true }).click();
  return creation;
}

test("credential inputs retain required markers and reject a seven character password", async ({ page }) => {
  const creation = page.getByRole("region", { name: "Add user", exact: true });
  await expect(creation.locator(".required-mark")).toHaveCount(3);
  await expect(creation).toContainText("Required field");
  await creation.getByLabel("Username", { exact: true }).fill("ux_short");
  await creation.getByLabel("Password", { exact: true }).fill("1234567");
  await creation.getByRole("button", { name: "Continue to access", exact: true }).click();
  await expect(creation.getByRole("heading", { name: "Identity and credentials", exact: true })).toBeVisible();
  await expect(creation.getByRole("combobox", { name: "Role", exact: true })).toHaveCount(0);
});

test("Dev creation corrects review and commits exact stable grants once without review secrets", async ({ page }) => {
  const creation = await identity(page, "ux_review_dev");
  await creation.getByRole("checkbox", { name: /alpha/ }).check();
  await creation.getByRole("button", { name: "Review account", exact: true }).click();
  await expect(creation.getByRole("heading", { name: "Review account" })).toBeFocused();
  await expect(creation).not.toContainText("review-secret-password");
  await expect(creation.locator('input[type="password"]')).toHaveCount(0);
  await creation.getByRole("button", { name: "Correct access", exact: true }).click();
  await creation.getByRole("checkbox", { name: /beta/ }).check();
  await creation.getByRole("button", { name: "Review account", exact: true }).click();
  const review = await creation.innerText();
  expect(review).toContain("alpha"); expect(review).toContain("beta");
  expect(review).toMatch(/[0-9a-f]{32}/);
  const alphaRepo = (await (await page.request.get("/api/v1/projects")).json()).find((item: { name: string }) => item.name === "alpha").repo;
  expect(review).toContain(alphaRepo);
  let calls = 0;
  page.on("request", request => { if (request.url().endsWith("/users/with-access")) calls++; });
  await creation.getByRole("button", { name: "Create reviewed account", exact: true }).dblclick();
  await expect(creation.getByRole("status")).toContainText("Account created");
  expect(calls).toBe(1);
  const accounts = await page.request.get("/api/v1/users");
  const created = (await accounts.json()).find((row: { username: string }) => row.username === "ux_review_dev");
  expect(created.project_ids).toHaveLength(2);
  expect(created.projects.sort()).toEqual(["alpha", "beta"]);
  expect(await page.evaluate(() => JSON.stringify([localStorage, sessionStorage]))).not.toContain("review-secret-password");
});

test("Admin global access and deliberate Dev with no projects are explicit reviewed choices", async ({ page }) => {
  let creation = await identity(page, "ux_review_admin");
  await creation.getByRole("combobox", { name: "Role", exact: true }).selectOption("admin");
  await expect(creation).toContainText("All projects and system administration");
  await expect(creation.getByRole("checkbox", { name: /alpha/ })).toHaveCount(0);
  await creation.getByRole("button", { name: "Review account", exact: true }).click();
  await expect(creation).toContainText("All projects and system administration");
  await creation.getByRole("button", { name: "Create reviewed account", exact: true }).click();
  await expect(creation.getByRole("status")).toContainText("Account created");
  await creation.getByRole("button", { name: "Create another user", exact: true }).click();
  creation = await identity(page, "ux_review_empty");
  await expect(creation.getByRole("button", { name: "Review account", exact: true })).toBeDisabled();
  await creation.getByRole("checkbox", { name: "Create Dev without project access", exact: true }).check();
  await creation.getByRole("button", { name: "Review account", exact: true }).click();
  await expect(creation).toContainText("No projects: deliberately selected");
  await creation.getByRole("button", { name: "Create reviewed account", exact: true }).click();
  await expect(creation.getByRole("status")).toContainText("Account created");
});

test("rejected creation retains correction and reload clears credential drafts", async ({ page }) => {
  const creation = await identity(page, "admin");
  await creation.getByRole("checkbox", { name: /alpha/ }).check();
  await creation.getByRole("button", { name: "Review account", exact: true }).click();
  await creation.getByRole("button", { name: "Create reviewed account", exact: true }).click();
  await expect(creation.getByRole("alert")).toBeVisible();
  await creation.getByRole("button", { name: "Correct identity", exact: true }).click();
  await expect(creation.getByLabel("Username", { exact: true })).toHaveValue("admin");
  await creation.getByLabel("Username", { exact: true }).fill("ux_corrected");
  await creation.getByRole("button", { name: "Continue to access", exact: true }).click();
  await expect(creation.getByRole("checkbox", { name: /alpha/ })).toBeChecked();
  await creation.getByRole("button", { name: "Review account", exact: true }).click();
  await creation.getByRole("button", { name: "Create reviewed account", exact: true }).click();
  await expect(creation.getByRole("status")).toContainText("Account created");
  await page.reload();
  await expect(page.getByLabel("Username", { exact: true })).toHaveValue("");
});

test("malformed account result fails closed and unmounted creation ignores a late result", async ({ page }) => {
  const creation = await identity(page, "ux_malformed");
  await creation.getByRole("checkbox", { name: /alpha/ }).check();
  await creation.getByRole("button", { name: "Review account", exact: true }).click();
  await page.route("**/api/v1/users/with-access", route => route.fulfill({ status: 200,
    contentType: "application/json", body: JSON.stringify({ id: 99, username: "ux_malformed", role: "admin", project_ids: [] }) }));
  await creation.getByRole("button", { name: "Create reviewed account", exact: true }).click();
  await expect(creation.getByRole("alert")).toContainText("unexpected response");
  await expect(creation.getByRole("status")).toHaveCount(0);
  await page.unroute("**/api/v1/users/with-access");
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let received!: () => void;
  const started = new Promise<void>(resolve => { received = resolve; });
  await page.route("**/api/v1/users/with-access", async route => {
    const response = await route.fetch(); received(); await held; await route.fulfill({ response });
  });
  await creation.getByRole("button", { name: "Create reviewed account", exact: true }).click();
  await started;
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  release();
  await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Account created" })).toHaveCount(0);
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Users", exact: true }).click();
  await expect(page.getByLabel("Username", { exact: true })).toHaveValue("");
});

test("assigned projects open below the account as aligned named rows", async ({ page }) => {
  const row = page.locator(".user-row").filter({ has: page.getByText("developer", { exact: true }) }).first();
  await row.getByText("Assigned projects", { exact: true }).click();
  const editor = row.locator(".membership-editor");
  const choice = editor.locator("label.access-choice").filter({ hasText: "alpha" });
  const box = (await choice.getByRole("checkbox").boundingBox())!, text = (await choice.locator("span").boundingBox())!;
  expect(Math.abs((box.y + box.height / 2) - (text.y + text.height / 2))).toBeLessThan(6);
  expect(text.x).toBeGreaterThan(box.x);
  const buttons = (await row.getByRole("button", { name: "Disable", exact: true }).boundingBox())!;
  expect((await editor.boundingBox())!.y).toBeGreaterThan(buttons.y + buttons.height - 1);
  expect(await editor.innerText()).not.toMatch(/[0-9a-f]{32}/);
  // Each choice names its forge and repository so the grant is unmistakable.
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: { name: string }) => item.name === "alpha");
  await expect(choice.locator(".access-repo")).toHaveText(`${alpha.platform} · ${alpha.repo}`);
});

test("failed access apply retains the reviewed choice for correction", async ({ page }) => {
  const row = page.locator(".user-row").filter({ has: page.getByText("developer", { exact: true }) }).first();
  await row.getByText("Assigned projects", { exact: true }).click();
  await row.getByRole("checkbox", { name: /beta/ }).uncheck();
  await row.getByRole("button", { name: "Save", exact: true }).click();
  await page.route("**/api/v1/users/*/projects", route => route.fulfill({ status: 409,
    contentType: "application/json", body: '{"detail":{"code":"project_changed"}}' }));
  const review = page.getByRole("region", { name: "Review access change", exact: true });
  await review.getByRole("button", { name: "Apply reviewed access", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("project changed");
  await expect(review).toBeVisible();
  await review.getByRole("button", { name: "Correct access", exact: true }).click();
  await expect(row.getByRole("button", { name: "Save", exact: true })).toBeEnabled();
});

test("malformed project options and account reads withhold access actions", async ({ page }) => {
  await page.route("**/api/v1/projects", route => route.fulfill({ status: 200,
    contentType: "application/json", body: '[{"id":"display-name"}]' }));
  await page.route("**/api/v1/users", route => route.fulfill({ status: 200,
    contentType: "application/json", body: '[{"id":3,"username":"unsafe","role":"developer","project_ids":"alpha"}]' }));
  await page.reload();
  const creation = await identity(page, "ux_unavailable");
  await expect(creation.getByRole("button", { name: "Review account", exact: true })).toBeDisabled();
  await expect(page.getByText("unsafe", { exact: true })).toHaveCount(0);
});

test("post-disable malformed account refresh withholds grant editors", async ({ page }) => {
  const row = page.locator(".user-row").filter({ has: page.getByText("developer", { exact: true }) }).first();
  await expect(row.getByRole("button", { name: "Disable", exact: true })).toBeVisible();
  await page.route("**/api/v1/users/*/disable", route => route.fulfill({ status: 200,
    contentType: "application/json", body: '{"ok":true}' }));
  await page.route("**/api/v1/users", route => route.fulfill({ status: 200,
    contentType: "application/json", body: '[{"id":3,"username":"unsafe","role":"developer","disabled":false,"project_ids":"alpha"}]' }));
  await row.getByRole("button", { name: "Disable", exact: true }).click();
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(page.getByText("unsafe", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Assigned projects", { exact: true })).toHaveCount(0);
});

test("review is readable with keyboard focus in four locales and both themes at 390px", async ({ page }, info) => {
  const me = await (await page.request.get("/api/v1/me")).json();
  try {
    for (const locale of ["en", "fr", "de", "ro"] as Locale[]) {
      const copy = userCopy[locale], labels = messages[locale];
      for (const theme of ["light", "dark"]) {
        expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } })).ok()).toBeTruthy();
        await page.reload();
        await page.setViewportSize({ width: 390, height: 844 });
        const creation = page.getByRole("region", { name: labels.createUser, exact: true });
        await creation.getByLabel(labels.username, { exact: true }).fill(`visual_${locale}_${theme}`);
        await creation.getByLabel(labels.password, { exact: true }).fill("visual-secret-password");
        await creation.getByRole("button", { name: copy.next, exact: true }).click();
        await creation.getByRole("checkbox", { name: /alpha/ }).check();
        await creation.getByRole("button", { name: copy.review, exact: true }).click();
        await expect(creation.getByRole("heading", { name: copy.review, exact: true })).toBeFocused();
        expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
        await expect(creation).not.toContainText("visual-secret-password");
        await page.screenshot({ path: info.outputPath(`users-${locale}-${theme}-390.png`), fullPage: true });
        if (locale === "en") {
          await page.setViewportSize({ width: 1440, height: 900 });
          expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
          await page.screenshot({ path: info.outputPath(`users-${locale}-${theme}-1440.png`), fullPage: true });
        }
      }
    }
  } finally {
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } });
  }
});

test("account and project grant edits show before after and actual result with cancel", async ({ page }) => {
  const row = page.locator(".user-row").filter({ has: page.getByText("developer", { exact: true }) }).first();
  await row.getByText("Assigned projects", { exact: true }).click();
  const beta = row.getByRole("checkbox", { name: /beta/ });
  await beta.check();
  await row.getByRole("button", { name: "Save", exact: true }).click();
  const review = page.getByRole("region", { name: "Review access change", exact: true });
  await expect(review).toContainText("Before"); await expect(review).toContainText("After");
  await review.getByRole("button", { name: "Correct access", exact: true }).click();
  await expect(review).toHaveCount(0);
  await row.getByRole("button", { name: "Save", exact: true }).click();
  await review.getByRole("button", { name: "Apply reviewed access", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Access updated" })).toBeVisible();
  const account = (await (await page.request.get("/api/v1/users")).json()).find((u: {username: string}) => u.username === "developer");
  expect(account.projects).toContain("beta");
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("link", { name: "beta", exact: true }).click();
  await page.getByRole("tab", { name: "Access", exact: true }).click();
  await page.getByRole("button", { name: "Remove access: developer", exact: true }).click();
  await expect(review).toContainText("Before"); await expect(review).toContainText("After");
  await review.getByRole("button", { name: "Apply reviewed access", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: /Access updated/ })).toBeVisible();
});

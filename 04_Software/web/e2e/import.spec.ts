/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { importCopy } from "../src/importCopy";
import { enrollmentCopy } from "../src/enrollmentCopy";
import { messages, type Locale } from "../src/i18n";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});
async function enter(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await page.goto("/projects/import");
}
async function upload(page: Page, name: string, bad = false) {
  const response = await page.request.post("/__e2e__/enrollment?mode=failed",
    { headers: { "X-ADORE-E2E": "local-test" } });
  const clone = ((await response.json()).clone as string).replaceAll("\\", "/");
  let text = readFileSync("../config.example.toml", "utf8").replace(/\r\n/g, "\n");
  const root = clone + "/" + name;
  for (const [old, value] of [[".adore", root + "/state"], ["../project", clone],
    ["worktrees", root + "/trees"], [".adore/metrics.db", root + "/state/metrics.db"],
    [".adore/metrics/runs.jsonl", root + "/state/runs.jsonl"],
    [".adore/metrics/stats.html", root + "/state/stats.html"]])
    text = text.replace('"' + old + '"', '"' + value + '"');
  if (bad) text += "\n[invalid\n";
  await page.getByLabel("Existing UTF-8 TOML file").setInputFiles({ name: "config.toml",
    mimeType: "text/plain", buffer: Buffer.from(text.replaceAll("\n", "\r\n")) });
  return { text: text.replaceAll("\n", "\r\n"), root, clone };
}
const next = (page: Page) => page.getByRole("button", { name: "Continue", exact: true }).click();
async function identity(page: Page, id: string) {
  await next(page);
  await page.getByLabel("Stable project ID", { exact: false }).fill(id);
  await page.getByLabel("Display name", { exact: false }).fill("Exact service");
  await next(page);
}
const validate = async (page: Page) => {
  await page.getByRole("button", { name: "Validate file", exact: true }).click();
  await expect(page.getByText("Structural configuration valid", { exact: true })).toBeVisible();
};
async function review(page: Page) {
  await next(page);
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
}

test("exact enrollment explains source, server locations, unchanged copy and stopped result", async ({ page }, info) => {
  let submits = 0;
  await page.route("**/api/v1/projects/import", async route => { submits++; await route.continue(); });
  await enter(page);
  await expect(page.getByText(/existing ADORE profile.*config.example.toml/)).toBeVisible();
  await expect(page.getByText(/file alone does not transfer historical jobs/)).toBeVisible();
  const file = await upload(page, "e2e-import-exact");
  await identity(page, "e2e-import-exact");
  await validate(page);
  await next(page);
  await page.getByRole("button", { name: "Check environment", exact: true }).click();
  await expect(page.getByText(/Failed —/).first()).toBeVisible();
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Review and enroll", exact: true })).toBeFocused();
  for (const value of [file.clone, file.root + "/state",
    file.root + "/trees", file.root + "/state/metrics.db", file.root + "/state/runs.jsonl",
    file.root + "/state/stats.html", "opencode", "docker", "Exact service"])
    await expect(page.locator(".import-review")).toContainText(value);
  await page.screenshot({ path: info.outputPath("import-review-desktop-light.png"), fullPage: true });
  await page.evaluate(() => document.documentElement.dataset.theme = "dark");
  await page.screenshot({ path: info.outputPath("import-review-desktop-dark.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => document.documentElement.dataset.theme = "light");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("import-review-mobile-light.png"), fullPage: true });
  await page.getByRole("button", { name: "Enroll with pickup stopped", exact: true }).evaluate(node => {
    (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click();
  });
  await expect(page.getByRole("heading", { name: "Enrollment complete", exact: true })).toBeFocused();
  await expect(page.getByText(/Activation is a separate/)).toBeVisible();
  expect(submits).toBe(1);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  expect(projects.find((p: { name: string }) => p.name === "e2e-import-exact").pickup_state).toBe("stopped");
});

test("Back and Change retain draft but invalidate review; failed confirmation stays actionable", async ({ page }) => {
  await enter(page); await upload(page, "e2e-import-correct");
  await identity(page, "e2e-import-correct"); await validate(page); await review(page);
  await page.getByRole("button", { name: "Change identity or source", exact: true }).click();
  await expect(page.getByLabel("Display name", { exact: false })).toHaveValue("Exact service");
  await page.getByLabel("Display name", { exact: false }).fill("Corrected service");
  await next(page);
  await expect(page.getByText(/Stale —/)).toBeVisible();
  await validate(page); await review(page);
  await expect(page.locator(".import-review")).toContainText("Corrected service");
  await page.route("**/projects/import", route => route.fulfill({ status: 409,
    json: { detail: { code: "stale_import_preview" } } }));
  await page.getByRole("button", { name: "Enroll with pickup stopped", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await expect(page.getByRole("heading", { name: "Enrollment complete", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(page.getByRole("button", { name: "Review candidate", exact: true })).toBeDisabled();
});

test("invalid file findings focus correction; replacement, loss guard and mobile dark layout", async ({ page }, info) => {
  await enter(page); await upload(page, "e2e-import-mobile", true);
  await identity(page, "e2e-import-mobile");
  await page.getByRole("button", { name: "Validate file", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await page.getByRole("button", { name: /config — Correct/ }).click();
  await expect(page.getByLabel("Existing UTF-8 TOML file")).toBeFocused();
  await upload(page, "e2e-import-mobile"); await next(page); await next(page); await validate(page); await review(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => document.documentElement.dataset.theme = "dark");
  await expect(page.getByRole("heading", { name: "Review and enroll", exact: true })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("import-review-mobile-dark.png"), fullPage: true });
  page.once("dialog", dialog => dialog.dismiss());
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.locator(".import-review")).toBeVisible();
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.goto("/projects/import");
  await expect(page.getByLabel("Existing UTF-8 TOML file")).toHaveValue("");
});

test("changed disk file rejects confirmation before any import request", async ({ page }) => {
  const directory = mkdtempSync(join(tmpdir(), "adore-import-source-"));
  const source = join(directory, "config.toml");
  try {
    await enter(page);
    const file = await upload(page, "e2e-import-changed");
    writeFileSync(source, file.text);
    await page.getByLabel("Existing UTF-8 TOML file").setInputFiles(source);
    await identity(page, "e2e-import-changed"); await validate(page); await review(page);
    writeFileSync(source, file.text + "# changed source bytes\r\n");
    let requests = 0;
    page.on("request", request => { if (request.url().endsWith("/api/v1/projects/import")) requests++; });
    await page.getByRole("button", { name: "Enroll with pickup stopped", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("source file changed or became unreadable");
    expect(requests).toBe(0);
    await expect(page.getByRole("heading", { name: "Enrollment complete", exact: true })).toHaveCount(0);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test("invalid encoding, empty file and corrupt preview fail closed with corrective focus", async ({ page }) => {
  await enter(page);
  for (const buffer of [Buffer.from([255]), Buffer.alloc(0), Buffer.alloc(524289, 32)]) {
    await page.getByLabel("Existing UTF-8 TOML file").setInputFiles({ name: "bad.toml", mimeType: "text/plain", buffer });
    await expect(page.getByRole("alert")).toBeFocused();
    await expect(page.getByRole("button", { name: "Continue", exact: true })).toBeDisabled();
  }
  await upload(page, "e2e-import-corrupt"); await identity(page, "e2e-import-corrupt");
  await page.route("**/import-preview", async route => {
    const response = await route.fetch(); const value = await response.json();
    await route.fulfill({ json: { ...value, revision: "invalid" } });
  });
  await page.getByRole("button", { name: "Validate file", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await expect(page.getByText("Structural configuration valid", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Continue", exact: true })).toBeDisabled();
});

test("late preview after cancellation, browser Back and refresh respect draft loss", async ({ page }) => {
  await enter(page); await upload(page, "e2e-import-late"); await identity(page, "e2e-import-late");
  let release!: () => void;
  const hold = new Promise<void>(resolve => release = resolve);
  const seen = new Promise<void>(resolve => {
    void page.route("**/import-preview", async route => {
      const response = await route.fetch(); resolve(); await hold;
      await route.fulfill({ response }).catch(() => {});
    });
  });
  await page.getByRole("button", { name: "Validate file", exact: true }).click(); await seen;
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "Cancel", exact: true }).click(); release();
  await page.goto("/projects/import");
  await expect(page.getByLabel("Existing UTF-8 TOML file")).toHaveValue("");
  await expect(page.getByText("Structural configuration valid", { exact: true })).toHaveCount(0);
  await page.unroute("**/import-preview");
  await upload(page, "e2e-import-loss");
  page.once("dialog", dialog => dialog.dismiss()); await page.evaluate(() => history.back());
  await expect(page.getByLabel("Existing UTF-8 TOML file")).not.toHaveValue("");
  page.once("dialog", dialog => dialog.accept()); await page.reload();
  await expect(page.getByLabel("Existing UTF-8 TOML file")).toHaveValue("");
});

test("failed or mismatched readiness never becomes a successful verification", async ({ page }) => {
  await enter(page); await upload(page, "e2e-import-evidence");
  await identity(page, "e2e-import-evidence"); await validate(page); await next(page);
  await page.route("**/import-check", route => route.fulfill({ status: 503, json: { detail: { code: "readiness_probe_failed" } } }));
  await page.getByRole("button", { name: "Check environment", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await expect(page.getByText(/Unverified —/)).toBeVisible();
  await page.unroute("**/import-check");
  await page.route("**/import-check", async route => {
    const response = await route.fetch(); const value = await response.json();
    await route.fulfill({ json: { ...value, revision: "0".repeat(64), status: "verified" } });
  });
  await page.getByRole("button", { name: "Check environment", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("unexpected");
  await expect(page.getByText(/Verified —/)).toHaveCount(0);
});

for (const locale of ["en", "fr", "de", "ro"] as Locale[]) {
  test(`exact enrollment guidance and keyboard focus are localized in ${locale}`, async ({ page }) => {
    await enter(page);
    const me = await (await page.request.get("/api/v1/me")).json();
    const configured = await page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": me.csrf }, data: { language: locale } });
    expect(configured.ok()).toBe(true);
    await page.reload();
    const c = importCopy[locale], e = enrollmentCopy[locale];
    await expect(page.getByRole("heading", { name: c.title, exact: true })).toBeVisible();
    await expect(page.getByText(c.source, { exact: true })).toBeVisible();
    await expect(page.getByText(c.history, { exact: true })).toBeVisible();
    await page.getByLabel(c.file).setInputFiles({ name: "config.toml", mimeType: "text/plain", buffer: Buffer.from("# sample") });
    await page.getByRole("button", { name: e.continue, exact: true }).focus(); await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: c.steps[1], exact: true })).toBeFocused();
    await page.getByRole("button", { name: e.continue, exact: true }).click();
    await expect(page.getByRole("alert")).toBeFocused();
    await page.getByRole("button", { name: new RegExp("^name —") }).click();
    await expect(page.getByLabel(e.id, { exact: false })).toBeFocused();
    await expect(page.getByLabel(messages[locale].description)).toBeVisible();
    const reset = await page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": me.csrf }, data: { language: "en" } });
    expect(reset.ok()).toBe(true);
  });
}

test("Dev sees no exact enrollment action and cannot enter its route", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("developer");
  await page.getByLabel("Password", { exact: false }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.goto("/projects/import");
  await expect(page.getByLabel("Existing UTF-8 TOML file")).toHaveCount(0);
  await expect(page.getByRole("button", { name: importCopy.en.title, exact: true })).toHaveCount(0);
});

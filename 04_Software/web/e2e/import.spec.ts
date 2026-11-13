/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { readFileSync, writeFileSync, mkdtempSync, rmSync, rmdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { importCopy } from "../src/importCopy";
import { environmentCopy } from "../src/environmentPreparation";
import { errorMessages } from "../src/errors";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

async function signIn(page: Page, developer = false) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(developer ? "developer" : "admin");
  await page.getByLabel("Password", { exact: false }).fill(developer ? "test-password" : "admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await page.goto("/projects");
}

const copy = importCopy.en;
const opener = (page: Page) => page.getByRole("button", { name: copy.title, exact: true });
async function open(page: Page, locale: keyof typeof importCopy = "en") {
  const c = importCopy[locale];
  await page.getByRole("button", { name: c.title, exact: true }).click();
  const dialog = page.getByRole("dialog", { name: c.title });
  await expect(dialog).toBeVisible();
  return dialog;
}

async function document(page: Page, name: string) {
  const response = await page.request.post("/__e2e__/enrollment?mode=failed",
    { headers: { "X-ADORE-E2E": "local-test" } });
  const clone = ((await response.json()).clone as string).replaceAll("\\", "/");
  const root = clone + "/" + name;
  let text = readFileSync("../config.example.toml", "utf8").replace(/\r\n/g, "\n")
    .replace("group/subgroup/project", "group/" + name);
  for (const [old, value] of [[".adore", root + "/state"], ["../project", clone],
    ["worktrees", root + "/trees"], [".adore/metrics.db", root + "/state/metrics.db"],
    [".adore/metrics/runs.jsonl", root + "/state/runs.jsonl"],
    [".adore/metrics/stats.html", root + "/state/stats.html"]]) {
    text = text.replace('"' + old + '"', '"' + value + '"');
  }
  return text.replaceAll("\n", "\r\n");
}

const choose = (page: Page, text: string | Buffer) => page.getByLabel(copy.file, { exact: true }).setInputFiles({
  name: "config.toml", mimeType: "application/toml", buffer: Buffer.from(text),
});

test("raw import shows automatic environment progress and can retry a failed build", async ({page}) => {
  await signIn(page);
  const dialog = await open(page);
  const submit = dialog.getByRole("button", {name:copy.confirm, exact:true});
  const text = await document(page, "e2e-auto-environment-retry");
  let outcome: "running" | "failed" | "ready" = "running", imports = 0;
  await page.route("**/api/v1/projects/import-environment", async route => {
    const value = await (await route.fetch()).json();
    await route.fulfill({status:202, json:{...value, status:"running", stage:"building_executor", error:null}});
  });
  await page.route("**/api/v1/environment-preparations/*", route => route.fulfill({json:{
    id:new URL(route.request().url()).pathname.split("/").at(-1), status:outcome,
    stage:outcome === "running" ? "building_executor" : outcome,
    error:outcome === "failed" ? "environment_build_failed" : null,
  }}));
  await page.route("**/api/v1/projects/import", route => { imports++; return route.continue(); });
  await choose(page, text); await expect(submit).toBeEnabled(); await submit.click();
  const progress = dialog.getByRole("region", {name:environmentCopy.en.title});
  await expect(progress).toContainText(environmentCopy.en.building_executor);
  await expect(progress.getByRole("progressbar")).toBeVisible();
  await expect(submit).toBeDisabled(); expect(imports).toBe(0);
  await expect(dialog.getByRole("button", {name:copy.cancel, exact:true})).toBeDisabled();
  outcome = "failed";
  await expect(dialog.getByRole("alert")).toContainText(errorMessages.en.environment_build_failed);
  await expect(submit).toBeEnabled(); expect(imports).toBe(0);
  outcome = "ready"; await submit.click();
  await expect(dialog).toHaveCount(0); expect(imports).toBe(1);
});

test("raw import dialog validates on file selection and enrolls the exact file", async ({ page }) => {
  await signIn(page);
  const dialog = await open(page);
  await expect(page).toHaveURL(/\/projects$/);
  const submit = dialog.getByRole("button", { name: copy.confirm, exact: true });
  await expect(submit).toBeDisabled();
  const text = await document(page, "e2e-raw-import");
  let imports = 0;
  await page.route("**/api/v1/projects/import", route => { imports++; return route.continue(); });
  await choose(page, text);
  await expect(dialog.getByRole("status")).toContainText("e2e-raw-import");
  expect(imports).toBe(0);
  await submit.evaluate(node => { (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click(); });
  await expect(dialog).toHaveCount(0);
  await expect(opener(page)).toBeFocused();
  const pageSize = page.getByRole("combobox", {name:"Rows per page"});
  if (await pageSize.count()) await pageSize.selectOption("50");
  await expect(page.getByRole("link", { name: "e2e-raw-import", exact: true })).toBeVisible();
  expect(imports).toBe(1);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const project = projects.find((item: { name: string }) => item.name === "e2e-raw-import");
  expect(project.pickup_state).toBe("stopped");
  const original = await page.request.get("/api/v1/projects/" + project.id + "/config/raw");
  expect(await original.text()).toBe(text);
});

test("raw import rejects unreadable files, invalid TOML and corrupt preview evidence", async ({ page }) => {
  await signIn(page);
  const dialog = await open(page);
  const submit = dialog.getByRole("button", { name: copy.confirm, exact: true });
  for (const invalid of [Buffer.from([255]), Buffer.alloc(0), Buffer.alloc(524289, 32)]) {
    await choose(page, invalid);
    await expect(dialog.getByRole("alert")).toHaveText(copy.invalidFile);
    await expect(submit).toBeDisabled();
  }
  await choose(page, "[invalid");
  await expect(dialog.getByRole("alert")).toContainText("config");
  await expect(submit).toBeDisabled();
  await page.route("**/api/v1/projects/import-preview", async route => {
    const response = await route.fetch();
    const preview = await response.json();
    await route.fulfill({ json: { ...preview, revision: "invalid" } });
  });
  await choose(page, await document(page, "e2e-raw-corrupt"));
  await expect(dialog.getByRole("alert")).toContainText(/unexpected/i);
  await expect(submit).toBeDisabled();
});

test("raw import explains state-folder conflicts and stale validation", async ({ page }) => {
  await signIn(page);
  const dialog = await open(page);
  const text = await document(page, "e2e-raw-remedy");
  const submit = dialog.getByRole("button", { name: copy.confirm, exact: true });
  await page.route("**/api/v1/projects/import-preview", async route => {
    const preview = await (await route.fetch()).json();
    await route.fulfill({ json: { ...preview, review: null, validation: {
      structural_valid: false, issues: [{ field: "state.store_root", code: "state_root_already_owned" }],
    } } });
  });
  await choose(page, text);
  await expect(dialog.getByRole("alert")).toContainText("Choose a state folder that is free on the server.");
  await expect(submit).toBeDisabled();
  await page.unroute("**/api/v1/projects/import-preview");
  await page.route("**/api/v1/projects/import", route => route.fulfill({
    status: 409, json: { detail: { code: "stale_import_preview" } },
  }));
  await choose(page, text);
  await submit.click();
  await expect(dialog.getByRole("alert")).toContainText("Select the file again to validate it.");
  await expect(submit).toBeDisabled();
});

test("raw import ignores a superseded preview and Escape reopens a blank dialog", async ({ page }) => {
  await signIn(page);
  const dialog = await open(page);
  const text = await document(page, "e2e-raw-replace");
  let release = () => {};
  const hold = new Promise<void>(resolve => { release = resolve; });
  let previews = 0;
  await page.route("**/api/v1/projects/import-preview", async route => {
    if (++previews !== 1) return route.continue();
    const response = await route.fetch();
    await hold;
    await route.fulfill({ response }).catch(() => undefined);
  });
  try {
    await choose(page, text);
    await expect.poll(() => previews).toBe(1);
    await choose(page, "[invalid");
    await expect(dialog.getByRole("alert")).toBeVisible();
    release();
    await expect(dialog.getByRole("button", { name: copy.confirm, exact: true })).toBeDisabled();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(opener(page)).toBeFocused();
    await open(page);
    await expect(page.getByLabel(copy.file, { exact: true })).toHaveValue("");
    await expect(dialog.getByRole("alert")).toHaveCount(0);
  } finally { release(); }
});

test("raw import rejects a changed disk file before publication", async ({ page }) => {
  const directory = mkdtempSync(join(tmpdir(), "adore-raw-import-"));
  const source = join(directory, "config.toml");
  try {
    await signIn(page);
    const dialog = await open(page);
    const text = await document(page, "e2e-raw-changed");
    writeFileSync(source, text);
    await page.getByLabel(copy.file, { exact: true }).setInputFiles(source);
    const submit = dialog.getByRole("button", { name: copy.confirm, exact: true });
    await expect(submit).toBeEnabled();
    writeFileSync(source, text + "# changed\r\n");
    let imports = 0;
    page.on("request", request => { if (request.url().endsWith("/api/v1/projects/import")) imports++; });
    await submit.click();
    await expect(dialog.getByRole("alert")).toHaveText(copy.changed);
    expect(imports).toBe(0);
  } finally { rmSync(source, { force: true }); rmdirSync(directory); }
});

test("raw import is administrator-only and former pages resolve to Projects", async ({ page }) => {
  await signIn(page, true);
  for (const path of ["/projects/import", "/projects/clone"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/projects$/);
    await expect(opener(page)).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
  }
});

for (const locale of ["en", "fr", "de", "ro"] as const) {
  test("raw import dialog is localized and fits 390px in " + locale, async ({ page }) => {
    await signIn(page);
    const { csrf } = await (await page.request.get("/api/v1/me")).json();
    const setLanguage = (language: string) => page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": csrf }, data: { language },
    });
    expect((await setLanguage(locale)).ok()).toBe(true);
    try {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.reload();
      const dialog = await open(page, locale);
      await expect(dialog.getByLabel(importCopy[locale].file, { exact: true })).toBeFocused();
      await expect(dialog.getByRole("button", { name: importCopy[locale].confirm, exact: true })).toBeDisabled();
      expect(await dialog.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
    } finally { expect((await setLanguage("en")).ok()).toBe(true); }
  });
}

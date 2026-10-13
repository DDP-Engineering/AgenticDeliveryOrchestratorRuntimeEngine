/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { transferCopy } from "../src/transferCopy";
import { type Locale } from "../src/i18n";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

async function selectSource(page: Page, method: "file" | "project") {
  await page.getByRole("button", { name: transferCopy.en[method], exact: true }).click();
  if (method === "project") await page.getByLabel("Source project", { exact: true }).selectOption({ label: "alpha" });
  else {
    const raw = await (await page.request.get("/api/v1/projects/alpha/config/portable-settings")).body();
    await page.getByLabel("Portable JSON file").setInputFiles({ name: "rules.json", mimeType: "application/json", buffer: raw });
  }
  await page.getByRole("button", { name: "Review source rules", exact: true }).click();
  await expect(page.getByText("polling.poll_interval_seconds", { exact: true })).toBeVisible();
}

async function target(page: Page, name: string) {
  const response = await page.request.post("/__e2e__/enrollment", { headers: { "X-ADORE-E2E": "local-test" } });
  const home = dirname((await response.json()).clone);
  await page.getByRole("button", { name: "Set up new target", exact: true }).click();
  await page.getByLabel("Repository URL", { exact: false }).fill(`ssh://git@forge.e2e.invalid:2222/transfer/${name}.git`);
  await page.getByRole("button", { name: "Read repository", exact: true }).click();
  await expect(page.getByRole("region", { name: "Detected from the repository" })).toBeVisible();
  await page.getByLabel("Display name", { exact: false }).fill("Transfer " + name);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel(/^Model \*/).fill("openai/fixture-model");
  await expect(page.getByLabel("Executor image", { exact: false })).toHaveCount(0);
  await page.getByLabel("Credential environment references", { exact: false }).fill("TARGET_API_KEY");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await expect(page.getByRole("heading", { name: "Agent and model", exact: true })).toBeVisible();
  await page.getByLabel(transferCopy.en.confirm, { exact: true }).check();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Reviewers", { exact: false }).fill("fixture-reviewer");
  await expect(page.getByLabel("Maximum executor launches", { exact: false })).toHaveAttribute("readonly", "");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await expect(page.getByText("Structural setup valid", { exact: true })).toBeVisible();
  await expect(page.getByText("Source value", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("This server value", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  return home;
}

for (const method of ["file", "project"] as const) {
  test(method + " transfer reviews mapping and creates once with independent stopped ownership", async ({ page }, info) => {
    await enter(page); await selectSource(page, method);
    await target(page, "transfer-" + method);
    await expect(page.getByRole("heading", { name: "Independent target locations" })).toBeVisible();
    await expect(page.getByText(/No jobs, history, users, grants, audit/)).toBeVisible();
    await page.screenshot({ path: info.outputPath("transfer-" + method + "-review.png"), fullPage: true });
    let creates = 0;
    await page.route("**/transfer-create", async route => { creates++; await route.continue(); });
    await page.getByRole("button", { name: "Create project with pickup stopped", exact: true }).evaluate(node => {
      (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click();
    });
    await expect(page.getByRole("heading", { name: "Enrollment complete", exact: true })).toBeFocused();
    expect(creates).toBe(1);
    const projects = await (await page.request.get("/api/v1/projects")).json();
    const created = projects.find((item: { name: string }) => item.name === "transfer-" + method);
    const source = projects.find((item: { name: string }) => item.name === "alpha");
    expect(created.id).not.toBe(source.id); expect(created.paused).toBe(true);
  });
}

test("target change/back invalidates review; actual source edit requires source rereview", async ({ page }) => {
  await enter(page); await selectSource(page, "project");
  const home = await target(page, "transfer-stale");
  await page.getByRole("button", { name: "Change — Repository and identity", exact: true }).click();
  await page.getByLabel("Display name", { exact: false }).fill("Changed target");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel(transferCopy.en.confirm)).not.toBeChecked();
  await page.getByLabel(transferCopy.en.confirm).check();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("button", { name: "Review candidate", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await page.getByRole("button", { name: "Review candidate", exact: true }).click();
  const sourcePath = join(home, "profiles", "alpha", "config.toml"), raw = await readFile(sourcePath);
  try {
    await writeFile(sourcePath, Buffer.concat([raw, Buffer.from("\n# changed after review\n")]));
    await page.getByRole("button", { name: "Create project with pickup stopped", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("Source or candidate changed");
    await expect(page.getByRole("button", { name: "Create project with pickup stopped", exact: true })).toHaveCount(0);
    page.once("dialog", dialog => dialog.accept());
    await page.getByRole("button", { name: "Review source again", exact: true }).click();
    await expect(page.getByRole("button", { name: "Review source rules", exact: true })).toBeVisible();
  } finally { await writeFile(sourcePath, raw); }
});

test("invalid file and corrupt or superseded source transport never unlock target", async ({ page }) => {
  await enter(page);
  await page.getByRole("button", { name: "From a portable settings file", exact: true }).click();
  await page.getByLabel("Portable JSON file").setInputFiles({ name: "bad.json", mimeType: "application/json", buffer: Buffer.from('{"secret":"fixture-value"}') });
  await page.getByRole("button", { name: "Review source rules", exact: true }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await expect(page.getByRole("button", { name: "Set up new target", exact: true })).toHaveCount(0);
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "From a project on this server", exact: true }).click();
  await page.getByLabel("Source project", { exact: true }).selectOption({ label: "alpha" });
  await page.route("**/transfer-source", route => route.fulfill({ status: 200, contentType: "application/json", body: '{"source_revision":"broken","settings":{}}' }));
  await page.getByRole("button", { name: "Review source rules", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: "Set up new target", exact: true })).toHaveCount(0);
  await page.unroute("**/transfer-source");
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let finished!: () => void;
  const done = new Promise<void>(resolve => { finished = resolve; });
  await page.route("**/transfer-source", async route => { await gate; await route.continue(); finished(); });
  await page.getByRole("button", { name: "Review source rules", exact: true }).click();
  await page.getByLabel("Source project", { exact: true }).selectOption({ label: "beta" });
  release(); await done;
  await page.unroute("**/transfer-source");
  await expect(page.getByRole("button", { name: "Set up new target", exact: true })).toHaveCount(0);
});

test("390px keyboard mapping wraps in light and dark themes", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enter(page); await selectSource(page, "file"); await target(page, "transfer-mobile");
  for (const theme of ["light", "dark"]) {
    await page.evaluate(value => document.documentElement.dataset.theme = value, theme);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole("button", { name: "Create project with pickup stopped", exact: true }).focus();
    await expect(page.getByRole("button", { name: "Create project with pickup stopped", exact: true })).toBeFocused();
    await page.screenshot({ path: info.outputPath("transfer-" + theme + "-390.png"), fullPage: true });
  }
});

test("changed selected file rejects confirmation", async ({ page }) => {
  await enter(page);
  const fixture = await page.request.post("/__e2e__/enrollment", { headers: { "X-ADORE-E2E": "local-test" } });
  const home = dirname((await fixture.json()).clone), filePath = join(home, "transfer-selected.json");
  const raw = await (await page.request.get("/api/v1/projects/alpha/config/portable-settings")).body();
  await writeFile(filePath, raw);
  await page.getByRole("button", { name: "From a portable settings file", exact: true }).click();
  await page.getByLabel("Portable JSON file").setInputFiles(filePath);
  await page.getByRole("button", { name: "Review source rules", exact: true }).click();
  await expect(page.getByText("polling.poll_interval_seconds", { exact: true })).toBeVisible();
  await target(page, "transfer-file-change");
  await writeFile(filePath, Buffer.concat([raw, Buffer.from(" ")]));
  let creates = 0;
  page.on("request", request => { if (request.url().endsWith("/transfer-create")) creates++; });
  await page.getByRole("button", { name: "Create project with pickup stopped", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Source or candidate changed");
  expect(creates).toBe(0);
});

test("malformed installed-default mapping blocks review", async ({ page }) => {
  await enter(page); await selectSource(page, "project"); await target(page, "transfer-mapping");
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.route("**/transfer-preview", async route => {
    const response = await route.fetch(), value = await response.json();
    value.mapping[0].server_value = { corrupt: "fixture-value" };
    await route.fulfill({ response, json: value });
  });
  await page.getByRole("button", { name: "Validate setup", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: "Review candidate", exact: true })).toBeDisabled();
});

for (const locale of ["en", "fr", "de", "ro"] as Locale[]) {
  test("portable guidance preserves locale " + locale, async ({ page }) => {
    await enter(page);
    const me = await (await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale } });
    await page.reload();
    const c = transferCopy[locale];
    await page.getByRole("button", { name: c.project, exact: true }).click();
    await expect(page.getByText(c.exclusions, { exact: true })).toBeVisible();
    await expect(page.getByLabel(c.source, { exact: true })).toBeVisible();
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en" } });
  });
}

test("Dev cannot discover portable enrollment controls or invoke either method", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("developer");
  await page.getByLabel("Password", { exact: false }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await page.goto("/projects/clone");
  await expect(page.getByRole("button", { name: "From a project on this server", exact: true })).toHaveCount(0);
  const me = await (await page.request.get("/api/v1/me")).json();
  for (const method of ["file", "project"]) {
    const response = await page.request.post("/api/v1/projects/transfer-source", {
      headers: { "X-CSRF-Token": me.csrf }, data: { method, file_text: "bad" },
    });
    expect(response.status()).toBe(403);
  }
});

async function enter(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await page.goto("/projects/clone");
}

test("portable methods explain recognized rules and independent target setup", async ({ page }) => {
  await enter(page);
  await page.getByRole("button", { name: "From a project on this server", exact: true }).click();
  await expect(page.getByText(/No jobs, history, users, grants, audit/)).toBeVisible();
  await page.getByLabel("Source project", { exact: true }).selectOption({ label: "alpha" });
  await page.getByRole("button", { name: "Review source rules", exact: true }).click();
  await expect(page.getByText("polling.poll_interval_seconds", { exact: true })).toBeVisible();
  await expect(page.getByText(/Source revision/)).toBeVisible();
  await page.getByRole("button", { name: "Set up new target", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Repository and identity", exact: true })).toBeVisible();
});

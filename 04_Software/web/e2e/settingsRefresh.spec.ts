/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage, trackScopeReads } from "./polling";
import { discardSettings, settingsImpact, settingsSave } from "./settings-actions";
import { chatgptCopy } from "../src/chatgptCopy";
import { settingsSaveCopy } from "../src/settingsSave";
import { userCopy } from "../src/userCopy";

const deferred = () => { let resolve!: () => void; const promise = new Promise<void>(done => { resolve = done; }); return { promise, resolve }; };
async function hide(page: Page) {
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }); document.dispatchEvent(new Event("visibilitychange")); });
}
test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
});
test.afterEach(async ({ page }) => {
  const me = await (await page.request.get("/api/v1/me")).json();
  await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } });
  await page.goto("about:blank");
});

/** Leave a genuine App operation pending while the operator opens Settings. */
async function pendingResult(page: Page) {
  const held = deferred(); let reads = 0;
  for (const action of ["pause", "resume"]) await page.route(`**/operations/${action}`, route => route.fulfill({ json: { id: 7790, status: "pending" } }));
  await page.route("**/operations/7790", async route => { reads++; await held.promise; await route.fulfill({ json: { id: 7790, status: "succeeded" } }).catch(() => {}); });
  const id = (await (await page.request.get("/api/v1/projects")).json()).find((project: { name: string }) => project.name === "alpha").id as string;
  await page.goto(`/projects/${id}`);
  await page.getByRole("button", { name: /^(Activate|Pause) monitoring$/ }).click();
  await expect.poll(() => reads).toBe(1);
  await page.getByRole("tab", { name: "Settings", exact: true }).click();
  await expect(page.locator("#project-settings")).toBeVisible();
  return { id, held };
}

for (const kind of ["impact review", "credential draft", "price draft"] as const) test(`Settings ${kind} survives unrelated operation results without bypassing clean-only guards`, async ({ page }) => {
  const { id, held } = await pendingResult(page);
  const agent = page.locator('details[data-setting-purpose="executor"]');
  let input = page.locator("#unused");
  try {
    if (kind === "impact review") {
      await page.locator('details[data-setting-purpose="implementation"] > summary').click();
      const row = page.locator('[id="setting-budgets.max_iterations"]');
      await row.getByRole("button", { name: /^Edit / }).click();
      input = row.getByRole("spinbutton"); await input.fill("123");
      await settingsSave(page).click();
      await expect(settingsImpact(page)).toBeVisible();
    } else {
      await agent.locator(":scope > summary").click();
      if (kind === "credential draft") {
        await agent.locator('[data-setting-topic="authentication"] > summary').click();
        input = page.locator("#executor-credentials").getByLabel("API key", { exact: true });
        await input.fill("offline-credential-draft-not-a-secret");
      } else { input = agent.getByLabel("Input USD / 1M tokens", { exact: false }); await input.fill("1.23"); }
    }
    const node = await input.elementHandle();
    const focused = kind === "impact review" ? settingsImpact(page).getByRole("button", { name: "Save changes", exact: true }) : input;
    await focused.focus();
    const focus = await focused.elementHandle();
    let configuration = 0, prices = 0, writes = 0;
    page.on("request", request => {
      const path = new URL(request.url()).pathname;
      if (request.method() === "GET" && path === `/api/v1/projects/${id}/config`) configuration++;
      if (request.method() === "GET" && path === `/api/v1/projects/${id}/prices`) prices++;
      if (request.method() !== "GET" && /\/(?:pending|apply|prices|executor-credentials)$/.test(path)) writes++;
    });
    const metadata = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
    held.resolve(); await (await metadata).finished();
    await expect(page.getByRole("status").filter({ hasText: "#7790" })).toContainText("succeeded");
    const rechecked = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
    await revalidateVisiblePage(page); await (await rechecked).finished();
    await expect(input).toHaveValue(kind === "impact review" ? "123" : kind === "credential draft" ? "offline-credential-draft-not-a-secret" : "1.23");
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
    expect(await focus!.evaluate(element => element === document.activeElement)).toBe(true);
    expect({ configuration, prices, writes }).toEqual({ configuration: 0, prices: 0, writes: 0 });
    if (kind === "impact review") {
      await expect(settingsImpact(page)).toBeVisible();
      await expect(settingsImpact(page).getByRole("button", { name: "Save changes", exact: true })).toBeEnabled();
      await settingsImpact(page).getByRole("button", { name: "Keep editing", exact: true }).click();
      await discardSettings(page);
    }
  } finally { held.resolve(); }
});

for (const change of ["rename", "archive", "pickup"] as const) test(`Settings ${change} invalidates confirmation permanently until a fresh review`, async ({ page }) => {
  const items = await (await page.request.get("/api/v1/projects")).json();
  const alpha = items.find((item: { name: string }) => item.name === "alpha"), original = { ...alpha };
  await page.route("**/api/v1/projects", route => route.fulfill({ json: items }));
  await page.goto(`/projects/${alpha.id}/configuration`);
  await expect(page.locator("#project-settings")).toBeVisible();
  await page.locator('details[data-setting-purpose="implementation"] > summary').click();
  const row = page.locator('[id="setting-budgets.max_iterations"]');
  await row.getByRole("button", { name: /^Edit / }).click();
  await row.getByRole("spinbutton").fill("123");
  await settingsSave(page).click();
  const dialog = settingsImpact(page), confirm = dialog.getByRole("button", { name: "Save changes", exact: true });
  await expect(dialog).toBeVisible(); await expect(confirm).toBeEnabled();
  let writes = 0;
  await page.route("**/config/pending", route => { if (route.request().method() !== "GET") writes++; return route.continue(); });
  await page.route("**/config/apply", route => { writes++; return route.continue(); });
  const refresh = async () => {
    const response = page.waitForResponse(value => value.url().endsWith("/api/v1/projects"));
    await revalidateVisiblePage(page); await (await response).finished();
  };
  // Successful identical metadata preserves the reviewed continuation and DOM.
  const node = await confirm.elementHandle(); await confirm.focus();
  await refresh(); await expect(confirm).toBeEnabled();
  expect(await node!.evaluate(element => element === document.activeElement)).toBe(true);
  if (change === "rename") alpha.name = "renamed-alpha";
  else if (change === "archive") alpha.archived = true;
  else alpha.paused = !alpha.paused;
  await refresh();
  await expect(dialog).toBeVisible(); await expect(confirm).toBeDisabled();
  await expect(dialog.getByRole("alert")).toBeVisible();
  Object.assign(alpha, original); await refresh();
  await expect(confirm).toBeDisabled();
  // Dispatching a synthetic activation also cannot resume the invalid continuation.
  await confirm.dispatchEvent("click"); expect(writes).toBe(0);
  await dialog.getByRole("button", { name: "Keep editing", exact: true }).click();
  await expect(row.getByRole("spinbutton")).toHaveValue("123");
  await settingsSave(page).click(); await expect(settingsImpact(page)).toBeVisible();
  await expect(settingsImpact(page).getByRole("button", { name: "Save changes", exact: true })).toBeEnabled();
  await settingsImpact(page).getByRole("button", { name: "Keep editing", exact: true }).click();
  await discardSettings(page); expect(writes).toBe(0);
});

for (const locale of ["en", "fr", "de", "ro"] as const) for (const theme of ["light", "dark"] as const) test(`Settings invalid confirmation stays accessible in ${locale} ${theme} at 390px`, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const me = await (await page.request.get("/api/v1/me")).json();
  await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } });
  const items = await (await page.request.get("/api/v1/projects")).json();
  const alpha = items.find((item: { name: string }) => item.name === "alpha");
  await page.route("**/api/v1/projects", route => route.fulfill({ json: items }));
  await page.goto(`/projects/${alpha.id}/configuration`);
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  await page.locator('details[data-setting-purpose="implementation"] > summary').click();
  const row = page.locator('[id="setting-budgets.max_iterations"]');
  await row.getByRole("button").click(); await row.getByRole("spinbutton").fill("123");
  await settingsSave(page, locale).click(); await expect(settingsImpact(page)).toBeVisible();
  alpha.archived = true;
  const refreshed = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
  await revalidateVisiblePage(page); await (await refreshed).finished();
  const dialog = settingsImpact(page), copy = settingsSaveCopy[locale];
  await expect(dialog.getByRole("alert")).toHaveText(userCopy[locale].reviewChanged);
  await expect(dialog.getByRole("button", { name: copy.confirm, exact: true })).toBeDisabled();
  expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  const correct = dialog.getByRole("button", { name: copy.cancel, exact: true });
  await correct.focus(); await page.keyboard.press("Enter");
  await expect(dialog).toHaveCount(0); await expect(row.getByRole("spinbutton")).toHaveValue("123");
  await discardSettings(page, locale);
});

for (const boundary of ["preview", "pending"] as const) test(`Settings changed authority during held ${boundary} cannot reach the next write`, async ({ page }) => {
  const items = await (await page.request.get("/api/v1/projects")).json();
  const alpha = items.find((item: { name: string }) => item.name === "alpha"), original = { ...alpha };
  await page.route("**/api/v1/projects", route => route.fulfill({ json: items }));
  const held = deferred(); let preview: unknown, reached = 0, pendingWrites = 0, applyWrites = 0;
  await page.route("**/config/preview", async route => {
    preview = await (await route.fetch()).json();
    if (boundary === "preview") { reached++; await held.promise; }
    await route.fulfill({ json: preview }).catch(() => {});
  });
  await page.route("**/config/pending", async route => {
    if (route.request().method() === "GET") return route.continue();
    pendingWrites++; reached++; await held.promise;
    await route.fulfill({ json: preview }).catch(() => {});
  });
  await page.route("**/config/apply", route => { applyWrites++; return route.fulfill({ status: 409, json: { detail: { code: "stale_config_revision" } } }); });
  try {
    await page.goto(`/projects/${alpha.id}/configuration`);
    await expect(page.locator("#project-settings")).toBeVisible();
    await page.locator('details[data-setting-purpose="implementation"] > summary').click();
    const row = page.locator('[id="setting-budgets.max_iterations"]');
    await row.getByRole("button", { name: /^Edit / }).click();
    await row.getByRole("spinbutton").fill("123"); await settingsSave(page).click();
    if (boundary === "pending") {
      await expect(settingsImpact(page)).toBeVisible();
      await settingsImpact(page).getByRole("button", { name: "Save changes", exact: true }).click();
    }
    await expect.poll(() => reached).toBe(1);
    const refresh = async () => {
      const response = page.waitForResponse(value => value.url().endsWith("/api/v1/projects"));
      await revalidateVisiblePage(page); await (await response).finished();
    };
    alpha.archived = true; await refresh(); Object.assign(alpha, original); await refresh();
    held.resolve();
    await expect(settingsSave(page)).toBeEnabled();
    await expect(settingsImpact(page)).toHaveCount(0);
    await expect(row.getByRole("spinbutton")).toHaveValue("123");
    expect(pendingWrites).toBe(boundary === "pending" ? 1 : 0); expect(applyWrites).toBe(0);
    await discardSettings(page);
  } finally { held.resolve(); }
});

test("Settings owned price validation survives an unrelated operation result", async ({ page }) => {
  const { held } = await pendingResult(page), saved = deferred();
  const agent = page.locator('details[data-setting-purpose="executor"]');
  await agent.locator(":scope > summary").click();
  const prices = agent.locator(".executor-prices"), form = prices.locator("form");
  const input = form.getByLabel("Input USD / 1M tokens", { exact: false });
  await input.fill("1.23"); await form.getByLabel("Output USD / 1M tokens", { exact: false }).fill("4.56");
  let writes = 0, reads = 0, cancelled = 0;
  const rates = [{ id: 7790, executor: "pi", model: "offline-model", effective_from: "2026-11-13", input_usd_per_million: "1.23", output_usd_per_million: "4.56" }];
  await page.route("**/prices", async route => {
    if (route.request().method() === "POST") { writes++; return route.fulfill({ json: {} }); }
    reads++; await saved.promise; return route.fulfill({ json: rates }).catch(() => {});
  });
  page.on("requestfailed", request => { if (request.url().endsWith("/prices")) cancelled++; });
  try {
    await form.getByRole("button", { name: "Save", exact: true }).click();
    await expect.poll(() => reads).toBe(1);
    const metadata = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
    held.resolve(); await (await metadata).finished();
    await expect(input).toHaveValue("1.23");
    expect({ reads, writes, cancelled }).toEqual({ reads: 1, writes: 1, cancelled: 0 });
    saved.resolve();
    await expect(prices.locator("tbody")).toContainText("1.23");
    await expect(prices.locator("tbody")).toContainText("4.56");
    await expect(input).toHaveValue("");
  } finally { held.resolve(); saved.resolve(); }
});

test("Settings pending ChatGPT sign-in keeps its address and serialized status across operation results and expires once", async ({ page }) => {
  const fixture = (value: string) => page.request.post(`/__e2e__/provider?value=${value}`, { headers: { "X-ADORE-E2E": "local-test" } });
  expect((await fixture("chatgpt")).ok()).toBe(true);
  const status = deferred(), settle = trackScopeReads(page);
  let started = false, hold = false, reads = 0;
  await page.route("**/api/v1/projects/*/chatgpt-sign-in", route => { started = true; return route.fulfill({ json: { authorize_url: "https://auth.openai.com/authorize?state=offline", expires_in: 900 } }); });
  await page.route("**/api/v1/chatgpt-sign-in", async route => {
    reads++; if (hold) await status.promise;
    await route.fulfill({ json: { status: "not-signed-in", pending: started } }).catch(() => {});
  });
  const { held } = await pendingResult(page);
  try {
    await page.clock.install();
    await page.locator('details[data-setting-purpose="executor"] > summary').click();
    await page.locator('[data-setting-topic="authentication"] > summary').click();
    const panel = page.locator("#chatgpt-sign-in"), copy = chatgptCopy.en;
    await panel.getByRole("button", { name: copy.start, exact: true }).click();
    const field = panel.getByLabel(copy.field, { exact: true });
    await field.fill("http://127.0.0.1:1455/auth/callback?code=offline&state=offline"); await field.focus();
    const node = await field.elementHandle(), baseline = reads;
    hold = true; await page.clock.runFor(1000); await expect.poll(() => reads).toBe(baseline + 1);
    const metadata = page.waitForResponse(response => response.url().endsWith("/api/v1/projects"));
    held.resolve(); await (await metadata).finished();
    await revalidateVisiblePage(page); await page.clock.runFor(4000);
    expect(reads).toBe(baseline + 1);
    await expect(field).toHaveValue("http://127.0.0.1:1455/auth/callback?code=offline&state=offline");
    expect(await node!.evaluate(element => element === document.activeElement)).toBe(true);
    hold = false; status.resolve();
    await expect(panel.getByRole("link", { name: copy.link, exact: true })).toBeVisible();
    await hide(page); await settle();
    await page.clock.runFor(895001);
    await expect(field).toHaveCount(0);
    await expect(panel.getByRole("link", { name: copy.link, exact: true })).toHaveCount(0);
    await expect(panel.getByRole("button", { name: copy.start, exact: true })).toBeEnabled();
    const expired = reads;
    await revalidateVisiblePage(page); await page.clock.runFor(2000);
    expect(reads).toBe(expired);
  } finally { held.resolve(); status.resolve(); expect((await fixture("openai")).ok()).toBe(true); }
});

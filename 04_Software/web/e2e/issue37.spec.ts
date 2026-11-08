/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect } from "@playwright/test";

test("monitoring and responsive epic tickets in four languages", async ({ page, context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: {name: string}) => row.name === "alpha").id;
  await page.goto(`/projects/${alpha}`);
  await page.getByRole("button", {name: "Activate monitoring", exact: true}).click();
  await expect(page.getByRole("button", {name: "Pause monitoring", exact: true})).toBeVisible();
  await page.getByRole("button", {name: "Pause monitoring", exact: true}).click();
  await expect(page.getByRole("button", {name: "Activate monitoring", exact: true})).toBeVisible();
  await page.route("**/api/v1/projects/*/tickets", async route => {
    const response = await route.fetch(); const body = await response.json();
    body.tickets[0] = {...body.tickets[0], labels: ["epic"], startable: false, reason: "epic", can_start: false, blocked_by: "epic", adds_ready_label: false, needs_priority: false};
    await route.fulfill({response, json: body});
  });
  try {
    for (const [locale, read, details] of [["en","Read tickets","Details"],["fr","Lire les tickets","Détails"],["de","Tickets lesen","Details"],["ro","Citește tichetele","Detalii"]]) {
      await page.goto("/account");
      const language = page.getByLabel(/Language|Langue|Sprache|Limbă/);
      if (await language.inputValue() !== locale) await Promise.all([page.waitForResponse(r => r.url().endsWith("/api/v1/me/preferences") && r.request().method() === "PATCH"), language.selectOption(locale)]);
      for (const width of [1366, 390]) {
        await page.setViewportSize({width, height: 900});
        await page.goto(`/projects/${alpha}/jobs`);
        await page.getByRole("button", {name: read, exact:true}).click();
        const row = page.locator(".ticket-row").first();
        await expect(row.locator("button").first()).toBeDisabled();
        const detail = row.getByRole("button", {name:details, exact:true});
        await detail.scrollIntoViewIfNeeded(); await detail.click();
        await expect(page.locator(".ticket-detail").first()).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      }
    }
  } finally {
    await page.goto("/account");
    const language = page.getByLabel(/Language|Langue|Sprache|Limbă/);
    if (await language.inputValue() !== "en") await Promise.all([page.waitForResponse(r => r.url().endsWith("/api/v1/me/preferences") && r.request().method() === "PATCH"), language.selectOption("en")]);
  }
});

test("monitoring keeps its pending operation until its failure is observed", async ({page, context}) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/");
  await page.getByLabel("Username", {exact:false}).fill("admin");
  await page.getByLabel("Password", {exact:false}).fill("admin");
  await page.getByRole("button", {name:"Sign in", exact:true}).click();
  await expect(page.getByRole("heading", {name:"Overview", exact:true})).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: {name:string}) => row.name === "alpha").id;
  let release!: () => void; const held = new Promise<void>(resolve => {release = resolve;});
  let polled!: () => void; const firstPoll = new Promise<void>(resolve => {polled = resolve;});
  let count = 0;
  await page.route("**/operations/resume", route => {count++; return route.fulfill({json:{id:2001,status:"pending"}});});
  await page.route("**/operations/2001", async route => {polled(); await held; await route.fulfill({json:{id:2001,status:"failed",action:"resume",result:"engine rejected operation",reason:"",detail:""}}).catch(() => {});});
  try {
    await page.goto(`/projects/${alpha}`);
    const activate = page.getByRole("button", {name:"Activate monitoring",exact:true});
    await activate.click(); await firstPoll;
    await expect(activate).toBeDisabled();
    await expect(page.getByRole("status").filter({hasText:"#2001"})).toContainText("Queued commands may wait");
    expect(count).toBe(1); release();
    await expect(page.getByRole("status").filter({hasText:"#2001"})).toContainText("failed");
    await expect(activate).toBeEnabled();
  } finally {release();}
});

test("empty project overview offers enrollment without an empty table", async ({page, context}) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.route("**/api/v1/projects", route => route.request().method() === "GET" ? route.fulfill({json:[]}) : route.continue());
  await page.goto("/");
  await page.getByLabel("Username", {exact:false}).fill("admin");
  await page.getByLabel("Password", {exact:false}).fill("admin");
  await page.getByRole("button", {name:"Sign in",exact:true}).click();
  await expect(page.getByRole("button", {name:"Enroll new project",exact:true})).toBeVisible();
  await page.goto("/projects");
  await expect(page.locator(".projects-table")).toHaveCount(0);
  await expect(page.locator(".section-actions + section.panel")).toHaveCount(0);
});

test("cancel requires confirmation before a request", async ({page, context, request}) => {
  expect((await request.post("/__e2e__/jobs", {headers:{"X-ADORE-E2E":"local-test"}})).ok()).toBe(true);
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/");
  await page.getByLabel("Username", {exact:false}).fill("admin");
  await page.getByLabel("Password", {exact:false}).fill("admin");
  await page.getByRole("button", {name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Overview",exact:true})).toBeVisible();
  let submitted = 0;
  await page.route("**/operations/cancel", async route => {submitted++; expect(route.request().postDataJSON().confirmed).toBe(true); await route.fulfill({json:{id:3001,status:"pending"}});});
  await page.route("**/operations/3001", route => route.fulfill({json:{id:9999,status:"succeeded"}}));
  await page.goto("/jobs?project=alpha&run=ux-working");
  const cancel = page.locator(".detail-panel").getByRole("button", {name:"Cancel",exact:true});
  page.once("dialog", dialog => dialog.dismiss()); await cancel.click();
  expect(submitted).toBe(0);
  page.once("dialog", dialog => {expect(dialog.message()).toContain("unpublished"); void dialog.accept();});
  await cancel.click();
  await expect(page.getByText("Command status could not be read; completion is unknown.", {exact:true})).toBeVisible();
  expect(submitted).toBe(1);
});


test("system status distinguishes busy, idle and unknown activity", async ({page, context}) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/"); await page.getByLabel("Username", {exact:false}).fill("admin");
  await page.getByLabel("Password", {exact:false}).fill("admin");
  await page.getByRole("button", {name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Overview",exact:true})).toBeVisible();
  let activity = "busy";
  await page.route("**/api/v1/ready", route => route.fulfill({json:{status:"ready",worker:"ready",activity}}));
  for (const [value,label] of [["busy","Busy"],["idle","Ready"],["unknown","Activity unknown"]]) {
    activity = value; await page.goto("/admin/status");
    await expect(page.locator(".system-indicator").filter({hasText:"Control worker"})).toContainText(label);
    await expect(page.locator(".system-indicator").filter({hasText:"Control worker"})).toContainText("Queued commands may wait");
    await page.goto("/");
  }
});

test("ticket operation shows queue wait and unreadable outcome", async ({page, context}) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/"); await page.getByLabel("Username", {exact:false}).fill("admin");
  await page.getByLabel("Password", {exact:false}).fill("admin");
  await page.getByRole("button", {name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Overview",exact:true})).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row:{name:string}) => row.name === "alpha").id;
  await page.route("**/tickets/21/start", route => route.fulfill({json:{operation_id:4001,status:"pending",labels_added:[]}}));
  let release!: () => void; const held = new Promise<void>(resolve => {release = resolve;});
  await page.route("**/operations/4001", async route => {await held; await route.fulfill({json:{id:4002,status:"succeeded"}}).catch(() => {});});
  try {
    await page.goto(`/projects/${alpha}/jobs`);
    await page.getByRole("button", {name:"Read tickets",exact:true}).click();
    await page.locator(".ticket-row").filter({hasText:"#21"}).getByRole("button", {name:"Start",exact:true}).click();
    await expect(page.locator(".ticket-notice")).toContainText("Queued commands may wait");
    release(); await expect(page.locator(".ticket-notice")).toContainText("Command status could not be read; completion is unknown.");
  } finally {release();}
});

test("late monitoring submission cannot cross a sign-out", async ({page, context}) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/"); await page.getByLabel("Username", {exact:false}).fill("admin");
  await page.getByLabel("Password", {exact:false}).fill("admin");
  await page.getByRole("button", {name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Overview",exact:true})).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row:{name:string}) => row.name === "alpha").id;
  let release!: () => void; const held = new Promise<void>(resolve => {release = resolve;});
  let entered!: () => void; const sent = new Promise<void>(resolve => {entered = resolve;});
  await page.route("**/operations/resume", async route => {entered(); await held; await route.fulfill({json:{id:5001,status:"pending"}}).catch(() => {});});
  try {
    await page.goto(`/projects/${alpha}`);
    await page.getByRole("button", {name:"Activate monitoring",exact:true}).click(); await sent;
    await page.getByRole("button", {name:"Sign out",exact:true}).click();
    await expect(page.getByRole("button", {name:"Sign in",exact:true})).toBeVisible();
    release();
    await page.getByLabel("Username", {exact:false}).fill("admin");
    await page.getByLabel("Password", {exact:false}).fill("admin");
    await page.getByRole("button", {name:"Sign in",exact:true}).click();
    await expect(page.getByRole("heading", {name:"Overview",exact:true})).toBeVisible();
    await expect(page.getByRole("status").filter({hasText:"#5001"})).toHaveCount(0);
  } finally {release();}
});

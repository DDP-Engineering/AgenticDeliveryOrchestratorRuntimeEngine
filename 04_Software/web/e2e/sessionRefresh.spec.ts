/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage } from "./polling";

const deferred = () => { let resolve!: () => void; const promise = new Promise<void>(done => { resolve = done; }); return { promise, resolve }; };
const login = async (page: Page) => {
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
};
test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/"); await login(page);
});

for (const view of ["Users", "Statistics", "Jobs", "Access", "Tickets"] as const) {
  test(`${view} sign-out immediately removes protected evidence and cancels held reads before DELETE completes`, async ({ page }) => {
    const projects = await (await page.request.get("/api/v1/projects")).json();
    const alpha = projects.find((item: { name: string }) => item.name === "alpha").id;
    const url = view === "Users" ? "/admin/users" : view === "Statistics" ? `/metrics?project=${alpha}` :
      view === "Jobs" ? `/jobs?project=${alpha}&view=jobs` : view === "Access" ? `/projects/${alpha}/access` : `/jobs?project=${alpha}`;
    await page.goto(url);
    await expect(page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true })).toBeVisible();
    const resource = view === "Users" ? /\/api\/v1\/users$/ : view === "Statistics" ? /\/api\/v1\/projects\/[^/]+\/metrics\?/ :
      view === "Jobs" ? /\/api\/v1\/jobs-page\?/ : view === "Access" ? /\/api\/v1\/projects\/[^/]+\/access$/ : /\/api\/v1\/projects\/[^/]+\/tickets$/;
    const held = deferred(), started = deferred(), deletion = deferred(), deleteStarted = deferred();
    let cancelled = 0;
    page.on("requestfailed", request => { if (resource.test(request.url())) cancelled++; });
    await page.route(resource, async route => { started.resolve(); await held.promise; await route.abort().catch(() => {}); });
    await page.route("**/api/v1/session", async route => {
      if (route.request().method() !== "DELETE") return route.continue();
      deleteStarted.resolve(); await deletion.promise; await route.continue();
    });
    if (view === "Users") await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
    else if (view === "Tickets") await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    else await revalidateVisiblePage(page);
    await started.promise;
    try {
      await page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
      await deleteStarted.promise;
      await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toHaveCount(0);
      await expect.poll(() => cancelled).toBeGreaterThan(0);
      // Signing in while the old DELETE is pending could delete the new cookie.
      await expect(page.getByRole("button", { name: "Sign in", exact: true })).toHaveCount(0);
    } finally { held.resolve(); deletion.resolve(); }
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await page.unroute(resource);
    await login(page);
    await expect(page.getByText("Could not load data", { exact: true })).toHaveCount(0);
  });
}

for (const code of ["authentication_required", "admin_required", "password_change_required"]) {
  test(`detected ${code} removes all prior authority while session correction waits`, async ({ page }) => {
    await page.goto("/admin/users");
    await expect(page.locator(".user-row").first()).toBeVisible();
    const current = await (await page.request.get("/api/v1/me")).json();
    const held = deferred(), started = deferred();
    await page.route("**/api/v1/me", async route => {
      started.resolve(); await held.promise;
      await route.fulfill({ json: { ...current, user: { ...current.user, password_change_required: code === "password_change_required", role: "developer", projects: [] } } }).catch(() => {});
    });
    await page.route("**/api/v1/users", route => route.fulfill({ status: code === "authentication_required" ? 401 : 403, json: { detail: { code } } }));
    try {
      await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
      await expect(page.locator(".user-row")).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Add user", exact: true })).toHaveCount(0);
      if (code !== "authentication_required") await started.promise;
    } finally { held.resolve(); }
    if (code === "authentication_required") await expect(page.locator('input[name="username"]')).toBeVisible();
    else if (code === "password_change_required") await expect(page.locator('input[name="replacement"]')).toBeVisible();
    else {
      await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
      await expect(page.getByRole("link", { name: "Users", exact: true })).toHaveCount(0);
    }
  });
}

test("Settings price denial uses the same session boundary as owned page reads", async ({ page }) => {
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((item: { name: string }) => item.name === "alpha").id;
  await page.goto(`/projects/${alpha}/configuration`);
  await expect(page.locator("#project-settings")).toBeVisible();
  const held = deferred(), started = deferred();
  await page.route("**/api/v1/me", async route => { started.resolve(); await held.promise; await route.fulfill({ status: 401, json: { detail: { code: "authentication_required" } } }).catch(() => {}); });
  await page.route("**/api/v1/projects/*/prices", route => route.fulfill({ status: 403, json: { detail: { code: "admin_required" } } }));
  try {
    await revalidateVisiblePage(page);
    await started.promise;
    await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toHaveCount(0);
    await expect(page.locator(".settings-list")).toHaveCount(0);
  } finally { held.resolve(); }
  await expect(page.locator('input[name="username"]')).toBeVisible();
});

test("unchanged session after denial stops at explicit sign-in instead of a background denial loop", async ({ page }) => {
  await page.goto("/admin/users");
  await expect(page.locator(".user-row").first()).toBeVisible();
  let usersReads = 0;
  await page.route("**/api/v1/users", route => { usersReads++; return route.fulfill({ status: 403, json: { detail: { code: "admin_required" } } }); });
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator('input[name="username"]')).toBeVisible();
  await page.clock.install(); await page.clock.runFor(60000);
  expect(usersReads).toBe(1);
  await expect(page.locator(".user-row")).toHaveCount(0);
});

test("account change cancels old privileged reads and late results cannot restore the old account", async ({ page }) => {
  const current = await (await page.request.get("/api/v1/me")).json();
  current.user.factory_password = true;
  await page.route("**/api/v1/me", route => route.fulfill({ json: current }));
  await page.goto("/admin/users");
  await expect(page.locator(".user-row").first()).toBeVisible();
  const held = deferred(), started = deferred(); let aborted = 0;
  page.on("requestfailed", request => { if (request.url().endsWith("/users")) aborted++; });
  await page.route("**/api/v1/users", async route => { const response = await route.fetch(); started.resolve(); await held.promise; await route.fulfill({ response }).catch(() => {}); });
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click(); await started.promise;
  await page.route("**/api/v1/me", route => route.fulfill({ json: { csrf: "replacement-session", user: { ...current.user, id: 9876, username: "replacement_developer", role: "developer", projects: [], factory_password: false } } }));
  await page.route(/\/api\/v1\/projects(?:\?overview=true)?$/, route => route.fulfill({ json: [] }));
  try {
    await revalidateVisiblePage(page);
    await expect.poll(() => aborted).toBe(1);
    await expect(page.locator(".user-row")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Users", exact: true })).toHaveCount(0);
    await expect(page.getByText("replacement_developer", { exact: true }).first()).toBeVisible();
  } finally { held.resolve(); }
  await expect(page.locator(".user-row")).toHaveCount(0);
});

test("factory-session read pauses while hidden and expires closed without accepting its late success", async ({ page }) => {
  const current = await (await page.request.get("/api/v1/me")).json();
  current.user.factory_password = true;
  await page.route("**/api/v1/me", route => route.fulfill({ json: current }));
  await page.reload(); await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
  await page.clock.install();
  const held = deferred(), started = deferred(); let reads = 0;
  await page.route("**/api/v1/me", async route => { reads++; started.resolve(); await held.promise; await route.fulfill({ json: current }).catch(() => {}); });
  const hide = () => page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }); document.dispatchEvent(new Event("visibilitychange")); });
  await hide(); await page.clock.runFor(45000); expect(reads).toBe(0);
  await revalidateVisiblePage(page); await started.promise; await hide();
  try {
    await page.clock.runFor(30001);
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toHaveCount(0);
    expect(reads).toBe(1);
  } finally { held.resolve(); }
  await expect(page.locator('input[name="username"]')).toBeVisible();
});

test("malformed session authority fails closed instead of retaining the last account", async ({ page }) => {
  const current = await (await page.request.get("/api/v1/me")).json();
  current.user.factory_password = true;
  await page.route("**/api/v1/me", route => route.fulfill({ json: current }));
  await page.reload(); await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
  await page.route("**/api/v1/me", route => route.fulfill({ json: { ...current, user: { ...current.user, projects: "not-an-access-list" } } }));
  await revalidateVisiblePage(page);
  await expect(page.locator('input[name="username"]')).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toHaveCount(0);
  await expect(page.getByRole("alert")).toBeVisible();
});

test("failed server sign-out stays locally signed out without restoring the old session automatically", async ({ page }) => {
  let sessionReads = 0;
  await page.route("**/api/v1/me", route => { sessionReads++; return route.continue(); });
  await page.route("**/api/v1/session", route => route.request().method() === "DELETE"
    ? route.fulfill({ status: 503, json: { detail: { code: "request_failed" } } }) : route.continue());
  await page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
  await expect(page.locator('input[name="username"]')).toBeVisible();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.clock.install(); await page.clock.runFor(60000);
  expect(sessionReads).toBe(0);
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toHaveCount(0);
});

test("factory-session reads coalesce and a required-password transition removes the workspace", async ({ page }) => {
  const current = await (await page.request.get("/api/v1/me")).json();
  current.user.factory_password = true;
  await page.route("**/api/v1/me", route => route.fulfill({ json: current }));
  await page.reload();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toBeVisible();
  await page.clock.install();
  const held = deferred(), started = deferred(); let reads = 0;
  await page.route("**/api/v1/me", async route => { reads++; started.resolve(); await held.promise; await route.fulfill({ json: { ...current, user: { ...current.user, password_change_required: true } } }).catch(() => {}); });
  await revalidateVisiblePage(page); await started.promise;
  try {
    await page.clock.runFor(15000);
    await revalidateVisiblePage(page);
    expect(reads).toBe(1);
  } finally { held.resolve(); }
  await expect(page.locator('input[name="replacement"]')).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation", exact: true })).toHaveCount(0);
});

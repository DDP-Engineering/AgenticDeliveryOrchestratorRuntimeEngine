/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";

// Browser traffic stays on the owned test server; API calls use relative URLs.
test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

async function signIn(page: Page, username = "admin", password = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(username);
  await page.getByLabel("Password", { exact: false }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}

async function openConfiguration(page: Page, name = "alpha") {
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("link", { name, exact: true }).click();
  await page.getByRole("tab", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Project settings", exact: true })).toBeVisible();
}

test("sign in, sign out and session revocation", async ({ page }) => {
  await signIn(page);
  expect((await page.request.get("/api/v1/projects")).status()).toBe(200);
  await page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  expect((await page.request.get("/api/v1/projects")).status()).toBe(401);
});

test("anonymous and incorrect credentials cannot expose projects", async ({ page }) => {
  expect((await page.request.post("/__e2e__/shutdown")).status()).toBe(403);
  expect((await page.request.get("/api/v1/projects")).status()).toBe(401);
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("wrong-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("username or password is incorrect");
  expect((await page.request.get("/api/v1/projects")).status()).toBe(401);
  await expect(page.getByRole("navigation")).toHaveCount(0);
});

test("developer scope protects projects, configuration writes and admin routes", async ({ page }) => {
  await signIn(page, "developer", "test-password");
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
  await expect(page.getByRole("link", { name: "alpha", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "beta", exact: true })).toHaveCount(0);
  expect((await page.request.get("/api/v1/projects/beta")).status()).toBe(404);
  expect((await page.request.get("/api/v1/users")).status()).toBe(403);
  await page.getByRole("link", { name: "alpha", exact: true }).click();
  await page.getByRole("tab", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Project settings", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Edit / })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Access", exact: true })).toHaveCount(0);
  const csrf = (await (await page.request.get("/api/v1/me")).json()).csrf;
  const forbidden = await page.request.post("/api/v1/projects/alpha/config/pending", {
    headers: { "X-CSRF-Token": csrf },
    data: { key: "budgets.max_iterations", value: "12", revision: "stale" },
  });
  expect(forbidden.status()).toBe(403);
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
});

test("admin stages and applies a budget change without changing live config during review", async ({ page }) => {
  await signIn(page);
  await openConfiguration(page);
  const before = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  const value = before.config.budgets.max_iterations + 1;
  await page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true }).click();
  const editor = page.locator(".setting-editor");
  await editor.getByRole("spinbutton").fill(String(value));
  await editor.getByRole("button", { name: "Prepare candidate", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Pending configuration", exact: true })).toBeVisible();
  const staged = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  expect(staged.revision).toBe(before.revision);
  expect(staged.config.budgets.max_iterations).toBe(before.config.budgets.max_iterations);
  await page.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Pending configuration", exact: true })).toHaveCount(0);
  await expect(page.locator(".notice[role=status]")).toContainText("Configuration applied");
  const applied = await (await page.request.get("/api/v1/projects/alpha/config")).json();
  expect(applied.config.budgets.max_iterations).toBe(value);
  expect(applied.revision).not.toBe(before.revision);
  const row = page.locator(".setting-row").filter({ has: page.getByText("Maximum iterations per job", { exact: true }) });
  await expect(row.locator(".setting-badge")).toHaveText("Set for this project");
  await expect(row.locator("code").first()).toHaveText(String(value));
});

test("CSRF and expired candidate revisions fail closed", async ({ page }) => {
  await signIn(page);
  const csrf = (await (await page.request.get("/api/v1/me")).json()).csrf;
  const before = await (await page.request.get("/api/v1/projects/beta/config")).json();
  const body = { key: "budgets.max_iterations", value: "12", revision: before.revision };
  expect((await page.request.post("/api/v1/projects/beta/config/pending", { data: body })).status()).toBe(403);
  const headers = { "X-CSRF-Token": csrf };
  const staged = await page.request.post("/api/v1/projects/beta/config/pending", { headers, data: body });
  expect(staged.status()).toBe(200);
  const pending = await staged.json();
  try {
    const rejected = await page.request.post("/api/v1/projects/beta/config/apply", {
      headers, data: { candidate_revision: "0".repeat(64) },
    });
    expect(rejected.status()).toBe(409);
    expect((await rejected.json()).detail.code).toBe("stale_pending_revision");
    const unchanged = await (await page.request.get("/api/v1/projects/beta/config")).json();
    expect(unchanged.revision).toBe(before.revision);
    const applied = await page.request.post("/api/v1/projects/beta/config/apply", {
      headers, data: { candidate_revision: pending.candidate_revision },
    });
    expect(applied.status()).toBe(200);
    const stale = await page.request.post("/api/v1/projects/beta/config/pending", { headers, data: body });
    expect(stale.status()).toBe(409);
    expect((await stale.json()).detail.code).toBe("stale_config_revision");
  } finally {
    await page.request.delete("/api/v1/projects/beta/config/pending", { headers });
  }
});

test("project tab route survives reload and browser back", async ({ page }) => {
  await signIn(page);
  await openConfiguration(page);
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+\/configuration$/);
  const route = page.url();
  await page.reload();
  await expect(page.getByRole("tab", { name: "Settings", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page).toHaveURL(route);
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Jobs", exact: true }).click();
  await expect(page).toHaveURL(/\/jobs/);
  await page.goBack();
  await expect(page).toHaveURL(route);
  await expect(page.getByRole("tab", { name: "Settings", exact: true })).toHaveAttribute("aria-selected", "true");
});

test("narrow viewport menu and configuration editor remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  const menu = page.getByRole("button", { name: /Menu/ });
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await openConfiguration(page);
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await page.getByRole("button", { name: "Edit Maximum iterations per job", exact: true }).click();
  await expect(page.locator(".setting-editor").getByRole("spinbutton")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
});

test("worker processes queued requests and preserves a rejected engine exit", async ({ page }) => {
  await signIn(page, "developer", "test-password");
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Jobs", exact: true }).click();
  const assigned = await (await page.request.get("/api/v1/projects")).json();
  await page.locator("#jobs-project").selectOption(assigned[0].id);
  await page.getByRole("spinbutton", { name: "Ticket number", exact: true }).fill("42");
  const submitted = page.waitForResponse(response => response.url().endsWith("/operations/start") &&
    response.request().method() === "POST");
  await page.getByRole("button", { name: "Start job", exact: true }).click();
  const response = await submitted;
  expect(response.status()).toBe(200);
  const operation = await response.json();
  await expect.poll(async () => (await (await page.request.get(
    `/api/v1/operations/${operation.id}`)).json()).status).toBe("succeeded");
  const csrf = (await (await page.request.get("/api/v1/me")).json()).csrf;
  const headers = { "X-CSRF-Token": csrf };
  const rejected = await page.request.post("/api/v1/projects/alpha/operations/start", {
    headers, data: { ticket_iid: 0, idempotency_key: "invalid-ticket" },
  });
  expect(rejected.status()).toBe(400);
  const failed = await page.request.post("/api/v1/projects/alpha/operations/start", {
    headers, data: { ticket_iid: 43, idempotency_key: "engine-fails" },
  });
  expect(failed.status()).toBe(200);
  const failedOperation = await failed.json();
  await expect.poll(async () => (await (await page.request.get(
    `/api/v1/operations/${failedOperation.id}`)).json()).status).toBe("failed");
  const outcome = await (await page.request.get(`/api/v1/operations/${failedOperation.id}`)).json();
  expect(outcome.result).toBe("engine rejected operation");
  const replay = await page.request.post("/api/v1/projects/alpha/operations/start", {
    headers, data: { ticket_iid: 43, idempotency_key: "engine-fails" },
  });
  expect((await replay.json()).id).toBe(failedOperation.id);
});

for (const finalStatus of ["succeeded", "failed"]) {
  test(`single transient operation notification: ${finalStatus}`, async ({ page }) => {
    await signIn(page);
    await page.goto("/projects/alpha");
    const monitoring = page.getByRole("button", { name: /^(Activate|Pause) monitoring$/ });
    await expect(monitoring).toBeVisible();
    await page.clock.install();
    let status = "pending";
    await page.route("**/api/v1/projects/*/operations/*", route => route.fulfill({ json: { id: 7001, status: "pending" } }));
    await page.route("**/api/v1/operations/7001", route => route.fulfill({ json: {
      id: 7001, status, result: status === "failed" ? "engine rejected operation" : "completed",
    } }));
    await monitoring.click();
    const notice = page.locator("main .notice[role=status]");
    await expect(notice).toHaveCount(1);
    await expect(notice).toContainText("pending");
    await page.clock.fastForward(6000);
    await expect(notice).toBeVisible();
    status = finalStatus;
    await page.clock.fastForward(2000);
    await expect(notice).toContainText(finalStatus);
    if (status === "failed") await expect(notice).toContainText("engine rejected operation");
    await page.clock.fastForward(5000);
    await expect(notice).toHaveCount(0);
  });
}

test("single transient operation notification preserves polling and replacement", async ({ page }) => {
  await signIn(page);
  await page.goto("/projects/alpha");
  const monitoring = page.getByRole("button", { name: /^(Activate|Pause) monitoring$/ });
  await expect(monitoring).toBeVisible();
  await page.clock.install();
  let id = 7100;
  let status = "pending";
  let polls = 0;
  await page.route("**/api/v1/projects/*/operations/*", route => route.fulfill({ json: { id: ++id, status: "pending" } }));
  await page.route(/\/api\/v1\/operations\/710[123]$/, route => {
    polls += 1;
    return route.fulfill({ json: { id, status } });
  });
  await monitoring.click();
  const notice = page.locator("main .notice[role=status]");
  await expect(notice).toHaveCount(1);
  await notice.getByRole("button", { name: "Close", exact: true }).click();
  await expect(notice).toHaveCount(0);
  const before = polls;
  status = "succeeded";
  await page.clock.fastForward(2000);
  await expect.poll(() => polls).toBeGreaterThan(before);
  await expect(notice).toHaveCount(0);
  status = "pending";
  await monitoring.click();
  await expect(notice).toContainText("7102");
  await page.clock.fastForward(6000);
  await expect(notice).toContainText("pending");
  status = "succeeded";
  await page.clock.fastForward(2000);
  await expect(notice).toContainText("succeeded");
  await page.clock.fastForward(4000);
  status = "pending";
  await monitoring.click();
  await expect(notice).toContainText("7103");
  await page.clock.fastForward(1000);
  await expect(notice).toContainText("7103");
});

test("single transient ordinary notification replaces operation feedback", async ({ page }) => {
  await signIn(page);
  await page.goto("/projects/alpha");
  const monitoring = page.getByRole("button", { name: /^(Activate|Pause) monitoring$/ });
  await expect(monitoring).toBeVisible();
  await page.clock.install();
  await page.route("**/api/v1/projects/*/operations/*", route => route.fulfill({ json: { id: 7201, status: "succeeded" } }));
  await page.route("**/api/v1/projects/*/archive", route => route.fulfill({ json: {} }));
  await monitoring.click();
  const notice = page.locator("main .notice[role=status]");
  await expect(notice).toContainText("succeeded");
  await page.clock.fastForward(4000);
  await page.getByRole("button", { name: "Archive project", exact: true }).click();
  await expect(notice).toHaveCount(1);
  await expect(notice).toContainText("archived");
  await page.clock.fastForward(1000);
  await expect(notice).toContainText("archived");
  await page.clock.fastForward(4000);
  await expect(notice).toHaveCount(0);
});

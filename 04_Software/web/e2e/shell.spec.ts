/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

async function signIn(page: Page, username = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(username);
  await page.getByLabel("Password", { exact: false }).fill(username === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}

const nav = (page: Page) => page.getByRole("navigation", { name: "Primary navigation", exact: true });

test("shell links, project context, keyboard and deep links preserve supported navigation", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await signIn(page);
  for (const name of ["Overview", "Projects", "Jobs", "Statistics", "My account", "Users", "Change history", "System status"]) {
    await expect(nav(page).getByRole("link", { name, exact: true })).toHaveAttribute("href", /.+/);
  }
  await expect(nav(page).getByRole("link", { name: "Overview", exact: true })).toHaveAttribute("aria-current", "page");
  const projects = nav(page).getByRole("link", { name: "Projects", exact: true });
  await page.keyboard.press("Tab");
  await projects.focus();
  expect(await projects.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe("none");
  await page.keyboard.press("Enter");
  await page.getByRole("link", { name: "beta", exact: true }).click();
  const projectURL = page.url();
  const context = page.getByRole("region", { name: "Project context" });
  const betaId = projectURL.split("/projects/")[1];
  await expect(context).toContainText("beta");
  await context.getByRole("tab", { name: "Jobs", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${betaId}/jobs$`));
  await expect(context).toContainText("beta");
  await expect(page.getByRole("button", { name: "Read tickets", exact: true })).toBeVisible();
  await expect(page.locator("#job-ticket-number")).toHaveCount(0);
  await nav(page).getByRole("link", { name: "Statistics", exact: true }).click();
  await expect(page).toHaveURL(/\/metrics\?project=/);
  await expect(context).toHaveCount(0);
  await expect(page.locator("#metrics-project")).toHaveValue(betaId);
  await page.reload();
  await expect(page.locator("#metrics-project")).toHaveValue(betaId);
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/projects/${betaId}/jobs$`));
  await page.goBack();
  await expect(page).toHaveURL(projectURL);
  await nav(page).getByRole("link", { name: "My account", exact: true }).click();
  await expect(page.getByLabel("Theme", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /merge|approve|clone|pause job/i })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("approved branding stays transparent and undistorted in both themes and widths", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await signIn(page);
  for (const theme of ["light", "dark"]) {
    await nav(page).getByRole("link", { name: "My account", exact: true }).click();
    await page.getByLabel("Theme", { exact: true }).selectOption(theme);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      if (width === 390) await page.getByRole("button", { name: /Menu/ }).click();
      await nav(page).getByRole("link", { name: "Overview", exact: true }).click();
      const logo = page.getByRole("img", { name: "DDP Engineering", exact: true });
      await expect(logo).toBeVisible();
      const measured = await logo.evaluate(node => {
        const img = node as HTMLImageElement;
        const rect = img.getBoundingClientRect();
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
        const ctx = canvas.getContext("2d")!;
        ctx.drawImage(img, 0, 0);
        const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        let transparent = 0;
        for (let i = 3; i < pixels.length; i += 4) if (pixels[i] === 0) transparent++;
        return { width: img.naturalWidth, height: img.naturalHeight, ratio: rect.width / rect.height,
          transparent, background: getComputedStyle(img.closest(".sidebar")!).backgroundColor };
      });
      expect(measured.width).toBe(630); expect(measured.height).toBe(300);
      expect(measured.ratio).toBeCloseTo(2.1, 2);
      expect(measured.transparent).toBeGreaterThan(100000);
      expect(measured.background).toBe("rgb(16, 47, 41)");
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      await page.screenshot({ path: info.outputPath(`shell-${theme}-${width}.png`), fullPage: true });
      if (width === 390) {
        await page.getByRole("button", { name: /Menu/ }).click();
        await nav(page).getByRole("link", { name: "My account", exact: true }).click();
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 });
  }
  expect(errors).toEqual([]);
});

test("Dev scope denies administration and foreign projects while preserving preferences", async ({ page }) => {
  await signIn(page, "developer");
  await nav(page).getByRole("link", { name: "Jobs", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
  expect(await page.evaluate(() => scrollY)).toBe(0);
  await expect(nav(page).getByRole("link", { name: "Users", exact: true })).toHaveCount(0);
  await expect(nav(page).getByRole("button", { name: "Administration", exact: true })).toHaveCount(0);
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  expect((await page.request.get("/api/v1/users")).status()).toBe(403);
  expect((await page.request.get("/api/v1/projects/beta/config")).status()).toBe(404);
  await page.goto("/projects/beta");
  await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("region", { name: "Project context" })).toHaveCount(0);
  await nav(page).getByRole("link", { name: "My account", exact: true }).click();
  await expect(page.getByLabel("Language", { exact: true })).toBeVisible();
});

test("Dev without grants sees helpful empty state, never a failed-request substitute", async ({ page }) => {
  await signIn(page);
  const csrf = (await (await page.request.get("/api/v1/me")).json()).csrf;
  const created = await page.request.post("/api/v1/users", { headers: { "X-CSRF-Token": csrf },
    data: { username: "no_grants", password: "test-password", role: "developer" } });
  expect(created.status()).toBe(200);
  await page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
  await signIn(page, "no_grants");
  for (const view of ["Overview", "Projects", "Jobs", "Statistics"]) {
    await nav(page).getByRole("link", { name: view, exact: true }).click();
    await expect(page.getByText("No project access yet", { exact: true })).toBeVisible();
    await expect(page.getByText("Ask an administrator to grant access to an enrolled project.", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Start job", exact: true })).toHaveCount(0);
    await expect(page.locator(".stats-grid")).toHaveCount(0);
  }
  expect((await page.request.get("/api/v1/projects/alpha/runs-page")).status()).toBe(404);
  await nav(page).getByRole("link", { name: "My account", exact: true }).click();
  await expect(page.getByLabel("Theme", { exact: true })).toBeVisible();
  for (const theme of ["light", "dark"]) {
    await page.getByLabel("Theme", { exact: true }).selectOption(theme);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 844 });
      if (width === 390) await page.getByRole("button", { name: /Menu/ }).click();
      await nav(page).getByRole("link", { name: "Jobs", exact: true }).click();
      await expect(page.getByText("No project access yet", { exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      if (width === 390) await page.getByRole("button", { name: /Menu/ }).click();
      await nav(page).getByRole("link", { name: "My account", exact: true }).click();
    }
    await page.setViewportSize({ width: 1440, height: 844 });
  }
});

test("pending and failed data hide false totals and refresh recovers", async ({ page }) => {
  let failing = true;
  await page.route("**/api/v1/jobs-page?*", async route => {
    if (failing) await route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":{"code":"request_failed"}}' });
    else await route.continue();
  });
  await signIn(page);
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Active jobs", exact: true })).toHaveCount(0);
  failing = false;
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("region", { name: "Active jobs", exact: true })).toBeVisible();
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/metrics?*", async route => { await pending; await route.fulfill({ status: 200, contentType: "application/json", body: "{}" }); });
  await page.goto("/metrics");
  await expect(page.getByText("Loading data…", { exact: true })).toBeVisible();
  await expect(page.locator(".stats-grid")).toHaveCount(0);
  release();
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.locator(".stats-grid")).toHaveCount(0);
  await expect(page.getByText("Export CSV", { exact: true })).toHaveCount(0);
});

test("failed projects and corrupt metrics fail closed instead of empty or zero", async ({ page }) => {
  await page.route("**/api/v1/projects", route => route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":{"code":"request_failed"}}' }));
  await signIn(page);
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(page.getByText("No project access yet", { exact: true })).toHaveCount(0);
  await expect(page.locator(".stats-grid")).toHaveCount(0);
  await page.unroute("**/api/v1/projects");
  await page.route("**/api/v1/metrics?*", route => route.fulfill({ status: 200, contentType: "application/json", body: '{"bad":{"totals":{"runs":-1}}}' }));
  await page.goto("/metrics");
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await expect(page.locator(".stats-grid")).toHaveCount(0);
});

test("glossary defines supported human actions with essential field help visible", async ({ page }) => {
  await signIn(page);
  await page.getByText("How ADORE works", { exact: true }).click();
  await expect(page.getByText("Pickup stopped", { exact: true })).toBeVisible();
  await expect(page.getByText(/does not pause an active job/)).toBeVisible();
  await expect(page.getByText(/Approval is recorded on the forge/)).toBeVisible();
  await expect(page.getByText(/Merge remains a human decision/)).toBeVisible();
  await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("button", { name: "Add project", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Enrollment method", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.locator("#enrollment-help-forge")).toBeVisible();
  await expect(page.locator("#enrollment-help-clone")).toBeVisible();
  await expect(page.getByLabel("Local clone path", { exact: false })).toHaveAttribute("aria-describedby", "enrollment-help-clone");
});

test("pending job details cannot refill another project's view", async ({ page }) => {
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  let release!: () => void;
  let started!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  const observed = new Promise<void>(resolve => { started = resolve; });
  await page.route("**/api/v1/jobs/*/historical-job", async route => {
    const response = await route.fetch();
    started(); await pending; await route.fulfill({ response });
  });
  await page.goto("/jobs?project=alpha&run=historical-job");
  await observed;
  await page.locator("#jobs-project").selectOption(projects.find((item: { name: string }) => item.name === "beta").id);
  const completed = page.waitForResponse(response => response.url().includes("/historical-job"));
  release(); await completed;
  await expect(page.locator("#jobs-project option:checked")).toHaveText("beta");
  await expect(page.getByRole("region", { name: "Project context" })).toHaveCount(0);
  await expect(page.locator(".detail-panel")).toHaveCount(0);
  await expect(page).not.toHaveURL(/run=historical-job/);
});

test("configuration and administration request failures have explicit feedback", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/projects/*/config", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":{"code":"request_failed"}}' }));
  await page.goto("/projects/alpha/configuration");
  await expect(page.getByText("Could not load data", { exact: true }).first()).toBeVisible();
  await page.unroute("**/api/v1/projects/*/config");
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByText("Could not load data", { exact: true })).toHaveCount(0);
  await page.route("**/api/v1/users", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":{"code":"request_failed"}}' }));
  await page.goto("/admin/users");
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await page.unroute("**/api/v1/users");
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByText("Could not load data", { exact: true })).toHaveCount(0);
  await page.route("**/api/v1/audit-page?*", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":{"code":"request_failed"}}' }));
  await page.goto("/admin/audit");
  await expect(page.getByText("Could not load data", { exact: true })).toBeVisible();
  await page.unroute("**/api/v1/audit-page?*");
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByText("Could not load data", { exact: true })).toHaveCount(0);
});

test("localized shell and assigned Dev remain usable in both themes and widths", async ({ page }, info) => {
  await signIn(page, "developer");
  for (const theme of ["light", "dark"]) {
    await nav(page).getByRole("link", { name: "My account", exact: true }).click();
    await page.getByLabel("Theme", { exact: true }).selectOption(theme);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 844 });
      if (width === 390) await page.getByRole("button", { name: /Menu/ }).click();
      await nav(page).getByRole("link", { name: "Jobs", exact: true }).click();
      expect(await page.evaluate(() => scrollY)).toBe(0);
      const assigned = await (await page.request.get("/api/v1/projects")).json();
      await page.locator("#jobs-project").selectOption(assigned[0].id);
      await expect(page.locator("#jobs-project")).toHaveValue(assigned[0].id);
      await expect(page.getByRole("region", { name: "Project context" })).toHaveCount(0);
      await expect(page.locator("#jobs-project option")).toHaveCount(2);
      await expect(page.locator("#job-ticket-number-help")).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      await page.screenshot({ path: info.outputPath(`dev-jobs-${theme}-${width}.png`), fullPage: true });
      if (width === 390) await page.getByRole("button", { name: /Menu/ }).click();
      await nav(page).getByRole("link", { name: "My account", exact: true }).click();
    }
    await page.setViewportSize({ width: 1440, height: 844 });
  }
  for (const [locale, accountLabel, glossary] of [["fr", "Mon compte", "Comment fonctionne ADORE"],
    ["de", "Mein Konto", "So funktioniert ADORE"], ["ro", "Contul meu", "Cum funcționează ADORE"],
    ["en", "My account", "How ADORE works"]]) {
    const saved = page.waitForResponse(response => response.url().endsWith("/me/preferences") &&
      response.request().method() === "PATCH" && response.request().postDataJSON()?.language === locale);
    await page.locator(".content select").first().selectOption(locale);
    expect((await saved).ok()).toBe(true);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.getByRole("navigation").getByRole("link", { name: accountLabel, exact: true })).toBeVisible();
    await expect(page.getByText(glossary, { exact: true })).toBeVisible();
  }
  await page.getByLabel("Theme", { exact: true }).selectOption("system");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "system");
});


test("closing a job removes its deep-link identity and refresh cannot reopen it", async ({ page }) => {
  await signIn(page);
  await page.goto("/jobs?project=alpha&run=historical-job");
  await expect(page.locator(".detail-panel")).toBeVisible();
  await page.locator(".detail-panel").getByRole("button", { name: "Close", exact: true }).click();
  await expect(page).not.toHaveURL(/run=/);
  await page.locator(".topbar").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".detail-panel")).toHaveCount(0);
});


test("empty administrator enrollment has an actionable explanation", async ({ page }) => {
  await page.route("**/api/v1/projects", route => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await signIn(page);
  await expect(page.getByText("No projects available", { exact: true })).toBeVisible();
  await expect(page.getByText("Enroll an existing repository from Projects using Add project or Import project.", { exact: true })).toBeVisible();
  await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
  await expect(page.getByRole("button", { name: "Add project", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start job", exact: true })).toHaveCount(0);
});


test("statistics labels scoped evidence and shares DST scope with CSV", async ({ page }) => {
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const projectId = projects.find((item: { name: string }) => item.name === "alpha").id;
  await page.goto(`/metrics?project=${projectId}&timezone=Europe%2FBucharest`);
  const tokenCard = page.locator(".stat-card").filter({ has: page.getByText("Input tokens", { exact: true }) });
  await expect(tokenCard).toContainText("\u2014");
  await page.getByLabel("From", { exact: true }).fill("2026-10-25");
  const response = page.waitForResponse(response => new URL(response.url()).pathname ===
    `/api/v1/projects/${projectId}/metrics` &&
    response.url().includes("timezone=Europe%2FBucharest") && response.url().includes("day_to=2026-10-25"));
  await page.getByLabel("Through", { exact: true }).fill("2026-10-25");
  const scoped = await (await response).json();
  expect(scoped.scope.interval_seconds).toBe(25 * 3600);
  expect(scoped.totals.tokens_in).toBeNull();
  expect(scoped.current_stock.jobs_now).toBeGreaterThanOrEqual(1);
  await page.getByText("Export CSV", { exact: true }).click();
  const link = page.getByRole("link", { name: "Project metrics", exact: true });
  const exported = await page.request.get((await link.getAttribute("href"))!);
  expect(exported.status()).toBe(200);
  expect(JSON.parse(exported.headers()["x-adore-scope"])).toEqual([scoped.scope]);
  await page.getByLabel("From", { exact: true }).fill("");
  await page.getByLabel("Through", { exact: true }).fill("");
  await page.getByRole("tab", { name: "Quality", exact: true }).click();
  await expect(page.locator(".metric-chips").first().getByText("Review still open", { exact: true })).toBeVisible();
});

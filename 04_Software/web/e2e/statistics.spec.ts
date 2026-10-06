/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { messages, type Locale } from "../src/i18n";
import { statisticsCopy } from "../src/statisticsCopy";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});
async function signIn(page: Page, user = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(user);
  await page.getByLabel("Password", { exact: false }).fill(user === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}
test.beforeEach(async ({ request }) => { expect((await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true); });
test.afterEach(async ({ page, request }) => {
  await page.unrouteAll({ behavior: "wait" });
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});
// Hand-calculated fixture: 12 lifetime input, 7 in period, 2 undated; zero output is observed.
const amounts = (input: number | null, output: number | null, events = 1, admin = true) => ({ events, tokens_in: input, tokens_out: output, cache_read_tokens: null, cache_write_tokens: null,
  ...(admin ? { reported_cost_usd: 0, estimated_cost_usd: null } : {}) });
const consumption = (id: string, input = 7, run = "ux-working", admin = true) => ({ project_id: id, run_id: run,
  lifetime: amounts(12, 0, 3, admin), in_period: amounts(input, 0, 1, admin), unallocated: amounts(2, 0, 1, admin), source: "journal",
  coverage: { lifetime_usage_events: 3, period_usage_events: 1, unallocated_usage_events: 1 } });
function analytical(value: any, input = 7) {
  const result = structuredClone(value), id = result.scope.project_ids[0];
  result.jobs = [consumption(id, input)];
  Object.assign(result.totals, { runs: 1, started: 0, completed: 1, failed: 1, tokens_in: input, tokens_out: 0 });
  Object.assign(result.period, result.totals);
  result.current_stock = { jobs_now: 1, active_now: 1, waiting_now: 0, review_now: 0, terminal_now: 0, basis: "current_state" };
  result.duration = result.period.duration = { sampled_runs: 2, sum_span_seconds: 120, samples_seconds: [0, 120], avg_span_seconds: 60, median_span_seconds: 60 };
  result.daily = [{ date: "2026-10-25", started: 0, completed: 1, failed: 1, merged: 0, tokens_in: input, tokens_out: 0, mr_revisions: 0, pipeline_repairs: 0, cost_usd: 0, estimated_cost_usd: null }];
  Object.assign(result.coverage, { usage_events_with_tokens: 1, usage_events_without_tokens: 1, usage_events_unallocated: 1 });
  return result;
}
test("statistics initial measures, explicit all-time, scope hints and message availability", async ({ page }) => {
  await signIn(page);
  await page.goto("/metrics");
  await expect(page.getByRole("button", { name: "All time", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Selected-period evidence", exact: true })).toBeVisible();
  await expect(page.locator(".statistics-evidence").getByText("Started jobs", { exact: true })).toBeVisible();
  await expect(page.locator(".statistics-evidence").getByText("Failed jobs", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Current state · active now" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Messages" })).toContainText("Not available");
  await expect(page.getByText(/next local midnight/)).toBeVisible();
});

test("captured scope follows project, inclusive dates, DST, grouping, CSV and reload", async ({ page }) => {
  await signIn(page); const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((item: any) => item.name === "alpha").id, beta = projects.find((item: any) => item.name === "beta").id;
  await page.goto(`/metrics?project=${alpha}`);
  await page.getByLabel("From", { exact: true }).fill("2026-10-25"); await page.getByLabel("Through", { exact: true }).fill("2026-10-25");
  await page.getByRole("combobox", { name: "Time zone", exact: true }).selectOption("Europe/Bucharest");
  await page.getByRole("combobox", { name: "Group by", exact: true }).selectOption("week");
  await expect(page.locator(".canonical-scope")).toContainText("90000 s");
  await page.locator("#metrics-project").selectOption(beta);
  await expect(page.locator(".statistics-evidence .stat-card").filter({ has: page.getByText("Started jobs", { exact: true }) })).toContainText("0");
  await expect(page.locator(".statistics-evidence .stat-card").filter({ has: page.getByText("Input tokens", { exact: true }) })).toContainText("—Not available");
  await expect(page.getByText(statisticsCopy.en.empty, { exact: true })).toBeVisible();
  await expect(page.locator(".current-stock")).toContainText("active now");
  await expect(page.locator(".canonical-scope")).toContainText("2026-10-24T21:00:00+00:00");
  await page.getByText("Export CSV", { exact: true }).click();
  for (const name of ["Project metrics", "Project usage", "Job consumption"]) {
    const href = (await page.getByRole("link", { name, exact: true }).getAttribute("href"))!;
    const query = new URL(href, "http://localhost").searchParams;
    expect(query.get("day_from")).toBe("2026-10-25"); expect(query.get("day_to")).toBe("2026-10-25");
    expect(query.get("timezone")).toBe("Europe/Bucharest"); expect(query.get("granularity")).toBe("week");
    expect(href).toContain(beta);
    const exported = await page.request.get(href); expect(exported.ok()).toBe(true);
    const scoped = JSON.parse(exported.headers()["x-adore-scope"])[0]; expect(scoped.project_ids).toEqual([beta]); expect(scoped.interval_seconds).toBe(90000);
  }
  await page.reload(); await expect(page.getByLabel("From", { exact: true })).toHaveValue("2026-10-25");
  await expect(page.getByRole("combobox", { name: "Time zone", exact: true })).toHaveValue("Europe/Bucharest");
  await expect(page.getByRole("combobox", { name: "Group by", exact: true })).toHaveValue("week");
  await page.getByRole("button", { name: "All time", exact: true }).click();
  await expect(page.getByLabel("From", { exact: true })).toHaveValue(""); await expect(page.getByLabel("Through", { exact: true })).toHaveValue("");
  await page.getByRole("tab", { name: "Trends", exact: true }).focus(); await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("tab", { name: "Quality", exact: true })).toBeFocused();
});

test("out-of-order old scope cannot overwrite new data or exports; route transition discards reads", async ({ page }) => {
  await signIn(page); const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  let release!: () => void, observed!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; }), started = new Promise<void>(resolve => { observed = resolve; });
  await page.route("**/api/v1/projects/*/metrics?*", async route => {
    const query = new URL(route.request().url()).searchParams;
    const body = analytical(await (await route.fetch()).json(), query.get("day_from") === "2026-10-24" ? 91 : 7);
    if (query.get("day_from") === "2026-10-24") { observed(); await pending; }
    await route.fulfill({ json: body });
  });
  await page.goto(`/metrics?project=${alpha}`); await expect(page.locator(".statistics-evidence")).toBeVisible();
  const staleResponse = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/projects/${alpha}/metrics` && new URL(response.url()).searchParams.get("day_from") === "2026-10-24");
  await page.getByLabel("From", { exact: true }).fill("2026-10-24"); await started;
  await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByText("Export CSV", { exact: true })).toHaveCount(0);
  await page.getByLabel("From", { exact: true }).fill("2026-10-25");
  const card = page.locator(".stat-card").filter({ has: page.getByText("Input tokens", { exact: true }) });
  await expect(card).toContainText("7"); release(); await staleResponse;
  await expect(card).not.toContainText("91"); await expect(card).toContainText("7");
  await page.getByText("Export CSV", { exact: true }).click(); await expect(page.getByRole("link", { name: "Project metrics", exact: true })).toHaveAttribute("href", /day_from=2026-10-25/);
  await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Jobs", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
  await page.goBack(); await expect(page.getByLabel("From", { exact: true })).toHaveValue("2026-10-25");
  await expect(card).toContainText("7");
});

test("corrupt and aborted responses expose error without false zero or stale export", async ({ page }) => {
  await signIn(page); await page.goto("/metrics"); await expect(page.locator(".statistics-evidence")).toBeVisible();
  await page.route("**/api/v1/metrics?*", async route => {
    const body = await (await route.fetch()).json(); const first = Object.keys(body)[0]; body[first].jobs[0].lifetime.tokens_in = "0";
    await route.fulfill({ json: body });
  });
  await page.getByRole("combobox", { name: "Group by", exact: true }).selectOption("month");
  await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByText("Export CSV", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("alert").first()).toBeVisible();
  await page.unroute("**/api/v1/metrics?*"); await page.route("**/api/v1/metrics?*", route => route.abort("failed"));
  await page.getByRole("combobox", { name: "Group by", exact: true }).selectOption("week");
  await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByRole("alert").first()).toBeVisible();
});

test("composite jobs, known zero, partial coverage and chart table parity work in four locales and themes at 390px", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await signIn(page);
  await page.route("**/api/v1/metrics?*", async route => {
    const body = await (await route.fetch()).json(); for (const name of Object.keys(body)) body[name] = analytical(body[name]); await route.fulfill({ json: body });
  });
  const cohort = (await (await page.request.get("/api/v1/projects")).json()).length;
  expect(cohort).toBeGreaterThanOrEqual(2); // One explicit analytical observation per authorized project.
  const me = await (await page.request.get("/api/v1/me")).json();
  for (const locale of ["en", "fr", "de", "ro"] as Locale[]) for (const theme of ["light", "dark"]) {
    const copy = statisticsCopy[locale];
    expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } })).ok()).toBe(true);
    await page.setViewportSize({ width: 390, height: 900 }); await page.goto("/metrics");
    await expect(page.getByRole("heading", { name: copy.evidence, exact: true })).toBeVisible();
    await expect(page.locator(".statistics-evidence")).toContainText(copy.partial);
    const rows = page.locator(".consumption-table tbody tr"); await expect(rows).toHaveCount(cohort);
    const identities = await page.locator(".consumption-table .job-consumption").evaluateAll(nodes => nodes.map(node => node.getAttribute("data-identity")));
    expect(new Set(identities).size).toBe(cohort); await expect(rows.first()).toContainText(copy.zero);
    await page.getByRole("tab", { name: messages[locale].metricsTabTrends, exact: true }).click();
    const chart = page.getByRole("figure", { name: copy.trend }); await expect(chart).toBeVisible();
    const table = page.getByRole("table", { name: copy.table }); await expect(table).toBeVisible();
    await expect(table.locator("tbody tr")).toHaveCount(1); await expect(table.locator("tbody tr")).toContainText("2026-10-25");
    await expect(table.locator("tbody tr td").nth(1)).toHaveText("0"); await expect(table.locator("tbody tr td").nth(2)).toHaveText(String(cohort)); await expect(table.locator("tbody tr td").nth(3)).toHaveText(String(cohort));
    await expect(chart).toContainText(`${copy.completed}: ${cohort}`); await expect(chart).toContainText(`${copy.failed}: ${cohort}`);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  }
  expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } })).ok()).toBe(true);
  expect(errors).toEqual([]);
});

test("job list and direct detail share selected-period and lifetime consumption without same-run collisions", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    const value = await (await route.fetch()).json(); const id = value.scope.project_ids[0]; value.jobs = new URL(route.request().url()).searchParams.has("day_from") ? [] : [consumption(id, id.startsWith("a") ? 0 : 7)]; await route.fulfill({ json: value });
  });
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  await page.route("**/api/v1/projects/*/metrics?*", async route => route.fulfill({ json: analytical(await (await route.fetch()).json()) }));
  await page.goto(`/metrics?project=${alpha}&from=2026-10-25&through=2026-10-25&timezone=Europe%2FBucharest&granularity=week`);
  const destination = page.locator(".consumption-table").getByRole("link", { name: "ux-working", exact: true });
  await expect(destination).toBeVisible();
  const selection = new URL((await destination.getAttribute("href"))!, "http://localhost").searchParams;
  expect(selection.get("from")).toBe("2026-10-25"); expect(selection.get("through")).toBe("2026-10-25");
  expect(selection.get("timezone")).toBe("Europe/Bucharest"); expect(selection.get("granularity")).toBe("week");
  await page.goto("/jobs");
  await page.getByRole("combobox", { name: "Rows per page", exact: true }).selectOption("all");
  const collisions = page.locator('.action-jobs-table .job-consumption').filter({ hasText: "ux-working" }); await expect(collisions).toHaveCount(2);
  expect(new Set(await collisions.evaluateAll(nodes => nodes.map(node => node.getAttribute("data-identity")))).size).toBe(2);
  await page.goto(`/jobs?project=${alpha}&run=ux-working&from=2026-10-25&through=2026-10-25&timezone=Europe%2FBucharest`);
  const detail = page.locator(".detail-panel"); await expect(detail).toContainText("2026-10-25");
  await expect(detail.locator(".job-consumption").first()).toContainText("Lifetime"); await expect(detail.locator(".job-consumption").first()).toContainText("Selected period");
  await expect(detail.locator(".job-consumption").first()).toContainText(statisticsCopy.en.missingJob);
  await expect(detail.locator(".job-consumption").first()).toContainText("12"); await expect(detail.locator(".job-consumption").first()).toContainText(alpha);
  await page.reload(); await expect(detail).toContainText("Europe/Bucharest");
  await page.getByLabel("Search jobs", { exact: true }).fill("ux-working");
  const jobHref = (await page.locator('.action-jobs-table td:first-child a[href*="run=ux-working"]').getAttribute("href"))!;
  expect(new URL(jobHref, "http://localhost").searchParams.get("from")).toBe("2026-10-25");
});

test("Dev direct statistics and CSV remain nonfinancial and denied project routes fail closed", async ({ page }) => {
  await signIn(page, "developer"); await page.goto("/metrics"); await expect(page.locator(".statistics-evidence")).toBeVisible();
  await expect(page.locator("#metrics-project option")).toHaveCount(1);
  await expect(page.getByText("Reported cost", { exact: true })).toHaveCount(0); await expect(page.getByText("Estimated cost", { exact: true })).toHaveCount(0);
  await page.getByText("Export CSV", { exact: true }).click();
  for (const name of ["Project metrics", "Project usage", "Job consumption"]) {
    const href = (await page.getByRole("link", { name, exact: true }).getAttribute("href"))!;
    const response = await page.request.get(href); expect(response.ok()).toBe(true); expect(await response.text()).not.toMatch(/cost|priced|usd/i);
  }
  expect((await page.request.get("/api/v1/metrics.csv")).status()).toBe(403);
  expect((await page.request.get("/api/v1/projects/beta/usage.csv")).status()).toBe(404);
  await page.goto("/metrics?project=beta"); await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.locator(".consumption-table")).not.toContainText("beta");
});

test("revoked Dev grant hides earlier values and discards an authorized response captured before revocation", async ({ page, request }) => {
  const session = await (await request.post("/api/v1/session", { data: { username: "admin", password: "admin" } })).json();
  const projects = await (await request.get("/api/v1/projects")).json(), alpha = projects.find((item: any) => item.name === "alpha").id;
  const members = await (await request.get(`/api/v1/projects/${alpha}/access`)).json(), developer = members.developers.find((item: any) => item.username === "developer").id;
  await signIn(page, "developer"); await page.goto(`/metrics?project=${alpha}`); await expect(page.locator(".statistics-evidence")).toBeVisible();
  let release!: () => void, observed!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; }), started = new Promise<void>(resolve => { observed = resolve; });
  await page.route("**/api/v1/projects/*/metrics?*", async route => {
    const response = await route.fetch(); const body = await response.json();
    if (response.ok()) { observed(); await pending; }
    await route.fulfill({ response, json: body });
  });
  await page.getByRole("combobox", { name: "Group by", exact: true }).selectOption("week"); await started;
  try {
    expect((await request.put(`/api/v1/projects/${alpha}/access/${developer}`, { headers: { "X-CSRF-Token": session.csrf }, data: { granted: false } })).ok()).toBe(true);
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(page.locator("#metrics-project")).toHaveCount(0); release();
    await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByText("Export CSV", { exact: true })).toHaveCount(0);
    expect((await page.request.get(`/api/v1/projects/${alpha}/usage.csv`)).status()).toBe(404);
  } finally {
    release(); expect((await request.put(`/api/v1/projects/${alpha}/access/${developer}`, { headers: { "X-CSRF-Token": session.csrf }, data: { granted: true } })).ok()).toBe(true);
  }
});

test("metric and usage responses with different canonical intervals fail closed together", async ({ page }) => {
  await signIn(page); const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    const body = await (await route.fetch()).json(); body.scope.from = "2026-10-24T00:00:00+00:00"; await route.fulfill({ json: body });
  });
  await page.goto(`/metrics?project=${alpha}&from=2026-10-25`);
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByText("Export CSV", { exact: true })).toHaveCount(0);
});

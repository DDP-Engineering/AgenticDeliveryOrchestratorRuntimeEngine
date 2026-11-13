/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { revalidateVisiblePage } from "./polling";
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
  const response = await page.request.get("/api/v1/me");
  if (response.ok()) {
    const me = await response.json();
    expect((await page.request.patch("/api/v1/me/preferences", {
      headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" },
    })).ok()).toBe(true);
  }
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});
// Hand-calculated fixture: 12 lifetime input, 7 in period; zero output is observed.
const amounts = (input: number | null, output: number | null, events = 1, admin = true) => ({ events, tokens_in: input, tokens_out: output, cache_read_tokens: null, cache_write_tokens: null,
  ...(admin ? { reported_cost_usd: 0, estimated_cost_usd: null } : {}) });
const consumption = (id: string, input = 7, run = "ux-working", admin = true) => ({ project_id: id, run_id: run,
  lifetime: amounts(12, 0, 3, admin), in_period: amounts(input, 0, 1, admin), unallocated: amounts(null, null, 0, admin), source: "journal",
  coverage: { lifetime_usage_events: 3, period_usage_events: 1 } });
function analytical(value: any, input = 7) {
  const result = structuredClone(value), id = result.scope.project_ids[0];
  result.jobs = [consumption(id, input)];
  Object.assign(result.totals, { runs: 1, started: 0, completed: 1, failed: 1, tokens_in: input, tokens_out: 0 });
  Object.assign(result.period, result.totals);
  result.current_stock = { jobs_now: 1, active_now: 1, waiting_now: 0, review_now: 0, terminal_now: 0, basis: "current_state" };
  result.duration = result.period.duration = { sampled_runs: 2, sum_span_seconds: 120, samples_seconds: [0, 120], avg_span_seconds: 60, median_span_seconds: 60 };
  result.daily = [{ date: "2026-10-25", started: 0, completed: 1, failed: 1, merged: 0, tokens_in: input, tokens_out: 0, mr_revisions: 0, pipeline_repairs: 0, cost_usd: 0, estimated_cost_usd: null }];
  Object.assign(result.coverage, { usage_events_with_tokens: 1, usage_events_without_tokens: 1 });
  return result;
}
test("statistics summary shows only measures, compact period and job elapsed time in Usage", async ({ page }) => {
  await signIn(page);
  await page.goto("/metrics");
  await expect(page.getByRole("button", { name: "All time", exact: true })).toBeVisible();
  await expect(page.locator(".statistics-evidence").getByText("Started jobs", { exact: true })).toBeVisible();
  await expect(page.locator(".statistics-evidence").getByText("Failed jobs", { exact: true })).toBeVisible();
  // Summary keeps only the measures: no heading, scope line, explanations, Messages, consumption or duration.
  await expect(page.getByRole("heading", { name: "Selected-period evidence", exact: true })).toHaveCount(0);
  await expect(page.getByText(/^All time · UTC$/)).toHaveCount(0);
  await expect(page.getByText(/Started means/)).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Messages" })).toHaveCount(0);
  await expect(page.locator(".job-consumption")).toHaveCount(0);
  await expect(page.locator(".statistics-evidence").getByText("Average elapsed", { exact: true })).toHaveCount(0);
  await expect(page.locator(".usage-totals")).toHaveCount(0);
  // Usage totals carry job elapsed time; per-job consumption lives only in the Jobs tab.
  await page.getByRole("tab", { name: "Usage", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Job elapsed time", exact: true })).toHaveCount(0);
  await expect(page.locator(".usage-totals").getByText("Average elapsed", { exact: true })).toBeVisible();
  // Usage has no identity filters, filter help or rebuild action; totals are compact chips.
  await expect(page.getByLabel("Executor", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Model", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Rebuild usage history", exact: true })).toHaveCount(0);
  await expect(page.getByText(/Executor and model filters/)).toHaveCount(0);
  await expect(page.locator(".usage-totals").first().getByText("Usage events", { exact: true })).toBeVisible();
  await expect(page.locator(".usage-totals").first().getByText("Median elapsed", { exact: true })).toBeVisible();
  await expect(page.locator(".job-consumption")).toHaveCount(0);
  await page.getByRole("tab", { name: "Summary", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Current state · active now" })).toHaveCount(0);
  await expect(page.getByText(/next local midnight/)).toHaveCount(0);
  await expect(page.getByText(/= Measured zero/)).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Time zone", exact: true })).toHaveCount(0);
  // The reporting period is one compact row with All time aligned to the fields.
  const row = page.locator(".metrics-period-row");
  for (const control of [row.getByLabel("From", { exact: true }), row.getByLabel("Through", { exact: true }),
    row.getByRole("combobox", { name: "Group by", exact: true }), row.getByRole("button", { name: "All time", exact: true }),
    row.getByText("Export CSV", { exact: true })]) await expect(control).toBeVisible();
  const field = (await row.getByLabel("From", { exact: true }).boundingBox())!;
  const allTime = (await row.getByRole("button", { name: "All time", exact: true }).boundingBox())!;
  expect(Math.abs(field.y + field.height - (allTime.y + allTime.height))).toBeLessThan(4);
  const period = (await page.locator(".metrics-period").boundingBox())!;
  expect(period.height).toBeLessThan(140);
  await expect(row.locator("#metrics-project")).toBeVisible();
  // The project hub Statistics tab uses the same compact row without a project selector.
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  await page.goto(`/projects/${alpha}/statistics`);
  const hubRow = page.locator(".metrics-period-row");
  await expect(hubRow.getByRole("button", { name: "All time", exact: true })).toBeVisible();
  await expect(hubRow.locator("#metrics-project")).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Time zone", exact: true })).toHaveCount(0);
  expect((await page.locator(".metrics-period").boundingBox())!.height).toBeLessThan(140);
});

test("usage table sorts by column with unknown values last", async ({ page }) => {
  await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  const row = (date: string, executor: string | null, input: number) => ({ date, executor, model: executor && "m", events: 1, tokens_in: input,
    tokens_out: 0, cache_read_tokens: null, cache_write_tokens: null, reported_cost_usd: null, estimated_cost_usd: null });
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    const value = await (await route.fetch()).json();
    value.daily = [row("2026-10-01", "pi", 30), row("2026-10-02", null, 10), row("2026-10-03", "codex", 20)];
    await route.fulfill({ json: value });
  });
  await page.goto(`/projects/${alpha}/statistics?tab=usage`);
  const inputs = page.locator(".usage-table tbody td:nth-child(5)"), executors = page.locator(".usage-table tbody td:nth-child(2)");
  await expect(page.getByRole("columnheader", { name: "Date", exact: true })).toHaveAttribute("aria-sort", "ascending");
  await expect(inputs).toHaveText(["30", "10", "20"]);
  const input = page.getByRole("columnheader", { name: "Input tokens", exact: true });
  await input.getByRole("button").click();
  await expect(input).toHaveAttribute("aria-sort", "ascending"); await expect(inputs).toHaveText(["10", "20", "30"]);
  await input.getByRole("button").click();
  await expect(input).toHaveAttribute("aria-sort", "descending"); await expect(inputs).toHaveText(["30", "20", "10"]);
  const executor = page.getByRole("columnheader", { name: "Executor", exact: true });
  await executor.getByRole("button").click(); await expect(executors).toHaveText(["codex", "pi", "—"]);
  await executor.getByRole("button").click(); await expect(executors).toHaveText(["pi", "codex", "—"]);
});

test("quality shows compact delivery, cost and active-day revision values", async ({ page }) => {
  await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  await page.route("**/api/v1/projects/*/metrics?*", async route => {
    const value = analytical(await (await route.fetch()).json());
    value.daily = [{ ...value.daily[0], date: "2026-10-24", mr_revisions: 0, pipeline_repairs: 0 }, { ...value.daily[0], mr_revisions: 2, pipeline_repairs: 1 }];
    Object.assign(value.totals, { mr_revisions: 2, pipeline_repairs: 1 });
    await route.fulfill({ json: value });
  });
  await page.goto(`/projects/${alpha}/statistics?tab=quality`);
  const chips = page.locator(".metric-chips");
  await expect(chips).toHaveCount(3);
  for (const label of ["Reviewer rework", "First validation pass", "Review still open", "Stage failures", "Operator retries"])
    await expect(chips.nth(0).getByText(label, { exact: true })).toBeVisible();
  await expect(chips.nth(1).getByText("Reported / completed", { exact: true })).toBeVisible();
  await expect(chips.nth(2).getByText("MR/PR reviewer revisions", { exact: true })).toBeVisible();
  await expect(chips.nth(2).getByText("Unclassified revisions", { exact: true })).toBeVisible();
  await expect(chips.nth(0).locator("div").filter({ has: page.getByText("Reviewer rework", { exact: true }) })).toContainText(/\d+\/\d+ reviewed jobs/);
  await expect(chips.nth(1).locator("div").filter({ has: page.getByText("Reported / completed", { exact: true }) })).toContainText("jobs with evidence");
  await expect(chips.nth(2).locator("div").filter({ has: page.getByText("MR/PR reviewer revisions", { exact: true }) })).toHaveText(/^MR\/PR reviewer revisions\s*2$/);
  await expect(chips.nth(2).locator("div").filter({ has: page.getByText("Pipeline repairs", { exact: true }) })).toHaveText(/^Pipeline repairs\s*1$/);
  await expect(page.getByText(/Job cohorts selected by/)).toHaveCount(0);
  await expect(page.getByText(/Each figure divides known USD/)).toHaveCount(0);
  await expect(page.getByText("All-time totals", { exact: true })).toHaveCount(0);
  const days = page.locator(".revision-days tbody tr"); await expect(days).toHaveCount(1); await expect(days).toContainText("2026-10-25");
  await expect(page.locator(".stats-grid")).toHaveCount(0);
  await page.unroute("**/api/v1/projects/*/metrics?*"); await page.context().clearCookies(); await signIn(page, "developer"); await page.goto(`/projects/${alpha}/statistics?tab=quality`);
  await expect(page.locator(".metric-chips")).toHaveCount(2); await expect(page.getByText("Reported / completed", { exact: true })).toHaveCount(0);
});

test("trends show one compact table and estimated cost appears once per place", async ({ page }) => {
  await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  await page.route("**/api/v1/projects/*/metrics?*", async route => route.fulfill({ json: analytical(await (await route.fetch()).json()) }));
  await page.goto(`/projects/${alpha}/statistics?tab=trends`);
  await expect(page.getByRole("heading", { name: "Daily activity", exact: true })).toBeVisible();
  await expect(page.locator(".metric-chips").getByText("Usage coverage", { exact: true })).toBeVisible();
  await expect(page.locator(".metric-chips").getByText("Usage without a consumption date", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Estimated cost (USD)", exact: true })).toHaveCount(0);
  await expect(page.locator("#metrics-tab-panel")).not.toContainText("UTC");
  await page.getByRole("tab", { name: "Usage", exact: true }).click();
  await expect(page.locator(".usage-totals").getByText("Unpriced usage events", { exact: true })).toBeVisible();
  await page.goto("/metrics"); await page.getByRole("tab", { name: "Usage", exact: true }).click();
  await expect(page.locator(".usage-totals div").filter({ has: page.getByText("Unpriced usage events", { exact: true }) })).toHaveText(/\d$/);
  const perProject = page.locator('h3:has-text("Enrolled projects") + .table-scroll');
  await expect(perProject.getByRole("columnheader", { name: "Unpriced usage events", exact: true })).toBeVisible();
  await expect(perProject.getByRole("columnheader", { name: "Estimated cost (USD)", exact: true })).toBeVisible();
});

test("all-project statistics show each per-project family once, in its own tab", async ({ page }) => {
  await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha");
  await page.goto("/metrics");
  await expect(page.locator(".statistics-evidence")).toBeVisible();
  await expect(page.locator(".scope-note")).toHaveCount(0);
  await expect(page.getByText(/Statistics cover all projects you can access/)).toHaveCount(0);
  await expect(page.getByRole("tablist", { name: "Statistics", exact: true }).getByRole("tab")).toHaveText(["Summary", "Usage", "Quality", "Trends"]);
  const table = page.locator("#metrics-tab-panel table").first();
  await expect(table.getByRole("columnheader")).toHaveText(["Project", "Started jobs", "Completed jobs", "Failed jobs", "Average elapsed"]);
  const alphaRow = table.locator("tbody tr").filter({ hasText: "alpha" });
  await expect(alphaRow).toContainText(alpha.repo);
  await expect(alphaRow).not.toContainText(alpha.id);
  await page.getByRole("tab", { name: "Usage", exact: true }).click();
  const perProject = page.locator('h3:has-text("Enrolled projects") + .table-scroll');
  for (const name of ["Estimated cost (USD)", "Unpriced usage events"])
    await expect(perProject.getByRole("columnheader", { name, exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Quality", exact: true }).click();
  for (const name of ["Reviewer rework", "MR/PR reviewer revisions", "Pipeline repairs", "Review rounds"])
    await expect(page.getByRole("columnheader", { name, exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Repository", exact: true })).toHaveCount(0);
  await page.goto("/metrics?tab=projects");
  await expect(page.getByRole("tab", { name: "Summary", exact: true })).toHaveAttribute("aria-selected", "true");
});

test("captured scope follows project, inclusive dates, DST, grouping, CSV and reload", async ({ page }) => {
  await signIn(page); const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((item: any) => item.name === "alpha").id, beta = projects.find((item: any) => item.name === "beta").id;
  // The time zone comes only from the URL now; UTC is the default.
  await page.goto(`/metrics?project=${alpha}&timezone=Europe%2FBucharest`);
  await page.getByLabel("From", { exact: true }).fill("2026-10-25"); await page.getByLabel("Through", { exact: true }).fill("2026-10-25");
  const read = (id: string, part: string) => page.waitForResponse(response => new URL(response.url()).pathname ===
    `/api/v1/projects/${id}/metrics` && response.url().includes(part));
  const weekly = read(alpha, "granularity=week");
  await page.getByRole("combobox", { name: "Group by", exact: true }).selectOption("week");
  expect((await (await weekly).json()).scope.interval_seconds).toBe(90000);
  const betaRead = read(beta, "day_to=2026-10-25");
  await page.locator("#metrics-project").selectOption(beta);
  expect((await (await betaRead).json()).scope.from).toBe("2026-10-24T21:00:00+00:00");
  await page.getByRole("tab", { name: "Trends", exact: true }).click();
  await expect(page.getByText(messages.en.metricsNoJobs, { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Summary", exact: true }).click();
  await expect(page.locator(".statistics-evidence .stat-card").filter({ has: page.getByText("Started jobs", { exact: true }) })).toContainText("0");
  await expect(page.locator(".statistics-evidence .stat-card").filter({ has: page.getByText("Input tokens", { exact: true }) })).toContainText("—Not available");
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
  await expect(page).toHaveURL(/timezone=Europe%2FBucharest/);
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
  const staleResponse = page.waitForEvent("requestfailed", request => new URL(request.url()).pathname === `/api/v1/projects/${alpha}/metrics` && new URL(request.url()).searchParams.get("day_from") === "2026-10-24");
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
    const body = await (await route.fetch()).json();
    // Enrollment can add empty projects before the seeded analytical job cohort.
    const project = Object.keys(body).find(id => body[id].jobs.length > 0);
    expect(project, "a seeded job is required to exercise malformed consumption").toBeDefined();
    body[project!].jobs[0].lifetime.tokens_in = "0";
    await route.fulfill({ json: body });
  });
  await page.getByRole("combobox", { name: "Group by", exact: true }).selectOption("month");
  await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByText("Export CSV", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("alert").first()).toBeVisible();
  await page.unroute("**/api/v1/metrics?*"); await page.route("**/api/v1/metrics?*", route => route.abort("failed"));
  await page.getByRole("combobox", { name: "Group by", exact: true }).selectOption("week");
  await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByRole("alert").first()).toBeVisible();
});

test("known zero, partial coverage, job duration and trend table bars work in four locales and themes at 390px", async ({ page }) => {
  test.setTimeout(60_000);
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await signIn(page);
  let failRefresh = false;
  await page.route("**/api/v1/metrics?*", async route => {
    if (failRefresh) { await route.abort("failed"); return; }
    const body = await (await route.fetch()).json(); for (const name of Object.keys(body)) body[name] = analytical(body[name]); await route.fulfill({ json: body });
  });
  const cohort = (await (await page.request.get("/api/v1/projects")).json()).length;
  expect(cohort).toBeGreaterThanOrEqual(2); // One explicit analytical observation per authorized project.
  const me = await (await page.request.get("/api/v1/me")).json();
  for (const locale of ["en", "fr", "de", "ro"] as Locale[]) for (const theme of ["light", "dark"]) {
    const copy = statisticsCopy[locale];
    expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } })).ok()).toBe(true);
    await page.setViewportSize({ width: 390, height: 900 }); await page.goto("/metrics");
    await expect(page.locator(".statistics-evidence")).toContainText(copy.partial);
    const feedback = page.locator(".refresh-feedback");
    await expect(feedback.getByRole("button", { name: messages[locale].refresh, exact: true })).toBeVisible();
    await expect(feedback.locator("time")).toHaveCount(3);
    expect(await feedback.locator("time").first().evaluate(node => node.closest('[aria-live], [role="status"], [role="alert"]'))).toBeNull();
    failRefresh = true;
    await feedback.getByRole("button", { name: messages[locale].refresh, exact: true }).click();
    await expect(feedback.getByRole("status")).toHaveText(messages[locale].refreshStale);
    await expect(page.locator(".statistics-evidence")).toBeVisible();
    const retry = feedback.getByRole("button", { name: messages[locale].retry, exact: true });
    await retry.focus(); await expect(retry).toBeFocused();
    failRefresh = false; await page.keyboard.press("Enter");
    await expect(feedback.getByRole("status")).toHaveCount(0);
    await page.getByRole("tab", { name: messages[locale].metricsTabUsage, exact: true }).click();
    await expect(page.locator(".usage-totals").first()).toContainText(messages[locale].averageSpan);
    await expect(page.locator(".job-consumption")).toHaveCount(0);
    await page.getByRole("tab", { name: messages[locale].metricsTabTrends, exact: true }).click();
    await expect(page.getByRole("figure")).toHaveCount(0);
    const table = page.getByRole("table", { name: copy.table }); await expect(table).toBeVisible();
    await expect(table.locator("tbody tr")).toHaveCount(1); await expect(table.locator("tbody tr")).toContainText("2026-10-25");
    await expect(table.locator("tbody tr td").nth(1)).toHaveText("0"); await expect(table.locator("tbody tr td").nth(2)).toHaveText(String(cohort)); await expect(table.locator("tbody tr td").nth(3)).toHaveText(String(cohort));
    await expect(table.locator("tbody tr td").nth(2).locator("i")).toHaveCount(1);
    await expect(table).not.toContainText(copy.measured);
    await expect(page.locator("#metrics-tab-panel")).not.toContainText("UTC");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  }
  expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } })).ok()).toBe(true);
  expect(errors).toEqual([]);
});

test("job list and direct detail show lifetime consumption without same-run collisions", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    const value = await (await route.fetch()).json(); const id = value.scope.project_ids[0]; value.jobs = [consumption(id, id.startsWith("a") ? 0 : 7)]; await route.fulfill({ json: value });
  });
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  await page.goto("/jobs?view=jobs");
  await page.getByRole("combobox", { name: "Rows per page", exact: true }).selectOption("all");
  const collisions = page.locator('.action-jobs-table .job-consumption[data-identity*="ux-working"]'); await expect(collisions).toHaveCount(2);
  expect(new Set(await collisions.evaluateAll(nodes => nodes.map(node => node.getAttribute("data-identity")))).size).toBe(2);
  await page.goto(`/jobs?project=${alpha}&run=ux-working`);
  const detail = page.locator(".detail-panel"); await expect(detail.locator(".job-consumption").first()).toContainText("12");
  await expect(detail).not.toContainText("Selected period");
  await detail.getByRole("tab", { name: "Technical details", exact: true }).click();
  await expect(detail.getByRole("tabpanel", { name: "Technical details", exact: true })).toContainText(alpha);
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
    await revalidateVisiblePage(page);
    await expect(page.locator("#metrics-project")).toHaveCount(0); release();
    await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.getByText("Export CSV", { exact: true })).toHaveCount(0);
    expect((await page.request.get(`/api/v1/projects/${alpha}/usage.csv`)).status()).toBe(404);
  } finally {
    release(); expect((await request.put(`/api/v1/projects/${alpha}/access/${developer}`, { headers: { "X-CSRF-Token": session.csrf }, data: { granted: true } })).ok()).toBe(true);
  }
});

/** Hold both reporting members to prove UI publication, not private controller state. */
for (const scope of ["global", "selected", "hub"] as const) {
  test(`coordinated background Statistics preserves every tab and export in ${scope} scope`, async ({ page }) => {
    await signIn(page);
    const projects = await (await page.request.get("/api/v1/projects")).json();
    const alpha = projects.find((item: any) => item.name === "alpha").id;
    await page.clock.install();
    let hold = false, input = 7;
    const releases: Partial<Record<"metrics" | "usage", () => void>> = {};
    const reads = { metrics: 0, usage: 0, unrelated: 0 };
    await page.route(/\/api\/v1\/(?:projects\/[^/]+\/)?(?:metrics|usage)\?/, async route => {
      const path = new URL(route.request().url()).pathname;
      const member = path.endsWith("/metrics") ? "metrics" : "usage";
      if (scope !== "global" && !path.includes("/projects/")) reads.unrelated++;
      const body = await (await route.fetch()).json();
      const transform = (value: any) => member === "metrics" ? analytical(value, input) : {
        ...value, totals: { ...value.totals, tokens_in: input, tokens_out: 0 },
      };
      const result = path.includes("/projects/") ? transform(body) : Object.fromEntries(Object.entries(body).map(([name, value]) => [name, transform(value)]));
      reads[member]++;
      if (hold) await new Promise<void>(resolve => { releases[member] = resolve; });
      await route.fulfill({ json: result });
    });
    await page.goto(scope === "global" ? "/metrics" : scope === "selected" ? `/metrics?project=${alpha}` : `/projects/${alpha}/statistics`);
    await expect(page.locator(".statistics-evidence")).toBeVisible();
    const total = scope === "global" ? projects.length : 1;
    for (const [index, tab] of ["Summary", "Usage", "Quality", "Trends"].entries()) {
      await page.getByRole("tablist", { name: "Statistics", exact: true }).getByRole("tab", { name: tab, exact: true }).click();
      if (index === 0) await page.getByText("Export CSV", { exact: true }).click();
      const firstLink = page.locator(".metrics-export a").first();
      await expect(firstLink).toBeVisible();
      const panel = await page.locator("#metrics-tab-panel").elementHandle();
      const disclosure = await page.locator(".metrics-export").elementHandle();
      const baseline = { ...reads };
      const times = await page.locator(".refresh-feedback time").evaluateAll(nodes => nodes.map(node => node.getAttribute("datetime")));
      hold = true; input = index % 2 ? 19 : 7;
      // Selected metrics stay at 15s; usage/global metrics at 30s. A slow
      // metrics proposal crossing the due boundary must promote its usage pin.
      await page.clock.runFor(30000);
      await expect.poll(() => reads.metrics).toBe(baseline.metrics + 1);
      await expect.poll(() => reads.usage).toBe(baseline.usage + 1);
      await expect(firstLink).toBeVisible();
      await expect(page.locator("#metrics-tab-panel .data-loading")).toHaveCount(0);
      await expect(page.getByRole("tablist", { name: "Statistics", exact: true }).getByRole("tab", { name: tab, exact: true })).toHaveAttribute("aria-selected", "true");
      expect(await panel!.evaluate(node => node === document.querySelector("#metrics-tab-panel"))).toBe(true);
      // Alternate member order; the first completion cannot publish half a report.
      const first = index % 2 ? "usage" : "metrics", second = first === "usage" ? "metrics" : "usage";
      releases[first]!();
      await expect(page.locator(".refresh-feedback")).toHaveAttribute("data-refreshing", "true");
      expect(await page.locator(".refresh-feedback time").evaluateAll(nodes => nodes.map(node => node.getAttribute("datetime")))).toEqual(times);
      await expect(firstLink).toBeVisible();
      hold = false; releases[second]!();
      await expect(page.locator(".refresh-feedback")).toHaveAttribute("data-refreshing", "false");
      expect(await disclosure!.evaluate(node => node === document.querySelector(".metrics-export") && (node as HTMLDetailsElement).open)).toBe(true);
      if (tab === "Summary") await expect(page.locator(".statistics-evidence")).toContainText(new Intl.NumberFormat("en").format(input * total));
    }
    expect(reads.unrelated).toBe(0);
  });
}

test("Statistics manual refresh preserves paging focus and freshness through failure and recovery", async ({ page }) => {
  await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  await page.clock.install();
  let mode: "ready" | "hold" | "transport" | "malformed" = "ready";
  let input = 7, release!: () => void, reads = 0;
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    reads++;
    if (mode === "transport") { await route.abort("failed"); return; }
    if (mode === "malformed") { await route.fulfill({ contentType: "application/json", body: "{" }); return; }
    const body = await (await route.fetch()).json();
    body.totals.tokens_in = input;
    body.daily = Array.from({ length: 61 }, (_, index) => ({ date: "2026-10-25", executor: "pi", model: `model-${String(index).padStart(2, "0")}`,
      ...amounts(index, 0) }));
    if (mode === "hold") await new Promise<void>(resolve => { release = resolve; });
    await route.fulfill({ json: body });
  });
  await page.goto(`/projects/${alpha}/statistics?tab=usage`);
  const table = page.locator(".usage-table"), feedback = page.locator(".refresh-feedback");
  await expect(table).toBeVisible();
  await page.getByRole("columnheader", { name: "Input tokens", exact: true }).getByRole("button").click();
  const size = page.getByRole("combobox", { name: "Rows per page", exact: true });
  await size.selectOption("25"); await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(table.locator("tbody tr")).toHaveCount(25);
  const beforeRows = (await table.locator("tbody").textContent())!;
  await page.getByText("Export CSV", { exact: true }).click();
  const initialTime = await feedback.locator("time").first().getAttribute("datetime");
  const firstInput = await table.locator("tbody tr").first().elementHandle();
  const focused = await size.elementHandle();
  const initialReads = reads;
  mode = "hold"; input = 19;
  await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect.poll(() => reads).toBe(initialReads + 1);
  await feedback.getByRole("button", { name: "Refresh", exact: true }).focus();
  await page.keyboard.press("Enter"); // aria-disabled remains focusable; the handler must coalesce/ignore.
  await size.focus();
  const scroll = await page.evaluate(() => ({ x: scrollX, y: scrollY }));
  try {
    await page.clock.runFor(15000);
    expect(reads).toBe(initialReads + 1);
    await expect(size).toHaveValue("25"); await expect(size).toBeFocused();
    await expect(table.locator("tbody")).toHaveText(beforeRows);
    await expect(feedback.locator("time").first()).toHaveAttribute("datetime", initialTime!);
    await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
    mode = "ready"; release();
    await expect(feedback).toHaveAttribute("data-refreshing", "false");
    await expect(size).toHaveValue("25"); await expect(size).toBeFocused();
    expect(await focused!.evaluate(node => node === document.activeElement)).toBe(true);
    expect(await firstInput!.evaluate(node => node === document.querySelector(".usage-table tbody tr"))).toBe(true);
    expect(await page.evaluate(() => ({ x: scrollX, y: scrollY }))).toEqual(scroll);
    await expect(table.locator("tbody")).toHaveText(beforeRows);
    await expect(page.locator(".usage-totals")).toContainText("19");
    await expect(feedback.locator("time").first()).not.toHaveAttribute("datetime", initialTime!);
    const successTime = await feedback.locator("time").first().getAttribute("datetime");
    mode = "transport";
    await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(feedback.getByRole("status")).toContainText("Refresh failed");
    await expect(table).toBeVisible(); await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
    await expect(feedback.locator("time").first()).toHaveAttribute("datetime", successTime!);
    mode = "ready";
    await feedback.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(feedback.getByRole("status")).toHaveCount(0); await expect(size).toHaveValue("25");
    mode = "malformed";
    await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(page.getByRole("alert")).toBeVisible(); await expect(table).toHaveCount(0);
    await expect(page.locator(".metrics-export")).toHaveCount(0); await expect(feedback.locator("time")).toHaveCount(0);
  } finally { release?.(); }
});

test("Usage bucket identity survives changed sort position and rejects duplicate evidence", async ({ page }) => {
  await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  let tokens = 5, duplicate = false;
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    const body = await (await route.fetch()).json();
    const bucket = (model: string, input: number) => ({ date: "2026-10-25", executor: "pi", model, ...amounts(input, 0) });
    body.daily = [bucket("surviving-model", tokens), bucket("lower-model", 1), bucket("upper-model", 10)];
    if (duplicate) body.daily.push({ ...body.daily[0], tokens_in: 99 });
    await route.fulfill({ json: body });
  });
  await page.goto(`/projects/${alpha}/statistics?tab=usage`);
  const table = page.locator(".usage-table"), feedback = page.locator(".refresh-feedback");
  await expect(table).toBeVisible();
  await page.getByRole("columnheader", { name: "Input tokens", exact: true }).getByRole("button").click();
  const row = table.locator("tbody tr").filter({ hasText: "surviving-model" });
  await expect(table.locator("tbody tr").nth(1)).toContainText("surviving-model");
  const identity = await row.elementHandle();
  tokens = 20;
  await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(table.locator("tbody tr").nth(2)).toContainText("surviving-model");
  expect(await identity!.evaluate(node => node.isConnected && node === [...document.querySelectorAll(".usage-table tbody tr")].find(row => row.textContent?.includes("surviving-model")))).toBe(true);
  await expect(row).toContainText("20");
  await page.getByText("Export CSV", { exact: true }).click();
  duplicate = true;
  await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible(); await expect(table).toHaveCount(0);
  await expect(page.locator(".metrics-export")).toHaveCount(0); await expect(feedback.locator("time")).toHaveCount(0);
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

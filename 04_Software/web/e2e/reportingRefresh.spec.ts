/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage, trackScopeReads } from "./polling";
import type { Metrics } from "../src/metrics";

const deferred = () => { let resolve!: () => void; const promise = new Promise<void>(done => { resolve = done; }); return { promise, resolve }; };
const feedback = (page: Page) => page.locator(".refresh-feedback");
const times = (page: Page) => feedback(page).locator("time").evaluateAll(nodes => nodes.map(node => node.getAttribute("datetime")));
async function hide(page: Page) {
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }); document.dispatchEvent(new Event("visibilitychange")); });
}
async function alpha(page: Page) { return (await (await page.request.get("/api/v1/projects")).json()).find((project: { name: string }) => project.name === "alpha").id as string; }

test.beforeEach(async ({ context, page, request }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  expect((await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
});
test.afterEach(async ({ page, request }) => {
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});

for (const scope of ["global", "project"] as const) for (const member of ["metrics", "usage"] as const) {
  test(`Statistics ${scope} ${member} deadline releases initial and stale proposals without late publication`, async ({ page }) => {
    const settle = trackScopeReads(page), held = deferred();
    await page.clock.install();
    const id = await alpha(page);
    let hold = true, reads = 0, cancelled = 0;
    const pattern = scope === "global" ? `**/api/v1/${member}?*` : `**/api/v1/projects/*/${member}?*`;
    page.on("requestfailed", request => { if (new URL(request.url()).pathname === (scope === "global" ? `/api/v1/${member}` : `/api/v1/projects/${id}/${member}`)) cancelled++; });
    await page.route(pattern, async route => {
      reads++; const response = await route.fetch();
      if (hold) await held.promise;
      await route.fulfill({ response }).catch(() => {});
    });
    try {
      await page.goto(scope === "global" ? "/metrics" : `/projects/${id}/statistics`);
      await expect.poll(() => reads).toBe(1);
      await expect(page.locator("#metrics-tab-panel .data-loading")).toBeVisible();
      await hide(page); await settle(); await page.clock.runFor(30001);
      await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
      await expect(page.locator(".statistics-evidence")).toHaveCount(0);
      await expect(page.locator(".metrics-export")).toHaveCount(0);
      expect(await times(page)).toEqual([]); await expect.poll(() => cancelled).toBe(1);
      hold = false;
      await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
      await expect(page.locator(".statistics-evidence")).toBeVisible();
      const good = await times(page), panel = await page.locator(".statistics-evidence").elementHandle();
      await page.getByText("Export CSV", { exact: true }).click();
      hold = true;
      await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
      await expect.poll(() => reads).toBe(3);
      await settle(); await page.clock.runFor(30001);
      await expect(feedback(page).getByRole("status")).toContainText("Refresh failed");
      expect(await times(page)).toEqual(good);
      await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
      expect(await panel!.evaluate(node => node.isConnected)).toBe(true);
      await expect.poll(() => cancelled).toBe(2);
      hold = false;
      await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
      await expect(feedback(page).getByRole("status")).toHaveCount(0);
      await expect(feedback(page)).toHaveAttribute("data-refreshing", "false");
      const recovered = await times(page);
      expect(recovered[0]).not.toBe(good[0]);
      held.resolve();
      expect(await times(page)).toEqual(recovered);
      expect(reads).toBe(4);
      expect(await panel!.evaluate(node => node.isConnected)).toBe(true);
    } finally { held.resolve(); }
  });
}

for (const scope of ["global", "project"] as const) test(`Statistics ${scope} cadence, carried source times and hidden return stay honest`, async ({ page }) => {
  const settle = trackScopeReads(page), held = deferred();
  await page.clock.install();
  const id = await alpha(page), reads = { metrics: 0, usage: 0 };
  let hold = false;
  await page.route(/\/api\/v1\/(?:projects\/[^/]+\/)?(?:metrics|usage)\?/, async route => {
    const member = new URL(route.request().url()).pathname.endsWith("/metrics") ? "metrics" : "usage";
    reads[member]++; const response = await route.fetch();
    if (hold) await held.promise;
    await route.fulfill({ response }).catch(() => {});
  });
  try {
    await page.goto(scope === "global" ? "/metrics" : `/projects/${id}/statistics`);
    await expect(page.locator(".statistics-evidence")).toBeVisible();
    const initial = await times(page), node = await page.locator(".statistics-evidence").elementHandle();
    await settle(); await page.clock.runFor(15000);
    if (scope === "project") {
      await expect.poll(() => reads).toEqual({ metrics: 2, usage: 1 });
      await expect(feedback(page)).toHaveAttribute("data-refreshing", "false");
      const carried = await times(page);
      expect(carried[0]).toBe(initial[0]); expect(carried[1]).not.toBe(initial[1]); expect(carried[2]).toBe(initial[2]);
    } else { expect(reads).toEqual({ metrics: 1, usage: 1 }); expect(await times(page)).toEqual(initial); }
    await page.clock.runFor(15000);
    await expect.poll(() => reads).toEqual({ metrics: scope === "project" ? 3 : 2, usage: 2 });
    await expect(feedback(page)).toHaveAttribute("data-refreshing", "false");
    const before = { ...reads }, success = await times(page);
    expect(success[0]).not.toBe(initial[0]); expect(success[2]).not.toBe(initial[2]);
    await hide(page); await settle(); await page.clock.runFor(90000);
    expect(reads).toEqual(before);
    hold = true; await revalidateVisiblePage(page);
    await expect.poll(() => reads).toEqual({ metrics: before.metrics + 1, usage: before.usage + 1 });
    await page.evaluate(() => { document.dispatchEvent(new Event("visibilitychange")); document.dispatchEvent(new Event("visibilitychange")); });
    await page.clock.runFor(15000);
    expect(reads).toEqual({ metrics: before.metrics + 1, usage: before.usage + 1 });
    expect(await times(page)).toEqual(success);
    expect(await node!.evaluate(element => element.isConnected)).toBe(true);
    hold = false; held.resolve();
    await expect(feedback(page)).toHaveAttribute("data-refreshing", "false");
    expect(reads).toEqual({ metrics: before.metrics + 1, usage: before.usage + 1 });
    expect((await times(page))[0]).not.toBe(success[0]);
  } finally { held.resolve(); }
});

for (const failure of ["canonical interval", "metrics aggregate", "usage aggregate", "metrics token direction", "metrics token total", "usage token direction", "usage token total"] as const) test(`Statistics global ${failure} fails closed before rendering and recovers`, async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  let corrupt = false;
  await page.route(/\/api\/v1\/(?:metrics|usage)\?/, async route => {
    const body = await (await route.fetch()).json();
    const entries = Object.values(body) as Array<{ scope: { from: string; to: string }; period?: { from: string; to: string }; totals: Record<string, number> }>;
    expect(entries.length).toBeGreaterThan(1);
    if (corrupt) {
      if (failure === "canonical interval") {
        const value = entries[1];
        value.scope.from = new Date(Date.parse(value.scope.from) + 3600000).toISOString();
        value.scope.to = new Date(Date.parse(value.scope.to) + 3600000).toISOString();
        if (value.period) Object.assign(value.period, { from: value.scope.from, to: value.scope.to });
      } else if (failure.includes("token")) {
        if (route.request().url().includes(failure.startsWith("metrics") ? "/metrics?" : "/usage?")) {
          for (const value of entries) Object.assign(failure.startsWith("metrics") ? value.period! : value.totals, {
            tokens_in: failure.endsWith("total") ? 3e15 : 5e15,
            tokens_out: failure.endsWith("total") ? 3e15 : 0,
          });
        }
      } else if (route.request().url().includes(failure === "metrics aggregate" ? "/metrics?" : "/usage?")) {
        for (const value of entries) value.totals[failure === "metrics aggregate" ? "cost_usd" : "reported_cost_usd"] = 1e308;
      }
    }
    await route.fulfill({ json: body });
  });
  await page.goto("/metrics?from=2026-10-25&through=2026-10-25");
  await expect(page.locator(".statistics-evidence")).toBeVisible();
  expect((await times(page)).length).toBe(3);
  await page.getByText("Export CSV", { exact: true }).click();
  corrupt = true;
  await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.locator(".statistics-evidence")).toHaveCount(0);
  await expect(page.locator(".metrics-export")).toHaveCount(0);
  expect(await times(page)).toEqual([]);
  expect(errors).toEqual([]);
  corrupt = false;
  await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator(".statistics-evidence")).toBeVisible();
  expect((await times(page)).length).toBe(3);
  expect(errors).toEqual([]);
});

for (const failure of ["collection", "null row", "review count", "review total"] as const) test(`Statistics global Quality rejects malformed run ${failure} before publication and recovers`, async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  let corrupt = true;
  await page.route(/\/api\/v1\/metrics\?/, async route => {
    const body = await (await route.fetch()).json();
    if (corrupt) {
      const value = Object.values(body)[0] as { runs: unknown };
      value.runs = failure === "collection" ? {} : failure === "null row" ? [null] :
        failure === "review count" ? [{ review_rounds: "2" }] :
          [{ review_rounds: Number.MAX_SAFE_INTEGER }, { review_rounds: 1 }];
    }
    await route.fulfill({ json: body });
  });
  await page.goto("/metrics?tab=quality");
  await expect(page.getByRole("tab", { name: "Quality", exact: true })).toHaveAttribute("aria-selected", "true");
  const closed = async () => {
    await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Delivery quality", exact: true })).toHaveCount(0);
    await expect(page.locator("#metrics-tab-panel table")).toHaveCount(0);
    await expect(page.locator(".metrics-export")).toHaveCount(0);
    expect(await times(page)).toEqual([]); expect(errors).toEqual([]);
  };
  for (let round = 0; round < 2; round++) {
    await closed();
    corrupt = false;
    await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Delivery quality", exact: true })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Review rounds", exact: true })).toBeVisible();
    expect((await times(page)).length).toBe(3); expect(errors).toEqual([]);
    if (round === 0) {
      await page.getByText("Export CSV", { exact: true }).click();
      corrupt = true;
      await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
    }
  }
});

for (const scope of ["selected", "project"] as const) for (const failure of ["collection", "null row", "identity", "value", "date", "trigger", "duplicate"] as const) {
  test(`Statistics ${scope} Quality rejects malformed revision ${failure} before publication and recovers`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const id = await alpha(page);
    let corrupt = true, empty = false;
    await page.route("**/api/v1/projects/*/metrics?*", async route => {
      const body = await (await route.fetch()).json();
      const row = { project_id: id, run_id: "revision-evidence-run", revision: 1, trigger: "revise-label",
        date: "2026-10-25", tokens_in: 0, tokens_out: null, reported_cost_usd: 0, estimated_cost_usd: null };
      body.revisions = empty ? [] : [row];
      if (corrupt) body.revisions = failure === "collection" ? { length: 1 } : failure === "null row" ? [null] :
        failure === "identity" ? [{ ...row, run_id: {} }] : failure === "value" ? [{ ...row, tokens_in: {} }] :
        failure === "date" ? [{ ...row, date: "2026-02-30" }] : failure === "trigger" ? [{ ...row, trigger: {} }] : [row, row];
      await route.fulfill({ json: body });
    });
    await page.goto(scope === "project" ? `/projects/${id}/statistics?tab=quality` : `/metrics?project=${id}&tab=quality`);
    await expect(page.getByRole("tab", { name: "Quality", exact: true })).toHaveAttribute("aria-selected", "true");
    for (let round = 0; round < 2; round++) {
      await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
      await expect(page.getByRole("alert")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Delivery quality", exact: true })).toHaveCount(0);
      await expect(page.locator("#metrics-tab-panel table")).toHaveCount(0);
      await expect(page.locator(".metrics-export")).toHaveCount(0);
      expect(await times(page)).toEqual([]); expect(errors).toEqual([]);
      corrupt = false; empty = round === 1;
      await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Delivery quality", exact: true })).toBeVisible();
      await expect(page.getByRole("cell", { name: "revision-evidence-run", exact: true })).toHaveCount(empty ? 0 : 1);
      expect((await times(page)).length).toBe(3); expect(errors).toEqual([]);
      if (round === 0) {
        await page.getByText("Export CSV", { exact: true }).click();
        corrupt = true;
        await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
      }
    }
  });
}

for (const scope of ["global", "selected", "project"] as const) for (const failure of ["collection", "entry", "count", "money string", "negative money", "money object", "weighted product", "weighted sum", "pooled count"] as const) {
  // Summation overflow needs more than one individually valid project.
  if (scope !== "global" && (failure === "weighted sum" || failure === "pooled count")) continue;
  test(`Statistics ${scope} Quality rejects invalid efficiency ${failure} before publication and recovers`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const id = await alpha(page);
    let corrupt = true, unknown = false;
    await page.route(/\/api\/v1\/(?:projects\/[^/]+\/)?metrics\?/, async route => {
      const body = await (await route.fetch()).json();
      const entries = scope === "global" ? Object.values(body) : [body];
      if (scope === "global") expect(entries.length).toBeGreaterThan(1);
      entries.forEach((entry, index) => {
        const value = entry as { quality: { cost_efficiency: unknown } };
        const evidence = { jobs_with_evidence: index === 0 ? 1 : 3, usd_per_job: unknown ? null : index === 0 ? 0 : 8 };
        if (corrupt) {
          if (failure === "count") Object.assign(evidence, { jobs_with_evidence: "2" });
          if (failure === "money string") Object.assign(evidence, { usd_per_job: "invalid" });
          if (failure === "negative money") evidence.usd_per_job = -1;
          if (failure === "money object") Object.assign(evidence, { jobs_with_evidence: 0, usd_per_job: { toString: null } });
          if (failure === "weighted product") Object.assign(evidence, { jobs_with_evidence: 2, usd_per_job: 1e308 });
          if (failure === "weighted sum") Object.assign(evidence, { jobs_with_evidence: 1, usd_per_job: 1e308 });
          if (failure === "pooled count") Object.assign(evidence, { jobs_with_evidence: Number.MAX_SAFE_INTEGER, usd_per_job: 0 });
        }
        value.quality.cost_efficiency = corrupt && failure === "collection" ? [] :
          { reported_per_completed: corrupt && failure === "entry" ? null : evidence };
      });
      await route.fulfill({ json: body });
    });
    await page.goto(scope === "global" ? "/metrics?tab=quality" : scope === "selected" ? `/metrics?project=${id}&tab=quality` : `/projects/${id}/statistics?tab=quality`);
    await expect(page.getByRole("tab", { name: "Quality", exact: true })).toHaveAttribute("aria-selected", "true");
    for (let round = 0; round < 2; round++) {
      await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
      await expect(page.getByRole("alert")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Delivery quality", exact: true })).toHaveCount(0);
      await expect(page.locator("#metrics-tab-panel .metric-chips, #metrics-tab-panel table")).toHaveCount(0);
      await expect(page.locator(".metrics-export")).toHaveCount(0);
      expect(await times(page)).toEqual([]); expect(errors).toEqual([]);
      corrupt = false; unknown = round === 1;
      await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Delivery quality", exact: true })).toBeVisible();
      const chip = page.locator(".metric-chips > div").filter({ has: page.getByText("Reported / completed", { exact: true }) });
      await expect(chip.locator("dd")).toContainText(unknown ? "—" : scope === "global" ? "$6.00" : "$0.00");
      expect((await times(page)).length).toBe(3); expect(errors).toEqual([]);
      if (round === 0) {
        await page.getByText("Export CSV", { exact: true }).click();
        corrupt = true;
        await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
      }
    }
  });
}

for (const scope of ["global", "selected", "project"] as const) for (const failure of ["negative", "text", "fractional", "unsafe", "pooled overflow"] as const) {
  if (scope !== "global" && failure === "pooled overflow") continue;
  test(`Statistics ${scope} Usage rejects invalid unpriced ${failure} before publication and recovers`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const id = await alpha(page);
    let corrupt = true, absent = false, pooledCount = 0;
    await page.route(/\/api\/v1\/(?:projects\/[^/]+\/)?usage\?/, async route => {
      const body = await (await route.fetch()).json();
      const entries = (scope === "global" ? Object.entries(body) : [["alpha", body]]) as Array<[string, { totals: Record<string, unknown> }]>;
      if (scope === "global") expect(entries.length).toBeGreaterThan(1);
      pooledCount = (entries.length - 1) * 2;
      entries.forEach(([name, entry]) => {
        if (absent) delete entry.totals.unpriced_events;
        else entry.totals.unpriced_events = corrupt ? failure === "negative" ? -1 : failure === "text" ? "not-a-count" :
          failure === "fractional" ? 0.5 : failure === "unsafe" ? Number.MAX_SAFE_INTEGER + 1 : Number.MAX_SAFE_INTEGER : name === "alpha" ? 0 : 2;
      });
      await route.fulfill({ json: body });
    });
    await page.goto(scope === "global" ? "/metrics?tab=usage" : scope === "selected" ? `/metrics?project=${id}&tab=usage` : `/projects/${id}/statistics?tab=usage`);
    await expect(page.getByRole("tab", { name: "Usage", exact: true })).toHaveAttribute("aria-selected", "true");
    for (let round = 0; round < 2; round++) {
      await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
      await expect(page.getByRole("alert")).toBeVisible();
      await expect(page.locator("#metrics-tab-panel .usage-totals, #metrics-tab-panel table")).toHaveCount(0);
      await expect(page.locator(".metrics-export")).toHaveCount(0);
      expect(await times(page)).toEqual([]); expect(errors).toEqual([]);
      corrupt = false; absent = round === 1;
      await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
      const chip = page.locator(".usage-totals > div").filter({ has: page.getByText("Unpriced usage events", { exact: true }) });
      await expect(chip.locator("dd")).toHaveText(absent ? "—" : scope === "global" ? new Intl.NumberFormat("en").format(pooledCount) : "0");
      if (scope === "global") {
        const table = page.locator("#metrics-tab-panel table").filter({ has: page.getByRole("columnheader", { name: "Unpriced usage events", exact: true }) });
        await expect(table.locator("tbody tr").filter({ hasText: /^alpha/ }).locator("td").last()).toHaveText(absent ? "—" : "0");
      }
      expect((await times(page)).length).toBe(3); expect(errors).toEqual([]);
      if (round === 0) {
        await page.getByText("Export CSV", { exact: true }).click();
        corrupt = true;
        await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
      }
    }
  });
}

for (const family of ["period", "stock", "quality", "coverage", "daily", "totals", "duration", "review rounds"] as const) {
  test(`Statistics global rejects pooled ${family} precision loss before publication and recovers`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    let corrupt = true;
    await page.route(/\/api\/v1\/metrics\?/, async route => {
      const body = await (await route.fetch()).json();
      const entries = Object.values(body) as Metrics[];
      expect(entries.length).toBeGreaterThan(1);
      entries.forEach((value, index) => {
        const number = corrupt ? index === 0 ? Number.MAX_SAFE_INTEGER : 2 : 1;
        if (family === "period") value.period.started = number;
        if (family === "stock") value.current_stock!.jobs_now = number;
        if (family === "quality") value.quality.operator_retries = number;
        if (family === "coverage") value.coverage.usage_events_with_tokens = number;
        if (family === "totals") value.totals.runs = number;
        if (family === "review rounds") value.runs = [{ review_rounds: number }];
        if (family === "daily") value.daily = [{ date: "2026-10-25", started: number, completed: 0, failed: 0,
          tokens_in: null, tokens_out: null, mr_revisions: 0, pipeline_repairs: 0 }];
        if (family === "duration") value.duration = value.period.duration = { sampled_runs: 1, samples_seconds: [number],
          sum_span_seconds: number, avg_span_seconds: number, median_span_seconds: number };
      });
      await route.fulfill({ json: body });
    });
    await page.goto("/metrics");
    for (let round = 0; round < 2; round++) {
      await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
      await expect(page.getByRole("alert")).toBeVisible();
      await expect(page.locator(".statistics-evidence")).toHaveCount(0);
      await expect(page.locator(".metrics-export")).toHaveCount(0);
      expect(await times(page)).toEqual([]); expect(errors).toEqual([]);
      corrupt = false;
      await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
      await expect(page.locator(".statistics-evidence")).toBeVisible();
      expect((await times(page)).length).toBe(3); expect(errors).toEqual([]);
      if (round === 0) {
        await page.getByText("Export CSV", { exact: true }).click();
        corrupt = true;
        await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
      }
    }
  });
}

for (const known of [0, 7]) test(`Statistics global Usage keeps mixed ${known} and absent unpriced evidence unknown`, async ({ page }) => {
  let mixed = true;
  await page.route(/\/api\/v1\/usage\?/, async route => {
    const body = await (await route.fetch()).json();
    const entries = Object.entries(body) as Array<[string, { totals: Record<string, unknown> }]>;
    expect(entries.length).toBeGreaterThan(1);
    for (const [name, value] of entries) {
      if (mixed && name !== "alpha") delete value.totals.unpriced_events;
      else value.totals.unpriced_events = known;
    }
    await route.fulfill({ json: body });
  });
  await page.goto("/metrics?tab=usage");
  const chip = page.locator(".usage-totals > div").filter({ has: page.getByText("Unpriced usage events", { exact: true }) });
  await expect(chip.locator("dd")).toHaveText("—");
  const table = page.locator("#metrics-tab-panel table").filter({ has: page.getByRole("columnheader", { name: "Unpriced usage events", exact: true }) });
  await expect(table.locator("tbody tr").filter({ hasText: /^alpha/ }).locator("td").last()).toHaveText(String(known));
  await page.getByText("Export CSV", { exact: true }).click();
  for (const next of [false, true, false]) {
    mixed = next;
    await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(feedback(page)).toHaveAttribute("data-refreshing", "false");
    await expect(chip.locator("dd")).toHaveText(mixed ? "—" : String(known * 2));
    await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
    expect((await times(page)).length).toBe(3);
    await expect(page.getByRole("alert")).toHaveCount(0);
  }
});

for (const failure of ["application", "media", "foreign", "scope"] as const) test(`Statistics ${failure} refresh refuses both report members and exports`, async ({ page }) => {
  const id = await alpha(page);
  await page.goto(`/projects/${id}/statistics`);
  await expect(page.locator(".statistics-evidence")).toBeVisible();
  await page.getByText("Export CSV", { exact: true }).click();
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    if (failure === "application") return route.fulfill({ status: 503, json: { detail: { code: "network_error" } } });
    if (failure === "media") return route.fulfill({ contentType: "text/html", body: "not JSON" });
    const body = await (await route.fetch()).json();
    if (failure === "foreign") body.scope.project_ids = ["unrelated-project"];
    else body.scope.timezone = "Europe/Bucharest";
    return route.fulfill({ json: body });
  });
  await feedback(page).getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(feedback(page).getByRole("button", { name: "Retry", exact: true })).toBeVisible();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.locator(".statistics-evidence")).toHaveCount(0);
  await expect(page.locator(".metrics-export")).toHaveCount(0);
  await expect(feedback(page).getByRole("status")).toHaveCount(0);
  expect(await times(page)).toEqual([]);
  await page.unroute("**/api/v1/projects/*/usage?*");
  await feedback(page).getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator(".statistics-evidence")).toBeVisible();
  expect((await times(page)).length).toBe(3);
});

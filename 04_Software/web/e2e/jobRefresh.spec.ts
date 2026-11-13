/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { revalidateVisiblePage, trackScopeReads } from "./polling";
import { messages, type Locale } from "../src/i18n";

test.beforeEach(async ({ context, request, page }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  expect((await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
});
test.afterEach(async ({ page, request }) => {
  const me = await (await page.request.get("/api/v1/me")).json();
  await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } });
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});
const alphaId = async (page: Page): Promise<string> =>
  (await (await page.request.get("/api/v1/projects")).json()).find((p: {name: string}) => p.name === "alpha").id;

for (const resource of ["list", "detail", "usage"]) {
  test(`Jobs ${resource} failures distinguish stale information from authority and invalid evidence`, async ({ page }) => {
    await page.clock.install();
    const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
    const id = await alphaId(page);
    let failure = "initial";
    const pattern = resource === "list" ? "**/api/v1/jobs-page?*" : resource === "detail" ? "**/api/v1/jobs/*/ux-working" : "**/api/v1/projects/*/usage?*";
    await page.route(pattern, async route => {
      if (["initial", "transport"].includes(failure)) return route.abort("failed");
      if (failure === "denied") return route.fulfill({ status: 403, json: { detail: { code: "forbidden" } } });
      if (failure === "application") return route.fulfill({ status: 503, json: { detail: { code: "arbitrary_failure" } } });
      if (failure === "malformed") return route.fulfill({ status: 200, contentType: "application/json", body: "{" });
      if (failure === "token total") {
        const value = await (await route.fetch()).json();
        const job = value.jobs.find((item: { run_id: string }) => item.run_id === "ux-working");
        expect(job).toBeTruthy(); Object.assign(job.lifetime, { tokens_in: 5e15, tokens_out: 5e15 });
        return route.fulfill({ json: value });
      }
      return route.continue();
    });
    await page.goto(`/jobs?project=${id}&run=ux-working`);
    const workspace = page.locator(".job-workspace"), detail = workspace.locator(".detail-panel");
    const feedback = workspace.locator(resource === "list" ? ".jobs-list-refresh .refresh-feedback" : resource === "detail" ? ".jobs-detail-refresh .refresh-feedback" : ".jobs-consumption-refresh .refresh-feedback");
    await expect(feedback.getByRole("button", { name: "Retry", exact: true })).toBeVisible();
    await expect(feedback.locator("time")).toHaveCount(0);
    const evidence = resource === "list" ? workspace.locator(".action-jobs-table") : resource === "detail" ? detail : detail.locator(".job-consumption");
    await expect(evidence).toHaveCount(0);
    failure = ""; await feedback.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(evidence).toBeVisible();
    const cancel = detail.getByRole("button", { name: "Cancel", exact: true });
    await expect(cancel).toBeEnabled();
    const time = await feedback.locator("time").getAttribute("datetime");
    const node = await evidence.elementHandle();
    failure = "transport"; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(feedback.getByRole("status")).toContainText(messages.en.refreshStale);
    expect(await node!.evaluate(node => node.isConnected)).toBe(true);
    await expect(feedback.locator("time")).toHaveAttribute("datetime", time!);
    // Consumption is not command authority; stale list/detail is never permission to act.
    if (resource === "usage") await expect(cancel).toBeEnabled(); else await expect(cancel).toBeDisabled();
    let mutations = 0;
    page.on("request", request => { if (request.method() === "POST" && request.url().includes("/operations/")) mutations++; });
    if (resource !== "usage") {
      await cancel.evaluate((button: HTMLButtonElement) => button.click());
      expect(mutations).toBe(0);
    }
    failure = ""; await feedback.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(feedback.getByRole("status")).toHaveCount(0); await expect(cancel).toBeEnabled();
    for (const invalid of ["malformed", "application", ...(resource === "usage" ? ["token total"] : [])]) {
      failure = invalid; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
      await expect(feedback.getByRole("button", { name: "Retry", exact: true })).toBeVisible();
      await expect(evidence).toHaveCount(0); await expect(feedback.locator("time")).toHaveCount(0);
      await expect(feedback.getByRole("status")).toHaveCount(0); expect(errors).toEqual([]);
      failure = ""; await feedback.getByRole("button", { name: "Retry", exact: true }).click();
      await expect(evidence).toBeVisible();
    }
    // HTTP denial now crosses the shared session boundary: no resource-local
    // Retry may reuse old authority, even if /me still reports the old role.
    failure = "denied"; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(evidence).toHaveCount(0);
    await expect(page.locator(".job-workspace")).toHaveCount(0);
    await expect(page.locator('input[name="username"]')).toBeVisible();
    expect(mutations).toBe(0);
  });
}

for (const resource of ["list", "detail", "usage"]) {
  test(`Jobs ${resource} deadline distinguishes initial failure and stale retry without accepting late evidence`, async ({ page }) => {
    const settleScope = trackScopeReads(page);
    await page.clock.install();
    const id = await alphaId(page);
    let hold = true;
    const releases: Array<() => void> = [];
    const pattern = resource === "list" ? "**/api/v1/jobs-page?*" : resource === "detail" ? "**/api/v1/jobs/*/ux-working" : "**/api/v1/projects/*/usage?*";
    await page.route(pattern, async route => {
      const response = await route.fetch();
      if (hold) await new Promise<void>(resolve => releases.push(resolve));
      await route.fulfill({ response }).catch(() => undefined);
    });
    try {
      await page.goto(`/jobs?project=${id}&run=ux-working`);
      const feedback = page.locator(resource === "list" ? ".jobs-list-refresh .refresh-feedback" : resource === "detail" ? ".jobs-detail-refresh .refresh-feedback" : ".jobs-consumption-refresh .refresh-feedback");
      await expect.poll(() => releases.length).toBe(1);
      // Drain real supporting HTTP work before a virtual 30s jump. Only the
      // deliberately held resource is under deadline test, not session/metadata.
      await settleScope();
      // Let this in-flight request expire without a coincident automatic retry.
      await page.evaluate(() => {
        Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
        document.dispatchEvent(new Event("visibilitychange"));
      });
      await page.clock.fastForward(30001);
      await expect(feedback.getByRole("button", { name: "Retry", exact: true })).toBeVisible();
      await expect(feedback.locator("time")).toHaveCount(0);
      await expect(feedback.getByRole("status")).toHaveCount(0);
      hold = false; await feedback.getByRole("button", { name: "Retry", exact: true }).click();
      await expect(feedback.locator("time")).toHaveCount(1);
      await expect(page.locator(".detail-panel .job-consumption")).toBeVisible();
      const time = await feedback.locator("time").getAttribute("datetime");
      hold = true; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
      await expect.poll(() => releases.length).toBe(2);
      await page.clock.fastForward(30001);
      await expect(feedback.getByRole("status")).toContainText(messages.en.refreshStale);
      await expect(feedback.locator("time")).toHaveAttribute("datetime", time!);
      hold = false; await feedback.getByRole("button", { name: "Retry", exact: true }).click();
      await expect(feedback.getByRole("status")).toHaveCount(0);
      const recovered = await feedback.locator("time").getAttribute("datetime");
      releases.forEach(release => release());
      await expect(feedback.locator("time")).toHaveAttribute("datetime", recovered!);
    } finally { releases.forEach(release => release()); }
  });
}

for (const scope of ["global", "project", "history"]) {
  test(`Jobs ${scope} background and manual reads retain the server page and DOM`, async ({ page }) => {
    await page.clock.install();
    const id = await alphaId(page);
    const source = await (await page.request.get(`/api/v1/jobs-page?project_id=${id}&limit=all`)).json();
    let changed = false, hold = false, reads = 0;
    const releases: Array<() => void> = [];
    await page.route("**/api/v1/jobs-page?*", async route => {
      reads++;
      const query = new URL(route.request().url()).searchParams, offset = Number(query.get("offset"));
      const limit = query.get("limit") === "all" ? 62 : Number(query.get("limit"));
      const items = Array.from({ length: 62 }, (_, index) => ({ ...source.items[0], run_id: `refresh-${index}`,
        evidence_url: `/api/v1/jobs/${id}/refresh-${index}`, ticket_iid: 500 + index,
        ticket_title: `${changed ? "Changed" : "Stable"} refresh row ${index}` }));
      const result = { ...source, total: 62, limit, offset, items: items.slice(offset, offset + limit),
        counts: { [source.items[0].lifecycle]: 62 }, groups: { active: 0, waiting: 0, review: 0, terminal: 0, [source.items[0].status_group]: 62 } };
      if (hold) await new Promise<void>(resolve => releases.push(resolve));
      await route.fulfill({ json: result }).catch(() => undefined);
    });
    try {
      await page.goto(scope === "global" ? "/jobs?view=jobs" : `/projects/${id}/${scope === "history" ? "history" : "jobs?view=jobs"}`);
      const workspace = page.locator(".job-workspace"), feedback = workspace.locator(".jobs-list-refresh .refresh-feedback");
      const pager = workspace.locator(".table-pagination");
      await expect(workspace.locator(".action-jobs-table tbody tr")).toHaveCount(10);
      await workspace.getByLabel("Search jobs", { exact: true }).fill("refresh");
      await workspace.locator(".action-jobs-table").getByRole("button", { name: "Status", exact: true }).click();
      await expect(workspace.getByRole("columnheader", { name: "Status", exact: true })).toHaveAttribute("aria-sort", "ascending");
      await pager.getByRole("combobox").selectOption("25");
      await pager.getByRole("button", { name: "Next", exact: true }).click();
      await expect(pager).toContainText("26–50 / 62");
      await expect(feedback.locator("time")).toHaveCount(1);
      const row = await workspace.locator(".action-jobs-table tbody tr").first().elementHandle();
      const beforeTime = await feedback.locator("time").getAttribute("datetime");
      await pager.getByRole("combobox").focus();
      const focused = await pager.getByRole("combobox").elementHandle();
      await page.evaluate(() => scrollTo(0, 250));
      const scroll = await page.evaluate(() => scrollY);
      const before = reads; hold = true;
      await page.clock.fastForward(15000);
      await expect.poll(() => reads).toBe(before + 1);
      await expect(feedback).toHaveAttribute("data-refreshing", "true");
      await expect(workspace.locator(".action-jobs-table tbody tr")).toHaveCount(25);
      await expect(pager).toContainText("26–50 / 62");
      expect(await row!.evaluate(node => node.isConnected)).toBe(true);
      expect(await focused!.evaluate(node => node === document.activeElement)).toBe(true);
      expect(await page.evaluate(() => scrollY)).toBe(scroll);
      await expect(feedback.locator("time")).toHaveAttribute("datetime", beforeTime!);
      // Repeated click/visibility/tick triggers join the same owned read.
      await feedback.getByRole("button").focus(); await page.keyboard.press("Enter");
      await revalidateVisiblePage(page);
      expect(reads).toBe(before + 1);
      hold = false; releases.shift()!();
      await expect(feedback).toHaveAttribute("data-refreshing", "false");
      expect(await row!.evaluate(node => node.isConnected)).toBe(true);
      await expect(feedback.locator("time")).not.toHaveAttribute("datetime", beforeTime!);
      // Same-query explicit revalidation changes surviving values, not their identities.
      changed = true; hold = true;
      await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
      await expect.poll(() => releases.length).toBe(1);
      await expect(workspace.locator(".action-jobs-table")).toContainText("Stable refresh row 25");
      hold = false; releases.shift()!();
      await expect(workspace.locator(".action-jobs-table")).toContainText("Changed refresh row 25");
      expect(await row!.evaluate(node => node.isConnected)).toBe(true);
      await expect(pager.getByRole("combobox")).toHaveValue("25");
      await expect(workspace.getByLabel("Search jobs", { exact: true })).toHaveValue("refresh");
      await expect(workspace.getByRole("columnheader", { name: "Status", exact: true })).toHaveAttribute("aria-sort", "ascending");
      await expect(pager).toContainText("26–50 / 62");
      expect(await feedback.getByRole("button").evaluate(node => node === document.activeElement)).toBe(true);
    } finally { releases.forEach(release => release()); }
  });
}

test("Jobs rejected continuation requires explicit reload rather than polling a different snapshot", async ({ page }) => {
  await page.clock.install();
  await page.goto("/jobs?view=jobs");
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(10);
  let reads = 0, conflict = false;
  await page.route("**/api/v1/jobs-page?*", route => {
    reads++;
    const query = new URL(route.request().url()).searchParams;
    if (conflict && Number(query.get("offset")) > 0) return route.fulfill({ status: 409, json: { detail: { code: "job_snapshot_changed" } } });
    return route.continue();
  });
  const pager = page.locator(".job-workspace .table-pagination");
  await pager.getByRole("button", { name: "Next", exact: true }).click();
  await expect(pager).toContainText("11–");
  conflict = true;
  await page.locator(".jobs-list-refresh").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Job sources changed", exact: true })).toBeVisible();
  await expect(page.locator(".action-jobs-table")).toHaveCount(0);
  const failedReads = reads;
  await page.clock.fastForward(30000); await revalidateVisiblePage(page);
  await page.locator(".jobs-list-refresh").getByRole("button", { name: "Retry", exact: true }).click();
  expect(reads).toBe(failedReads);
  await page.getByRole("button", { name: "Reload first page", exact: true }).click();
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(10);
  await expect(pager).toContainText("1–10");
  expect(reads).toBe(failedReads + 1);
});

test("Jobs hidden return coalesces, query and navigation cancel owned reads, and deadlines release stale authority", async ({ page }) => {
  await page.clock.install();
  const id = await alphaId(page);
  let hold = false, reads = 0;
  const releases: Array<() => void> = [];
  await page.route("**/api/v1/jobs-page?*", async route => {
    reads++;
    const response = await route.fetch();
    if (hold) await new Promise<void>(resolve => releases.push(resolve));
    await route.fulfill({ response }).catch(() => undefined);
  });
  try {
    await page.goto(`/jobs?project=${id}&run=ux-working`);
    const feedback = page.locator(".jobs-list-refresh .refresh-feedback");
    await expect(feedback.locator("time")).toHaveCount(1);
    const before = reads;
    await page.evaluate(() => {
      Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await page.clock.fastForward(60000); expect(reads).toBe(before);
    hold = true;
    await page.evaluate(() => {
      Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
      document.dispatchEvent(new Event("visibilitychange")); document.dispatchEvent(new Event("visibilitychange"));
    });
    await expect.poll(() => releases.length).toBe(1); expect(reads).toBe(before + 1);
    const cancelled = page.waitForEvent("requestfailed", request => request.url().includes("jobs-page?"));
    await page.getByLabel("Search jobs", { exact: true }).fill("ux-working");
    await cancelled; await expect.poll(() => releases.length).toBe(2);
    await expect(page.locator(".action-jobs-table")).toHaveCount(0);
    await expect(feedback.locator("time")).toHaveCount(0);
    releases[0](); hold = false; releases[1]();
    await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(1);
    await expect(feedback).toHaveAttribute("data-refreshing", "false");
    // The finite slot releases without any obsolete completion or tick backlog.
    const last = await feedback.locator("time").getAttribute("datetime");
    hold = true; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect.poll(() => releases.length).toBe(3);
    const expired = page.waitForEvent("requestfailed", request => request.url().includes("jobs-page?"));
    await page.clock.fastForward(30001); await expired;
    await expect(feedback.getByRole("status")).toContainText(messages.en.refreshStale);
    await expect(feedback.locator("time")).toHaveAttribute("datetime", last!);
    await expect(page.locator(".detail-panel").getByRole("button", { name: "Cancel", exact: true })).toBeDisabled();
    hold = false; await feedback.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(feedback.getByRole("status")).toHaveCount(0);
    const recovered = await feedback.locator("time").getAttribute("datetime");
    releases[2](); await expect(feedback.locator("time")).toHaveAttribute("datetime", recovered!);
    hold = true; await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect.poll(() => releases.length).toBe(4);
    const leaving = page.waitForEvent("requestfailed", request => request.url().includes("jobs-page?"));
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await leaving;
    const exited = reads; releases[3](); await page.clock.fastForward(60000);
    expect(reads).toBe(exited); await expect(page.locator(".job-workspace")).toHaveCount(0);
  } finally { releases.forEach(release => release()); }
});

test("Jobs detail and consumption remain mounted with manual output through parent reads", async ({ page }) => {
  await page.clock.install();
  const id = await alphaId(page);
  let hold = false, changedTitle = false, changedRevision = false, detailReads = 0, usageReads = 0, outputReads = 0;
  const releases: Array<() => void> = [];
  for (const [pattern, kind] of [["**/api/v1/jobs/*/ux-clarification", "detail"], ["**/api/v1/projects/*/usage?*", "usage"]]) {
    await page.route(pattern, async route => {
      if (kind === "detail") detailReads++; else usageReads++;
      const response = await route.fetch(), value = await response.json();
      if (kind === "detail") value.job.timeline = Array.from({ length: changedTitle ? 41 : 40 }, (_, index) => ({
        ts: `2026-11-05T10:12:${String(index).padStart(2, "0")}Z`, event: `stable-timeline-${index}`, stage: "build",
      }));
      if (kind === "detail" && changedTitle) value.job.ticket_title = "Updated clarification title";
      if (kind === "detail" && changedRevision) value.job.state_revision = "f".repeat(64);
      if (hold) await new Promise<void>(resolve => releases.push(resolve));
      await route.fulfill({ response, json: value }).catch(() => undefined);
    });
  }
  await page.route("**/api/v1/jobs/*/ux-clarification/executor-output", route => {
    outputReads++;
    return route.fulfill({ json: { project_id: id, run_id: "ux-clarification", availability: "observed", exit_code: 0, timed_out: false,
      stdout: "diagnostic: network\n" + Array(100).fill("[other output withheld]").join("\n"), stderr: "" } });
  });
  try {
    await page.goto(`/jobs?project=${id}&run=ux-clarification`);
    const detail = page.locator(".detail-panel"), amounts = detail.locator(".job-consumption");
    await expect(amounts).toBeVisible();
    await detail.getByRole("button", { name: "View latest executor output", exact: true }).click();
    const output = detail.locator(".executor-output pre").first();
    await expect(output).toContainText("diagnostic: network");
    await detail.locator("details > summary").click();
    const timelinePager = detail.locator(".timeline-pagination");
    await timelinePager.getByRole("combobox").selectOption("25");
    await timelinePager.getByRole("button", { name: "Next", exact: true }).click();
    const timelineRow = await detail.locator(".timeline-table tbody tr").filter({ hasText: "stable-timeline-10" }).elementHandle();
    await output.focus();
    const node = await output.elementHandle(), panel = await detail.elementHandle(), amountNode = await amounts.elementHandle();
    await output.evaluate(node => {
      node.scrollTop = 120;
      const range = document.createRange(); range.setStart(node.firstChild!, 0); range.setEnd(node.firstChild!, 24);
      const selection = getSelection()!; selection.removeAllRanges(); selection.addRange(range);
    });
    const selection = await page.evaluate(() => getSelection()!.toString());
    const localScroll = await output.evaluate(node => node.scrollTop);
    const before = [detailReads, usageReads]; hold = true;
    await page.clock.fastForward(30000);
    await expect.poll(() => [detailReads, usageReads]).toEqual([before[0] + 1, before[1] + 1]);
    await expect(detail).toBeVisible(); await expect(amounts).toBeVisible();
    expect(await panel!.evaluate(node => node.isConnected)).toBe(true);
    expect(await amountNode!.evaluate(node => node.isConnected)).toBe(true);
    expect(await node!.evaluate(node => node === document.activeElement)).toBe(true);
    expect(await page.evaluate(() => getSelection()!.toString())).toBe(selection);
    expect(outputReads).toBe(1);
    hold = false; releases.splice(0).forEach(release => release());
    await expect(page.locator(".jobs-detail-refresh .refresh-feedback")).toHaveAttribute("data-refreshing", "false");
    expect(await node!.evaluate(node => node.isConnected && node === document.activeElement)).toBe(true);
    expect(await output.evaluate(node => node.scrollTop)).toBe(localScroll);
    expect(await page.evaluate(() => getSelection()!.toString())).toBe(selection);
    await expect(detail.locator("details")).toHaveAttribute("open", "");
    expect(outputReads).toBe(1);
    changedTitle = true;
    await page.locator(".jobs-detail-refresh").getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(detail.locator(".panel-heading h2")).toHaveText("Updated clarification title");
    expect(await node!.evaluate(node => node.isConnected)).toBe(true); expect(outputReads).toBe(1);
    expect(await timelineRow!.evaluate(node => node.isConnected)).toBe(true);
    await expect(timelinePager.getByRole("combobox")).toHaveValue("25");
    await expect(timelinePager).toContainText("26–41 / 41");
    // Preserve, never relax, the existing conservative revision-bound output invalidation.
    changedRevision = true;
    await page.locator(".jobs-detail-refresh").getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(output).toHaveCount(0);
    await expect(detail.getByRole("button", { name: "View latest executor output", exact: true })).toBeEnabled();
    expect(outputReads).toBe(1);
  } finally { releases.forEach(release => release()); }
});

for (const outcome of ["succeeded", "failed"]) {
  test(`Jobs ${outcome} operation rereads after the write without losing detail or trusting pre-write evidence`, async ({ page }) => {
    await page.clock.install();
    const id = await alphaId(page);
    let hold = false, afterResult = false, listReads = 0, detailReads = 0, usageReads = 0, outputReads = 0;
    const releases: Array<() => void> = [];
    for (const [pattern, kind] of [["**/api/v1/jobs-page?*", "list"], ["**/api/v1/jobs/*/ux-working", "detail"], ["**/api/v1/projects/*/usage?*", "usage"]]) {
      await page.route(pattern, async route => {
        if (kind === "list") listReads++; else if (kind === "detail") detailReads++; else usageReads++;
        const response = await route.fetch(), value = await response.json();
        if (kind === "detail" && afterResult) value.job.ticket_title = "Observed post-operation title";
        if (hold) await new Promise<void>(resolve => releases.push(resolve));
        await route.fulfill({ response, json: value }).catch(() => undefined);
      });
    }
    await page.route("**/api/v1/jobs/*/ux-working/executor-output", route => {
      outputReads++;
      return route.fulfill({ json: { project_id: id, run_id: "ux-working", availability: "observed", exit_code: 0,
        timed_out: false, stdout: "diagnostic: network", stderr: "" } });
    });
    let finish!: () => void;
    const pending = new Promise<void>(resolve => { finish = resolve; });
    await page.route("**/operations/cancel", route => route.fulfill({ json: { id: 7701, status: "pending" } }));
    await page.route("**/operations/7701", async route => {
      await pending; afterResult = true;
      await route.fulfill({ json: { id: 7701, status: outcome } }).catch(() => undefined);
    });
    try {
      await page.goto(`/jobs?project=${id}&run=ux-working`);
      const detail = page.locator(".detail-panel"), cancel = detail.getByRole("button", { name: "Cancel", exact: true });
      await expect(cancel).toBeEnabled();
      const pager = page.locator(".job-workspace .table-pagination");
      await pager.getByRole("combobox").selectOption("25");
      await expect(page.locator(".jobs-list-refresh .refresh-feedback")).toHaveAttribute("data-refreshing", "false");
      await detail.getByRole("button", { name: "View latest executor output", exact: true }).click();
      await expect(detail.locator(".executor-output pre").first()).toContainText("diagnostic: network");
      await detail.locator("details > summary").click();
      const panel = await detail.elementHandle(), output = await detail.locator(".executor-output pre").first().elementHandle();
      hold = true; await revalidateVisiblePage(page);
      await expect.poll(() => releases.length).toBe(3);
      const aborted: string[] = [];
      page.on("requestfailed", request => { if (/jobs-page|\/jobs\/.*ux-working$|\/usage\?/.test(request.url())) aborted.push(request.url()); });
      page.once("dialog", dialog => dialog.accept()); await cancel.click();
      await expect.poll(() => aborted.length).toBe(3);
      const before = [listReads, detailReads, usageReads];
      await page.clock.fastForward(16000);
      expect([listReads, detailReads, usageReads]).toEqual(before);
      // Read controls cannot bypass the write/queued-operation boundary.
      await page.locator(".jobs-detail-refresh").getByRole("button").click();
      expect(detailReads).toBe(before[1]);
      await detail.locator(".executor-output pre").first().focus();
      finish();
      await expect.poll(() => releases.length).toBe(6);
      expect(await panel!.evaluate(node => node.isConnected)).toBe(true);
      expect(await output!.evaluate(node => node.isConnected && node === document.activeElement)).toBe(true);
      await expect(detail.locator("details")).toHaveAttribute("open", "");
      await expect(cancel).toBeDisabled();
      // The cancelled pre-write successes cannot restore authority or advance time.
      releases.slice(0, 3).forEach(release => release());
      await expect(cancel).toBeDisabled();
      hold = false; releases.slice(3).forEach(release => release());
      await expect(detail.locator(".panel-heading h2")).toHaveText("Observed post-operation title");
      await expect(cancel).toBeEnabled();
      expect(await output!.evaluate(node => node.isConnected && node === document.activeElement)).toBe(true);
      expect(outputReads).toBe(1);
      await expect(pager.getByRole("combobox")).toHaveValue("25");
      await expect(page.locator(".command-result")).toContainText(`#7701`);
      await expect(page.locator(".command-result")).toContainText(outcome === "succeeded" ? "Command completed" : "Command failed");
    } finally { finish(); releases.forEach(release => release()); }
  });
}

test("Jobs worker and operation reads coalesce, expire and cancel on navigation without late publication", async ({ page }) => {
  const settleScope = trackScopeReads(page);
  await page.clock.install();
  const id = await alphaId(page);
  await page.goto(`/jobs?project=${id}&run=ux-working`);
  const cancel = page.locator(".detail-panel").getByRole("button", { name: "Cancel", exact: true });
  await expect(cancel).toBeEnabled();
  let workerReads = 0, operationReads = 0, hold = true;
  const releases: Array<() => void> = [];
  await page.route("**/api/v1/ready", async route => {
    workerReads++;
    if (hold) await new Promise<void>(resolve => releases.push(resolve));
    await route.fulfill({ json: { status: "ready", worker: "ready", activity: "idle" } }).catch(() => undefined);
  });
  await page.route("**/operations/cancel", route => route.fulfill({ json: { id: 7702, status: "pending" } }));
  await page.route("**/operations/7702", async route => {
    operationReads++;
    if (hold) await new Promise<void>(resolve => releases.push(resolve));
    await route.fulfill({ json: { id: 7702, status: "succeeded" } }).catch(() => undefined);
  });
  try {
    page.once("dialog", dialog => dialog.accept()); await cancel.click();
    await expect.poll(() => operationReads).toBe(1);
    await page.clock.fastForward(5000);
    await expect.poll(() => workerReads).toBe(1);
    await page.clock.fastForward(16000); await revalidateVisiblePage(page);
    expect([workerReads, operationReads]).toEqual([1, 1]);
    await page.evaluate(() => {
      Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await settleScope();
    const aborted: string[] = [];
    page.on("requestfailed", request => { if (/\/ready$|\/operations\/7702$/.test(request.url())) aborted.push(request.url()); });
    await page.clock.fastForward(30001);
    await expect.poll(() => aborted.length).toBe(2);
    await expect(page.locator(".command-result")).toContainText("Command status could not be read; completion is unknown.");
    await expect(page.locator(".worker-evidence")).toBeVisible();
    expect([workerReads, operationReads]).toEqual([1, 1]);
    hold = false; await revalidateVisiblePage(page);
    await expect(page.locator(".command-result")).toContainText("Command completed");
    await expect(page.locator(".worker-evidence")).toHaveCount(0);
    const done = operationReads;
    releases.splice(0).forEach(release => release()); await page.clock.fastForward(6000);
    expect(operationReads).toBe(done);
    hold = true; await revalidateVisiblePage(page);
    await expect.poll(() => releases.length).toBe(1);
    const leaving = page.waitForEvent("requestfailed", request => request.url().endsWith("/ready"));
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await leaving;
    const exited = workerReads; releases.forEach(release => release()); await page.clock.fastForward(60000);
    expect(workerReads).toBe(exited);
  } finally { releases.forEach(release => release()); }
});

test("Jobs failed post-operation evidence never restores command authority from a retained pre-write detail", async ({ page }) => {
  await page.clock.install();
  const id = await alphaId(page);
  await page.goto(`/jobs?project=${id}&run=ux-working`);
  const detail = page.locator(".detail-panel"), cancel = detail.getByRole("button", { name: "Cancel", exact: true });
  await expect(cancel).toBeEnabled();
  await page.route("**/api/v1/jobs/*/ux-working", route => route.abort("failed"));
  await page.route("**/operations/cancel", route => route.fulfill({ json: { id: 7703, status: "failed" } }));
  page.once("dialog", dialog => dialog.accept()); await cancel.click();
  const feedback = page.locator(".jobs-detail-refresh .refresh-feedback");
  await expect(feedback.getByRole("status")).toContainText(messages.en.refreshStale);
  await expect(detail).toBeVisible(); await expect(cancel).toBeDisabled();
  await page.locator(".jobs-list-refresh").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".jobs-list-refresh .refresh-feedback")).toHaveAttribute("data-refreshing", "false");
  await expect(cancel).toBeDisabled();
  await page.unroute("**/api/v1/jobs/*/ux-working");
  await feedback.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(cancel).toBeEnabled();
});

test("Jobs running operation keeps one polling owner and cancels it when its view exits", async ({ page }) => {
  await page.clock.install();
  const id = await alphaId(page);
  let reads = 0, release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/operations/cancel", route => route.fulfill({ json: { id: 7704, status: "pending" } }));
  await page.route("**/operations/7704", async route => {
    reads++;
    if (reads > 1) await held;
    await route.fulfill({ json: { id: 7704, status: reads === 1 ? "running" : "succeeded" } }).catch(() => undefined);
  });
  try {
    await page.goto(`/jobs?project=${id}&run=ux-working`);
    const cancel = page.locator(".detail-panel").getByRole("button", { name: "Cancel", exact: true });
    await expect(cancel).toBeEnabled();
    page.once("dialog", dialog => dialog.accept()); await cancel.click();
    await expect(page.locator(".command-result")).toContainText("Command running");
    expect(reads).toBe(1);
    await page.clock.fastForward(2000); await expect.poll(() => reads).toBe(2);
    await page.clock.fastForward(8000); expect(reads).toBe(2);
    const aborted = page.waitForEvent("requestfailed", request => request.url().endsWith("/operations/7704"));
    await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Projects", exact: true }).click();
    await aborted; release(); await page.clock.fastForward(60000);
    expect(reads).toBe(2); await expect(page.locator(".command-result")).toHaveCount(0);
  } finally { release(); }
});

test("Jobs run navigation cancels the old operation even inside the same project", async ({ page }) => {
  await page.clock.install();
  const id = await alphaId(page);
  let reads = 0, release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/operations/cancel", route => route.fulfill({ json: { id: 7705, status: "pending" } }));
  await page.route("**/operations/7705", async route => {
    reads++; await held;
    await route.fulfill({ json: { id: 7705, status: "succeeded" } }).catch(() => undefined);
  });
  try {
    await page.goto(`/jobs?project=${id}&run=ux-working`);
    const cancel = page.locator(".detail-panel").getByRole("button", { name: "Cancel", exact: true });
    await expect(cancel).toBeEnabled();
    page.once("dialog", dialog => dialog.accept()); await cancel.click();
    await expect.poll(() => reads).toBe(1);
    const aborted = page.waitForEvent("requestfailed", request => request.url().endsWith("/operations/7705"));
    await page.locator('.action-jobs-table a[href*="ux-clarification"]').click();
    await aborted;
    await expect(page.locator(".detail-panel")).toContainText("Waiting for clarification");
    await expect(page.locator(".detail-panel").getByRole("button", { name: "Cancel", exact: true })).toBeEnabled();
    release(); await page.clock.fastForward(6000);
    await expect(page.locator(".command-result")).toHaveCount(0); expect(reads).toBe(1);
  } finally { release(); }
});

test("Jobs worker refuses malformed successful readiness evidence and retains its unavailable distinction", async ({ page }) => {
  await page.clock.install();
  await page.goto("/jobs?view=jobs");
  await expect(page.locator(".action-jobs-table")).toBeVisible();
  let invalid = true;
  await page.route("**/api/v1/ready", route => invalid
    ? route.fulfill({ json: { status: "ready", worker: false, activity: "idle" } })
    : route.fulfill({ status: 503, json: { detail: { code: "worker_unavailable" } } }));
  await revalidateVisiblePage(page);
  await expect(page.locator(".worker-evidence")).toContainText("Worker status could not be read");
  invalid = false; await revalidateVisiblePage(page);
  await expect(page.locator(".worker-evidence")).toContainText("Worker unavailable or heartbeat stale");
  await page.unroute("**/api/v1/ready"); await revalidateVisiblePage(page);
  await expect(page.locator(".worker-evidence")).toHaveCount(0);
});

test("Jobs refresh feedback supports four locales, keyboard retry and both narrow themes", async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 390, height: 844 });
  const id = await alphaId(page), me = await (await page.request.get("/api/v1/me")).json();
  for (const locale of ["en", "fr", "de", "ro"] as Locale[]) {
    for (const theme of ["light", "dark"]) {
      expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } })).ok()).toBe(true);
      await page.goto(`/jobs?project=${id}&run=ux-working`);
      const feedback = page.locator(".jobs-detail-refresh .refresh-feedback");
      await expect(feedback.locator("time")).toHaveCount(1);
      await page.route("**/api/v1/jobs/*/ux-working", route => route.abort("failed"));
      await feedback.getByRole("button", { name: messages[locale].refresh, exact: true }).click();
      await expect(feedback.getByRole("status")).toHaveText(messages[locale].refreshStale);
      await expect(page.locator(".detail-panel")).toBeVisible();
      await feedback.getByRole("button", { name: messages[locale].retry, exact: true }).focus();
      await page.unroute("**/api/v1/jobs/*/ux-working"); await page.keyboard.press("Enter");
      await expect(feedback.getByRole("status")).toHaveCount(0);
      await expect(feedback.getByRole("button", { name: messages[locale].refresh, exact: true })).toBeFocused();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    }
  }
});

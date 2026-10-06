/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";

const nav = (page: Page) => page.getByRole("navigation", { name: "Primary navigation", exact: true });
async function signIn(page: Page, user = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(user);
  await page.getByLabel("Password", { exact: false }).fill(user === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}
test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});
test.beforeEach(async ({ request }) => {
  const response = await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } });
  expect(response.ok()).toBe(true);
});
test.afterEach(async ({ request, page }) => {
  await page.goto("about:blank");
  const response = await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } });
  expect(response.ok()).toBe(true);
});

test("overview foregrounds complete authorized attention before current cards", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Needs attention", exact: true })).toBeVisible();
  await expect(page.getByLabel("Job scope", { exact: true })).toHaveValue("");
  await expect(page.locator(".job-workspace .scope-note")).toHaveText("All authorized projects");
  await expect(page.getByText("Worker available", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /merge|approve|pause job|resume job/i })).toHaveCount(0);
});

test("hub separates pickup and verification and keeps role-appropriate navigation", async ({ page }) => {
  await signIn(page);
  await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
  await expect(page.getByRole("columnheader", { name: "Pickup", exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Environment verification", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "alpha", exact: true }).click();
  await expect(page.getByText("Active jobs continue when pickup is stopped.", { exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Summary", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Settings", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "History", exact: true })).toBeVisible();
});

test("manual start explains queue effect and reports asynchronous worker failure", async ({ page }) => {
  await signIn(page);
  await page.goto("/jobs?project=alpha");
  await expect(page.getByText("The worker will attempt this existing ticket through the configured selection, readiness and approval gates.", { exact: true })).toBeVisible();
  await page.locator("#job-ticket-number").fill("43");
  await page.getByRole("button", { name: "Start job", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Command failed" })).toContainText("engine rejected operation");
  await expect(page.getByText("Command completed", { exact: false })).toHaveCount(0);
});

test("all real lifecycle groups explain exact stage evidence and protected handoffs", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const id = projects.find((row: { name: string }) => row.name === "alpha").id;
  const cases = [
    ["working", "Working", "Build", true], ["publishing", "Publishing", "Deliver", true],
    ["clarification", "Waiting for clarification", "Build", true], ["approval", "Waiting for approval", "Deliver", true],
    ["review", "Draft review", "Done", true], ["handoff-pending", "Handoff pending", "Build", false],
    ["handed-off", "Handed off", "Build", false], ["done", "Completed", "Done", false],
    ["failed", "Failed", "Build", false], ["cancelled", "Cancelled", "Build", false], ["stale", "Stale", "Build", false],
  ] as const;
  for (const [suffix, _status, _stage, cancellable] of cases) {
    await page.goto(`/jobs?project=${id}&run=ux-${suffix}`);
    const detail = page.locator(".detail-panel");
    await expect(detail.getByRole("heading", { name: "What is happening now" })).toBeVisible();
    await expect(detail.locator(".next-action-panel .status")).toContainText(_status);
    await expect(detail.locator(".next-action-panel")).toContainText(`Stage: ${_stage}`);
    await expect(detail.getByText("Who acts", { exact: true })).toBeVisible();
    await expect(detail.getByText("Where", { exact: true })).toBeVisible();
    await expect(detail.getByText("What follows", { exact: true })).toBeVisible();
    await expect(detail.getByRole("button", { name: "Cancel", exact: true })).toHaveCount(cancellable ? 1 : 0);
    await expect(detail.getByRole("button", { name: "Retry", exact: true })).toHaveCount(suffix === "failed" ? 1 : 0);
    await expect(detail.getByRole("button", { name: /merge|approve|pause|resume/i })).toHaveCount(0);
    await expect(detail).not.toContainText(/\d+%/);
    if (suffix === "done") await expect(detail).toContainText("does not establish a human merge");
    if (suffix === "handed-off") await expect(detail).toContainText("retained worktree is protected");
  }
  expect(errors).toEqual([]);
});

test("clarification candidate and draft actions open actual saved locations and quick path", async ({ page }) => {
  await signIn(page);
  for (const [run, name, href] of [
    ["ux-clarification", "Answer on the ticket", "https://forge.example/offline/alpha/issues/42#note_7"],
    ["ux-approval", "Review the candidate on the forge", "https://forge.example/offline/alpha/issues/42#note_8"],
    ["ux-review", "Review the draft MR/PR", "https://forge.example/offline/alpha/pulls/3"],
  ]) {
    await page.goto(`/jobs?project=alpha&run=${run}`);
    const detail = page.locator(".detail-panel");
    await expect(detail.locator(".next-action-panel").getByRole("link", { name })).toHaveAttribute("href", href);
    await expect(detail).toContainText("Named person not recorded");
    if (run === "ux-clarification") {
      await expect(detail).toContainText("Which export format?");
      await expect(detail).not.toContainText("fixture-secret");
    }
    if (run === "ux-approval") {
      const timeline = detail.getByRole("table", { name: "Timeline" });
      await expect(timeline).toContainText("Frame"); await expect(timeline).toContainText("Build"); await expect(timeline).toContainText("Validate");
      await expect(timeline).not.toContainText("Specify"); await expect(timeline).not.toContainText("Design");
      await expect(detail).toContainText("Only saved events are shown.");
    }
  }
});

test("missing evidence and stale worker activity do not fabricate telemetry or actions", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/ready", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":{"code":"worker_unavailable"}}' }));
  await page.goto("/jobs?project=alpha&run=ux-missing");
  await expect(page.getByText("Worker unavailable or heartbeat stale", { exact: true })).toBeVisible();
  const detail = page.locator(".detail-panel");
  await expect(detail.getByRole("heading", { name: "Ticket title not recorded" })).toBeVisible();
  await expect(detail).toContainText("No activity timestamp recorded.");
  await expect(detail).toContainText("saved evidence does not identify an action location");
  await expect(detail.locator(".next-action-panel a")).toHaveCount(0);
  await detail.getByText("Technical details", { exact: true }).click();
  await expect(detail.locator(".job-consumption").first()).toContainText("Input tokens: —Not available");
  await expect(detail.locator(".job-consumption").first()).toContainText("Output tokens: —Not available");
  await page.goto("/jobs?project=alpha&run=ux-working");
  await expect(page.locator(".detail-panel")).toContainText("over 15 minutes old");
});

test("global complete search paging advanced filters and source revision conflicts", async ({ page }) => {
  await signIn(page); await page.goto("/jobs");
  await expect(page.locator("#jobs-project")).toHaveValue("");
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(10);
  const continuation = page.waitForRequest(request => request.url().includes("jobs-page?") && new URL(request.url()).searchParams.get("offset") === "10");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  expect(new URL((await continuation).url()).searchParams.get("snapshot")).toMatch(/^[a-f0-9]{64}$/);
  await expect(page.locator(".action-jobs-table tbody tr")).not.toHaveCount(10);
  await page.request.post("/__e2e__/jobs?mode=mutate", { headers: { "X-ADORE-E2E": "local-test" } });
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Job sources changed", exact: true })).toBeVisible();
  await expect(page.locator(".action-jobs-table")).toHaveCount(0);
  await page.getByRole("button", { name: "Reload first page", exact: true }).click();
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(10);
  await page.getByLabel("Search jobs", { exact: true }).fill("actual beta collision");
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(1);
  await expect(page.locator(".action-jobs-table")).toContainText("beta");
  await page.getByLabel("Search jobs", { exact: true }).fill("no-such-ticket");
  await expect(page.getByText("No jobs match these filters", { exact: true })).toBeVisible();
  await page.getByLabel("Search jobs", { exact: true }).fill("");
  await page.getByRole("button", { name: "Advanced filters", exact: true }).click();
  await page.getByLabel("Observed executor", { exact: true }).fill("pi");
  await expect(page.locator(".action-jobs-table")).not.toContainText("Actual beta collision");
  await page.getByLabel("Observed executor", { exact: true }).fill("PI");
  await expect(page.getByText("No jobs match these filters", { exact: true })).toBeVisible();
});

test("composite colliding IDs and reload preserve the owning project", async ({ page }) => {
  await signIn(page);
  await page.goto("/jobs");
  await page.getByLabel("Search jobs", { exact: true }).fill("ux-working");
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(2);
  const links = await page.locator(".action-jobs-table tbody td:first-child a").evaluateAll(nodes => nodes.map(node => (node as HTMLAnchorElement).href));
  expect(new Set(links).size).toBe(2);
  await page.getByRole("link", { name: /Actual beta collision/ }).click();
  await expect(page.locator(".detail-panel .panel-heading h2")).toHaveText("Actual beta collision");
  await expect(page.getByRole("region", { name: "Project context" })).toContainText("beta");
  await page.reload();
  await expect(page.locator(".detail-panel .panel-heading h2")).toHaveText("Actual beta collision");
  await page.locator(".detail-panel").getByRole("button", { name: "Close", exact: true }).click();
  await expect(page).not.toHaveURL(/run=/);
});

test("incomplete corrupt and failed job reads hide totals and stale details", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/jobs-page?*", async route => {
    const response = await route.fetch(); const value = await response.json(); value.complete = false;
    await route.fulfill({ response, json: value });
  });
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Incomplete job response", exact: true })).toBeVisible();
  await expect(page.locator(".overview-card")).toHaveCount(0);
  await page.unroute("**/api/v1/jobs-page?*");
  await page.route("**/api/v1/jobs-page?*", route => route.fulfill({ status: 200, contentType: "application/json", body: '{"complete":true,"items":[],"total":-1}' }));
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Could not load data", exact: true })).toBeVisible();
  await expect(page.locator(".overview-card")).toHaveCount(0);
  await page.unroute("**/api/v1/jobs-page?*");
  await page.request.post("/__e2e__/jobs?mode=corrupt", { headers: { "X-ADORE-E2E": "local-test" } });
  await page.goto("/jobs");
  await expect(page.getByRole("heading", { name: "Could not load data", exact: true })).toBeVisible();
  await expect(page.locator(".action-jobs-table")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText("BROKEN_FIXTURE_SECRET");
});

test("developer search counts navigation direct routes and command CSRF exclude other projects", async ({ page }) => {
  await signIn(page, "developer");
  await page.goto("/jobs");
  await expect(page.locator("#jobs-project option")).toHaveCount(2);
  await page.getByLabel("Search jobs", { exact: true }).fill("beta");
  await expect(page.locator(".action-jobs-table")).toHaveCount(0);
  const admin = await page.request.post("/api/v1/session", { data: { username: "admin", password: "admin" } });
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const beta = projects.find((row: { name: string }) => row.name === "beta").id;
  const dev = await page.request.post("/api/v1/session", { data: { username: "developer", password: "test-password" } });
  expect(admin.ok() && dev.ok()).toBe(true);
  expect((await page.request.get(`/api/v1/jobs/${beta}/ux-working`)).status()).toBe(404);
  expect((await page.request.get(`/api/v1/jobs-page?project_id=${beta}`)).status()).toBe(404);
  expect((await page.request.post("/api/v1/projects/alpha/operations/start", { data: { ticket_iid: 42, idempotency_key: "missing-csrf" } })).status()).toBe(403);
  await page.goto(`/jobs?project=${beta}&run=ux-working`);
  await expect(page.locator(".detail-panel")).toHaveCount(0);
  await expect(page.getByRole("alert").first()).toContainText("project");
  await page.goto("/projects/alpha/access");
  await expect(page.getByRole("tab", { name: "Access", exact: true })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Summary", exact: true })).toBeVisible();
});

test("queued pending and final successful commands do not predict job outcome", async ({ page }) => {
  await signIn(page); await page.goto("/jobs?project=alpha");
  let release!: () => void; const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/operations/*", async route => { const response = await route.fetch(); await pending; await route.fulfill({ response }); });
  let submits = 0; page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/operations/start")) submits++; });
  await page.locator("#job-ticket-number").fill("42");
  await page.getByRole("button", { name: "Start job", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Command queued" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start job", exact: true })).toBeDisabled();
  expect(submits).toBe(1);
  await expect(page.getByText("Command completed", { exact: false })).toHaveCount(0);
  release();
  await expect(page.getByRole("status").filter({ hasText: "Command completed" })).toBeVisible();
  await page.goto("/jobs?project=alpha&run=ux-failed");
  await expect(page.locator(".detail-panel")).toContainText("does not bypass validation or approval");
  await page.locator(".detail-panel").getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Command failed" })).toBeVisible();
});

test("keyboard 390px both themes and localized evidence remain usable", async ({ page }, info) => {
  await signIn(page);
  for (const theme of ["light", "dark"]) {
    await page.goto("/account"); await page.getByLabel("Theme", { exact: true }).selectOption(theme);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/jobs?project=alpha&run=ux-approval");
    await expect(page.locator(".detail-panel")).toBeVisible();
    const link = page.locator(".detail-panel .next-action-panel a");
    await link.focus(); await expect(link).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({ path: info.outputPath(`job-${theme}-390.png`), fullPage: true });
    await page.goto("/projects/alpha");
    const summary = page.getByRole("tab", { name: "Summary", exact: true }); await summary.focus(); await page.keyboard.press("End");
    await expect(page.getByRole("tab", { name: "History", exact: true })).toBeFocused();
    await expect(page.getByRole("tab", { name: "History", exact: true })).toHaveAttribute("aria-selected", "true");
    await page.setViewportSize({ width: 1440, height: 900 });
  }
  for (const [locale, heading] of [["fr", "Que se passe-t-il maintenant"], ["de", "Was gerade geschieht"], ["ro", "Ce se întâmplă acum"], ["en", "What is happening now"]]) {
    await page.goto("/account"); await page.getByLabel(/Language|Langue|Sprache|Limbă/).selectOption(locale);
    await page.goto("/jobs?project=alpha&run=ux-approval");
    await expect(page.locator(".detail-panel").getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }
  await page.screenshot({ path: info.outputPath("job-desktop-dark.png"), fullPage: true });
});


test("observed timeline retains paging and rejects unsafe action locations", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/jobs/*/ux-working", async route => {
    const response = await route.fetch(); const data = await response.json();
    data.job.timeline = Array.from({ length: 26 }, (_, index) => ({ ts: null, event: `saved-${index}`, stage: "build" }));
    await route.fulfill({ response, json: data });
  });
  await page.goto("/jobs?project=alpha&run=ux-working");
  const timeline = page.getByRole("table", { name: "Timeline", exact: true });
  await expect(timeline.getByRole("row")).toHaveCount(11);
  await expect(timeline).toContainText("saved-25");
  const pager = page.locator(".timeline-pagination");
  await pager.getByRole("button", { name: "Next", exact: true }).click();
  await expect(timeline).toContainText("saved-15");
  await pager.getByRole("combobox").selectOption("all");
  await expect(timeline.getByRole("row")).toHaveCount(27);
  await page.unroute("**/api/v1/jobs/*/ux-working");
  await page.route("**/api/v1/jobs/*/ux-clarification", async route => {
    const response = await route.fetch(); const data = await response.json();
    data.job.waiting.evidence_url = "javascript:alert(1)";
    await route.fulfill({ response, json: data });
  });
  await page.goto("/jobs?project=alpha&run=ux-clarification");
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.locator(".detail-panel")).toHaveCount(0);
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
});


test("project hub exposes verification revision and time and rejects corrupt stamps", async ({ page }) => {
  let corrupt = false;
  await page.route("**/api/v1/projects", async route => {
    const response = await route.fetch(); const rows = await response.json();
    const alpha = rows.find((row: { name: string }) => row.name === "alpha");
    expect(alpha).toBeTruthy();
    alpha.verification = { status: "stale", checked_at: corrupt ? "bad-timestamp" : "2026-10-05T01:00:00Z", revision: "a".repeat(64) };
    await route.fulfill({ response, json: rows });
  });
  await signIn(page);
  await page.goto("/projects/alpha");
  await expect(page.locator(".project-verification-evidence")).toContainText("aaaaaaaaaaaa");
  await expect(page.locator(".project-verification-evidence")).toContainText("Oct 5, 2026");
  corrupt = true;
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.locator(".project-verification-evidence")).toHaveCount(0);
  // Drain in-flight rewrites before fixture teardown disposes their API responses.
  await page.unrouteAll({ behavior: "wait" });
});

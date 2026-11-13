/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { setPickup } from "./pickup";


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

test.describe("Direct job evidence", () => {
  test.beforeEach(async ({request}) => {
    expect((await request.post("/__e2e__/jobs?mode=direct", {headers: {"X-ADORE-E2E": "local-test"}})).ok()).toBe(true);
  });
  test.afterEach(async ({page}) => {
    const response = await page.request.get("/api/v1/me");
    if (response.ok()) {
      const {csrf} = await response.json();
      await page.request.patch("/api/v1/me/preferences", {headers: {"X-CSRF-Token": csrf}, data: {language: "en", theme: "light"}});
    }
  });
  test("publication reset retry and exact whitespace commands remain readable", async ({page}) => {
    await signIn(page);
    for (const suffix of ["whitespace", "publication-reset", "retried"]) {
      await page.goto(`/jobs?project=alpha&run=ux-direct-${suffix}`);
      const detail = page.locator(".detail-panel"), evidence = detail.locator(".direct-evidence");
      await detail.getByRole("tab", {name:"Evidence and artifacts",exact:true}).click();
      await expect(evidence).toBeVisible();
      await expect(evidence).toContainText("Latest recorded attempt");
      await expect(detail.locator(".job-detail-meta")).toContainText(
        suffix === "publication-reset" ? "Stage: Publishing" : "Stage: Done");
      if (suffix !== "whitespace")
        await expect(detail.locator(".timeline-table tr").filter({hasText:"reset"})).toContainText("Publishing");
      await expect(evidence.locator("code, pre")).toHaveCount(0);
    }
  });

  for (const corruption of ["workflow-list", "workflow-detail", "direct", "stage"]) {
    test(`corrupt ${corruption} hides previously valid direct evidence`, async ({page}) => {
      await page.clock.install();
      await signIn(page); await page.goto("/jobs?project=alpha&run=ux-direct-passed");
      await expect(page.locator(".direct-evidence")).toContainText("Latest recorded attempt");
      const pattern = corruption === "workflow-list" ? "**/api/v1/jobs-page?*" : "**/api/v1/jobs/*/ux-direct-passed";
      await page.route(pattern, async route => {
        const response = await route.fetch(), data = await response.json();
        if (corruption === "workflow-list") data.items[0].workflow = "unrecognized";
        else if (corruption === "workflow-detail") data.job.workflow = "unrecognized";
        else if (corruption === "direct") data.job.direct.attempt = -1;
        else data.job.timeline.push({ts: null, event: "stage-launch", stage: "design"});
        await route.fulfill({response, json: data});
      });
      // Trigger the actual visible polling timer after a successful read.
      const refreshed = page.waitForResponse(response => response.url().includes(corruption === "workflow-list" ? "/jobs-page?" : "/ux-direct-passed"));
      await page.clock.fastForward(16000); await refreshed;
      await expect(page.locator(".data-feedback[role=alert]").first()).toBeVisible();
      await expect(page.locator(".detail-panel")).toHaveCount(0);
      await expect(page.locator(".direct-evidence")).toHaveCount(0);
      if (corruption === "workflow-list") await expect(page.locator(".action-jobs-table, .table-pagination")).toHaveCount(0);
    });
  }

});

test("overview uses compact attention and active tables without reporting noise", async ({ page }) => {
  const usageRequests: string[] = [];
  page.on("request", request => { if (/\/usage\?/.test(request.url())) usageRequests.push(request.url()); });
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Needs attention", exact: true })).toBeVisible();
  await expect(page.getByLabel("Project", { exact: true })).toHaveValue("");
  await expect(page.locator(".job-workspace .scope-note")).toHaveCount(0);
  await expect(page.getByText("Worker available", { exact: true })).toHaveCount(0);
  await expect(page.locator(".statistics-job-scope, .job-workspace .overview-card")).toHaveCount(0);
  const attention = page.getByRole("region", { name: "Needs attention", exact: true });
  await expect(attention.getByRole("columnheader")).toHaveText(["Job", "Status", "Details"]);
  await expect(attention.locator("time, .job-consumption")).toHaveCount(0);
  const active = page.getByRole("region", { name: "Active jobs", exact: true });
  await expect(active).toContainText("Working");
  await expect(active).toContainText("Publishing");
  await expect(active).not.toContainText("Failed");
  expect(usageRequests).toEqual([]);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
  await page.getByLabel("Project", { exact: true }).selectOption(alpha);
  await expect(active).not.toContainText("Actual beta collision");
  await expect(active).toContainText("Working");
  await expect(page.getByRole("link", { name: "View all jobs", exact: false })).toHaveCount(0);
  await expect(nav(page).getByRole("link", { name: "Jobs", exact: true })).toHaveAttribute("href", `/jobs?project=${alpha}`);
  // How ADORE works opens the help center by keyboard; Back returns to the scoped Overview.
  const help = page.locator(".top-actions").getByRole("link", { name: "How ADORE works", exact: true });
  await expect(help).toHaveAttribute("href", "/help");
  await help.focus(); await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/help$/);
  await page.goBack();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await attention.getByRole("link", { name: "Details", exact: true }).first().click();
  await expect(page.locator(".detail-panel")).toBeVisible();
  await expect(page.getByRole("button", { name: /merge|approve|pause job|resume job/i })).toHaveCount(0);
});

test("overview surfaces worker faults and withholds corrupt active evidence", async ({ page }) => {
  await page.route("**/api/v1/ready", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":{"code":"worker_unavailable"}}' }));
  await page.route("**/api/v1/jobs-page?*", route => {
    if (new URL(route.request().url()).searchParams.get("status_group") === "active") return route.fulfill({ status: 200, contentType: "application/json", body: '{"complete":false}' });
    return route.continue();
  });
  await signIn(page);
  await expect(page.getByText("Worker unavailable or heartbeat stale", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Incomplete job response", exact: true })).toBeVisible();
  await expect(page.locator(".overview-jobs-table")).toHaveCount(0);
});

test("hub separates pickup and verification and keeps role-appropriate navigation", async ({ page }, info) => {
  await page.setViewportSize({width:1366,height:768});
  let checks = 0;
  await page.route("**/api/v1/projects/*/readiness-check", route => {
    checks++; expect(route.request().headers()["x-csrf-token"]).toBeTruthy();
    return route.fulfill({ status: 200, json: readinessFixture(decodeURIComponent(new URL(route.request().url()).pathname.split("/")[4]), { forge_auth: false }) });
  });
  await signIn(page);
  await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
  await expect(page.getByRole("columnheader", { name: "Monitoring", exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Environment verification", exact: true })).toHaveCount(0);
  await expect(page.getByRole("columnheader", { name: "Actions", exact: true })).toHaveCount(0);
  await expect(page.getByRole("columnheader", { name: "Repo", exact: true })).toBeVisible();
  await expect(page.getByText("Active jobs continue when pickup is stopped.", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Pause monitoring|Activate monitoring/ })).toHaveCount(0);
  await page.getByRole("link", { name: "alpha", exact: true }).click();
  await expect(page.locator(".project-summary-window > .panel")).toHaveCount(2);
  const facts = page.locator(".project-summary");
  await expect(facts.locator(".summary-fact").filter({ hasText: "Container type" })).toContainText("Docker");
  await expect(facts.locator(".summary-fact").filter({ hasText: "Executor" })).toHaveCount(0);
  await expect(facts.locator(".summary-fact")).toHaveCount(7);
  await expect(facts.locator(".summary-fact").filter({ hasText: "Active jobs" })).toContainText("3");
  await expect(page.locator(".statistics-job-scope, .job-workspace .scope-note")).toHaveCount(0);
  await expect(page.locator(".project-summary-window .summary-job-window")).toContainText("Working");
  const hub = page.locator(".project-hub");
  await expect(hub.locator("strong")).toHaveText("alpha");
  await expect(hub.locator("button, a")).toHaveText(["Summary", "Settings", "Jobs", "Statistics", "History", "Access"]);
  await expect(page.locator(".project-links")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "alpha", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Pause monitoring|Activate monitoring/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Archive project", exact: true })).toBeVisible();
  const project = new URL(page.url()).pathname.split("/")[2];
  await expect(hub.getByRole("link")).toHaveCount(0);
  await expect(hub.getByRole("tab", { name: "Jobs", exact: true })).toBeVisible();
  await expect(hub.getByRole("tab", { name: "Statistics", exact: true })).toBeVisible();

  await expect(page.getByText("Active jobs continue when pickup is stopped.", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Summary", exact: true })).toBeVisible();
  await expect(page.locator(".overview-controls")).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Settings", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "History", exact: true })).toBeVisible();
  expect(checks).toBe(0);
  expect((await facts.boundingBox())!.height).toBeLessThan(180);
  await page.screenshot({path:info.outputPath("compact-project-summary.png"),fullPage:true});
  await facts.getByRole("button", { name: "Check host prerequisites", exact: true }).click();
  await expect(facts.locator(".readiness-verdict")).toHaveCount(0);
  await expect(facts.locator(".readiness-check").filter({ hasText: "Repository sign-in" })).toContainText("Sign in on the ADORE server");
  await expect(facts.locator(".readiness-check").filter({ hasText: /^GitCreates/ })).toContainText("Creates isolated working copies");
  await expect(facts.locator(".readiness-metadata")).toHaveCount(0);
  expect(checks).toBe(1);
  await expect(page.locator(".project-summary-window > .panel")).toHaveCount(2);
  await page.screenshot({ path: info.outputPath("project-hub-desktop.png"), fullPage: true });
  await hub.getByRole("tab", { name: "Statistics", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${project}/statistics$`));
  await expect(hub).toBeVisible();
  await page.goBack();
  await expect(hub).toBeVisible();
  await page.getByRole("tab", { name: "Settings", exact: true }).click();
  await expect(page.locator(".project-summary")).toHaveCount(0);
  await expect(hub).toBeVisible();
});

test("jobs table shows compact columns and sorts on the server", async ({ page }) => {
  await signIn(page); await page.goto("/jobs?view=jobs");
  const toolbar=page.locator(".jobs-toolbar");
  const tabsBox=(await toolbar.getByRole("tablist").boundingBox())!;
  const scopeBox=(await toolbar.locator("#jobs-project").boundingBox())!;
  expect(scopeBox.x).toBeGreaterThan(tabsBox.x+tabsBox.width);
  expect(Math.abs(scopeBox.y-tabsBox.y)).toBeLessThan(8);
  await expect(page.locator("#job-search-help")).toHaveCount(0);
  await expect(page.locator("#job-search")).not.toHaveAttribute("aria-describedby");
  await expect(page.locator("#job-search")).toHaveAttribute("maxlength","80");
  const table = page.locator(".action-jobs-table");
  await expect(table.getByRole("columnheader")).toHaveText([/^Ticket/, /^Project/, /^Status/, /^Last activity/, /^Consumption/]);
  await expect(page.getByText(/Selected period/)).toHaveCount(0);
  await expect(page.locator(".statistics-job-scope")).toHaveCount(0);
  await expect(table.locator("tbody tr").first()).not.toContainText("Project ID");
  await expect(table.locator("tbody tr").first()).not.toContainText("Run ID");
  await expect(table.locator("tbody tr").first()).not.toContainText("Known measurement");
  await expect(table.locator("tbody tr").first().locator(".job-consumption")).toContainText(/Input tokens: [\d,—]+Output tokens: [\d,—]+/);
  const header = table.getByRole("columnheader", { name: "Project", exact: true });
  const firstProject = () => table.locator("tbody tr").first().locator("td").nth(1).innerText();
  const request = (order: string) => page.waitForResponse(response => response.url().includes("/jobs-page?") &&
    new URL(response.url()).searchParams.get("sort") === "project" && new URL(response.url()).searchParams.get("order") === order);
  let response = request("asc"); await header.getByRole("button").click(); await response;
  await expect(header).toHaveAttribute("aria-sort", "ascending");
  await expect.poll(firstProject).toMatch(/^alpha/);
  response = request("desc"); await header.getByRole("button").click(); await response;
  await expect(header).toHaveAttribute("aria-sort", "descending");
  await expect.poll(firstProject).not.toMatch(/^alpha/);
});

test("manual start from Tickets reports queueing and the asynchronous worker failure", async ({ page }) => {
  await signIn(page);
  await page.goto("/jobs?project=alpha");
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  await page.locator(".ticket-table tbody tr.ticket-row").filter({ hasText: "#43" }).getByRole("button", { name: "Start", exact: true }).click();
  const notice = page.locator(".ticket-notice");
  await expect(notice).toContainText("Start for #43 queued");
  await expect(notice).toContainText("Starts only this ticket, even with monitoring paused. All other checks still apply.");
  await expect(notice).toContainText("failed · engine rejected operation");
  await expect(notice).not.toContainText("finished");
});

test("global Jobs mirrors the project hub with a compact scope and Tickets/Jobs sub-tabs", async ({ page }) => {
  // Start needs active pickup; the fixture keeps it stopped for the other specs.
  await setPickup("beta", true);
  try {
    await signIn(page);
    await page.goto("/jobs");
    await expect(page.locator("#jobs-project")).toHaveValue("");
    const tabs = page.locator(".jobs-subtabs");
    await expect(tabs.getByRole("tab", { name: "Tickets", exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#job-ticket-number")).toHaveCount(0);
    await expect(page.getByText("Worker available", { exact: true })).toHaveCount(0);
    await expect(page.getByText(/Jobs shown here belong|The heartbeat describes/)).toHaveCount(0);
    const projects = await (await page.request.get("/api/v1/projects")).json();
    const alpha = projects.find((item: { name: string }) => item.name === "alpha").id, beta = projects.find((item: { name: string }) => item.name === "beta").id;
    // All projects reads every authorized project's tickets into one table with a Project column;
    // a failed project read reports only that project and keeps the others.
    const betaTickets = `**/api/v1/projects/${beta}/tickets`;
    await page.route(betaTickets, route => route.abort());
    await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    const rows = page.locator(".ticket-table tbody tr.ticket-row");
    // Other specs may add projects whose forge reads fail too, so alerts are matched per project.
    const alerts = page.locator(".ticket-workspace .alert");
    const projectRows = (name: string) => rows.filter({ has: page.getByRole("cell", { name, exact: true }) });
    await expect(page.getByRole("columnheader", { name: "Project", exact: true })).toBeVisible();
    await expect(alerts.filter({ hasText: /^beta: / })).toHaveCount(1);
    await expect(alerts.filter({ hasText: /^alpha: / })).toHaveCount(0);
    await expect(projectRows("alpha").filter({ hasText: "#44" })).toHaveCount(1);
    await expect(projectRows("beta")).toHaveCount(0);
    await page.unroute(betaTickets);
    await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    await expect(alerts.filter({ hasText: /^beta: / })).toHaveCount(0);
    // Both projects' tickets exceed one page of 10; show them all.
    await page.locator(".ticket-pagination").getByLabel("Rows per page").selectOption("all");
    await expect(projectRows("alpha").filter({ hasText: "#44" })).toHaveCount(1);
    const betaRow = projectRows("beta").filter({ hasText: "#44" });
    await expect(betaRow).toHaveCount(1);
    const started = page.waitForRequest(request => request.method() === "POST" && new URL(request.url()).pathname === `/api/v1/projects/${beta}/tickets/44/start`);
    await betaRow.getByRole("button", { name: "Start", exact: true }).click();
    await started;
    await expect(page.locator(".ticket-notice")).toContainText("beta · Start for #44 queued");
    await tabs.getByRole("tab", { name: "Jobs", exact: true }).click();
    await expect(page).toHaveURL(/view=jobs/);
    await expect(page.locator(".action-jobs-table")).toBeVisible();
    await page.locator("#jobs-project").selectOption(alpha);
    await tabs.getByRole("tab", { name: "Tickets", exact: true }).click();
    await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    await expect(rows.first()).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Project", exact: true })).toHaveCount(0);
    await tabs.getByRole("tab", { name: "Jobs", exact: true }).click();
    await expect(page).toHaveURL(/view=jobs/);
    await expect(page.locator(".action-jobs-table")).toBeVisible();
    await page.reload();
    await expect(tabs.getByRole("tab", { name: "Jobs", exact: true })).toHaveAttribute("aria-selected", "true");
    await page.goto(`/jobs?project=${alpha}&run=ux-working`);
    await expect(tabs.getByRole("tab", { name: "Jobs", exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(page.locator(".detail-panel")).toBeVisible();
  } finally {
    await setPickup("beta", false);
  }
});

test("all real lifecycle groups explain exact stage evidence and protected handoffs", async ({ page }) => {
  test.setTimeout(90_000); // This journey opens eleven complete job details in sequence.
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const id = projects.find((row: { name: string }) => row.name === "alpha").id;
  const cases = [
    ["working", "Working", "Build", true], ["publishing", "Publishing", "Done", true],
    ["clarification", "Waiting for clarification", "Build", true], ["approval", "Waiting for approval", "Done", true],
    ["review", "Human review", "Done", true], ["handoff-pending", "Handoff pending", "Build", false],
    ["handed-off", "Handed off", "Build", false], ["done", "Completed", "Done", false],
    ["failed", "Failed", "Build", false], ["cancelled", "Cancelled", "Build", false], ["stale", "Stale", "Build", false],
  ] as const;
  for (const [suffix, _status, _stage, cancellable] of cases) {
    await page.goto(`/jobs?project=${id}&run=ux-${suffix}`);
    const detail = page.locator(".detail-panel");
    await expect(detail.getByRole("heading", { name: "What is happening now" })).toBeVisible();
    await expect(detail.locator(".next-action-panel .status")).toContainText(_status);
    await expect(detail.locator(".job-detail-meta")).toContainText(`Stage: ${_stage}`);
    await expect(detail.getByText("Next step", { exact: true })).toBeVisible();
    await expect(detail.getByRole("tab", {name:"Activity",exact:true})).toHaveAttribute("aria-selected", "true");
    if (await detail.locator(".job-actions").count()) await detail.locator(".job-actions summary").click();
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
    ["ux-review", "Review the MR/PR", "https://forge.example/offline/alpha/pulls/3"],
  ]) {
    await page.goto(`/jobs?project=alpha&run=${run}`);
    const detail = page.locator(".detail-panel");
    if (run === "ux-clarification") await detail.getByRole("button", {name:"Read the question",exact:true}).click();
    await expect(detail.getByRole("link", { name }).first()).toHaveAttribute("href", href);

    if (run === "ux-clarification") {
      await expect(detail).toContainText("Which export format?");
      await expect(detail).not.toContainText("fixture-secret");
    }
    if (run === "ux-approval") {
      await detail.getByRole("tab", {name:"Technical details",exact:true}).click();
      await detail.getByText("Original recorded events", {exact:true}).click();
      const timeline = detail.getByRole("table", { name: "Timeline" });
      await expect(timeline).toContainText("Frame"); await expect(timeline).toContainText("Build"); await expect(timeline).toContainText("Validate");
      await expect(timeline).not.toContainText("Specify"); await expect(timeline).not.toContainText("Design");
      await detail.getByRole("tab",{name:"Activity",exact:true}).click();
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
  await expect(detail.getByRole("heading", { name: /Ticket title not recorded/ })).toBeVisible();
  await expect(detail).toContainText("no human intervention is currently requested");
  await expect(detail.locator(".next-action-panel a")).toHaveCount(0);
  await expect(detail.locator(".job-consumption").first()).toContainText("Input tokens: —");
  await expect(detail.locator(".job-consumption").first()).not.toContainText("Not available");
  await page.goto("/jobs?project=alpha&run=ux-working");
  await expect(page.locator(".detail-panel")).toContainText("over 15 minutes old");
});

test("global complete search paging basic filters and source revision conflicts", async ({ page }) => {
  await signIn(page); await page.goto("/jobs?view=jobs");
  await expect(page.locator("#jobs-project")).toHaveValue("");
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(10);
  const continuation = page.waitForRequest(request => request.url().includes("jobs-page?") && new URL(request.url()).searchParams.get("offset") === "10");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  expect(new URL((await continuation).url()).searchParams.get("snapshot")).toMatch(/^[a-f0-9]{64}$/);
  await expect(page.locator(".action-jobs-table tbody tr")).not.toHaveCount(10);
  await page.request.post("/__e2e__/jobs?mode=mutate", { headers: { "X-ADORE-E2E": "local-test" } });
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
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
  // Only search and the status group filter jobs; there is no advanced filter panel.
  await expect(page.getByRole("button", { name: "Advanced filters", exact: true })).toHaveCount(0);
  await expect(page.locator("#job-advanced-filters, .job-text-filters")).toHaveCount(0);
  await expect(page.getByLabel("Observed executor", { exact: true })).toHaveCount(0);
});

test("composite colliding IDs and reload preserve the owning project", async ({ page }) => {
  await signIn(page);
  await page.goto("/jobs?view=jobs");
  await page.getByLabel("Search jobs", { exact: true }).fill("ux-working");
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(2);
  const links = await page.locator(".action-jobs-table tbody td:first-child a").evaluateAll(nodes => nodes.map(node => (node as HTMLAnchorElement).href));
  expect(new Set(links).size).toBe(2);
  await page.getByRole("link", { name: /Actual beta collision/ }).click();
  await expect(page.locator(".detail-panel .job-detail-title h2")).toContainText("Actual beta collision");
  await expect(page.getByRole("region", { name: "Project context" })).toHaveCount(0);
  await expect(page.locator("#jobs-project option:checked")).toHaveText("beta");
  await page.reload();
  await expect(page.locator(".detail-panel .job-detail-title h2")).toContainText("Actual beta collision");
  await page.locator(".detail-panel").getByRole("button", { name: "Close", exact: true }).click();
  await expect(page).not.toHaveURL(/run=/);
});

test("incomplete corrupt and failed job reads hide totals and stale details", async ({ page }) => {
  await signIn(page);
  // One handler for the whole test: swapping handlers with unroute while a background
  // Overview poll is still inside the old one made its fulfill hit an already-handled route.
  let mode: "incomplete" | "malformed" | "server" = "incomplete";
  await page.route("**/api/v1/jobs-page?*", async route => {
    if (mode === "server") return route.fallback();
    if (mode === "malformed") return route.fulfill({ status: 200, contentType: "application/json", body: '{"complete":true,"items":[],"total":-1}' });
    const response = await route.fetch(); const value = await response.json(); value.complete = false;
    await route.fulfill({ response, json: value });
  });
  // Overview refreshes itself; a visibilitychange runs its poll at once.
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await expect(page.getByRole("heading", { name: "Incomplete job response", exact: true })).toBeVisible();
  await expect(page.locator(".overview-jobs-table")).toHaveCount(0);
  mode = "malformed";
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await expect(page.getByRole("heading", { name: "Could not load data", exact: true })).toBeVisible();
  await expect(page.locator(".overview-jobs-table")).toHaveCount(0);
  mode = "server";
  await page.request.post("/__e2e__/jobs?mode=corrupt", { headers: { "X-ADORE-E2E": "local-test" } });
  await page.goto("/jobs?view=jobs");
  await expect(page.getByRole("heading", { name: "Could not load data", exact: true })).toBeVisible();
  await expect(page.locator(".action-jobs-table")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText("BROKEN_FIXTURE_SECRET");
});

test("developer search counts navigation direct routes and command CSRF exclude other projects", async ({ page }) => {
  await signIn(page, "developer");
  await expect(page.locator("#overview-project option")).toHaveCount(2);
  await expect(page.getByRole("region", { name: "Active jobs", exact: true })).not.toContainText("Actual beta collision");
  await page.goto("/jobs?view=jobs");
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
  await expect(page.getByRole("button", { name: /Pause monitoring|Activate monitoring|Archive project|Restore project|Delete project/ })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Prices", exact: true })).toHaveCount(0);
});

test("queued pending and final successful commands do not predict job outcome", async ({ page }) => {
  // Start needs active pickup; the fixture keeps it stopped for the other specs.
  await setPickup("alpha", true);
  try {
    await signIn(page); await page.goto("/jobs?project=alpha");
    let release!: () => void; const pending = new Promise<void>(resolve => { release = resolve; });
    await page.route("**/api/v1/operations/*", async route => { const response = await route.fetch(); await pending; await route.fulfill({ response }); });
    let submits = 0; page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/tickets/44/start")) submits++; });
    await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    const row = page.locator(".ticket-table tbody tr.ticket-row").filter({ hasText: "#44" });
    await row.getByRole("button", { name: "Start", exact: true }).click();
    const notice = page.locator(".ticket-notice");
    await expect(notice).toContainText("Start for #44 queued");
    await expect(row.getByRole("button", { name: "Start", exact: true })).toBeDisabled();
    expect(submits).toBe(1);
    await expect(notice).not.toContainText("finished");
    release();
    await expect(notice).toContainText("finished");
    await page.goto("/jobs?project=alpha&run=ux-failed");
    await page.locator(".detail-panel .job-actions summary").click();
    await expect(page.locator(".job-action-menu")).toContainText("Retry follows validation");
    await page.locator(".detail-panel").getByRole("button", { name: "Retry", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: "Command failed" })).toBeVisible();
  } finally {
    await setPickup("alpha", false);
  }
});

test.describe("Keyboard and localized job evidence", () => {
  test.afterEach(async ({page}) => {
    const response = await page.request.get("/api/v1/me");
    if (response.ok()) {
      const {csrf} = await response.json();
      const reset = await page.request.patch("/api/v1/me/preferences", {
        headers:{"X-CSRF-Token":csrf}, data:{language:"en",theme:"light"}});
      expect(reset.ok()).toBe(true);
    }
  });
  for (const theme of ["light", "dark"] as const) {
    test(`keyboard 390px remains usable in ${theme} theme`, async ({page}, info) => {
      await signIn(page);
    await page.goto("/account"); await page.getByLabel("Theme", { exact: true }).selectOption(theme);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await expect(page.locator(".overview-jobs-table").first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    expect(await page.locator(".overview-workspace .table-scroll").evaluateAll(nodes => nodes.every(node => node.scrollWidth <= node.clientWidth + 1))).toBe(true);
    await page.screenshot({ path: info.outputPath(`overview-${theme}-390.png`), fullPage: true });
    await page.goto("/jobs?project=alpha&run=ux-approval");
    await expect(page.locator(".detail-panel")).toBeVisible();
    const link = page.locator(".detail-panel .next-action-panel a");
    await link.focus(); await expect(link).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({ path: info.outputPath(`job-${theme}-390.png`), fullPage: true });
    await page.goto("/projects/alpha");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({ path: info.outputPath(`project-hub-${theme}-390.png`), fullPage: true });
    const summary = page.getByRole("tab", { name: "Summary", exact: true }); await summary.focus(); await page.keyboard.press("End");
    // End moves to the last hub tab, which is Access for administrators.
    await expect(page.getByRole("tab", { name: "Access", exact: true })).toBeFocused();
    await expect(page.getByRole("tab", { name: "Access", exact: true })).toHaveAttribute("aria-selected", "true");
    await page.setViewportSize({ width: 1440, height: 900 });
    });
  }
  for (const [locale, heading] of [["fr", "Que se passe-t-il maintenant"], ["de", "Was gerade geschieht"], ["ro", "Ce se întâmplă acum"], ["en", "What is happening now"]]) {
    test(`localized job evidence remains usable in ${locale}`, async ({page}, info) => {
      await signIn(page);
    await page.goto("/account");
    await page.getByLabel("Theme", {exact:true}).selectOption("dark");
    await page.getByLabel(/Language|Langue|Sprache|Limbă/).selectOption(locale);
    await page.goto("/");
    await expect(page.locator(".overview-jobs-table").first()).toBeVisible();
    await expect(page.locator(".overview-header-scope select")).toHaveValue("");
    await page.goto("/jobs?project=alpha&run=ux-approval");
    await expect(page.locator(".detail-panel").getByRole("heading", { name: heading, exact: true })).toBeVisible();
      await page.screenshot({path:info.outputPath("job-desktop-dark.png"),fullPage:true});
    });
  }
});


test("observed timeline retains paging and rejects unsafe action locations", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/jobs/*/ux-working", async route => {
    const response = await route.fetch(); const data = await response.json();
    data.job.timeline = Array.from({ length: 26 }, (_, index) => ({ ts: null, event: `saved-${index}`, stage: "build" }));
    await route.fulfill({ response, json: data });
  });
  await page.goto("/jobs?project=alpha&run=ux-working");
  await page.getByRole("tab",{name:"Technical details",exact:true}).click();
  await page.getByText("Original recorded events",{exact:true}).click();
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


test("project hub shows verification state and rejects corrupt stamps", async ({ page }) => {
  let corrupt = false;
  await page.route("**/api/v1/projects", async route => {
    const response = await route.fetch(); const rows = await response.json();
    const alpha = rows.find((row: { name: string }) => row.name === "alpha");
    expect(alpha).toBeTruthy();
    alpha.verification = { ...readinessFixture(alpha.id), status: "stale",
      checked_at: corrupt ? "bad-timestamp" : "2026-10-05T01:00:00Z" };
    await route.fulfill({ response, json: rows });
  });
  await signIn(page);
  await page.goto("/projects/alpha");
  const verification = page.locator(".summary-fact").filter({ hasText: "Environment verification" });
  await expect(verification).toContainText("Stale verification");
  // The compact summary presents status; API evidence stamps are still validated.
  await expect(page.locator(".project-verification-evidence")).toHaveCount(0);
  corrupt = true;
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(verification).toHaveCount(0);
  // Drain in-flight rewrites before fixture teardown disposes their API responses.
  await page.unrouteAll({ behavior: "wait" });
});


test("overview header selector precedes job tables without a duplicate context band and navigation resets all projects", async ({ page }) => {
  await signIn(page);
  const selector = page.getByLabel("Project", { exact: true });
  await expect(page.locator(".topbar").getByLabel("Project", { exact: true })).toBeVisible();
  await expect(page.locator(".refresh-stamp")).toHaveCount(0);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
  await selector.selectOption(alpha);
  const context = page.getByRole("region", { name: "Project context", exact: true });
  await expect(page.locator(".overview-jobs-table").first()).toBeVisible();
  await expect(context).toHaveCount(0);
  const bounds = await Promise.all([selector.boundingBox(), page.locator(".overview-jobs-table").first().boundingBox()]);
  expect(bounds[0]!.y + bounds[0]!.height).toBeLessThanOrEqual(bounds[1]!.y);
  await page.reload();
  await expect(selector).toHaveValue(alpha);
  const overview = nav(page).getByRole("link", { name: "Overview", exact: true });
  await expect(overview).toHaveAttribute("href", "/");
  await overview.click();
  await expect(selector).toHaveValue("");
  await expect(context).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Active jobs", exact: true })).toContainText("Actual beta collision");
  await page.goto("/projects/alpha");
  await nav(page).getByRole("link", { name: "Overview", exact: true }).click();
  await expect(selector).toHaveValue("");
});

for (const mode of ["corrupt", "legacy-timestamp"]) {
test(`overview keeps healthy jobs visible and names only the unreadable project (${mode})`, async ({ page, request }) => {
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha");
  const beta = projects.find((row: { name: string }) => row.name === "beta");
  const corrupted = await request.post(`/__e2e__/jobs?mode=${mode}`, { headers: { "X-ADORE-E2E": "local-test" } });
  expect(corrupted.ok()).toBe(true);
  await page.reload();
  const selector = page.getByLabel("Project", { exact: true });
  const attention = page.getByRole("region", { name: "Needs attention", exact: true });
  const warning = attention.getByRole("alert");
  const active = page.getByRole("region", { name: "Active jobs", exact: true });
  await expect(warning).toContainText(alpha.display_name);
  await expect(warning).toContainText("The job state cannot be read");
  await expect(warning).not.toContainText(beta.display_name);
  await expect(active).toContainText("Actual beta collision");
  await expect(page.getByText("Could not load data", { exact: true })).toHaveCount(0);
  await selector.selectOption(beta.id);
  await expect(active).toContainText("Actual beta collision");
  await expect(warning).toHaveCount(0);
  await selector.selectOption(alpha.id);
  await expect(warning).toContainText(alpha.display_name);
  await expect(attention.getByRole("table")).toHaveCount(0);
  await expect(attention.getByRole("status")).toHaveCount(0);
  await expect(active).toHaveCount(0);
  await page.goto("/projects/alpha");
  await expect(warning).toContainText(alpha.display_name);
  await expect(page.locator(".summary-fact").filter({ hasText: "Active jobs" }).locator("dd")).toHaveText("—");
});
}

test("overview background poll stays visible while pending and fails closed", async ({ page }) => {
  await page.clock.install();
  await signIn(page);
  const table = page.locator(".overview-jobs-table").first();
  await expect(table).toBeVisible();
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  let requests = 0;
  await page.route("**/api/v1/jobs-page?*", async route => { requests++; await pending; await route.continue(); });
  await page.clock.fastForward(15000);
  await expect.poll(() => requests).toBeGreaterThan(0);
  try {
    await expect(table).toBeVisible();
    await expect(page.getByText("Loading data…", { exact: true })).toHaveCount(0);
  } finally { release(); }
  await page.unrouteAll({ behavior: "wait" });
  await page.route("**/api/v1/jobs-page?*", route => route.fulfill({ status: 200, contentType: "application/json", body: '{"complete":false}' }));
  await page.clock.fastForward(15000);
  await expect(page.getByRole("heading", { name: "Incomplete job response", exact: true })).toBeVisible();
  await expect(page.locator(".overview-jobs-table")).toHaveCount(0);
});


test("project hub lifecycle actions keep scoped CSRF and exact-name deletion", async ({ page }) => {
  await signIn(page);
  const projectResponse = await page.request.get("/api/v1/projects");
  expect(projectResponse.ok()).toBe(true);
  const projects = await projectResponse.json();
  expect(Array.isArray(projects)).toBe(true);
  let archived = false;
  const writes: { path: string; csrf: string; data: Record<string, unknown> | null }[] = [];
  // A fixed fixture catalog needs no upstream fetch during each poll. Removing
  // an in-flight async proxy lets routing fall back before its fulfill resumes.
  await page.route("**/api/v1/projects", route => route.fulfill({
    json: projects.map((project: { name: string }) => project.name === "alpha" ? { ...project, archived } : project),
  }));
  await page.route("**/api/v1/projects/*/archive", route => {
    writes.push({ path: new URL(route.request().url()).pathname, csrf: route.request().headers()["x-csrf-token"], data: null });
    archived = true; return route.fulfill({ status: 200, json: {} });
  });
  await page.route("**/api/v1/projects/*/restore", route => {
    writes.push({ path: new URL(route.request().url()).pathname, csrf: route.request().headers()["x-csrf-token"], data: null });
    archived = false; return route.fulfill({ status: 200, json: {} });
  });
  // The clone of alpha is ADORE's own until the preview says it is not.
  let clonePreview: Record<string, unknown> = { path: "/srv/adore/repos/alpha", removable: true, reason: "" };
  await page.route("**/api/v1/projects/*/delete-preview", route => route.fulfill({ status: 200, json: { clone: clonePreview } }));
  await page.route("**/api/v1/projects/*/delete", route => {
    writes.push({ path: new URL(route.request().url()).pathname, csrf: route.request().headers()["x-csrf-token"], data: route.request().postDataJSON() });
    return route.fulfill({ status: 202, json: { id: 9001, status: "pending" } });
  });
  await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("link", { name: "alpha", exact: true }).click();
  const id = new URL(page.url()).pathname.split("/")[2];
  await page.getByRole("button", { name: "Archive project", exact: true }).click();
  await expect(page.getByRole("button", { name: "Restore project", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Restore project", exact: true }).click();
  await expect(page.getByRole("button", { name: "Delete project", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Archive project", exact: true }).click();
  await page.getByRole("button", { name: "Delete project", exact: true }).click();
  const confirm = page.getByRole("dialog").filter({ has: page.locator(".delete-confirm") });
  await expect(confirm).toBeVisible();
  await expect(confirm.getByText(/This permanently removes|Kept:|Required field/)).toHaveCount(0);
  await expect(confirm.locator(".delete-confirm-label")).toContainText("Type alpha to confirm");
  await page.keyboard.press("Escape");
  await expect(confirm).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Delete project", exact: true })).toBeFocused();
  await page.getByRole("button", { name: "Delete project", exact: true }).click();
  await expect(confirm.getByRole("button", { name: "Delete project", exact: true })).toBeDisabled();
  const removeClone = confirm.getByRole("checkbox", { name: /Also remove the local clone/ });
  await expect(removeClone).not.toBeChecked();
  await expect(confirm.getByText("/srv/adore/repos/alpha", { exact: true })).toBeVisible();
  // The checkbox sits on the line of its title; the clone path follows below the title.
  const box = await removeClone.boundingBox();
  const title = await confirm.locator(".delete-clone-title").boundingBox();
  const path = await confirm.locator(".delete-clone code").boundingBox();
  expect(box && title && path).toBeTruthy();
  expect(Math.abs(box!.y + box!.height / 2 - (title!.y + title!.height / 2))).toBeLessThan(6);
  expect(box!.x + box!.width).toBeLessThanOrEqual(title!.x);
  expect(path!.y).toBeGreaterThanOrEqual(title!.y + title!.height - 1);
  expect(Math.abs(path!.x - title!.x)).toBeLessThan(2);
  // Only the name to type is emphasized in the confirmation label.
  await expect(confirm.locator(".delete-confirm-name")).toHaveText("alpha");
  expect(await confirm.locator(".delete-confirm-label").evaluate(el => Number(getComputedStyle(el).fontWeight))).toBeLessThan(600);
  expect(await confirm.locator(".delete-confirm-name").evaluate(el => Number(getComputedStyle(el).fontWeight))).toBeGreaterThanOrEqual(700);
  await removeClone.check();
  await confirm.getByRole("textbox").fill("wrong-project");
  await expect(confirm.getByRole("button", { name: "Delete project", exact: true })).toBeDisabled();
  await confirm.getByRole("textbox").fill("alpha");
  await expect(confirm.getByRole("button", { name: "Delete project", exact: true })).toBeEnabled();
  await page.keyboard.press("Escape");
  await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("link", { name: "beta", exact: true }).click();
  await expect(confirm).toHaveCount(0);
  expect(writes.filter(write => write.path.endsWith("/delete"))).toEqual([]);
  await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByRole("link", { name: "alpha", exact: true }).click();
  // A clone that is not removable explains why it stays and offers no choice.
  clonePreview = { path: "/srv/adore/repos/alpha", removable: false, reason: "uncommitted" };
  await page.getByRole("button", { name: "Delete project", exact: true }).click();
  await expect(confirm.getByText(/The local clone stays:.*uncommitted changes/)).toBeVisible();
  await expect(confirm.getByRole("checkbox")).toHaveCount(0);
  await page.keyboard.press("Escape");
  clonePreview = { path: "/srv/adore/repos/alpha", removable: true, reason: "" };
  await page.getByRole("button", { name: "Delete project", exact: true }).click();
  await expect(removeClone).not.toBeChecked();
  await removeClone.check();
  await confirm.getByRole("textbox").fill("alpha");
  await confirm.getByRole("button", { name: "Delete project", exact: true }).click();
  await expect(confirm).toHaveCount(0);
  expect(writes.map(write => write.path)).toEqual(["archive", "restore", "archive", "delete"].map(action => `/api/v1/projects/${id}/${action}`));
  expect(writes.every(write => !!write.csrf)).toBe(true);
  expect(writes.at(-1)?.data?.confirm_name).toBe("alpha");
  expect(writes.at(-1)?.data?.remove_clone).toBe(true);
  // Deletion refreshes the directory after the modal closes.
  await page.unrouteAll({ behavior: "wait" });
});


test("summary with corrupt job evidence shows unknown counters and no fabricated jobs", async ({ page }) => {
  await page.route("**/api/v1/jobs-page?*", route => route.fulfill({ status: 200, json: { complete: false } }));
  await signIn(page); await page.goto("/projects/alpha");
  await expect(page.getByRole("heading", { name: "Incomplete job response", exact: true })).toBeVisible();
  await expect(page.locator(".project-summary .summary-fact").filter({ hasText: "Active jobs" }).locator("dd")).toHaveText("—");
  await expect(page.locator(".summary-job-window table")).toHaveCount(0);
});

function readinessFixture(project: string, changes: Record<string, unknown> = {}) {
  return { workflow: "direct", auth_bound: true, required_checks: ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "egress_proxy", ...Object.keys(changes).filter(key => !["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "egress_proxy"].includes(key))], status: Object.values(changes).includes(false) ? "failed" : changes.container_runtime === null ? "partial" : "verified", project_id: project, revision: "a".repeat(64), context: "api-host", checked_at: "2026-10-06T10:00:00Z",
    checks: { git: true, forge_cli: true, forge_auth: true, container_runtime: true, executor_cli: true, egress_proxy: true, ...changes } };
}

for (const scenario of ["passed", "partial", "malformed", "wrong-project"] as const) {
  test(`host prerequisites explain ${scenario} evidence`, async ({ page }, info) => {
    await page.route("**/api/v1/projects/*/readiness-check", route => {
      const project = decodeURIComponent(new URL(route.request().url()).pathname.split("/")[4]);
      const result = readinessFixture(scenario === "wrong-project" ? "another-project" : project,
        scenario === "partial" ? { container_runtime: null } : scenario === "malformed" ? { git: "yes" } : {});
      return route.fulfill({ status: 200, json: result });
    });
    await signIn(page);
    await nav(page).getByRole("link", { name: "Projects", exact: true }).click();
    await page.getByRole("link", { name: "alpha", exact: true }).click();
    await page.getByRole("button", { name: "Check host prerequisites", exact: true }).click();
    if (scenario === "malformed" || scenario === "wrong-project") {
      await expect(page.locator(".readiness-check")).toHaveCount(0);
      await expect(page.getByRole("alert")).toBeVisible();
      await expect(page.getByRole("button", { name: "Check details", exact: true })).toHaveCount(0);
    } else {
      const panel = page.locator(".readiness-evidence");
      await expect(panel.locator(".readiness-verdict")).toHaveCount(0);
      await expect(panel.locator(".readiness-check")).toHaveCount(7);
      await expect(panel.locator(".workflow-information")).toContainText("Direct, no AEGIS found");
      const model = panel.locator(".readiness-check").filter({ hasText: "AI model connection" });
      await expect(model).toContainText("Use Test AI connection in Settings → Agent and model");
      await expect(panel).toContainText("does not test a complete job");
      await expect(page.locator(".readiness-metadata")).toHaveCount(0);
      if (scenario === "partial") await expect(panel.locator(".readiness-check").filter({ hasText: "Container engine" })).toContainText("Could not verify");
      await page.setViewportSize({ width: 390, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: info.outputPath(`readiness-${scenario}.png`), fullPage: true });
    }
  });
}

test("local host prerequisites state the local notice once and give the agent row its own fix", async ({ page }) => {
  await page.route("**/api/v1/projects/*/readiness-check", route => {
    const project = decodeURIComponent(new URL(route.request().url()).pathname.split("/")[4]);
    const evidence = readinessFixture(project, { container_runtime: null, executor_cli: false });
    const { egress_proxy, ...checks } = evidence.checks;
    return route.fulfill({ status: 200, json: { ...evidence, checks, required_checks: Object.keys(checks),
      local_probe: { ready: false, reason: "node-incompatible", exit_code: 0 } } });
  });
  // The project directory reports the local backend as the project's runtime.
  await page.route(/\/api\/v1\/projects(\?.*)?$/, async route => {
    const response = await route.fetch();
    const rows = await response.json();
    for (const row of rows) if (row.name === "alpha") {
      row.runtime = "local";
      row.verification_requirements = row.verification_requirements.filter((key: string) => key !== "egress_proxy");
      row.verification = { status: "unverified", checked_at: null, revision: null };
    }
    await route.fulfill({ response, json: rows });
  });
  await signIn(page);
  await page.goto("/projects/alpha");
  await page.getByRole("button", { name: "Check host prerequisites", exact: true }).click();
  const panel = page.locator(".readiness-evidence");
  await expect(panel.locator(".readiness-check")).toHaveCount(5);
  const agent = panel.locator(".readiness-check").filter({ hasText: "Local execution" });
  await expect(agent).toContainText("Checks managed Pi and Node");
  await expect(agent).toContainText("Managed Pi requires Node 22.23.4");
  await expect(agent).not.toContainText("Use a dedicated OS account");
  await expect(panel.locator("p").filter({ hasText: "Use a dedicated OS account" })).toHaveCount(1);
});

test("host prerequisite explanations support four locales and dark theme", async ({ page }, info) => {
  await page.route("**/api/v1/projects/*/readiness-check", route => route.fulfill({ status: 200,
    json: readinessFixture(decodeURIComponent(new URL(route.request().url()).pathname.split("/")[4]), { forge_auth: false }) }));
  await signIn(page);
  for (const [locale, status] of [["fr", "! Intervention nécessaire"], ["de", "! Handlung erforderlich"], ["ro", "! Necesită intervenție"], ["en", "! Action needed"]]) {
    await page.goto("/account");
    await page.getByLabel(/Language|Langue|Sprache|Limbă/).selectOption(locale);
    await page.goto("/projects/alpha");
    await page.getByRole("button", { name: /Check host prerequisites|Vérifier les prérequis|Host-Voraussetzungen prüfen|Verifică cerințele gazdei/ }).click();
    await expect(page.locator(".readiness-result").filter({hasText:status})).toBeVisible();
    await expect(page.locator(".readiness-metadata")).toHaveCount(0);
  }
  await page.goto("/account"); await page.getByLabel("Theme", { exact: true }).selectOption("dark");
  await page.goto("/projects/alpha"); await page.getByRole("button", { name: /Check host prerequisites|Vérifier les prérequis|Host-Voraussetzungen prüfen|Verifică cerințele gazdei/ }).click();
  await page.screenshot({ path: info.outputPath("readiness-dark.png"), fullPage: true });
});

test("host prerequisite explanation accepts the real offline API contract", async ({ page }) => {
  await signIn(page); await page.goto("/projects/alpha");
  await page.getByRole("button", { name: "Check host prerequisites", exact: true }).click();
  await expect(page.locator(".readiness-check").filter({hasText:"Repository sign-in"})).toContainText("! Action needed");
  await expect(page.locator(".readiness-check")).toHaveCount(7);
  await expect(page.locator(".readiness-check").filter({hasText:"Network proxy image"})).toHaveCount(1);
  await expect(page.locator(".readiness-metadata")).toHaveCount(0);
  await expect(page.locator(".summary-fact").filter({ hasText: "Environment verification" })).toContainText("Verification failed");
});

test("host check result survives an older project snapshot but accepts a fresh poll", async ({ page }) => {
  await signIn(page); await page.goto("/projects/alpha");
  const fact = page.locator(".summary-fact").filter({ hasText: "Environment verification" });
  await expect(fact).toBeVisible();
  let snapshotReady!: () => void;
  const captured = new Promise<void>(resolve => { snapshotReady = resolve; });
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let hold = true;
  await page.route(/\/api\/v1\/projects(\?.*)?$/, async route => {
    const response = await route.fetch();
    const rows = await response.json();
    for (const row of rows) if (row.name === "alpha") row.verification = hold
      ? { status: "unverified", checked_at: null, revision: null } : readinessFixture(row.id);
    if (hold) { snapshotReady(); await gate; }
    await route.fulfill({ response, json: rows });
  });
  await page.route("**/readiness-check", route => route.fulfill({ status: 200,
    json: readinessFixture(decodeURIComponent(new URL(route.request().url()).pathname.split("/")[4]), { forge_auth: false }) }));
  // Visibility resumes the real project poll; hold its older snapshot across the mutation.
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await captured;
  await page.getByRole("button", { name: "Check host prerequisites", exact: true }).click();
  await expect(fact).toContainText("Verification failed");
  const oldResponse = page.waitForResponse(response => /\/api\/v1\/projects$/.test(response.url()));
  release();
  await (await oldResponse).finished();
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(fact).toContainText("Verification failed");
  hold = false;
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await expect(fact).toContainText("Verified");
});

test("host check opens immediately with internal close and preserves user collapse", async ({ page }) => {
  await signIn(page); await page.goto("/projects/alpha");
  const check = page.getByRole("button", { name: "Check host prerequisites", exact: true });
  const panel = page.locator("#host-check-details");
  const close = panel.getByRole("button", { name: "Close details", exact: true });
  await expect(panel).not.toBeVisible();
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/readiness-check", async route => { await gate; await route.continue(); });
  await check.click();
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("status")).toContainText("Checking");
  await expect(check).toBeDisabled();
  await close.click();
  await expect(panel).not.toBeVisible();
  await expect(check).toBeFocused();
  release();
  await expect(check).toBeEnabled();
  await expect(panel).not.toBeVisible();
  await page.unroute("**/readiness-check");
  await check.click();
  await expect(panel.locator(".readiness-check")).toHaveCount(7);
  await expect(page.locator(".readiness-check").filter({hasText:"Network proxy image"})).toHaveCount(1);
  await expect(panel).toBeVisible();
  await expect(page.getByRole("button", { name: "Check details", exact: true })).toHaveCount(0);
  await close.click();
  await page.route("**/readiness-check", route => route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({detail:{code:"config_corrupt"}})}));
  await check.click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(panel.locator(".readiness-check")).toHaveCount(0);
  await expect(check).toBeEnabled();
  await close.click();
  await expect(panel).not.toBeVisible();
  await page.goto("/projects/beta");
  await expect(panel).not.toBeVisible();
});


test("repository connection clears tokens and shows scoped verified identity", async ({ page }) => {
  await signIn(page); await page.goto("/projects/alpha");
  const project = (await (await page.request.get("/api/v1/projects")).json()).find((p: {name: string}) => p.name === "alpha");
  await page.route("**/repository-connection", async route => {
    expect(route.request().headers()["x-csrf-token"]).toBeTruthy();
    expect(route.request().postDataJSON()).toEqual({ server: "https://git.example.com", token: "test-only-value", allow_http: false });
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ project_id: project.id, provider: project.platform, server: "https://git.example.com", repository: project.repo, account: "alice" }) });
  });
  const area = page.locator(".repository-connection");
  const trigger = area.getByRole("button", {name: "Repository access", exact: true});
  const check = page.getByRole("button", {name: "Check host prerequisites", exact: true});
  expect(Math.abs((await trigger.boundingBox())!.y - (await check.boundingBox())!.y)).toBeLessThan(2);
  await trigger.click();
  await expect(area.getByRole("dialog")).toBeVisible();
  await expect(area.getByRole("button", {name: "Close", exact: true})).toHaveCount(0);
  await expect(area.getByRole("button", {name: "Cancel", exact: true})).toHaveCount(1);
  await area.getByLabel("Repository server", {exact: true}).fill("https://git.example.com");
  const token = area.getByLabel("Access token", {exact: true});
  await token.fill("test-only-value");
  await area.getByRole("button", {name: "Verify and connect"}).click();
  await expect(token).toHaveValue("");
  await expect(area.getByRole("status")).toContainText("Connected account: alice");
  await expect(page.locator(".summary-fact").filter({hasText: "Environment verification"})).not.toContainText("Verified");
  expect(await page.evaluate(() => JSON.stringify([localStorage, sessionStorage]))).not.toContain("test-only-value");
  await token.fill("discard-me"); await area.getByRole("button", {name: "Cancel", exact: true}).click();
  await area.getByRole("button", {name: "Repository access", exact: true}).click();
  await expect(token).toHaveValue("");
  await area.getByLabel("Repository server", {exact: true}).fill("http://git.example.com");
  const checkbox = area.getByRole("checkbox");
  expect((await checkbox.boundingBox())!.width).toBeLessThan(24);
  expect(await checkbox.locator("..").evaluate(node => getComputedStyle(node).flexDirection)).toBe("row");
  await token.fill("discard-on-escape");
  await page.keyboard.press("Escape");
  await expect(area.getByRole("dialog")).not.toBeVisible();
  await area.getByRole("button", {name: "Repository access", exact: true}).click(); await expect(token).toHaveValue("");
  await area.getByRole("button", {name: "Cancel", exact: true}).click();
  await expect(area.getByRole("dialog")).not.toBeVisible();
});

test("repository connection rejects failed or mismatched evidence without exposing secrets", async ({ page }) => {
  await signIn(page); await page.goto("/projects/alpha");
  const area = page.locator(".repository-connection");
  await area.getByRole("button", {name: "Repository access", exact: true}).click();
  await area.getByLabel("Repository server", {exact: true}).fill("https://git.example.com");
  await page.route("**/repository-connection", route => route.fulfill({status: 400, contentType: "application/json", body: JSON.stringify({detail: {code: "repository_connection_failed", message: "DO-NOT-DISPLAY-SECRET"}})}));
  await area.getByLabel("Access token", {exact: true}).fill("test-secret");
  await area.getByRole("button", {name: "Verify and connect"}).click();
  await expect(area.getByRole("alert")).toContainText("Connection failed");
  await expect(area).not.toContainText("DO-NOT-DISPLAY-SECRET");
  await page.unroute("**/repository-connection");
  await page.route("**/repository-connection", route => route.fulfill({contentType: "application/json", body: JSON.stringify({project_id: "wrong", account: "alice"})}));
  await area.getByLabel("Access token", {exact: true}).fill("test-secret");
  await area.getByRole("button", {name: "Verify and connect"}).click();
  await expect(area.getByRole("alert")).toContainText("Credential storage is invalid");
  await expect(area.getByRole("status")).toHaveCount(0);
  await page.goto("/projects/beta");
  await page.locator(".repository-connection").getByRole("button", {name: "Repository access", exact: true}).click();
  await expect(page.getByLabel("Access token", {exact: true})).toHaveValue("");
});


test("repository connection supports keyboard four locales and narrow dark layout", async ({ page }, info) => {
  await signIn(page);
  await page.setViewportSize({width: 390, height: 844});
  for (const [locale, button, label] of [["fr", "Accès au dépôt", "Jeton d’accès"], ["de", "Repository-Zugang", "Zugriffstoken"], ["ro", "Acces la repository", "Token de acces"], ["en", "Repository access", "Access token"]]) {
    await page.goto("/account");
    const [savedLanguage] = await Promise.all([
      page.waitForResponse(response => response.url().endsWith("/api/v1/me/preferences") &&
        response.request().method() === "PATCH"),
      page.getByLabel(/Language|Langue|Sprache|Limbă/).selectOption(locale),
    ]);
    expect(savedLanguage.ok()).toBe(true);
    await page.goto("/projects/alpha");
    const open = page.locator(".repository-connection").getByRole("button", {name: button, exact: true});
    await open.focus(); await page.keyboard.press("Enter");
    await expect(page.getByLabel(label, {exact: true})).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.goto("/account");
  const [savedTheme] = await Promise.all([
    page.waitForResponse(response => response.url().endsWith("/api/v1/me/preferences") &&
      response.request().method() === "PATCH"),
    page.getByLabel("Theme", {exact: true}).selectOption("dark"),
  ]);
  expect(savedTheme.ok()).toBe(true);
  await page.goto("/projects/alpha");
  await page.getByRole("button", {name: "Repository access", exact: true}).click();
  await page.screenshot({path: info.outputPath("repository-connection-dark.png"), fullPage: true});
});

test("project hub shows jobs and statistics as tabs without duplicated scope", async ({ page }) => {
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
  await page.goto(`/projects/${alpha}`);
  const hub = page.locator(".project-hub");
  await hub.getByRole("tab", { name: "Jobs", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs$`));
  await expect(hub.getByRole("tab", { name: "Jobs", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("button", { name: "Read tickets", exact: true })).toBeVisible();
  await expect(page.locator("#job-ticket-number")).toHaveCount(0);
  await expect(page.locator("#jobs-project")).toHaveCount(0);
  await expect(page.getByText("Jobs shown here belong to the selected project.")).toHaveCount(0);
  await expect(page.locator(".project-context")).toHaveCount(1);
  await page.locator(".jobs-subtabs").getByRole("tab", { name: "Jobs", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs\\?view=jobs$`));
  await expect(page.locator("#job-search")).toBeVisible();
  const firstJob = page.locator(".action-jobs-table tbody tr").first().locator("td:first-child a");
  await expect(firstJob).toHaveAttribute("href", new RegExp(`^/projects/${alpha}/jobs\\?run=`));
  await firstJob.click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs\\?run=`));
  await expect(page.locator(".detail-panel")).toBeVisible();
  await expect(hub.getByRole("tab", { name: "Jobs", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.reload();
  await expect(page.locator(".detail-panel")).toBeVisible();
  await page.locator(".detail-panel").getByRole("button", { name: "Close", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs\\?view=jobs$`));
  await hub.getByRole("tab", { name: "Summary", exact: true }).click();
  await page.locator(".overview-jobs-table tbody tr").first().locator("a").first().click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs\\?run=`));
  await expect(page.locator(".detail-panel")).toBeVisible();
  await hub.getByRole("tab", { name: "History", exact: true }).click();
  await page.locator(".action-jobs-table tbody tr").first().locator("td:first-child a").click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs\\?run=`));
  await expect(hub.getByRole("tab", { name: "Jobs", exact: true })).toHaveAttribute("aria-selected", "true");
  await hub.getByRole("tab", { name: "Statistics", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/statistics$`));
  await expect(page.locator(".metrics-period")).toBeVisible();
  await expect(page.locator("#metrics-project")).toHaveCount(0);
  await expect(page.locator("#metrics-tab-projects")).toHaveCount(0);
  await expect(page.locator(".statistics-evidence")).toBeVisible();
  await page.locator("#metrics-tab-usage").click();
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/statistics\\?tab=usage$`));
  await page.reload();
  await expect(page.locator("#metrics-tab-usage")).toHaveAttribute("aria-selected", "true");
  await expect(hub.getByRole("tab", { name: "Statistics", exact: true })).toHaveAttribute("aria-selected", "true");
});


test("job budgets show retained consumption and boundary timing in four locales", async ({ page }) => {
  test.setTimeout(60_000);
  await signIn(page);
  await page.route("**/api/v1/jobs/*/ux-clarification", async route => {
    const response = await route.fetch(), data = await response.json();
    data.job.budget = {availability:"observed",reason:null,launches:18,max_launches:20,active_seconds:90,max_active_seconds:5400,
      config_revision:"b".repeat(64)};
    await route.fulfill({response,json:data});
  });
  try {
    for (const [locale,title,warning] of [
      ["fr","Budgets du travail","Une limite de budget approche"],
      ["de","Jobbudgets","Eine Budgetgrenze nähert sich"],
      ["ro","Bugetele jobului","Se apropie o limită de buget"],
      ["en","Job budgets","Approaching a budget limit"],
    ]) {
      await page.goto("/account");
      await Promise.all([page.waitForResponse(r=>r.url().endsWith("/api/v1/me/preferences") && r.request().method()==="PATCH"),
        page.getByLabel(/Language|Langue|Sprache|Limbă/).selectOption(locale)]);
      await page.goto("/jobs?project=alpha&run=ux-clarification");
      const budgets = page.getByRole("region",{name:title,exact:true});
      await expect(budgets).toContainText("18 / 20");
      await expect(budgets).toContainText("90 / 5400");
      await expect(budgets.getByRole("status")).toContainText(warning);
      await expect(budgets.getByRole("link")).toHaveAttribute("href",/\/projects\/[a-f0-9]{32}\/configuration$/);
    }
    await page.route("**/api/v1/jobs/*/ux-failed", async route => {
      const response = await route.fetch(), data = await response.json();
      data.job.budget = {availability:"unavailable",reason:"config_corrupt",launches:18,
        active_seconds:90,max_launches:null,max_active_seconds:null,config_revision:null};
      await route.fulfill({response,json:data});
    });
    await page.goto("/jobs?project=alpha&run=ux-failed");
    const unavailable = page.getByRole("region",{name:"Job budgets",exact:true});
    await expect(unavailable).toContainText("18 / —");
    await expect(unavailable).toContainText("90 / —");
    await expect(unavailable.getByRole("status")).toContainText("Current limits are unavailable");
    await page.locator(".detail-panel .job-actions summary").click();
    await expect(page.locator(".detail-panel").getByRole("button",{name:"Retry",exact:true})).toBeVisible();
    await page.route("**/api/v1/jobs/*/ux-clarification", async route => {
      const response = await route.fetch(), data = await response.json();
      data.job.budget.active_seconds = -1;
      await route.fulfill({response,json:data});
    });
    await page.goto("/jobs?project=alpha&run=ux-clarification");
    await expect(page.getByText("The server sent an unexpected response.",{exact:true})).toBeVisible();
    await expect(page.locator(".job-budgets")).toHaveCount(0);
  } finally {
    await page.goto("/account");
    const language = page.getByLabel(/Language|Langue|Sprache|Limbă/);
    if (await language.inputValue() !== "en") await Promise.all([
      page.waitForResponse(r=>r.url().endsWith("/api/v1/me/preferences") && r.request().method()==="PATCH"),
      language.selectOption("en"),
    ]);
    const theme = page.getByLabel("Theme",{exact:true});
    if (await theme.inputValue() !== "light") await Promise.all([
      page.waitForResponse(r=>r.url().endsWith("/api/v1/me/preferences") && r.request().method()==="PATCH"),
      theme.selectOption("light"),
    ]);
  }
});


test("executor output retains verified evidence across a live journal conflict", async ({page}) => {
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const projectId = projects.find((project: {name: string}) => project.name === "alpha").id;
  const source = await (await page.request.get(`/api/v1/jobs/${projectId}/ux-working`)).json();
  let reads = 0;
  await page.route("**/api/v1/jobs/*/ux-working/executor-output", route => {
    reads++;
    if (reads === 2) return route.fulfill({status:409,json:{detail:{code:"job_snapshot_changed"}}});
    return route.fulfill({json:{
      project_id:projectId,run_id:"ux-working",availability:"observed",
      stdout:"RPC completed",stderr:"",exit_code:0,timed_out:false,
      state_revision:source.job.state_revision,in_progress:reads === 3,attempt:reads === 1 ? 1 : 2,
      stage:"validate",recorded_at:"2026-11-05T10:12:34Z",
    }});
  });
  await page.goto("/jobs?project=alpha&run=ux-working");
  await page.getByRole("tab",{name:"Technical details",exact:true}).click();
  const output = page.locator(".executor-output");
  const read = output.getByRole("button",{name:"View latest executor output",exact:true});
  await read.click();
  await expect(output.getByText("Succeeded",{exact:true})).toBeVisible();
  await expect(output.getByText("No stderr records.",{exact:true})).toBeVisible();
  await expect(output.locator("summary")).toHaveText(["stdout"]);
  await expect(output.locator("time")).toHaveAttribute("datetime","2026-11-05T10:12:34Z");
  await output.locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(output.locator("pre")).toHaveText("RPC completed");
  await read.click();
  await expect(output.getByText(/Output changed during reading/)).toBeVisible();
  await expect(output.getByText(/Last verified snapshot/)).toBeVisible();
  await expect(output.locator("pre")).toBeVisible();
  await output.getByRole("button",{name:"Retry",exact:true}).click();
  await expect(output.getByText(/A launch is in progress/)).toBeVisible();
  await expect(output.getByText(/Last verified snapshot/)).toHaveCount(0);
  expect(reads).toBe(3);
  await page.setViewportSize({width:390,height:844});
  const box = await output.boundingBox();
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
});


test("issue35 job diagnostics clarify status, safe questions, seconds and consumption reload", async ({page}) => {
  await signIn(page);
  await page.route("**/api/v1/jobs/*/ux-working", async route => {
    const response=await route.fetch(), data=await response.json();
    data.job.stage_failures=1;
    data.job.timeline=[{ts:"2026-11-05T10:12:34Z",event:"stage-failed",stage:"build"}];
    await route.fulfill({response,json:data});
  });
  await page.route("**/api/v1/projects/*/usage?*",route=>route.fulfill({status:503,json:{detail:{code:"usage_corrupt"}}}));
  await page.route("**/api/v1/jobs/*/ux-working/executor-output",route=>route.fulfill({json:{
    project_id:new URL(route.request().url()).pathname.split("/")[4],run_id:"ux-working",availability:"observed",
    stdout:"ModuleNotFoundError: No module named 'yaml'\npytest: 1 failed, 2 passed",stderr:"diagnostic: credential",exit_code:1,timed_out:false,
    state_revision:"a".repeat(64),in_progress:false,attempt:1,stage:"build",recorded_at:"2026-11-05T10:12:34Z"}}));
  await page.goto("/jobs?project=alpha&run=ux-working");
  const card=page.locator(".next-action-panel"),detail=page.locator(".detail-panel");
  await expect(card).toContainText("Failed attempts in this stage: 1");
  await expect(card).not.toContainText(/Reason not recorded|Unknown — no recorded evidence|does not identify/);
  await detail.getByRole("tab",{name:"Technical details",exact:true}).click();
  await detail.getByText("Original recorded events",{exact:true}).click();
  await expect(detail.getByRole("table",{name:"Timeline",exact:true})).toContainText(/:34/);
  await expect(detail.getByRole("table",{name:"Timeline",exact:true})).toContainText("Build");
  await expect(detail.getByRole("button",{name:"Refresh consumption",exact:true})).toBeVisible();
  await page.unroute("**/api/v1/projects/*/usage?*");
  await detail.getByRole("button",{name:"Refresh consumption",exact:true}).click();
  await expect(detail.locator(".job-consumption")).toBeVisible();
  await detail.getByRole("button",{name:"View latest executor output",exact:true}).click();
  await detail.locator(".executor-output summary").filter({hasText:"stdout"}).click();
  await detail.locator(".executor-output summary").filter({hasText:"stderr"}).click();
  await expect(detail.locator(".executor-output")).toContainText("credential");
  await expect(detail.locator(".executor-output")).toContainText("ModuleNotFoundError: No module named 'yaml'");
  await expect(detail.locator(".executor-output")).toContainText("pytest: 1 failed, 2 passed");
  await page.route("**/api/v1/jobs/*/ux-clarification",async route=>{
    const response=await route.fetch(),data=await response.json();
    data.job.waiting.responsible_role=null;
    data.job.waiting.evidence_url=null;
    data.job.waiting.next_action=null;
    data.job.waiting.reason="## Choose a format\n\n- **JSON**\n- CSV\n\n`code`\n\n<script>window.issue35=true</script>\n\n[unsafe](javascript:alert(1))\n\n![image](https://invalid.example/private.png)";
    await route.fulfill({response,json:data});
  });
  await page.goto("/jobs?project=alpha&run=ux-clarification");
  await card.getByRole("button",{name:"Read the question",exact:true}).click();
  const question = detail.locator(".job-question");
  await expect(question.getByRole("heading",{name:"Choose a format"})).toBeVisible();
  await expect(card).toContainText("Human responder");
  await expect(card).not.toContainText("Unknown — no recorded evidence");
  await expect(question.locator("ul li")).toHaveCount(2);
  await expect(question.locator("code")).toHaveText("code");
  await expect(question).toContainText("<script>window.issue35=true</script>");
  await expect(question.locator("img, script, a[href^='javascript:']")).toHaveCount(0);
  expect(await page.evaluate(()=>Object.hasOwn(window,"issue35"))).toBe(false);
});


test("issue35 normal lifecycle copy in four locales and safe Markdown scroll on dark mobile", async ({page}, info) => {
  test.setTimeout(90_000);
  await signIn(page);
  const me=await (await page.request.get("/api/v1/me")).json();
  const preferences=async(language:string,theme:string)=>{
    expect((await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":me.csrf},data:{language,theme}})).ok()).toBe(true);
  };
  try {
    for (const [locale,working,failed,parked] of [
      ["en","no human intervention is currently requested","Autonomous work has stopped","After an accepted answer"],
      ["fr","aucune intervention humaine","Le travail autonome est arrêté","Après une réponse acceptée"],
      ["de","kein menschlicher Eingriff","Autonome Arbeit wurde angehalten","Nach einer angenommenen Antwort"],
      ["ro","nu se cere intervenția unui om","Lucrul autonom s-a oprit","După un răspuns acceptat"],
    ]) {
      await preferences(locale,"dark");
      for (const [suffix,text] of [["working",working],["failed",failed],["clarification",parked]]) {
        await page.goto(`/jobs?project=alpha&run=ux-${suffix}`);
        const card=page.locator(".next-action-panel");
        // Saved failed outcomes remain visible; the lifecycle explanation is separately localized.
        if(suffix==="failed") await expect(card).toContainText(/failed|échoué|fehlgeschlagen|eșuat/);
        else if(suffix==="clarification") await expect(card).toContainText(/clarification|Klärung|clarificare/);
        else await expect(card).toContainText(text);
      }
    }
    await preferences("en","dark");
    await page.route("**/api/v1/jobs/*/ux-clarification",async route=>{
      const response=await route.fetch(),data=await response.json();
      data.job.waiting.reason="## Long question\n\n| Header | Other |\n|---|---|\n| "+"a".repeat(600)+" | value |\n\n```\n"+"long_code ".repeat(120)+"\n```";
      await route.fulfill({response,json:data});
    });
    await page.setViewportSize({width:390,height:900});
    await page.goto("/jobs?project=alpha&run=ux-clarification");
    await expect(page.locator("html")).toHaveAttribute("data-theme","dark");
    await page.getByRole("button",{name:"Read the question",exact:true}).click();
    const regions=page.locator(".job-question .forge-scroll");
    await expect(regions).toHaveCount(2);
    // Detail reads can replace the card; query both current regions atomically on each poll.
    await expect.poll(()=>regions.evaluateAll(elements=>elements.map(element=>({
      scrolls:element.scrollWidth>element.clientWidth,
      overflow:getComputedStyle(element).overflowX,
    })))).toEqual([{scrolls:true,overflow:"auto"},{scrolls:true,overflow:"auto"}]);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({path:info.outputPath("issue35-question-dark-mobile.png"),fullPage:true});
  } finally {await preferences("en","light");}
});


test("compact summary and Jobs toolbar fit desktop and narrow screens", async ({page}, info) => {
  await page.setViewportSize({width:1366,height:768});
  await signIn(page);
  await page.goto("/projects/beta");
  const summary=page.locator(".project-summary-window");
  await expect(summary.locator(".summary-fact")).toHaveCount(7);
  await expect(summary.locator(".summary-job-window")).toContainText("Actual beta collision");
  const summaryBox=(await summary.boundingBox())!;
  expect(summaryBox.y+summaryBox.height).toBeLessThanOrEqual(768);
  await page.screenshot({path:info.outputPath("summary-one-screen.png")});

  await page.goto("/jobs?view=jobs");
  const toolbar=page.locator(".jobs-toolbar");
  await expect(toolbar.locator("#jobs-project")).toBeVisible();
  await page.screenshot({path:info.outputPath("jobs-toolbar-desktop.png")});
  await page.setViewportSize({width:390,height:844});
  const tabs=(await toolbar.getByRole("tablist").boundingBox())!;
  const scope=(await toolbar.locator("#jobs-project").boundingBox())!;
  expect(scope.y).toBeGreaterThanOrEqual(tabs.y+tabs.height);
  expect(scope.x+scope.width).toBeLessThanOrEqual(390);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
  const projects=await(await page.request.get("/api/v1/projects")).json();
  const beta=projects.find((item:{name:string})=>item.name==="beta").id;
  await toolbar.locator("#jobs-project").selectOption(beta);
  await expect(page.locator(".action-jobs-table")).toContainText("Actual beta collision");
  await expect(page.locator("#job-search-help")).toHaveCount(0);
  await toolbar.getByRole("tab",{name:"Tickets",exact:true}).click();
  await expect(toolbar.locator("#jobs-project")).toHaveValue(beta);
  await expect(page.getByRole("button",{name:"Read tickets",exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath("jobs-toolbar-mobile.png")});

  await page.setViewportSize({width:1366,height:768});
  await page.goto(`/projects/${beta}/configuration`);
  await expect(page.locator("#project-settings")).toBeVisible();
  await expect(page.locator(".settings-save-bar")).toHaveCount(0);
  await page.screenshot({path:info.outputPath("settings-clean.png")});
});

import { test, expect, type Page } from "@playwright/test";
import { messages, type Locale } from "../src/i18n";
import { refreshCopy } from "../src/refreshCopy";

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}
const reporting = /\/api\/v1\/(?:projects\/[^/]+\/)?(?:metrics|usage)\?/;
test.beforeEach(async ({ context, request }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
  expect((await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});
test.afterEach(async ({ page, request }) => {
  await page.unrouteAll({ behavior: "wait" });
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});

for (const scope of ["global", "project"]) test(`${scope} Statistics keeps all tabs, exports and focus through independent slow refreshes`, async ({ page }) => {
  test.setTimeout(60000);
  await page.clock.install(); await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  let hold = false, metricsReads = 0, usageReads = 0;
  let releaseMetrics = () => {}, releaseUsage = () => {};
  let metricsGate = Promise.resolve(), usageGate = Promise.resolve();
  await page.route(reporting, async route => {
    const body = await (await route.fetch()).json();
    if (hold) {
      if (new URL(route.request().url()).pathname.endsWith("/metrics")) { metricsReads++; await metricsGate; }
      else { usageReads++; await usageGate; }
    }
    await route.fulfill({ json: body });
  });
  try {
    for (const [index, tab] of ["summary", "usage", "quality", "trends"].entries()) {
      hold = false;
      await page.goto(scope === "global" ? `/metrics?tab=${tab}` : `/projects/${alpha}/statistics?tab=${tab}`);
      await expect(page.locator("#metrics-tab-panel .data-feedback")).toHaveCount(0);
      await expect(page.locator(".metrics-export")).toBeVisible();
      await page.locator(".metrics-export summary").click();
      const panel = page.locator("#metrics-tab-panel"), text = await panel.innerText();
      const trigger = page.locator(".metrics-export summary"); await trigger.focus();
      metricsReads = usageReads = 0;
      metricsGate = new Promise(resolve => { releaseMetrics = resolve; });
      usageGate = new Promise(resolve => { releaseUsage = resolve; }); hold = true;
      await page.clock.fastForward(30000);
      await expect.poll(() => [metricsReads, usageReads]).toEqual([1, 1]);
      await expect(panel).toHaveText(text, { useInnerText: true });
      await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
      await expect(trigger).toBeFocused();
      // Duplicate manual actions and visibility notifications join the existing reads.
      for (let click = 0; click < 3; click++) await page.locator(".refresh-status button").dispatchEvent("click");
      await page.evaluate(() => { document.dispatchEvent(new Event("visibilitychange")); document.dispatchEvent(new Event("visibilitychange")); });
      await expect.poll(() => [metricsReads, usageReads]).toEqual([1, 1]);
      await trigger.focus();
      if (index % 2) releaseMetrics(); else releaseUsage();
      await expect(panel).toHaveText(text, { useInnerText: true }); await expect(trigger).toBeFocused();
      hold = false; releaseMetrics(); releaseUsage();
      await expect(page.locator(".refresh-status button")).toHaveAttribute("aria-disabled", "false");
      await expect(panel).toHaveText(text, { useInnerText: true }); await expect(trigger).toBeFocused();
      await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
    }
  } finally { hold = false; releaseMetrics(); releaseUsage(); }
});

for (const scope of ["global", "project"] as const) for (const heldSource of ["usage", "metrics"] as const) {
  test(`${scope} manual Refresh coalesces after one source completes while ${heldSource} is pending`, async ({ page }) => {
    // Freeze timers near server time so current readiness evidence stays valid.
    const time = new Date();
    await page.clock.install({ time }); await page.clock.pauseAt(new Date(time.getTime() + 1000));
    await signIn(page);
    const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
    const reads = { metrics: 0, usage: 0 };
    let hold = false, release = () => {};
    const gate = new Promise<void>(resolve => { release = resolve; });
    await page.route(reporting, async route => {
      const source = new URL(route.request().url()).pathname.endsWith("/metrics") ? "metrics" : "usage";
      reads[source]++;
      const response = await route.fetch();
      if (hold && source === heldSource) await gate;
      await route.fulfill({ response });
    });
    try {
      await page.goto(scope === "global" ? "/metrics" : `/projects/${alpha}/statistics`);
      const refresh = page.locator(".refresh-status button");
      await expect(refresh).toHaveAttribute("aria-disabled", "false");
      expect(reads).toEqual({ metrics: 1, usage: 1 });
      const panel = page.locator("#metrics-tab-panel"), original = await panel.innerText();
      const completedSource = heldSource === "usage" ? "metrics" : "usage";
      const completed = page.waitForResponse(response => new URL(response.url()).pathname.endsWith(`/${completedSource}`));
      hold = true; await refresh.click(); await (await completed).finished();
      await page.clock.runFor(100);
      await expect.poll(() => reads).toEqual({ metrics: 2, usage: 2 });
      await expect(refresh).toHaveAttribute("aria-disabled", "true");
      // Real pointer clicks bypass Playwright's aria-disabled actionability guard.
      const box = (await refresh.boundingBox())!;
      for (let click = 0; click < 3; click++) await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.clock.runFor(100);
      expect(reads).toEqual({ metrics: 2, usage: 2 });
      await expect(panel).toHaveText(original, { useInnerText: true }); await expect(refresh).toBeFocused();
      hold = false; release();
      await expect(refresh).toHaveAttribute("aria-disabled", "false");
      expect(reads).toEqual({ metrics: 2, usage: 2 });
      await expect(panel).toHaveText(original, { useInnerText: true }); await expect(refresh).toBeFocused();
      await refresh.click(); await expect.poll(() => reads).toEqual({ metrics: 3, usage: 3 });
      await expect(refresh).toHaveAttribute("aria-disabled", "false");
      // Independent automatic cadences still work after the manual cohort settles.
      await page.clock.fastForward(15000);
      await expect.poll(() => reads).toEqual({ metrics: scope === "project" ? 4 : 3, usage: 3 });
      await expect(refresh).toHaveAttribute("aria-disabled", "false");
      await page.clock.fastForward(15000);
      await expect.poll(() => reads).toEqual({ metrics: scope === "project" ? 5 : 4, usage: 4 });
      await expect(refresh).toHaveAttribute("aria-disabled", "false");
    } finally { hold = false; release(); }
  });
}

test("new metrics wait for validated usage from the same cohort; rejected authority discards the snapshot", async ({ page }) => {
  await page.clock.install(); await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  let input = 97, hold = false, denied = false, release = () => {}, observed = false;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/projects/*/metrics?*", async route => {
    if (denied) return route.fulfill({ status: 403, json: { detail: { code: "admin_required" } } });
    const body = await (await route.fetch()).json(); body.period.tokens_in = input; body.totals.tokens_in = input;
    await route.fulfill({ json: body });
  });
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    const body = await (await route.fetch()).json();
    if (hold) { observed = true; await gate; }
    await route.fulfill({ json: body });
  });
  try {
    await page.goto(`/projects/${alpha}/statistics`);
    const card = page.locator(".stat-card").filter({ has: page.getByText("Input tokens", { exact: true }) });
    await expect(card).toContainText("97");
    input = 197; hold = true;
    const metricsRead = page.waitForResponse(response => /\/metrics\?/.test(response.url()));
    await page.getByRole("button", { name: "Refresh", exact: true }).click(); await metricsRead;
    await expect.poll(() => observed).toBe(true); await expect(card).toContainText("97"); await expect(card).not.toContainText("197");
    hold = false; release(); await expect(card).toContainText("197");
    denied = true; await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(card).toHaveCount(0); await expect(page.locator(".metrics-export")).toHaveCount(0);
    await expect(page.locator("#metrics-tab-panel .data-feedback[role=alert]")).toBeVisible();
  } finally { hold = false; release(); }
});

test("Usage retains non-default pagination, sorting, scroll and focused controls; replacements publish together", async ({ page }) => {
  await page.clock.install(); await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  let hold = false, input = 100, release = () => {}, reads = 0;
  let gate = Promise.resolve();
  await page.route("**/api/v1/projects/*/usage?*", async route => {
    const body = await (await route.fetch()).json();
    body.daily = Array.from({ length: 65 }, (_, index) => ({ date: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10), executor: "pi", model: "fixture", events: 1,
      tokens_in: input + index, tokens_out: 0, cache_read_tokens: null, cache_write_tokens: null, reported_cost_usd: null, estimated_cost_usd: null }));
    if (hold) { reads++; await gate; }
    await route.fulfill({ json: body });
  });
  await page.goto(`/projects/${alpha}/statistics?tab=usage`);
  const table = page.locator(".usage-table"), pager = page.locator("#metrics-tab-panel section").first();
  await expect(table.locator("tbody tr")).toHaveCount(10);
  await page.getByRole("columnheader", { name: "Input tokens", exact: true }).getByRole("button").click();
  const size = pager.getByRole("combobox", { name: "Rows per page", exact: true });
  await size.selectOption("25"); await pager.getByRole("button", { name: "Next", exact: true }).click();
  await expect(table.locator("tbody tr")).toHaveCount(25);
  await expect(table.locator("tbody tr").first()).toContainText("125");
  await size.focus();
  await table.locator("..").evaluate(element => { element.scrollLeft = 40; });
  const scroll = await table.locator("..").evaluate(element => element.scrollLeft);
  gate = new Promise(resolve => { release = resolve; }); hold = true; input = 200;
  try {
    await page.clock.fastForward(30000); await expect.poll(() => reads).toBe(1);
    await expect(size).toHaveValue("25"); await expect(size).toBeFocused();
    await expect(table.locator("tbody tr").first()).toContainText("125");
    hold = false; release();
    await expect(table.locator("tbody tr").first()).toContainText("225");
    await expect(size).toHaveValue("25"); await expect(size).toBeFocused();
    await expect(page.getByRole("columnheader", { name: "Input tokens", exact: true })).toHaveAttribute("aria-sort", "ascending");
    expect(await table.locator("..").evaluate(element => element.scrollLeft)).toBe(scroll);
  } finally { hold = false; release(); }
});

test("Statistics retains only transport-stale information, retries in place, and pauses hidden tabs", async ({ page }) => {
  await page.clock.install(); await signIn(page);
  let outage = false, corrupt = false, reads = 0;
  await page.route(reporting, async route => {
    reads++;
    if (outage) return route.abort("failed");
    const body = await (await route.fetch()).json();
    if (corrupt) Object.values(body).forEach((value: any) => { value.scope.project_ids = ["bad"]; });
    await route.fulfill({ json: body });
  });
  await page.goto("/metrics"); await expect(page.locator(".statistics-evidence")).toBeVisible();
  await page.locator(".metrics-export summary").click();
  outage = true; await page.clock.fastForward(30000);
  await expect(page.getByText("Refresh failed. Displayed information may be out of date.")).toBeVisible();
  await expect(page.locator(".statistics-evidence")).toBeVisible();
  await expect(page.locator(".refresh-status time")).toBeVisible();
  outage = false; await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByText("Refresh failed. Displayed information may be out of date.")).toHaveCount(0);
  await expect(page.locator(".metrics-export")).toHaveAttribute("open", "");
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }); document.dispatchEvent(new Event("visibilitychange")); });
  const before = reads; await page.clock.fastForward(60000); expect(reads).toBe(before);
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" }); document.dispatchEvent(new Event("visibilitychange")); document.dispatchEvent(new Event("visibilitychange")); });
  await expect.poll(() => reads).toBe(before + 2);
  await expect(page.locator(".refresh-status button")).toHaveAttribute("aria-disabled", "false");
  corrupt = true; await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".statistics-evidence")).toHaveCount(0); await expect(page.locator(".metrics-export")).toHaveCount(0);
  await expect(page.locator("#metrics-tab-panel .data-feedback[role=alert]")).toBeVisible();
});

test("Jobs and consumption keep rows, filters and active detail disclosures during slow reads", async ({ page }) => {
  test.setTimeout(60000);
  await page.clock.install(); await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: any) => item.name === "alpha").id;
  let hold = false, reads = 0, release = () => {}, gate = Promise.resolve();
  await page.route(/\/api\/v1\/(?:jobs-page\?|projects\/[^/]+\/usage\?)/, async route => {
    const response = await route.fetch();
    if (hold) { reads++; await gate; }
    await route.fulfill({ response });
  });
  try {
    for (const url of ["/jobs?view=jobs", `/projects/${alpha}/jobs`, `/projects/${alpha}/history`]) {
      hold = false; await page.goto(url);
      const workspace = page.locator(".job-workspace"), rows = workspace.locator(".action-jobs-table tbody tr");
      await expect(rows.first()).toBeVisible();
      const size = workspace.getByRole("combobox", { name: "Rows per page", exact: true });
      await size.selectOption("25"); await expect(size).toBeVisible();
      await expect(workspace.locator(".job-consumption").first()).toBeVisible();
      await size.focus(); const text = await rows.allTextContents();
      reads = 0; gate = new Promise(resolve => { release = resolve; }); hold = true;
      await page.clock.fastForward(30000); await expect.poll(() => reads).toBeGreaterThan(1);
      await expect(rows).toHaveText(text); await expect(size).toHaveValue("25"); await expect(size).toBeFocused();
      await expect(workspace.locator(".job-consumption").first()).toBeVisible();
      hold = false; release(); await expect(workspace.locator(".refresh-status").first().getByRole("button")).toHaveAttribute("aria-disabled", "false");
    }
    await page.goto(`/jobs?project=${alpha}&run=ux-working`);
    const detail = page.locator(".detail-panel"); await expect(detail).toBeVisible();
    await expect(detail.locator(".job-consumption").first()).toBeVisible();
    await detail.getByRole("tab", { name: "Job details", exact: true }).click();
    await detail.locator(".job-diagnostics > summary").click();
    const summary = detail.locator(".job-diagnostics > summary"); await summary.focus();
    reads = 0; gate = new Promise(resolve => { release = resolve; }); hold = true;
    await page.clock.fastForward(30000); await expect.poll(() => reads).toBeGreaterThan(1);
    await expect(detail.locator(".job-diagnostics")).toHaveAttribute("open", ""); await expect(summary).toBeFocused();
    await expect(detail.locator(".job-consumption").first()).toBeVisible();
    hold = false; release(); await expect(summary).toBeFocused();
  } finally { hold = false; release(); }
});

test("Jobs transport failures retain marked information, but snapshot conflicts remove it and disable actions", async ({ page }) => {
  await page.clock.install(); await signIn(page);
  await page.goto("/jobs?view=jobs");
  const workspace = page.locator(".job-workspace"), rows = workspace.locator(".action-jobs-table tbody tr");
  await expect(rows.first()).toBeVisible();
  await expect(workspace.locator(".job-consumption").first()).toBeVisible();
  let conflict = false;
  await page.route("**/api/v1/jobs-page?*", route => conflict ? route.fulfill({ status: 409, json: { detail: { code: "job_snapshot_changed" } } }) : route.abort("failed"));
  await page.clock.fastForward(15000);
  await expect(workspace.getByText(refreshCopy.en.failed)).toBeVisible(); await expect(rows.first()).toBeVisible();
  conflict = true; await workspace.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(rows).toHaveCount(0); await expect(workspace.getByText("Job sources changed", { exact: true })).toBeVisible();
  await page.unroute("**/api/v1/jobs-page?*");
  await workspace.getByRole("button", { name: "Reload first page", exact: true }).click();
  await expect(rows.first()).toBeVisible();
});

test("refresh feedback is localized and fits both themes on narrow screens", async ({ page }) => {
  test.setTimeout(60000); await page.clock.install(); await signIn(page);
  const me = await (await page.request.get("/api/v1/me")).json();
  let outage = false;
  await page.route(reporting, route => outage ? route.abort("failed") : route.continue());
  try {
    for (const locale of ["en", "fr", "de", "ro"] as Locale[]) for (const theme of ["light", "dark"]) {
      outage = false;
      expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme } })).ok()).toBe(true);
      await page.setViewportSize({ width: 390, height: 900 }); await page.goto("/metrics");
      await expect(page.locator(".statistics-evidence")).toBeVisible();
      await expect(page.locator(".refresh-status")).toContainText(refreshCopy[locale].updated);
      outage = true; await page.clock.fastForward(30000);
      await expect(page.getByText(refreshCopy[locale].failed)).toBeVisible();
      await expect(page.getByRole("button", { name: refreshCopy[locale].retry, exact: true })).toBeVisible();
      await expect(page.getByRole("tab", { name: messages[locale].metricsTabSummary, exact: true })).toHaveAttribute("aria-selected", "true");
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    }
  } finally {
    expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } })).ok()).toBe(true);
  }
});

test("audit manual Refresh preserves expanded evidence, filters, pager and focus", async ({ page }) => {
  await signIn(page); await page.goto("/admin/audit");
  const audit = page.locator(".audit-evidence"); await expect(audit.locator("tbody tr").first()).toBeVisible();
  const toggle = audit.locator(".audit-toggle").first(); await toggle.click();
  const actor = audit.getByLabel("Actor ID", { exact: true }); await actor.fill("123");
  let release = () => {}, observed = false;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/audit-page?*", async route => { const response = await route.fetch(); observed = true; await gate; await route.fulfill({ response }); });
  try {
    await audit.getByRole("button", { name: "Refresh", exact: true }).click(); await expect.poll(() => observed).toBe(true);
    await expect(toggle).toHaveAttribute("aria-expanded", "true"); await expect(actor).toHaveValue("123");
    await actor.focus(); release();
    await expect(audit.locator(".refresh-status button")).toHaveAttribute("aria-disabled", "false");
    await expect(toggle).toHaveAttribute("aria-expanded", "true"); await expect(actor).toBeFocused();
  } finally { release(); }
});

test("change history waits for a slow project catalog instead of reading evidence twice", async ({ page }) => {
  await signIn(page);
  const events: string[] = [];
  page.on("request", request => { if (request.url().includes("/api/v1/audit-page?")) events.push("audit"); });
  page.on("response", response => { if (new URL(response.url()).pathname === "/api/v1/projects") events.push("projects"); });
  await page.route("**/api/v1/projects", async route => {
    await new Promise(resolve => setTimeout(resolve, 800)); await route.continue().catch(() => {});
  });
  await page.goto("/admin/audit");
  await expect(page.locator(".audit-evidence tbody tr").first()).toBeVisible();
  await page.unrouteAll({ behavior: "wait" });
  // The catalog is part of the evidence key, so an earlier read would be discarded and blank the table.
  expect(events.indexOf("projects")).toBeGreaterThanOrEqual(0);
  expect(events.indexOf("audit")).toBeGreaterThan(events.indexOf("projects"));
});

test("Users manual Refresh preserves membership disclosure and unrelated form draft", async ({ page }) => {
  await signIn(page); await page.goto("/admin/users");
  const users = page.locator(".user-list"); await expect(users).toBeVisible();
  await users.locator(".membership-editor summary").first().click();
  let release = () => {}, observed = false;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/users", async route => { const response = await route.fetch(); observed = true; await gate; await route.fulfill({ response }); });
  try {
    await page.getByRole("button", { name: "Refresh", exact: true }).click(); await expect.poll(() => observed).toBe(true);
    await expect(users).toBeVisible(); await expect(users.locator(".membership-editor").first()).toHaveAttribute("open", "");
    await page.getByRole("button", { name: "Add user", exact: true }).click();
    const dialog = page.getByRole("dialog"), username = dialog.getByLabel("Username", { exact: false });
    await username.fill("refresh_draft");
    await dialog.getByLabel("Password", { exact: true }).fill("refresh-test-password");
    await dialog.getByLabel("Repeat new password", { exact: true }).fill("refresh-test-password");
    await dialog.getByRole("button", { name: "Continue to access", exact: true }).click();
    const project = dialog.getByRole("checkbox", { name: /alpha/ }); await project.check(); await project.focus();
    release();
    await expect(page.locator(".refresh-status button")).toHaveAttribute("aria-disabled", "false");
    await expect(project).toBeChecked(); await expect(project).toBeFocused();
    await dialog.getByRole("button", { name: "Correct identity", exact: true }).click();
    await expect(username).toHaveValue("refresh_draft");
    await expect(users.locator(".membership-editor").first()).toHaveAttribute("open", "");
  } finally { release(); }
});

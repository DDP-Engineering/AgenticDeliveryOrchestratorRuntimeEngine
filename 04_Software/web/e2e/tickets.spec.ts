/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { setPickup } from "./pickup";
import { ticketCopy } from "../src/ticketCopy";

async function signIn(page: Page, username = "admin", password = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(username);
  await page.getByLabel("Password", { exact: false }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}

/** Press a project Summary's monitoring control and wait until the worker applied it. */
async function setMonitoring(page: Page, project: string, press: string, then: string) {
  await page.goto(`/projects/${project}`);
  await page.getByRole("button", { name: press, exact: true }).click();
  await expect(page.getByRole("button", { name: then, exact: true })).toBeVisible();
}

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

test("the ticket number column leaves room for content in both scopes", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
  const table = page.locator(".ticket-table");
  const number = table.getByRole("columnheader", { name: "#", exact: true });
  const title = table.getByRole("columnheader", { name: "Title", exact: true });
  for (const url of ["/jobs", `/projects/${alpha}/jobs`]) {
    await page.goto(url);
    await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    await expect(number).toBeVisible();
    const numberWidth = await number.evaluate(cell => cell.getBoundingClientRect().width);
    const titleWidth = await title.evaluate(cell => cell.getBoundingClientRect().width);
    expect(numberWidth).toBeLessThanOrEqual(90);
    expect(titleWidth).toBeGreaterThan(numberWidth * 2);
  }
  await page.setViewportSize({ width: 360, height: 800 });
  const firstTicket = table.locator(".ticket-row").first();
  const firstNumber = firstTicket.getByRole("cell").first();
  expect(await firstNumber.evaluate(cell => cell.scrollWidth)).toBeLessThanOrEqual(
    await firstNumber.evaluate(cell => cell.clientWidth)
  );
  await firstTicket.getByRole("button", { name: "Details", exact: true }).click();
  await expect(table.locator(".ticket-detail")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
});

for (const locale of ["en", "fr", "de", "ro"] as const) {
  test(`expanded ticket actions stay on one desktop row in ${locale}`, async ({page},info) => {
    await signIn(page);
    const me=await (await page.request.get("/api/v1/me")).json();
    const prefs={headers:{"X-CSRF-Token":me.csrf},data:{language:locale,theme:"light"}};
    await page.request.patch("/api/v1/me/preferences",prefs);
    const projects=await (await page.request.get("/api/v1/projects")).json();
    const alpha=projects.find((project:{name:string})=>project.name==="alpha").id;
    const copy=ticketCopy[locale];
    try {
      for(const width of [1440,1600]) {
        await page.setViewportSize({width,height:900});
        for(const url of ["/jobs",`/projects/${alpha}/jobs`]) {
          await page.goto(url);
          await page.getByRole("button",{name:copy.read,exact:true}).click();
          const row=page.locator(".ticket-row").first();
          await row.getByRole("button",{name:copy.details,exact:true}).click();
          await expect(row.getByRole("button",{name:copy.hide,exact:true})).toBeVisible();
          const buttons=row.locator(".ticket-actions button");
          const bounds=await buttons.evaluateAll(nodes=>nodes.map(node=>{
            const box=node.getBoundingClientRect();
            return {top:box.top,right:box.right,scroll:node.scrollWidth,client:node.clientWidth};
          }));
          expect(bounds).toHaveLength(3);
          expect(Math.max(...bounds.map(box=>box.top))-Math.min(...bounds.map(box=>box.top))).toBeLessThan(1);
          for(const box of bounds) expect(box.scroll).toBeLessThanOrEqual(box.client);
          expect(Math.max(...bounds.map(box=>box.right))).toBeLessThanOrEqual(width);
          if(width===1440 && url!=="/jobs") await page.screenshot({path:info.outputPath(`expanded-actions-${locale}.png`),fullPage:true});
          await row.getByRole("button",{name:copy.hide,exact:true}).click();
        }
      }
      await page.setViewportSize({width:360,height:800});
      const row=page.locator(".ticket-row").first();
      await row.getByRole("button",{name:copy.details,exact:true}).click();
      await expect(page.locator(".ticket-detail").first()).toBeVisible();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
    } finally {
      await page.request.patch("/api/v1/me/preferences",{...prefs,data:{language:"en",theme:"light"}});
    }
  });
}

test("tickets sub-tab reads open tickets on request and controls them safely", async ({ page }) => {
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
  // The fixture keeps pickup stopped; Start needs it active, as an operator would set it.
  await setMonitoring(page, alpha, "Activate monitoring", "Pause monitoring");
  try {
    const reads: string[] = [];
    page.on("request", request => { if (new URL(request.url()).pathname.endsWith("/tickets")) reads.push(request.url()); });
    await page.goto(`/projects/${alpha}/jobs`);
    const sections = page.locator(".jobs-subtabs");
    await expect(sections.getByRole("tab", { name: "Tickets", exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(page.locator(".ticket-table")).toHaveCount(0);
    await expect(page.locator("#job-ticket-number")).toHaveCount(0);
    await expect(page.getByText("Press Read tickets to load this project's open tickets", { exact: false })).toBeVisible();
    expect(reads).toEqual([]);

    await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    const rows = page.locator(".ticket-table tbody tr.ticket-row");
    await expect(rows).toHaveCount(7);
    expect(reads).toHaveLength(1);
    const ready = rows.filter({ hasText: "#21" });
    const unsafe = rows.filter({ hasText: "#22" });
    await expect(ready).toContainText("Ready to start");
    await expect(ready.getByRole("button", { name: "Start", exact: true })).toBeEnabled();
    await expect(unsafe).toContainText("Missing label agent-ready");
    // Start can add the missing ready label, so it stays available.
    await expect(unsafe.getByRole("button", { name: "Start", exact: true })).toBeEnabled();
    const held = rows.filter({ hasText: "#23" });
    await expect(held).toContainText("On hold");
    await expect(held.getByRole("button", { name: "Start", exact: true })).toBeDisabled();
    await expect(held.getByRole("button", { name: "Stop", exact: true })).toBeDisabled();
    // Disabled actions must look disabled, not only be inert.
    const opacity = (name: string) => held.getByRole("button", { name, exact: true }).evaluate(el => Number(getComputedStyle(el).opacity));
    expect(await opacity("Start")).toBeLessThan(0.7);
    expect(await opacity("Stop")).toBeLessThan(0.7);
    expect(await ready.getByRole("button", { name: "Start", exact: true }).evaluate(el => Number(getComputedStyle(el).opacity))).toBe(1);

    // Forge text is inert: markup shows literally and unsafe links are not rendered.
    await expect(unsafe).toContainText("<img src=x onerror=alert(1)> Fix login");
    await expect(page.locator(".ticket-table img")).toHaveCount(0);
    await expect(unsafe.getByRole("link")).toHaveCount(0);
    const link = ready.getByRole("link", { name: "Add export button", exact: true });
    await expect(link).toHaveAttribute("href", "https://gitlab.example/offline/alpha/-/issues/21");
    await expect(link).toHaveAttribute("rel", "noopener noreferrer");
    await expect(link).toHaveAttribute("target", "_blank");

    await unsafe.getByRole("button", { name: "Details", exact: true }).click();
    const unsafeDetail = page.locator(".ticket-detail").filter({ hasText: "Steps" });
    await expect(unsafeDetail).toContainText("<script>window.__ticketInjected = true</script>Steps");
    await expect(unsafeDetail).toContainText("<b onclick=alert(1)>urgent</b>");
    await expect(page.locator(".ticket-detail b, .ticket-detail script")).toHaveCount(0);
    expect(await page.evaluate(() => (window as unknown as { __ticketInjected?: boolean }).__ticketInjected)).toBeUndefined();

    await ready.getByRole("button", { name: "Details", exact: true }).click();
    const readyDetail = page.locator(".ticket-detail").filter({ hasText: "Export the table." });
    await expect(readyDetail.locator("strong")).toHaveText("bold");
    await expect(readyDetail).not.toContainText("added ~agent-ready label");

    await ready.getByRole("button", { name: "Start", exact: true }).click();
    await expect(page.locator(".ticket-notice")).toContainText("Start for #21 queued");
    await expect(page.locator(".ticket-start-confirm")).toHaveCount(0);
    await expect(ready.getByRole("button", { name: "Start", exact: true })).toBeDisabled();

    // Start adds a missing ready label after confirmation.
    await unsafe.getByRole("button", { name: "Start", exact: true }).click();
    await expect(page.locator(".ticket-start-confirm")).toContainText("agent-ready");
    await expect(page.locator(".ticket-start-confirm select")).toHaveCount(0);
    await page.getByRole("button", { name: "Add labels and start", exact: true }).click();
    await expect(page.locator(".ticket-notice")).toContainText("Labels added: agent-ready.");
    await expect(page.locator(".ticket-notice")).toContainText("Start for #22 queued");

    // A ticket without a priority asks for one.
    const unlabelled = rows.filter({ hasText: "#25" });
    await unlabelled.getByRole("button", { name: "Start", exact: true }).click();
    await page.locator(".ticket-start-confirm").getByLabel("Priority", { exact: true }).selectOption("P1");
    await page.getByRole("button", { name: "Add labels and start", exact: true }).click();
    await expect(page.locator(".ticket-notice")).toContainText("Labels added: agent-ready, P1.");

    // A failed job is retried from the table.
    const failed = rows.filter({ hasText: "#24" });
    await expect(failed).toContainText("Job: failed");
    await failed.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(page.locator(".ticket-notice")).toContainText("Retry for #24 queued");

    await ready.getByRole("button", { name: "Stop", exact: true }).click();
    await expect(page.locator(".ticket-stop-confirm")).toContainText("agent-ready");
    await page.getByRole("button", { name: "Stop ticket", exact: true }).click();
    await expect(page.locator(".ticket-notice")).toContainText("Ready label removed.");
    await expect(page.locator(".ticket-notice")).toContainText(/#21 (had no unfinished job to cancel|queued as operation #\d+)/);
    await page.getByRole("button", { name: "Read tickets", exact: true }).click();
    await expect(rows.filter({ hasText: "#21" })).toContainText("Missing label agent-ready");

    await sections.getByRole("tab", { name: "Jobs", exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs\\?view=jobs$`));
    await expect(page.locator("#job-search")).toBeVisible();
    await expect(page.locator("#job-ticket-number")).toHaveCount(0);
    await page.reload();
    await expect(sections.getByRole("tab", { name: "Jobs", exact: true })).toHaveAttribute("aria-selected", "true");
  } finally {
    // Later specs expect the fixture's stopped pickup.
    await setPickup("alpha", false);
  }
});

test("Start explains stopped pickup and a refused start keeps its reason, lines and labels", async ({ page }) => {
  // Shape three fixture tickets so earlier tests' Start calls cannot change what this one sees.
  await page.route("**/api/v1/projects/*/tickets", async route => {
    const response = await route.fetch(); const list = await response.json();
    const shape: Record<number, object> = {
      21: { labels: ["agent-ready", "P2"], reason: null, startable: true, can_start: false, blocked_by: "pickup_paused", adds_ready_label: false, needs_priority: false, job: null },
      22: { labels: ["P2"], reason: "missing_ready_label", startable: false, can_start: true, blocked_by: null, adds_ready_label: true, needs_priority: false, job: null },
      25: { labels: [], reason: "missing_ready_label", startable: false, can_start: true, blocked_by: null, adds_ready_label: true, needs_priority: true, job: null },
    };
    const tickets = list.tickets.map((item: { iid: number }) => ({ ...item, ...(shape[item.iid] ?? {}) }));
    await route.fulfill({ response, json: { ...list, tickets } });
  });
  // #22: pickup stopped between the read and the click.
  await page.route("**/api/v1/projects/*/tickets/22/start", route => route.fulfill({
    status: 409, json: { detail: { code: "ticket_not_startable", message: "pickup_paused" } } }));
  // #25: queued, then refused by the engine because every execution slot was busy.
  await page.route("**/api/v1/projects/*/tickets/25/start", route => route.fulfill({
    json: { operation_id: 9001, status: "pending", labels_added: ["agent-ready", "P1"] } }));
  await page.route("**/api/v1/operations/9001", route => route.fulfill({ json: {
    id: 9001, project: "alpha", action: "start", status: "failed", result: "engine rejected operation",
    reason: "at_capacity", detail: "{\"picked\": null}\nerror: ticket #25 not started: at_capacity",
    created_at: "2026-11-01T10:00:00Z", updated_at: "2026-11-01T10:00:01Z" } }));
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
  await page.goto(`/projects/${alpha}/jobs`);
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  const rows = page.locator(".ticket-table tbody tr.ticket-row");
  await expect(rows).toHaveCount(7);

  // A ticket blocked by stopped pickup says so; the view explains how to continue.
  const stopped = rows.filter({ hasText: "#21" });
  await expect(stopped).toContainText("Monitoring paused");
  await expect(stopped.getByRole("button", { name: "Start", exact: true })).toBeDisabled();
  await expect(page.locator(".ticket-pickup-stopped")).toContainText("An administrator activates monitoring in the project Summary");
  await expect(rows.filter({ hasText: "#23" })).toContainText("On hold");

  // A confirmation opens directly under its row, names the chosen priority and is the only one open.
  const unlabelled = rows.filter({ hasText: "#25" });
  await unlabelled.getByRole("button", { name: "Start", exact: true }).click();
  const confirmRows = page.locator("tr.ticket-confirm-row");
  await expect(confirmRows).toHaveCount(1);
  expect(await unlabelled.evaluate(row => !!row.nextElementSibling?.querySelector(".ticket-start-confirm"))).toBe(true);
  const startConfirm = page.locator(".ticket-start-confirm");
  await expect(startConfirm).toContainText("agent-ready, P3");
  await expect(startConfirm.locator("p")).not.toContainText("Priority");
  await startConfirm.getByLabel("Priority", { exact: true }).selectOption("P1");
  await expect(startConfirm).toContainText("agent-ready, P1");
  await stopped.getByRole("button", { name: "Stop", exact: true }).click();
  await expect(startConfirm).toHaveCount(0);
  await expect(confirmRows).toHaveCount(1);
  expect(await stopped.evaluate(row => !!row.nextElementSibling?.querySelector(".ticket-stop-confirm"))).toBe(true);
  await page.getByRole("button", { name: "Keep running", exact: true }).click();
  await expect(confirmRows).toHaveCount(0);

  // A queued start the engine refuses shows the reason, the engine's lines and the kept labels.
  await unlabelled.getByRole("button", { name: "Start", exact: true }).click();
  await startConfirm.getByLabel("Priority", { exact: true }).selectOption("P1");
  await page.getByRole("button", { name: "Add labels and start", exact: true }).click();
  const notice = page.locator(".ticket-notice");
  await expect(notice).toContainText("all execution slots are busy");
  await expect(notice).not.toContainText("engine rejected operation");
  await expect(notice.locator("pre.operation-detail")).toContainText("error: ticket #25 not started: at_capacity");
  await expect(notice).toContainText("The ticket keeps the labels agent-ready, P1");

  // Last: pickup stopped after the read. Start explains it instead of the generic refusal,
  // and every Start of the project becomes unavailable.
  await rows.filter({ hasText: "#22" }).getByRole("button", { name: "Start", exact: true }).click();
  await page.getByRole("button", { name: "Add labels and start", exact: true }).click();
  const alert = page.locator(".ticket-workspace p.alert");
  await expect(alert).toContainText("Monitoring is paused for this project");
  await expect(alert).not.toContainText("cannot be started yet");
  const refused = rows.filter({ hasText: "#22" });
  await expect(refused).toContainText("Monitoring paused");
  await expect(refused.getByRole("button", { name: "Start", exact: true })).toBeDisabled();
});

test("many tickets are paged with a rows-per-page selector", async ({ page }) => {
  // 23 open tickets: the fixture's seven plus sixteen numbered copies.
  await page.route("**/api/v1/projects/*/tickets", async route => {
    const response = await route.fetch(); const list = await response.json();
    const extra = Array.from({ length: 16 }, (_, index) => ({ ...list.tickets[0], iid: 100 + index, title: `Bulk ticket ${100 + index}`, job: null }));
    await route.fulfill({ response, json: { ...list, tickets: [...extra.reverse(), ...list.tickets] } });
  });
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
  await page.goto(`/projects/${alpha}/jobs`);
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  const rows = page.locator(".ticket-table tbody tr.ticket-row");
  const pager = page.locator(".ticket-pagination");
  await expect(rows).toHaveCount(10);
  await expect(pager).toContainText("1–10 / 23");
  await expect(pager).toContainText("Page 1 of 3");
  await expect(rows.first()).toContainText("#115");
  await expect(pager.getByRole("button", { name: "Previous", exact: true })).toBeDisabled();
  await pager.getByRole("button", { name: "Next", exact: true }).click();
  await expect(pager).toContainText("Page 2 of 3");
  await expect(rows.first()).toContainText("#105");
  await pager.getByRole("button", { name: "Next", exact: true }).click();
  await expect(rows).toHaveCount(3);
  await expect(pager).toContainText("21–23 / 23");
  await expect(pager.getByRole("button", { name: "Next", exact: true })).toBeDisabled();
  await pager.getByLabel("Rows per page").selectOption("25");
  await expect(rows).toHaveCount(23);
  await expect(pager).toContainText("Page 1 of 1");
  await pager.getByLabel("Rows per page").selectOption("10");
  await pager.getByRole("button", { name: "Next", exact: true }).click();
  // A new read starts again on the first page.
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  await expect(pager).toContainText("Page 1 of 3");
  await pager.getByLabel("Rows per page").selectOption("all");
  await expect(rows).toHaveCount(23);
  await expect(pager.getByRole("button", { name: "Next", exact: true })).toHaveCount(0);
  await page.unroute("**/api/v1/projects/*/tickets");
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  await expect(rows).toHaveCount(7);
  await expect(pager).toHaveCount(0);
});

/** Open the same offline ticket surface without changing pickup or invoking an executor. */
async function openBodies(page: Page, project = "alpha", read = "Read tickets", details = "Details") {
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const id = projects.find((row: { name: string }) => row.name === project).id;
  await page.goto(`/projects/${id}/jobs`);
  await page.getByRole("button", { name: read, exact: true }).click();
  for (const iid of [21, 22]) await page.locator("tr.ticket-row").filter({ hasText: `#${iid}` }).getByRole("button", { name: details, exact: true }).click();
}

test("ticket bodies render by default, share exact source and retain keyboard focus", async ({ page }) => {
  const source = '  # Goal\n\n**bold** and *italic*, `code`.\n\n- [ ] task\n\n<script>window.__ticketInjected=true</script>\n<img src="https://tracker.invalid/raw" onerror="alert(1)">\n\n[allowed](https://forge.invalid/issue) [unsafe](javascript:alert%281%29)\n![tracking](https://tracker.invalid/pixel)\n  ';
  const comment = '  **Comment**\n\n> quote\n\n[mail](mailto:help@example.invalid)\n![comment image](https://tracker.invalid/comment)\n  ';
  await page.route("**/api/v1/me/preferences", route => route.request().method() === "GET" ? route.fulfill({ json: { language: "en", theme: "light", ticket_body_mode: null } }) : route.fulfill({ json: { language: "en", theme: "light", ...route.request().postDataJSON() } }));
  await page.route("**/api/v1/projects/*/tickets", async route => {
    const response = await route.fetch(); const list = await response.json();
    await route.fulfill({ response, json: { ...list, tickets: list.tickets.map((item: { iid: number; labels: string[] }) => ({ ...item, labels: [...item.labels, '<b onclick="alert(1)">**label**</b>'], description: item.iid === 21 ? source : "" })) } });
  });
  let releaseComments!: () => void;
  const commentsReady = new Promise<void>(resolve => { releaseComments = resolve; });
  await page.route("**/api/v1/projects/*/tickets/*/comments", async route => {
    await commentsReady;
    await route.fulfill({ json: { iid: Number(route.request().url().split("/").at(-2)), comments: [{ author: "<b>author</b>", created_at: "2026-11-01T10:00:00Z", body: comment }] } });
  });
  const external: string[] = [];
  page.on("request", request => { if (new URL(request.url()).origin !== "http://127.0.0.1:18765") external.push(request.url()); });
  await signIn(page); await openBodies(page);
  const details = page.locator(".ticket-detail");
  const controls = details.getByRole("combobox", { name: "Body display", exact: true });
  await expect(controls).toHaveCount(2);
  await expect(page.locator(".ticket-labels").first()).toContainText('<b onclick="alert(1)">**label**</b>');
  await expect(page.locator(".ticket-labels b, .ticket-labels strong")).toHaveCount(0);
  await expect(controls.first()).toHaveValue("rendered");
  await expect(details.first().getByRole("heading", { name: "Goal", exact: true })).toBeVisible();
  await expect(details.first().locator("strong")).toHaveText("bold");
  await expect(details.first().getByRole("checkbox")).toBeDisabled();
  await expect(details.last()).toContainText("No description.");
  await expect(details.first().getByRole("link", { name: "allowed", exact: true })).toHaveAttribute("rel", "noopener noreferrer");
  await expect(details.first().getByRole("link", { name: "allowed", exact: true })).toHaveAttribute("target", "_blank");
  await expect(details.getByRole("link", { name: "unsafe", exact: true })).toHaveCount(0);
  await expect(details.locator("script, img, iframe, b")).toHaveCount(0);
  await expect(details.first()).toContainText('<script>window.__ticketInjected=true</script>');
  expect(await page.evaluate(() => (window as unknown as { __ticketInjected?: boolean }).__ticketInjected)).toBeUndefined();
  // Tab into the first native selector, then choose each mode without replacing the element.
  await details.first().locator("h3").first().evaluate(el => { el.setAttribute("tabindex", "-1"); (el as HTMLElement).focus(); });
  await page.keyboard.press("Tab");
  await expect(controls.first()).toBeFocused();
  await page.keyboard.press("ArrowDown"); await page.keyboard.press("Enter");
  await expect(controls.first()).toHaveValue("source");
  await expect(controls.last()).toHaveValue("source");
  await expect(controls.first()).toBeFocused();
  expect(await details.first().locator(".ticket-source").textContent()).toBe(source);
  releaseComments();
  await expect(details.locator(".ticket-comments .ticket-source")).toHaveCount(2);
  expect(await details.first().locator(".ticket-comments .ticket-source").textContent()).toBe(comment);
  await expect(details.last()).toContainText("No description.");
  await expect(details.locator("a, img, script, b")).toHaveCount(0);
  await page.keyboard.press("ArrowUp"); await page.keyboard.press("Enter");
  await expect(controls.first()).toHaveValue("rendered");
  await expect(controls.first()).toBeFocused();
  await expect(details.first().locator(".ticket-comments strong")).toHaveText("Comment");
  await expect(details.first()).toContainText("<b>author</b>");
  await expect(details.locator("img, script, iframe, b")).toHaveCount(0);
  expect(external).toEqual([]);
});

test("ticket mode saves single-flight, rolls back failures and retries explicitly", async ({ page }) => {
  let mode = "rendered"; let writes = 0; let fail: "http" | "network" | null = "http";
  let release!: () => void;
  let pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/me/preferences", async route => {
    if (route.request().method() === "PATCH") {
      writes += 1; await pending;
      if (fail === "network") { await route.abort("failed"); return; }
      if (fail === "http") { await route.fulfill({ status: 503, json: { detail: { code: "preferences_corrupt" } } }); return; }
      mode = route.request().postDataJSON().ticket_body_mode;
    }
    await route.fulfill({ json: { language: "en", theme: "light", ticket_body_mode: mode } });
  });
  await signIn(page); await openBodies(page);
  const controls = page.locator(".ticket-detail").getByRole("combobox", { name: "Body display", exact: true });
  await controls.first().selectOption("source");
  await expect(controls.first()).toHaveAttribute("aria-disabled", "true");
  await controls.last().evaluate(el => { (el as HTMLSelectElement).value = "rendered"; el.dispatchEvent(new Event("change", { bubbles: true })); });
  expect(writes).toBe(1);
  release();
  await expect(controls.first()).toHaveValue("rendered");
  const error = page.locator(".main-content [role=alert], main [role=alert]").first();
  await expect(error).toContainText("Saved preferences cannot be read.");
  fail = "network"; pending = Promise.resolve();
  await controls.first().selectOption("source");
  await expect.poll(() => writes).toBe(2);
  await expect(controls.first()).toHaveValue("rendered");
  await expect(error).toContainText("The ADORE server cannot be reached. Check your connection.");
  fail = null;
  await controls.first().selectOption("source");
  await expect(controls.first()).toHaveAttribute("aria-disabled", "false");
  await expect.poll(() => writes).toBe(3);
  await page.reload(); await openBodies(page);
  await expect(page.getByRole("combobox", { name: "Body display", exact: true }).first()).toHaveValue("source");
});

test("ticket bodies contain wide content locally in both themes and widths", async ({ page }) => {
  const wide = "wide_".repeat(90);
  const source = `# Heading\n\n${"Readable prose ".repeat(100)}\n\nhttps://forge.invalid/${wide}\n\n\`\`\`\n${wide}\n\`\`\`\n\n| Wide | Other |\n| --- | --- |\n| ${wide} | cell |`;
  await page.route("**/api/v1/me/preferences", route => route.fulfill({ json: { language: "en", theme: "light", ticket_body_mode: route.request().method() === "PATCH" ? route.request().postDataJSON().ticket_body_mode : "rendered" } }));
  await page.route("**/api/v1/projects/*/tickets", async route => {
    const response = await route.fetch(); const list = await response.json();
    await route.fulfill({ response, json: { ...list, tickets: list.tickets.map((item: object) => ({ ...item, description: source })) } });
  });
  await signIn(page); await openBodies(page);
  for (const width of [1280, 360]) {
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ["light", "dark"]) {
      await page.evaluate(value => { document.documentElement.dataset.theme = value; }, theme);
      for (const mode of ["source", "rendered"]) {
        const control = page.locator(".ticket-detail select").first();
        await control.selectOption(mode);
        await expect(control).toHaveAttribute("aria-disabled", "false");
        await control.scrollIntoViewIfNeeded();
        await expect(control).toBeInViewport();
        await control.focus(); await expect(control).toBeFocused();
        const box = await control.boundingBox();
        expect(box!.width).toBeGreaterThan(100); expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.x + box!.width).toBeLessThanOrEqual(width);
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
        const region = page.locator(".ticket-detail").first().locator(".forge-scroll").first();
        const geometry = await region.evaluate(el => ({ scroll: el.scrollWidth, client: el.clientWidth, overflow: getComputedStyle(el).overflowX, color: getComputedStyle(el).color, background: getComputedStyle(el).backgroundColor }));
        expect(geometry.scroll).toBeGreaterThan(geometry.client);
        expect(geometry.overflow).toBe("auto");
        expect(geometry.color).not.toBe(geometry.background);
        expect(await control.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe("none");
      }
    }
  }
});

test("ticket mode persists through the real API across projects and browsers independently of accounts", async ({ page, browser }) => {
  await signIn(page); await openBodies(page);
  const select = () => page.getByRole("combobox", { name: "Body display", exact: true }).first();
  await select().selectOption("source");
  await expect(select()).toHaveAttribute("aria-disabled", "false");
  await openBodies(page, "beta"); await expect(select()).toHaveValue("source");
  await page.reload(); await openBodies(page); await expect(select()).toHaveValue("source");
  const fresh = await browser.newContext({ serviceWorkers: "block" });
  await fresh.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  try {
    const other = await fresh.newPage();
    await signIn(other); await openBodies(other);
    await expect(other.getByRole("combobox", { name: "Body display", exact: true }).first()).toHaveValue("source");
    await other.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
    await expect(other.getByLabel("Username", { exact: false })).toBeVisible();
    await signIn(other, "developer", "test-password"); await openBodies(other);
    await expect(other.getByRole("combobox", { name: "Body display", exact: true }).first()).toHaveValue("rendered");
    await select().selectOption("rendered");
    await expect(select()).toHaveAttribute("aria-disabled", "false");
    await page.reload(); await openBodies(page); await expect(select()).toHaveValue("rendered");
  } finally { await fresh.close(); }
});

test("late old-account ticket save cannot change the next account or its pending guard", async ({ page }) => {
  let release!: () => void; let seen!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const started = new Promise<void>(resolve => { seen = resolve; });
  await page.route("**/api/v1/me/preferences", async route => {
    if (route.request().method() === "PATCH") {
      seen(); await gate;
      await route.fulfill({ json: { language: "ro", theme: "dark", ticket_body_mode: "source" } });
    } else await route.continue();
  });
  await signIn(page); await openBodies(page);
  await page.getByRole("combobox", { name: "Body display", exact: true }).first().selectOption("source");
  await started;
  await page.getByRole("button", { name: "Sign out", exact: true }).filter({ visible: true }).click();
  // Keep the same App mounted: a document navigation would cancel the held fetch
  // and would only test browser cleanup, not the session-generation guard.
  await page.getByLabel("Username", { exact: false }).fill("developer");
  await page.getByLabel("Password", { exact: false }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Jobs", exact: true }).click();
  await page.getByRole("button", { name: "Read tickets", exact: true }).click();
  await page.locator("tr.ticket-row").filter({ hasText: "#21" }).getByRole("button", { name: "Details", exact: true }).click();
  const delivered = page.waitForResponse(response => response.url().endsWith("/me/preferences") && response.request().method() === "PATCH");
  release(); await delivered;
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page.getByRole("combobox", { name: "Body display", exact: true }).first()).toHaveValue("rendered");
  await expect(page.getByRole("combobox", { name: "Body display", exact: true }).first()).toHaveAttribute("aria-disabled", "false");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("ticket mode labels and help use all four locales without resetting source", async ({ page }) => {
  test.setTimeout(60_000);
  let language = "en", mode = "rendered";
  await page.route("**/api/v1/me/preferences", async route => {
    if (route.request().method() === "PATCH") {
      const update = route.request().postDataJSON();
      language = update.language ?? language; mode = update.ticket_body_mode ?? mode;
    }
    await route.fulfill({ json: { language, theme: "light", ticket_body_mode: mode } });
  });
  await signIn(page); await openBodies(page);
  await page.getByRole("combobox", { name: "Body display", exact: true }).first().selectOption("source");
  for (const [locale, read, details, label, rendered, source] of [
    ["en", "Read tickets", "Details", "Body display", "Rendered", "Markdown source"],
    ["fr", "Lire les tickets", "Détails", "Affichage du contenu", "Rendu", "Source Markdown"],
    ["de", "Tickets lesen", "Details", "Inhaltsanzeige", "Gerendert", "Markdown-Quelltext"],
    ["ro", "Citește tichetele", "Detalii", "Afișarea conținutului", "Randat", "Sursă Markdown"],
  ]) {
    await page.goto("/account");
    await page.locator("select").filter({ has: page.locator('option[value="en"]') }).selectOption(locale);
    await openBodies(page, "alpha", read, details);
    const control = page.getByRole("combobox", { name: label, exact: true }).first();
    await expect(control).toHaveValue("source");
    await expect(control.locator('option[value="rendered"]')).toHaveText(rendered);
    await expect(control.locator('option[value="source"]')).toHaveText(source);
    await control.selectOption("rendered"); await expect(control).toHaveAttribute("aria-disabled", "false");
    await control.selectOption("source"); await expect(control).toHaveAttribute("aria-disabled", "false");
    await page.goto("/help/tickets#reading-bodies");
    await expect(page.locator("#reading-bodies")).toBeVisible();
    await expect(page.locator(".help-article")).toContainText(source);
  }
});

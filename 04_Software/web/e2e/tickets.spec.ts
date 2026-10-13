/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}

test.beforeEach(async ({ context }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin ===
    "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

test("tickets sub-tab reads open tickets on request and controls them safely", async ({ page }) => {
  await signIn(page);
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const alpha = projects.find((row: { name: string }) => row.name === "alpha").id;
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
  await expect(readyDetail).toContainText("Please keep **bold** headers");
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

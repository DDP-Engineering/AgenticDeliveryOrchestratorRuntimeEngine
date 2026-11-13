/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page, context, request }) => {
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  expect((await request.post("/__e2e__/jobs", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".shell")).toBeVisible();
  const me = await (await page.request.get("/api/v1/me")).json();
  expect((await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: "en", theme: "light" } })).ok()).toBe(true);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
});
test.afterEach(async ({ page, request }) => {
  await page.goto("about:blank");
  expect((await request.post("/__e2e__/jobs?mode=reset", { headers: { "X-ADORE-E2E": "local-test" } })).ok()).toBe(true);
});

test("compact details keep filters on return and support keyboard evidence navigation", async ({ page }, info) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/jobs?project=alpha&view=jobs");
  await page.getByLabel("Search jobs", { exact: true }).fill("ux-clarification");
  await page.locator(".action-jobs-table tbody tr td:first-child a").click();
  const detail = page.locator(".job-details");
  await expect(page.locator("#job-search, .action-jobs-table")).toHaveCount(0);
  await expect(detail.locator(".job-detail-title h2")).toHaveText(/Ticket #42 · Actual clarification ticket/);
  const stage = await detail.locator(".job-detail-meta > span").first().boundingBox();
  const actions = await detail.locator(".job-actions summary").boundingBox();
  expect(Math.abs(stage!.y + stage!.height / 2 - actions!.y - actions!.height / 2)).toBeLessThan(5);
  await detail.getByRole("button", { name: "Read the question", exact: true }).click();
  const question = detail.getByRole("tab", { name: "Agent question", exact: true });
  await expect(question).toBeFocused();
  await expect(question).toHaveAttribute("aria-selected", "true");
  await expect(detail.getByRole("tabpanel", { name: "Agent question", exact: true })).toContainText("Which export format?");
  await page.keyboard.press("End");
  await expect(detail.getByRole("tab", { name: "Technical details", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(detail.getByRole("tab", { name: "Activity", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.screenshot({ path: info.outputPath("job-details-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await detail.getByRole("button", { name: "Read the question", exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
  await page.screenshot({ path: info.outputPath("job-details-mobile.png"), fullPage: true });
  await detail.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.getByLabel("Search jobs", { exact: true })).toHaveValue("ux-clarification");
  await expect(page.locator(".action-jobs-table tbody tr")).toHaveCount(1);
  // The project hub embeds the same workspace; its refresh must retain the selected evidence tab.
  await page.goto("/projects/alpha/jobs?run=ux-clarification");
  await detail.getByRole("button", { name: "Read the question", exact: true }).click();
  await expect(question).toHaveAttribute("aria-selected", "true");
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await expect(question).toHaveAttribute("aria-selected", "true");
});

test("question readability preserves original evidence and never activates untrusted content", async ({ page }) => {
  const source = '<!-- Copyright sample -->\n\n## Which format?\n\n```\n<!-- keep code literal -->\n```\n\n<script>window.questionSentinel=true</script>\n\n[unsafe](javascript:alert(1))\n\n![image](https://tracker.invalid/private.png)';
  await page.route("**/api/v1/jobs/*/ux-clarification", async route => {
    const response = await route.fetch(), data = await response.json();
    data.job.waiting.reason = source;
    await route.fulfill({ response, json: data });
  });
  await page.goto("/jobs?project=alpha&run=ux-clarification");
  const detail = page.locator(".job-details");
  await expect(detail.locator(".job-state")).not.toContainText("Which format?");
  await detail.getByRole("button", { name: "Read the question", exact: true }).click();
  const readable = detail.locator(".job-question .forge-markdown");
  await expect(readable).not.toContainText("Copyright sample");
  await expect(readable.getByRole("heading", { name: "Which format?" })).toBeVisible();
  await expect(readable.locator("code")).toHaveText("<!-- keep code literal -->\n");
  await expect(readable.locator("script, img, a[href^='javascript:']")).toHaveCount(0);
  await expect(readable).toContainText("<script>window.questionSentinel=true</script>");
  expect(await page.evaluate(() => Object.hasOwn(window, "questionSentinel"))).toBe(false);
  await detail.getByText("Original question and evidence", { exact: true }).click();
  await expect(detail.locator(".job-question .job-original pre")).toHaveText(source);
});

test("resuming a job removes the active question and its action without rewriting history", async ({ page }) => {
  let resumed = false;
  await page.route("**/api/v1/jobs/*/ux-clarification", async route => {
    const response = await route.fetch(), data = await response.json();
    if (resumed) {
      data.job.lifecycle = "working"; data.job.status_group = "active";
      data.job.waiting = { availability: "unknown", reason: null, next_action: null, responsible_role: null, responsible_person: null, evidence_url: null, source: null };
      data.job.timeline.push({ ts: "2026-11-12T15:05:42Z", event: "resumed", stage: "build" });
    }
    await route.fulfill({ response, json: data });
  });
  await page.goto("/jobs?project=alpha&run=ux-clarification");
  await page.getByRole("button", { name: "Read the question", exact: true }).click();
  resumed = true;
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  const detail = page.locator(".job-details");
  await expect(detail.locator(".job-state .status")).toContainText("Working");
  await expect(detail.getByRole("tab", { name: "Agent question", exact: true })).toHaveCount(0);
  await expect(detail.getByRole("link", { name: "Answer on the ticket", exact: false })).toHaveCount(0);
  await expect(detail).not.toContainText("Active question");
  await detail.getByRole("tab", { name: "Activity", exact: true }).click();
  await expect(detail.locator(".job-activity li").first()).toContainText("Work resumed");
  await expect(detail.locator(".job-activity")).toContainText("parked");
});

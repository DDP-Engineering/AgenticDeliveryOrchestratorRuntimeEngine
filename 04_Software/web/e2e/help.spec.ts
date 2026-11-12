/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { messages } from "../src/i18n";
import { workflowCopy } from "../src/readiness";

const title = (locale: string, topic: string) =>
  readFileSync(new URL(`../src/help/content/${locale}/${topic}.md`, import.meta.url), "utf8").split("\n")[0].replace(/^# /, "").trim();

async function signIn(page: Page, username = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(username);
  await page.getByLabel("Password", { exact: false }).fill(username === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}

const article = (page: Page) => page.locator(".help-article");

test("How ADORE works opens the help center with topics, outline, links and search", async ({ page }) => {
  await signIn(page);
  await page.locator(".topbar").getByRole("link", { name: "How ADORE works", exact: true }).click();
  await expect(page).toHaveURL(/\/help$/);
  await expect(article(page).locator(".help-title")).toHaveText(title("en", "overview"));
  const topics = page.getByRole("navigation", { name: "Help topics", exact: true });
  await expect(topics.getByRole("link")).toHaveCount(10);
  await topics.getByRole("link", { name: title("en", "tickets"), exact: true }).click();
  await expect(page).toHaveURL(/\/help\/tickets$/);
  await expect(article(page).locator(".help-title")).toHaveText(title("en", "tickets"));
  await expect(topics.getByRole("link", { name: title("en", "tickets"), exact: true })).toHaveAttribute("aria-current", "page");
  // The outline jumps to a section of the article.
  const outline = page.getByRole("navigation", { name: "On this page", exact: true });
  await outline.locator('a[href="#labels"]').click();
  await expect(page).toHaveURL(/\/help\/tickets#labels$/);
  await expect(page.locator("#labels")).toBeInViewport();
  // In-article links navigate inside the help center.
  await article(page).locator('a[href="/help/jobs"]').first().click();
  await expect(page).toHaveURL(/\/help\/jobs$/);
  await expect(article(page).locator(".help-title")).toHaveText(title("en", "jobs"));
  await page.goBack();
  await expect(article(page).locator(".help-title")).toHaveText(title("en", "tickets"));
  // Search narrows the topic list.
  const search = page.getByRole("searchbox", { name: "Search help", exact: true });
  await search.fill("agent-ready");
  await expect(topics.getByRole("link", { name: title("en", "tickets"), exact: true })).toBeVisible();
  await search.fill("zzzz-no-such-word");
  await expect(topics.getByRole("link")).toHaveCount(0);
  await expect(page.getByText("No topic matches your search.", { exact: true })).toBeVisible();
  await search.fill("");
  await expect(topics.getByRole("link")).toHaveCount(10);
  // Addresses survive a reload; the glossary keeps the delivery terms.
  await page.goto("/help/glossary");
  await expect(article(page).locator(".help-title")).toHaveText(title("en", "glossary"));
  await expect(article(page).getByRole("cell", { name: "Pickup stopped", exact: true })).toBeVisible();
  await expect(article(page)).toContainText("does not pause an active job");
  await page.goto("/help/no-such-topic");
  await expect(page).toHaveURL(/\/$/);
});

test("contextual help links open their topic in a new tab and keep the page", async ({ page }) => {
  await signIn(page);
  const alpha = (await (await page.request.get("/api/v1/projects")).json()).find((item: { name: string }) => item.name === "alpha").id;
  for (const [path, topic] of [[`/projects/${alpha}/jobs`, "tickets"], [`/projects/${alpha}/configuration`, "settings"], ["/projects/new", "projects"]]) {
    await page.goto(path);
    const link = page.getByRole("link", { name: `Help: ${title("en", topic)}`, exact: true });
    await expect(link, path).toHaveAttribute("href", `/help/${topic}`);
    await expect(link, path).toHaveAttribute("target", "_blank");
  }
  await page.goto(`/projects/${alpha}/jobs`);
  const [popup] = await Promise.all([page.waitForEvent("popup"), page.getByRole("link", { name: `Help: ${title("en", "tickets")}`, exact: true }).click()]);
  await expect(popup).toHaveURL(/\/help\/tickets$/);
  await expect(popup.locator(".help-article").locator(".help-title")).toHaveText(title("en", "tickets"));
  await expect(page).toHaveURL(new RegExp(`/projects/${alpha}/jobs$`));
  await popup.close();
});

for (const locale of ["en", "fr", "de", "ro"] as const) {
  test(`help describes both workflows and verification command in ${locale}`, async ({ page }) => {
    await signIn(page);
    const me = await (await page.request.get("/api/v1/me")).json();
    const headers = { "X-CSRF-Token": me.csrf };
    try {
      expect((await page.request.patch("/api/v1/me/preferences", { headers, data: { language: locale } })).ok()).toBe(true);
      await page.goto("/help/projects#workflows");
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.locator("#workflows")).toBeInViewport();
      for (const text of [workflowCopy[locale].aegis, workflowCopy[locale].direct, messages[locale].verificationCommand,
        messages[locale].aegisTestCommands]) await expect(article(page)).toContainText(text);
      await article(page).locator('a[href="/help/settings#verification-command"]').click();
      await expect(page.locator("#verification-command")).toBeInViewport();
      await expect(article(page)).toContainText("[workflow] verify_command");
      await expect(article(page)).toContainText("NUL");
      await page.goto("/help/glossary");
      await expect(article(page).getByRole("cell", { name: messages[locale].verificationCommand, exact: true })).toBeVisible();
      const direct = { en: "Direct workflow", fr: "Workflow direct", de: "Direkter Workflow", ro: "Flux direct" }[locale];
      await expect(article(page).getByRole("cell", { name: direct, exact: true })).toBeVisible();
      await page.goto("/help/tickets");
      await expect(article(page)).toContainText(".agentic/aegis.py");
      await article(page).locator('a[href="/help/projects#workflows"]').click();
      await expect(page.locator("#workflows")).toBeInViewport();
    } finally {
      await page.request.patch("/api/v1/me/preferences", { headers, data: { language: "en" } });
    }
  });
}

test("developers read help in their own language", async ({ page }) => {
  await signIn(page, "developer");
  await page.goto("/account");
  await page.getByLabel("Language", { exact: true }).selectOption("fr");
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  try {
    await page.locator(".topbar").getByRole("link", { name: "Comment fonctionne ADORE", exact: true }).click();
    await expect(article(page).locator(".help-title")).toHaveText(title("fr", "overview"));
    await page.getByRole("navigation", { name: "Rubriques d'aide", exact: true }).getByRole("link", { name: title("fr", "administration"), exact: true }).click();
    await expect(article(page).locator(".help-title")).toHaveText(title("fr", "administration"));
  } finally {
    await page.goto("/account");
    await page.getByLabel("Langue", { exact: true }).selectOption("en");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  }
});

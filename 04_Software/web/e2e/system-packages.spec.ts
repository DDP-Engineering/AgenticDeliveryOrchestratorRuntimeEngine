import {settingsSave,settingsImpact,discardSettings} from "./settings-actions";
import { test, expect } from "@playwright/test";

test("agent package permission reviews separately from network access", async ({ page }) => {
  await page.context().route("**/*", route =>
    new URL(route.request().url()).origin === "http://127.0.0.1:18765"
      ? route.continue() : route.abort());
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill("admin");
  await page.getByLabel("Password", { exact: false }).fill("admin");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const id = projects.find((project: { name: string }) => project.name === "alpha").id;
  const before = await (await page.request.get(`/api/v1/projects/${id}/config`)).json();
  await page.goto(`/projects/${id}/configuration`);
  await page.getByText(/^Agent and model \(\d+\)$/).click();
  const row = page.locator('[id="setting-container.system_packages"]');
  await expect(row).toContainText("Network access is separate");
  await row.getByRole("button", { name: "Edit Allow agent environment administration" }).click();
  await row.getByRole("combobox").selectOption("true");
  await settingsSave(page).click();
  await expect(settingsImpact(page)).toContainText(
    "Allow agent environment administration");
  const pending = await (await page.request.get(`/api/v1/projects/${id}/config/pending`)).json();
  expect(pending).toBeNull();
  await expect(settingsImpact(page)).toContainText("true");
  const current = await (await page.request.get(`/api/v1/projects/${id}/config`)).json();
  expect(current.config.container.egress).toEqual(before.config.container.egress);
  await discardSettings(page);
});

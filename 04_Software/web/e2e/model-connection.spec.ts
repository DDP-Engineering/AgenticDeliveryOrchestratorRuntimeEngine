/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect } from "@playwright/test";

for (const invalid of [false, true]) {
 test(`explicit AI model test ${invalid ? "rejects stale evidence" : "shows scoped response"}`, async ({ page }) => {
  await page.context().route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/");
  await page.getByLabel("Username", {exact:false}).fill("admin");
  await page.getByLabel("Password", {exact:false}).fill("admin");
  await page.getByRole("button", {name:"Sign in", exact:true}).click();
  await page.getByRole("navigation", {name:"Primary navigation",exact:true}).getByRole("link", {name:"Projects",exact:true}).click();
  await page.getByRole("link", {name:"alpha",exact:true}).click();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const project = projects.find((p: {name:string}) => p.name === "alpha");
  const configuration = await (await page.request.get(`/api/v1/projects/${project.id}/config`)).json();
  let calls = 0;
  await page.route("**/model-connection-test", async route => {
   calls++;
   await route.fulfill({json:{project_id:project.id, revision:invalid ? "0".repeat(64) : configuration.revision, checked_at:new Date().toISOString(), executor:"opencode", model:configuration.config.executor.commands.opencode.model, ready:true, reason:"ready"}});
  });
  const button = page.getByRole("button", {name:"Test AI connection",exact:true});
  await expect(button).toBeVisible();
  await expect(page.getByText(/Provider charges may apply/)).toBeVisible();
  expect(calls).toBe(0);
  await button.click();
  await expect(page.getByText(invalid ? "The test could not complete. Check that the project is idle and its settings are valid." : "AI model connected", {exact:true})).toBeVisible();
  expect(calls).toBe(1);
 });
}

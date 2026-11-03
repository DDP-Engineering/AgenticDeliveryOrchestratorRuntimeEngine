/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect,type Page} from "@playwright/test";
import {localCopy} from "../src/localExecution";

async function enter(page:Page) {
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");
 await page.getByLabel("Username",{exact:false}).fill("admin");
 await page.getByLabel("Password",{exact:false}).fill("admin");
 await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
 await page.goto("/projects/new");
 await page.getByLabel("Repository URL",{exact:false}).fill("ssh://git@forge.e2e.invalid:2222/team/local-executors.git");
 await page.getByRole("button",{name:"Read repository",exact:true}).click();
 await page.getByRole("button",{name:"Continue",exact:true}).click();
 await page.getByLabel("Runs in",{exact:false}).selectOption("local");
}

test("native enrollment offers the project tools PATH without discovering executables", async ({page}) => {
 let discoveryRequests = 0;
 await page.route("**/api/v1/local-executors", route => {
  discoveryRequests++;
  return route.fulfill({status: 503, json: {}});
 });
 await enter(page);
 const path = page.getByLabel(localCopy.en.path, {exact: true});
 await expect(path).toBeVisible();
 await expect(page.getByText(localCopy.en.agentFix, {exact: false})).toBeVisible();
 await path.fill("C:/Project Tools;C:/Git/bin");
 await expect(path).toHaveValue("C:/Project Tools;C:/Git/bin");
 await expect(page.locator("#enroll-executor_command")).toHaveCount(0);
 await expect(page.locator("#enroll-local_home")).toHaveCount(0);
 await expect(page.locator("#enroll-local_cgroup_root")).toHaveCount(0);
 expect(discoveryRequests).toBe(0);
});

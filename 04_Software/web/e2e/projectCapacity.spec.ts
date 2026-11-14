/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect,type Page} from "@playwright/test";
import {settingsSave,discardSettings} from "./settings-actions";
import {workerCopy} from "../src/projectStatus";
import type {Locale} from "../src/i18n";
import {jobCopy} from "../src/jobCopy";

async function login(page:Page) {
  await page.goto("/");
  await page.getByLabel("Username",{exact:false}).fill("admin");
  await page.getByLabel("Password",{exact:false}).fill("admin");
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
  return await (await page.request.get("/api/v1/projects")).json() as Array<{id:string;name:string;display_name:string}>;
}
async function settings(page:Page,id:string) {
  await page.goto(`/projects/${id}/configuration`);
  await expect(page.locator("#project-settings")).toBeVisible();
  for(const purpose of ["implementation","executor"])await page.locator(`[data-setting-purpose="${purpose}"] > summary`).click();
}
test.beforeEach(async({context})=>{
  await context.route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort("blockedbyclient"));
});
test.afterEach(async({page})=>{
  const me=await page.request.get("/api/v1/me");if(me.ok()){
    const session=await me.json();await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":session.csrf},data:{language:"en",theme:"light"}});
  }
});

test("drafts and invalid limits survive project navigation, refresh and stale revisions",async({page})=>{
  const projects=await login(page), a=projects.find(p=>p.name==="alpha")!,b=projects.find(p=>p.name==="beta")!;
  await settings(page,a.id);
  const n=page.locator('[id="setting-polling.max_concurrent_runs"]');
  await n.getByRole("button").click();await n.getByRole("spinbutton").fill("0");
  await expect(settingsSave(page)).toBeDisabled();
  await n.getByRole("spinbutton").fill("3");
  const runtime=page.locator('[id="setting-container.runtime"]');await runtime.getByRole("button").click();
  await runtime.getByRole("combobox").selectOption("");
  await runtime.getByRole("textbox").fill("podman");
  await expect(settingsSave(page)).toBeEnabled();
  await settings(page,b.id);
  await expect(page.locator('[id="setting-polling.max_concurrent_runs"]')).toContainText("1");
  await expect(page.locator(".settings-save-bar")).toHaveCount(0);
  await page.reload();await expect(page.locator("#project-settings")).toBeVisible();
  await settings(page,a.id);
  await expect(n.getByRole("spinbutton")).toHaveValue("3");
  await expect(runtime.getByRole("textbox")).toHaveValue("podman");
  await page.reload();await expect(page.locator("#project-settings")).toBeVisible();
  await page.locator('[data-setting-purpose="implementation"] > summary').click();
  await expect(n.getByRole("spinbutton")).toHaveValue("3");
  await page.route(`**/api/v1/projects/${a.id}/config`,async route=>{
    const response=await route.fetch();const value=await response.json();value.revision="c".repeat(64);await route.fulfill({json:value});
  });
  await page.reload();
  await expect(page.locator(".settings-save-bar")).toContainText("Settings changed on the server");
  await expect(settingsSave(page)).toBeDisabled();
  await discardSettings(page);
});

test("capacity and durable operation feedback stay local through reload in all locales",async({page},info)=>{
  const projects=await login(page),a=projects.find(p=>p.name==="alpha")!,b=projects.find(p=>p.name==="beta")!;
  let status="pending";
  await page.route("**/api/v1/projects/*/capacity",async route=>{
    const id=new URL(route.request().url()).pathname.split("/").at(-2)!;
    const busy=id===a.id;
    await route.fulfill({json:{project_id:id,active_limit:busy?2:1,limit:1,occupied:busy?2:0,free:busy?0:1,waiting_jobs:busy?1:0,available:!busy,
      worker:{role:"project",project_id:id,run_id:"",heartbeat:busy?"missing":"recent",activity:busy?"unknown":"idle",updated_at:busy?null:"2026-11-14T01:00:00+00:00"},
      waiting_runs:[],queue:busy?[{id:901,action:"start",reason:"worker_unavailable"}]:[],staged_change:busy,staged_limit:busy?1:null,
      recent_operations:busy?[{id:901,action:"start",status,result:"",reason:status==="failed"?"at_capacity":""}]:[]}});
  });
  for(const locale of ["en","fr","de","ro"] as Locale[]){
    const me=await(await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":me.csrf},data:{language:locale,theme:locale==="de"?"dark":"light"}});
    await page.goto(`/projects/${a.id}`);
    const card=page.getByRole("region",{name:workerCopy[locale].capacity});
    await expect(card).toContainText(workerCopy[locale].worker_unavailable);
    await expect(card).toContainText(workerCopy[locale].pending);
    await page.reload();await expect(card.locator('[data-operation-id="901"]')).toContainText(workerCopy[locale].pending);
    await page.screenshot({path:info.outputPath(`capacity-${locale}.png`),fullPage:true});
    await page.goto(`/projects/${b.id}`);
    await expect(page.getByRole("region",{name:workerCopy[locale].capacity})).toContainText(workerCopy[locale].recent);
    await expect(page.locator('[data-operation-id="901"]')).toHaveCount(0);
    await expect(page.getByRole("button",{name:jobCopy[locale].startPickup,exact:true})).toBeEnabled();
  }
  status="failed";await page.goto(`/projects/${a.id}`);
  await expect(page.locator('[data-operation-id="901"]')).toContainText(workerCopy.ro.failed);
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:info.outputPath("capacity-mobile.png"),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

test("System status separates server and project roles",async({page})=>{
  await login(page);await page.goto("/admin/status");
  const roles=page.locator(".worker-roles");
  await expect(roles).toContainText("Supervisor");
  await expect(roles).toContainText("Configuration worker");
  await expect(roles).toContainText("Project worker");
  await expect(roles).toContainText("activity and free slots are separate");
});

test("staged increases and unrelated settings never claim a reduced admission limit",async({page})=>{
  test.setTimeout(60_000);
  const projects=await login(page),a=projects.find(p=>p.name==="alpha")!;
  let proposed=2;
  await page.route(`**/api/v1/projects/${a.id}/capacity`,async route=>{
    const value=await(await route.fetch()).json();
    await route.fulfill({json:{...value,active_limit:2,limit:Math.min(2,proposed),occupied:0,free:Math.min(2,proposed),staged_change:true,staged_limit:proposed}});
  });
  for(const locale of ["en","fr","de","ro"] as Locale[]){
    const me=await(await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":me.csrf},data:{language:locale}});
    for(const limit of [3,2,1]){
      proposed=limit;await page.goto(`/projects/${a.id}`);
      const card=page.getByRole("region",{name:workerCopy[locale].capacity});
      await expect(card).toContainText(workerCopy[locale].staged);
      if(limit<2)await expect(card).toContainText(workerCopy[locale].stagedLower);
      else await expect(card).not.toContainText(workerCopy[locale].stagedLower);
    }
  }
});

test("credential-bearing endpoint drafts remain only in memory",async({page})=>{
  const projects=await login(page),a=projects.find(p=>p.name==="alpha")!;
  await settings(page,a.id);
  await page.locator('[id="setting-executor.model"]').getByRole("button").click();
  const connection=page.locator(".connection-editor");
  await connection.getByRole("combobox",{name:"Provider",exact:true}).selectOption("custom");
  await connection.getByRole("textbox",{name:"Model",exact:true}).fill("retention-model");
  await connection.getByRole("textbox",{name:"Endpoint base URL",exact:true}).fill("http://user:private-password@host/v1");
  await expect(page.locator(".settings-save-bar")).toContainText("Your draft could not be retained");
  const retained=await page.evaluate(()=>Object.values(sessionStorage).join("\n"));
  expect(retained).not.toContain("private-password");
  await expect(settingsSave(page)).toBeDisabled();
  await discardSettings(page);
});

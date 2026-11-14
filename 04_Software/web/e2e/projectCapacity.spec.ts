/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect,type Page} from "@playwright/test";
import {settingsSave,discardSettings} from "./settings-actions";
import {capacityCopy} from "../src/projectStatus";
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

test("Settings Statistics History and Access omit redundant capacity in every locale",async({page})=>{
  const projects=await login(page),a=projects.find(p=>p.name==="alpha")!;
  for(const locale of ["en","fr","de","ro"] as Locale[]){
    const me=await(await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":me.csrf},data:{language:locale,theme:"light"}});
    for(const tab of ["configuration","statistics","history","access"]){
      await page.goto(`/projects/${a.id}/${tab}`);
      await expect(page.locator("#project-tab-panel")).toBeVisible();
      await expect(page.locator(".project-capacity")).toHaveCount(0);
      await expect(page.locator("[data-capacity-fact]")).toHaveCount(0);
    }
  }
});

test("System status separates server and project roles",async({page})=>{
  await login(page);await page.goto("/admin/status");
  const roles=page.locator(".worker-roles");
  await expect(roles).toContainText("Supervisor");
  await expect(roles).toContainText("Configuration worker");
  await expect(roles).toContainText("Project worker");
  await expect(roles).toContainText("activity and free slots are separate");
});

test("Summary compact capacity reflects the effective staged admission limit",async({page})=>{
  const projects=await login(page),a=projects.find(p=>p.name==="alpha")!;
  let proposed=2;
  await page.route(`**/api/v1/projects/${a.id}/capacity`,async route=>{
    const value=await(await route.fetch()).json();
    await route.fulfill({json:{...value,active_limit:2,limit:Math.min(2,proposed),occupied:0,free:Math.min(2,proposed),staged_change:true,staged_limit:proposed}});
  });
  for(const limit of [3,2,1]){
    proposed=limit;await page.goto(`/projects/${a.id}`);
    await expect(page.locator('[data-capacity-fact="limit"] dd')).toHaveText(String(Math.min(2,limit)));
    await expect(page.locator(".project-capacity")).toHaveCount(0);
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


function capacityRow(id:string) {
  return {project_id:id,active_limit:2,limit:2,occupied:1,free:1,waiting_jobs:3,available:true,
    worker:{role:"project",project_id:id,run_id:"",heartbeat:"recent",activity:"busy",updated_at:"2026-11-14T01:00:00+00:00"},
    paused:false,job_counts:{working:1,publishing:0,"parked-clarification":2,"awaiting-approval":0,"in-review":0,"handoff-pending":0},
    waiting_runs:[],queue:[],staged_change:false,staged_limit:null,
    recent_operations:[{id:901,action:"start",status:"succeeded",result:"historical-operation-marker",reason:""}]};
}

test("Summary folds only three capacity facts into two rows",async({page},info)=>{
  const projects=await login(page),a=projects.find(item=>item.name==="alpha")!;
  await page.route(`**/api/v1/projects/${a.id}/capacity`,route=>route.fulfill({json:capacityRow(a.id)}));
  await page.setViewportSize({width:1560,height:1000});
  await page.goto(`/projects/${a.id}`);
  const summary=page.locator(".project-summary"),facts=summary.locator(".summary-fact");
  await expect(facts).toHaveCount(10);
  await expect(summary.locator('[data-capacity-fact="limit"]')).toHaveText("Parallel job limit2");
  await expect(summary.locator('[data-capacity-fact="free"]')).toHaveText("Free1");
  await expect(summary.locator('[data-capacity-fact="queued"]')).toHaveText("Queued jobs3");
  await expect(page.locator(".project-capacity")).toHaveCount(0);
  await expect(summary).not.toContainText("historical-operation-marker");
  const tops=await facts.evaluateAll(items=>items.map(item=>Math.round(item.getBoundingClientRect().top)));
  expect(new Set(tops).size).toBe(2);
  await page.screenshot({path:info.outputPath("summary-capacity-compact.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

test("Capacity is a paginated current-state table, separate from Tickets and Jobs",async({page},info)=>{
  test.setTimeout(90_000);
  const projects=await login(page),template=projects.find(item=>item.name==="alpha")!;
  const rows=Array.from({length:12},(_,index)=>({...template,id:(index+1).toString(16).padStart(32,"0"),name:`capacity-${index+1}`,display_name:`Project ${String(index+1).padStart(2,"0")}`,archived:false}));
  await page.route("**/api/v1/projects",route=>route.fulfill({json:rows}));
  await page.route("**/api/v1/projects/*/capacity",route=>{
    const id=new URL(route.request().url()).pathname.split("/").at(-2)!;
    return route.fulfill(id===rows[2].id?{status:503,json:{detail:{code:"project_capacity_unavailable"}}}:{json:{...capacityRow(id),paused:id===rows[1].id}});
  });
  for(const locale of ["en","fr","de","ro"] as Locale[]){
    const me=await(await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":me.csrf},data:{language:locale}});
    await page.goto("/jobs?view=capacity");
    const panel=page.getByRole("region",{name:capacityCopy[locale].tab,exact:true});
    await expect(page.getByRole("tab",{name:capacityCopy[locale].tab,exact:true})).toHaveAttribute("aria-selected","true");
    await expect(panel.locator("tbody tr")).toHaveCount(10);
    await expect(panel.locator("tbody tr").first()).toContainText("1 ·");
    await expect(panel.locator("tbody tr").nth(1)).toContainText(jobCopy[locale].pickupStopped);
    await expect(panel.locator("tbody tr").nth(2).getByRole("alert")).toBeVisible();
    await expect(panel.locator("tbody tr").nth(2).locator("td").first()).toHaveText("—");
    await expect(panel).not.toContainText("historical-operation-marker");
    await expect(page.locator(".project-capacity,.project-operations")).toHaveCount(0);
    const next=panel.locator(".page-controls button").last();await next.click();
    await expect(panel.locator("tbody tr")).toHaveCount(2);
    await panel.locator(".page-controls select").selectOption("25");
    await expect(panel.locator("tbody tr")).toHaveCount(12);
    await page.screenshot({path:info.outputPath(`capacity-table-${locale}.png`),fullPage:true});
    await page.reload();await expect(page.getByRole("tab",{name:capacityCopy[locale].tab,exact:true})).toHaveAttribute("aria-selected","true");
  }
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:info.outputPath("capacity-table-mobile.png"),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.locator("#jobs-subtab-jobs").click();
  await expect(page.locator(".project-capacity,.capacity-table")).toHaveCount(0);
  await page.locator("#jobs-subtab-tickets").click();
  await expect(page.locator(".project-capacity,.capacity-table")).toHaveCount(0);
  await page.locator("#jobs-subtab-tickets").press("End");
  await expect(page.locator("#jobs-subtab-capacity")).toHaveAttribute("aria-selected","true");
});

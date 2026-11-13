/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test, expect} from "@playwright/test";
import {discardSettings,settingsImpact,settingsSave} from "./settings-actions";

test("one Save commits several ordinary setting edits without an impact dialog", async ({page}) => {
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");
 await page.getByLabel("Username",{exact:false}).fill("admin");
 await page.getByLabel("Password",{exact:false}).fill("admin");
 await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();
 const id=projects.find((item:{name:string})=>item.name==="alpha").id;
 const endpoint="/api/v1/projects/"+id+"/config";
 const before=await(await page.request.get(endpoint)).json();
 const keys=["polling.poll_interval_seconds","polling.poll_jitter_seconds"];
 try {
  await page.goto("/projects/"+id+"/configuration");
  const bar=page.locator(".settings-save-bar");
  await expect(bar).toHaveCount(0);
  await page.locator('[data-setting-purpose="tickets"] > summary').click();
  for(const [index,key] of keys.entries()){
   const row=page.locator('[id="setting-'+key+'"]');
   await row.getByRole("button",{name:/^Edit /}).click();
   if(index===0){
    await expect(bar).toHaveCount(0);
    const unchanged=await row.getByRole("spinbutton").inputValue();
    await row.getByRole("spinbutton").fill(String(Number(unchanged)+1));
    await expect(bar).toBeVisible();
    await row.getByRole("spinbutton").fill(unchanged);
    await expect(bar).toHaveCount(0);
   }
   await row.getByRole("spinbutton").fill(String(index===0?75:7));
  }
  await expect(page.getByRole("button",{name:"Prepare candidate",exact:true})).toHaveCount(0);
  await expect(bar.getByRole("button",{name:"Save",exact:true})).toBeEnabled();
  await bar.getByRole("button",{name:"Save",exact:true}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect.poll(async()=>{const c=await(await page.request.get(endpoint)).json();return [c.config.polling.poll_interval_seconds,c.config.polling.poll_jitter_seconds];}).toEqual([75,7]);
  await expect(bar).toHaveCount(0);
 } finally {
  const me=await(await page.request.get("/api/v1/me")).json();
  const headers={"X-CSRF-Token":me.csrf};
  await page.request.delete(endpoint+"/pending",{headers});
  const current=await(await page.request.get(endpoint)).json();
  const staged=await page.request.post(endpoint+"/pending",{headers,data:{key:"settings.batch",revision:current.revision,value:JSON.stringify(keys.map(key=>({key,value:String(before.config.polling[key.split(".")[1]])})))}});
  if(staged.ok()){const c=await staged.json();await page.request.post(endpoint+"/apply",{headers,data:{base_revision:c.base_revision,candidate_revision:c.candidate_revision}});}
 }
});

test("important multi-setting Save confirms exact values and keeps cancelled edits",async({page})=>{
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");
 await page.getByLabel("Username",{exact:false}).fill("admin");
 await page.getByLabel("Password",{exact:false}).fill("admin");
 await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();
 const id=projects.find((item:{name:string})=>item.name==="alpha").id;
 const endpoint="/api/v1/projects/"+id+"/config";
 const before=await(await page.request.get(endpoint)).json();
 try {
  await page.goto("/projects/"+id+"/configuration");
  await page.locator('[data-setting-purpose="implementation"] > summary').click();
  const row=page.locator('[id="setting-budgets.max_iterations"]');
  await row.getByRole("button",{name:/^Edit /}).click();
  await row.getByRole("spinbutton").fill(String(before.config.budgets.max_iterations+1));
  await settingsSave(page).click();
  await expect(settingsImpact(page)).toBeVisible();
  await expect(settingsImpact(page)).toContainText("Maximum executor launches per job");
  expect((await(await page.request.get(endpoint)).json()).revision).toBe(before.revision);
  await settingsImpact(page).getByRole("button",{name:"Keep editing",exact:true}).click();
  await expect(settingsImpact(page)).toHaveCount(0);
  expect(await(await page.request.get(endpoint+"/pending")).json()).toBeNull();
  await expect(row.getByRole("spinbutton")).toHaveValue(String(before.config.budgets.max_iterations+1));
  await expect(settingsSave(page)).toBeEnabled();
  await settingsSave(page).click();
  await settingsImpact(page).getByRole("button",{name:"Save changes",exact:true}).click();
  await expect(page.locator(".settings-save-bar")).toHaveCount(0);
  expect((await(await page.request.get(endpoint)).json()).config.budgets.max_iterations).toBe(before.config.budgets.max_iterations+1);
 } finally {
  if(await settingsImpact(page).count()) await settingsImpact(page).getByRole("button",{name:"Keep editing",exact:true}).click();
  if(await page.locator(".settings-save-bar").count() && await settingsSave(page).isEnabled())await discardSettings(page);
  const me=await(await page.request.get("/api/v1/me")).json();
  const headers={"X-CSRF-Token":me.csrf};
  await page.request.delete(endpoint+"/pending",{headers});
  const current=await(await page.request.get(endpoint)).json();
  const staged=await page.request.post(endpoint+"/pending",{headers,data:{key:"budgets.max_iterations",revision:current.revision,value:String(before.config.budgets.max_iterations)}});
  if(staged.ok()){const c=await staged.json();await page.request.post(endpoint+"/apply",{headers,data:{base_revision:c.base_revision,candidate_revision:c.candidate_revision}});}
 }
});


test("dirty settings guard navigation and background refresh without losing invalid inputs",async({page})=>{
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 await page.goto(`/projects/${id}/configuration`);await page.locator('[data-setting-purpose="implementation"] > summary').click();
 const row=page.locator('[id="setting-budgets.max_iterations"]');await row.getByRole("button").click();await row.getByRole("spinbutton").fill("");
 const url=page.url();let prompts=0;
 page.on("dialog",async dialog=>{prompts++;expect(dialog.type()).toBe("confirm");await dialog.dismiss();});
 await page.getByRole("tab",{name:"Summary",exact:true}).click();await expect(page).toHaveURL(url);
 let reads=0;
 page.on("request", request=>{if(request.method()==="GET"&&request.url().endsWith("/config"))reads++;});
 const projectPoll=page.waitForResponse(response=>response.url().endsWith("/api/v1/projects"));
 await page.evaluate(()=>document.dispatchEvent(new Event("visibilitychange")));
 await projectPoll;
 await expect(row.getByRole("spinbutton")).toHaveValue("");await expect(settingsSave(page)).toBeDisabled();
 expect(reads).toBe(0);expect(prompts).toBe(1);
 await discardSettings(page);await page.getByRole("tab",{name:"Summary",exact:true}).click();await expect(page).not.toHaveURL(url);
});

test("a mismatched important preview cannot prepare or apply settings and remains retryable",async({page})=>{
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 const endpoint=`/api/v1/projects/${id}/config`;const before=await(await page.request.get(endpoint)).json();
 let writes=0;page.on("request",r=>{if(r.method()==="POST" && /config\/(pending|apply)$/.test(r.url()))writes++;});
 await page.goto(`/projects/${id}/configuration`);await page.locator('[data-setting-purpose="implementation"] > summary').click();
 const row=page.locator('[id="setting-budgets.max_iterations"]');await row.getByRole("button").click();await row.getByRole("spinbutton").fill(String(before.config.budgets.max_iterations+1));
 await page.route("**/config/preview",async route=>{const response=await route.fetch();const body=await response.json();body.proposed_value["budgets.max_iterations"]=999;body.value=JSON.stringify(body.proposed_value);await route.fulfill({response,json:body});});
 await settingsSave(page).click();await expect(page.getByRole("alert").first()).toBeVisible();await expect(settingsImpact(page)).toHaveCount(0);await expect(settingsSave(page)).toBeEnabled();
 await expect(row.getByRole("spinbutton")).toHaveValue(String(before.config.budgets.max_iterations+1));expect(writes).toBe(0);expect((await(await page.request.get(endpoint)).json()).revision).toBe(before.revision);
 await page.unroute("**/config/preview");await settingsSave(page).click();await expect(settingsImpact(page)).toBeVisible();await discardSettings(page);
 expect(await(await page.request.get(endpoint+"/pending")).json()).toBeNull();
});


test("recovered pending settings display their values and save as one bound batch",async({page})=>{
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 const endpoint=`/api/v1/projects/${id}/config`;const before=await(await page.request.get(endpoint)).json();
 const me=await(await page.request.get("/api/v1/me")).json();const headers={"X-CSRF-Token":me.csrf};
 const keys=["polling.poll_interval_seconds","polling.poll_jitter_seconds"],values=[82,8];
 try {
  const prepared=await page.request.post(endpoint+"/pending",{headers,data:{key:"settings.batch",revision:before.revision,value:JSON.stringify(keys.map((key,i)=>({key,value:String(values[i])})))}});expect(prepared.ok()).toBe(true);const pending=await prepared.json();
  await page.goto(`/projects/${id}/configuration`);await page.locator('[data-setting-purpose="tickets"] > summary').click();
  for(const [i,key] of keys.entries()) await expect(page.locator('[id="setting-'+key+'"]').getByRole("spinbutton")).toHaveValue(String(values[i]));
  const replacement=page.waitForRequest(r=>r.method()==="POST"&&r.url().endsWith("/config/pending"));
  await settingsSave(page).click();expect((await replacement).postDataJSON().pending_revision).toBe(pending.candidate_revision);
  await expect(page.locator(".settings-save-bar")).toHaveCount(0);
  const current=await(await page.request.get(endpoint)).json();expect(keys.map(k=>current.config.polling[k.split(".")[1]])).toEqual(values);
 } finally {
  await page.request.delete(endpoint+"/pending",{headers});const current=await(await page.request.get(endpoint)).json();
  const restore=await page.request.post(endpoint+"/pending",{headers,data:{key:"settings.batch",revision:current.revision,value:JSON.stringify(keys.map(key=>({key,value:String(before.config.polling[key.split(".")[1]])})))}});
  if(restore.ok()){const c=await restore.json();await page.request.post(endpoint+"/apply",{headers,data:{base_revision:c.base_revision,candidate_revision:c.candidate_revision}});}
 }
});


for(const outcome of ["saved","stale","corrupt"] as const){
 test(`API-only pending settings recover through exact Save: ${outcome}`,async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
  const endpoint=`/api/v1/projects/${id}/config`;const before=await(await page.request.get(endpoint)).json();const me=await(await page.request.get("/api/v1/me")).json();const headers={"X-CSRF-Token":me.csrf};
  const value="recovered-test-agent";
  try {
   const prepared=await page.request.post(endpoint+"/pending",{headers,data:{key:"agent.slug",value,revision:before.revision}});expect(prepared.ok()).toBe(true);const pending=await prepared.json();
   await page.goto(`/projects/${id}`);await page.getByRole("tab",{name:"Settings",exact:true}).click();await page.locator('[data-setting-purpose="technical"] > summary').click();
   await expect(page.locator('[id="setting-agent.slug"]').getByRole("button",{name:/^Edit /})).toHaveCount(0);
   await expect(settingsSave(page)).toBeEnabled();
   let writes=0;page.on("request",r=>{if(r.method()==="POST"&&/config\/(pending|apply)$/.test(r.url()))writes++;});
   if(outcome==="corrupt") await page.route("**/config/pending",route=>route.request().method()==="GET"?route.fulfill({status:503,json:{detail:{code:"pending_config_corrupt"}}}):route.continue());
   if(outcome==="stale") await page.route("**/config/apply",route=>route.fulfill({status:409,json:{detail:{code:"stale_config_revision"}}}));
   await settingsSave(page).click();
   if(outcome==="corrupt"){
    await expect(page.getByRole("alert").first()).toBeVisible();await expect(settingsImpact(page)).toHaveCount(0);await expect(settingsSave(page)).toBeDisabled();expect(writes).toBe(0);
   } else {
    await expect(settingsImpact(page)).toContainText(value);expect(writes).toBe(0);
    if(outcome==="saved"){
     const url=page.url();await page.goBack();await expect(page).toHaveURL(url);await expect(settingsImpact(page)).toBeVisible();expect(writes).toBe(0);
     await settingsImpact(page).getByRole("button",{name:"Keep editing",exact:true}).click();await expect(settingsSave(page)).toBeEnabled();
     await settingsSave(page).click();await expect(settingsImpact(page)).toContainText(value);expect(writes).toBe(0);
    }
    const applied=page.waitForRequest(r=>r.method()==="POST"&&r.url().endsWith("/config/apply"));
    await settingsImpact(page).getByRole("button",{name:"Save changes",exact:true}).click();
    expect((await applied).postDataJSON()).toEqual({base_revision:pending.base_revision,candidate_revision:pending.candidate_revision});
    if(outcome==="saved") await expect(page.locator(".settings-save-bar")).toHaveCount(0);
    else await expect(settingsSave(page)).toBeDisabled();
    expect(writes).toBe(1);
   }
   const current=await(await page.request.get(endpoint)).json();expect(current.config.agent.slug).toBe(outcome==="saved"?value:before.config.agent.slug);
  } finally {
   await page.unroute("**/config/pending");await page.unroute("**/config/apply");
   await page.request.delete(endpoint+"/pending",{headers});const current=await(await page.request.get(endpoint)).json();
   const restore=await page.request.post(endpoint+"/pending",{headers,data:{key:"agent.slug",value:before.config.agent.slug,revision:current.revision}});
   if(restore.ok()){const c=await restore.json();await page.request.post(endpoint+"/apply",{headers,data:{base_revision:c.base_revision,candidate_revision:c.candidate_revision}});}
  }
 });
}

test("mobile Settings heading remains readable above raw configuration actions",async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Overview",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 await page.goto(`/projects/${id}/configuration`);const heading=await page.getByRole("heading",{name:"Project settings",exact:true}).boundingBox();const action=await page.getByRole("button",{name:"Preview raw configuration",exact:true}).boundingBox();
 expect(heading!.width).toBeGreaterThan(100);expect(heading!.height).toBeLessThan(30);expect(action!.y).toBeGreaterThanOrEqual(heading!.y+heading!.height);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
});

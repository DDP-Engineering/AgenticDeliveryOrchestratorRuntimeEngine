/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect,type Page} from "@playwright/test";
import {discoveryCopy} from "../src/localExecutors";
import {enrollmentCopy} from "../src/enrollmentCopy";

const command = '"C:/Installed/OpenCode/opencode.exe" run --dir {worktree} -m {model} --format json {prompt}';
const piCommand = '"C:/Node/node.exe" "C:/npm/pi/cli.js" -p --mode json --model {model} {prompt}';
const discovery = {system:"Windows",machine:"test-host",account:"test-user",executors:[
 {agent:"opencode",installations:[{executable:"C:/Installed/OpenCode/opencode.exe",entrypoint:null,source:"npm",command}]},
 {agent:"pi",installations:[{executable:"C:/Node/node.exe",entrypoint:"C:/npm/pi/cli.js",source:"npm",command:piCommand}]},
 {agent:"codex",installations:[]},{agent:"qwen",installations:[]},
]};

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

test("local enrollment prefills npm launches, switches agents and preserves manual commands",async({page})=>{
 await page.route("**/api/v1/local-executors",route=>route.fulfill({json:discovery}));
 await enter(page);
 const argv=page.locator("#enroll-executor_command");
 await expect(argv).not.toBeVisible();
 await expect(page.locator("#enroll-local_account")).toHaveCount(0);
 await expect(page.locator("#enroll-local_home")).not.toBeVisible();
 await expect(page.getByRole("button",{name:discoveryCopy.en.refresh,exact:true})).not.toBeVisible();
 await expect(page.locator(".local-executor-picker").getByText(/test-user.*test-host/)).toBeVisible();
 await page.screenshot({path:"test-results/simple-local-setup-windows.png",fullPage:true});
 await page.locator(".local-executor-advanced > summary").click();
 await expect(argv).toHaveValue(command);
 await expect(page.getByLabel("Executable path on the ADORE host",{exact:true})).toHaveValue("C:/Installed/OpenCode/opencode.exe");
 await expect(page.locator(".local-executor-picker").getByText(/test-user.*test-host/)).toBeVisible();
 await page.getByLabel("Executor",{exact:false}).first().selectOption("qwen");
 await expect(argv).toHaveValue("");
 await expect(page.getByText(discoveryCopy.en.missing,{exact:true})).toBeVisible();
 await page.getByLabel("Executor",{exact:false}).first().selectOption("pi");
 await expect(argv).toHaveValue(piCommand);
 await page.getByRole("button",{name:"Use executable",exact:true}).click();
 await expect(argv).toHaveValue(piCommand);
 await argv.fill('"C:/Custom/pi.exe" -p {prompt}');
 await page.getByRole("button",{name:"Detect installed executors",exact:true}).click();
 await expect(argv).toHaveValue('"C:/Custom/pi.exe" -p {prompt}');
 await page.getByLabel("Executable path on the ADORE host",{exact:true}).fill("C:/Manual/pi.exe");
 await page.getByRole("button",{name:"Use executable",exact:true}).click();
 await expect(argv).toHaveValue('"C:/Manual/pi.exe" -p --mode json --model {model} {prompt}');
 await expect(page.getByLabel("Delegated Linux cgroup root",{exact:false})).toHaveCount(0);
 await page.screenshot({path:"test-results/local-executors-windows.png",fullPage:true});
});

test("unavailable discovery keeps manual Linux execution possible",async({page})=>{
 await page.route("**/api/v1/local-executors",route=>route.fulfill({status:503,json:{}}));
 await enter(page);
 await page.locator(".local-executor-advanced > summary").click();
 await expect(page.getByText(discoveryCopy.en.unavailable,{exact:true})).toBeVisible();
 await page.getByLabel("Executable path on the ADORE host",{exact:true}).fill("/opt/tools/opencode");
 await page.getByRole("button",{name:"Use executable",exact:true}).click();
 await expect(page.locator("#enroll-executor_command")).toHaveValue('"/opt/tools/opencode" run --dir {worktree} -m {model} --format json {prompt}');
});

test("simple local enrollment sends the current account and automatic home and PATH",async({page})=>{
 await page.route("**/api/v1/local-executors",route=>route.fulfill({json:discovery}));
 let submitted:Record<string,unknown>|undefined;
 await page.route("**/api/v1/projects/setup-preview",route=>{
  submitted=route.request().postDataJSON();
  return route.fulfill({json:{structural_valid:false,issues:[],revision:null,config_revision:null,review:null}});
 });
 await enter(page);
 await page.locator("#enroll-model").fill("openai/offline-model");
 await page.getByRole("button",{name:"Continue",exact:true}).click();
 await page.getByRole("button",{name:"Continue",exact:true}).click();
 await page.getByRole("button",{name:"Validate setup",exact:true}).click();
 await expect.poll(()=>submitted?.local_account).toBe("current");
 expect(submitted?.local_home).toBe("");expect(submitted?.local_path).toBe("");
 expect(submitted?.executor_command).toBe(command);
 expect(submitted?.auth_mode).toBe("existing");
});

test("late detection preserves edits and Linux offers its native launch",async({page})=>{
 let release!:()=>void;
 const wait=new Promise<void>(resolve=>{release=resolve;});
 await page.route("**/api/v1/local-executors",async route=>{await wait;await route.fulfill({json:{...discovery,system:"Linux",executors:discovery.executors.map(item=>item.agent!=="opencode"?item:{agent:"opencode",installations:[{executable:"/opt/tools/opencode",entrypoint:null,source:"PATH",command:'"/opt/tools/opencode" run --dir {worktree} -m {model} --format json {prompt}'}]})}});});
 await enter(page);
 const argv=page.locator("#enroll-executor_command");
 await page.locator(".local-executor-advanced > summary").click();
 await argv.fill('"/custom/opencode" run {prompt}');
 release();
 await expect(page.getByText(/test-host.*Linux/)).toBeVisible();
 await expect(argv).toHaveValue('"/custom/opencode" run {prompt}');
 await page.getByLabel("Detected installations",{exact:true}).selectOption({index:1});
 await expect(argv).toHaveValue('"/opt/tools/opencode" run --dir {worktree} -m {model} --format json {prompt}');
 await expect(page.getByLabel("Delegated Linux cgroup root",{exact:false})).toBeVisible();
});

test("local Settings preserves saved command until an installation is selected",async({page})=>{
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");
 await page.request.post("/api/v1/session",{data:{username:"admin",password:"admin"}});
 const projects=await(await page.request.get("/api/v1/projects")).json();
 const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 const config=await(await page.request.get(`/api/v1/projects/${id}/config`)).json();
 config.config.execution={backend:"local",preparation:""};
 const saved='"C:/Custom/opencode.exe" run --dir {worktree} -m {model} --format json {prompt}';
 config.config.executor.commands.opencode.command=saved;
 config.settings.find((s:{key:string})=>s.key==="executor.commands.opencode.command").choices=[];
 await page.route(`**/api/v1/projects/${id}/config`,route=>route.fulfill({json:config}));
 await page.route("**/api/v1/local-executors",route=>route.fulfill({json:discovery}));
 await page.goto(`/projects/${id}/configuration`);
 await page.locator('[data-setting-purpose="executor"] > summary').click();
 const technical=page.locator('[data-setting-topic="localTechnical"]');
 await expect(technical).toBeVisible();
 await expect(technical).not.toHaveAttribute("open", "");
 await expect(page.locator('[id="setting-local.home"]')).not.toBeVisible();
 await technical.locator(":scope > summary").click();
 await expect(page.locator('[id="setting-local.home"]')).toBeVisible();
 await page.getByRole("button",{name:"Edit Executor launch command",exact:true}).click();
 await page.locator(".local-executor-advanced > summary").click();
 const argv=page.getByLabel("Executor launch command",{exact:true});
 await expect(page.locator(".local-executor-picker").getByText(/test-user.*test-host/)).toBeVisible();
 await expect(argv).toHaveValue(saved);
 await page.getByLabel("Detected installations",{exact:true}).selectOption({index:1});
 await expect(argv).toHaveValue(command);
 await expect(page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true})).toBeEnabled();
});

for(const locale of ["en","ro","fr","de"] as const){
 test(`local executor choices and paths are localized and fit mobile ${locale}`,async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  await page.route("**/api/v1/local-executors",route=>route.fulfill({json:discovery}));
  const session=await page.request.post("/api/v1/session",{data:{username:"admin",password:"admin"}});
  const headers={"X-CSRF-Token":(await session.json()).csrf};
  await page.request.patch("/api/v1/me/preferences",{headers,data:{language:locale}});
  try {
   await page.setViewportSize({width:390,height:844});
   await page.goto("/projects/new");
   await page.locator("#enroll-clone_url").fill("ssh://git@forge.e2e.invalid:2222/team/local-executors.git");
   await page.getByRole("button",{name:enrollmentCopy[locale].read,exact:true}).click();
   await page.getByRole("button",{name:enrollmentCopy[locale].continue,exact:true}).click();
   await page.locator("#enroll-execution_backend").selectOption("local");
   await expect(page.locator("#enroll-executor_command")).toHaveValue(command);
   await expect(page.locator("#enroll-executor_command")).not.toBeVisible();
   await page.locator(".local-executor-advanced > summary").click();
   await expect(page.getByLabel(discoveryCopy[locale].path,{exact:true})).toHaveValue("C:/Installed/OpenCode/opencode.exe");
   await expect(page.getByRole("button",{name:discoveryCopy[locale].refresh,exact:true})).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
   if(locale==="ro")await page.screenshot({path:"test-results/local-executors-ro-mobile.png",fullPage:true});
  } finally {await page.request.patch("/api/v1/me/preferences",{headers,data:{language:"en"}});}
 });
}

test("native mode detects automatically and keeps agent fields in independent compact columns",async({page})=>{
 let requests=0;
 await page.route("**/api/v1/local-executors",route=>{requests++;return route.fulfill({json:discovery});});
 await enter(page);
 await expect(page.getByLabel(discoveryCopy.en.installed,{exact:true})).toHaveValue(command);
 expect(requests).toBe(1);
 const left=page.locator(".enrollment-agent-column").first();
 await expect(left.locator("#enroll-executor_cli")).toBeVisible();
 const run=await left.locator("#enroll-execution_backend").boundingBox();
 const auth=await left.locator("#enroll-auth_mode").boundingBox();
 expect(auth!.y-(run!.y+run!.height)).toBeLessThan(65);
 await expect(page.getByRole("button",{name:discoveryCopy.en.refresh,exact:true})).not.toBeVisible();
 await page.locator("#enroll-executor_cli").selectOption("pi");
 await expect(page.getByLabel(discoveryCopy.en.installed,{exact:true})).toHaveValue(piCommand);
 expect(requests).toBe(1);
 await page.locator("#enroll-execution_backend").selectOption("container");
 await page.locator("#enroll-execution_backend").selectOption("local");
 await expect.poll(()=>requests).toBe(2);
 await expect(page.getByLabel(discoveryCopy.en.installed,{exact:true})).toBeVisible();
 await page.screenshot({path:"test-results/compact-agent-model-desktop.png",fullPage:true});
});

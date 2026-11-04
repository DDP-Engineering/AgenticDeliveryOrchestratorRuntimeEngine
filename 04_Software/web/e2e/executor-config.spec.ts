/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {agentSettingsCopy,credentialEditorCopy} from "../src/executorSettings";
import {connectionCopy} from "../src/agentConnection";
import {chatgptCopy} from "../src/chatgptCopy";
import {errorMessages} from "../src/errors";
import {test, expect} from "@playwright/test";

const PI_PRESET="pi -p --mode json --model {model} {prompt}";

test("executor workspace owns model, credentials and coherent evidence", async ({page}) => {
 await page.context().route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
 await page.goto("/"); await page.getByLabel("Username",{exact:false}).fill("admin"); await page.getByLabel("Password",{exact:false}).fill("admin"); await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await (await page.request.get("/api/v1/projects")).json();
 const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 await page.goto(`/projects/${id}/executor`);
 await expect(page.getByRole("tab",{name:"Settings",exact:true})).toHaveAttribute("aria-selected","true");
 await expect(page.getByRole("tab",{name:"Executor configuration",exact:true})).toHaveCount(0);
 await page.getByText(/^Agent and model \(\d+\)$/).click();
 await page.locator('[data-setting-topic="authentication"] > summary').click();
 await expect(page.getByRole("button",{name:"Edit Model",exact:true})).toBeVisible();
 await expect(page.getByRole("button",{name:"Edit Provider",exact:true})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Provider API key",exact:true})).toBeVisible();
 const panel=page.locator("#project-settings");
 await expect(panel.getByRole("heading",{name:"Provider API key",exact:true})).toBeVisible();
 // The endpoint rows belong to an OpenAI-compatible endpoint only.
 await expect(panel.locator('[id="setting-executor.endpoint.base_url"]')).toHaveCount(0);
 const heading=panel.getByRole("heading",{name:"AI connection",exact:true});
 const testButton=panel.getByRole("button",{name:"Test AI connection",exact:true});
 const titleBox=await heading.boundingBox(), testBox=await testButton.boundingBox();
 expect(titleBox && testBox).toBeTruthy();
 expect(testBox!.x).toBeGreaterThan(titleBox!.x+titleBox!.width);
 expect(Math.abs((testBox!.y+testBox!.height/2)-(titleBox!.y+titleBox!.height/2))).toBeLessThan(10);
 // Pi is the only coding agent: no agent choice and no agent sign-in hint.
 await expect(panel.getByRole("button",{name:"Edit Default coding agent",exact:true})).toHaveCount(0);
 await expect(panel.getByLabel("Default coding agent",{exact:true})).toHaveCount(0);
 await expect(panel.getByText("Subscription or browser sign-in",{exact:true})).toHaveCount(0);
 await expect(panel).not.toContainText(".pi/agent");
 await panel.getByRole("button",{name:"Edit Executor launch command",exact:true}).click();
 const command=panel.getByLabel("Executor launch command",{exact:true});
 await expect(command).toHaveJSProperty("tagName","SELECT");
 await command.selectOption(PI_PRESET);
 await panel.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 await expect(page.locator(".candidate-review")).toContainText("pi -p --mode json");
 await page.locator(".candidate-review").getByRole("button",{name:"Discard change",exact:true}).click();
 await page.getByLabel("Credential variable",{exact:true}).selectOption("OPENAI_API_KEY");
 await page.getByLabel("API key",{exact:true}).fill("offline-private-key");
 await page.getByRole("button",{name:"Save API key",exact:true}).click();
 await expect(page.getByText("Key saved. Test AI connection to verify model access.",{exact:true})).toBeVisible();
 await expect(page.getByLabel("API key",{exact:true})).toHaveValue("");
 await page.getByRole("button",{name:"Disconnect project API key",exact:true}).click();
 await expect(page.getByText("Project API key removed.",{exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Edit Model",exact:true}).click();
 await page.locator(".setting-editor").getByLabel("Model",{exact:true}).fill("offline-test-model");
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 await expect(page.locator(".candidate-review")).toContainText("offline-test-model");
 await page.locator(".candidate-review").getByRole("button",{name:"Discard change",exact:true}).click();
 await page.getByRole("tab",{name:"Settings",exact:true}).click();
 await expect(page.getByRole("button",{name:"Edit Model",exact:true})).toHaveCount(1);
 await expect(page.getByRole("heading",{name:"Provider API key",exact:true})).toHaveCount(1);
});

for (const user of ["admin", "developer"]) {
 test(`executor preset editor preserves current commands and role boundaries ${user}`, async ({page}) => {
  await page.context().route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/"); await page.getByLabel("Username",{exact:false}).fill(user); await page.getByLabel("Password",{exact:false}).fill(user === "admin" ? "admin" : "test-password"); await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json();
  const id=projects.find((p:{name:string})=>p.name==="alpha").id;
  const config=await(await page.request.get(`/api/v1/projects/${id}/config`)).json();
  const current="pi -p --mode json --model {model} --thinking medium {prompt}";
  config.config.executor.command=current;
  await page.route("**/projects/*/config", route=>route.fulfill({json:config}));
  await page.goto(`/projects/${id}/executor`);
  await expect(page.getByRole("tab",{name:"Agent and model",exact:true})).toHaveCount(0);
  await page.getByText(/^Agent and model \(\d+\)$/).click();
  const panel=page.locator("#project-settings");
  await expect(panel.getByRole("heading",{name:"AI connection",exact:true})).toBeVisible();
  await expect(panel).toContainText(current);
  if (user === "admin") {
   await panel.getByRole("button",{name:"Edit Executor launch command",exact:true}).click();
   const command=panel.getByLabel("Executor launch command",{exact:true});
   await expect(command).toHaveValue(current);
   await expect(panel.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true})).toBeDisabled();
   await command.selectOption(config.settings.find((s:{key:string})=>s.key==="executor.command").choices[0]);
   await expect(panel.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true})).toBeEnabled();
   await panel.getByRole("button",{name:"Cancel",exact:true}).click();
   await page.setViewportSize({width:390,height:844});
   const box=await panel.getByRole("button",{name:"Test AI connection",exact:true}).boundingBox();
   expect(box!.x+box!.width).toBeLessThanOrEqual(390);
   await page.screenshot({path:"test-results/executor-unified-mobile.png",fullPage:true});
  } else {
   await expect(panel.getByRole("button",{name:/^Edit /})).toHaveCount(0);
   await expect(panel.getByRole("button",{name:"Test AI connection",exact:true})).toHaveCount(0);
   await expect(panel.locator("#executor-credentials")).toHaveCount(0);
  }
 });
}


test("current model evidence remains coherent in Summary and host check details",async({page})=>{
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 const config=await(await page.request.get(`/api/v1/projects/${id}/config`)).json();
 const result={project_id:id,revision:config.revision,checked_at:new Date().toISOString(),executor:"pi",model:config.config.executor.model,ready:true,reason:"ready"};
 await page.route("**/projects/*/config",route=>route.fulfill({json:{...config,model_connection:result}}));
 await page.route("**/readiness-check",route=>route.fulfill({json:{status:"verified",project_id:id,revision:config.revision,checked_at:new Date().toISOString(),context:"api-host",checks:{git:true,forge_cli:true,forge_auth:true,container_runtime:true,executor_cli:true,aegis_files:true}}}));
 await page.goto(`/projects/${id}`);
 await expect(page.getByText("AI model connected",{exact:true})).toHaveCount(0);
 await page.getByRole("button",{name:"Check host prerequisites",exact:true}).click();
 await expect(page.locator(".readiness-check").first()).toBeVisible();
 const row=page.locator(".readiness-check").filter({has:page.getByText("AI model connection",{exact:true})});
 await expect(row).toContainText("✓ Passed");await expect(row).not.toContainText("Not checked");
 await expect(row).toContainText(result.model);
 await expect(page.getByText(result.model,{exact:true})).toHaveCount(0);
 await expect(page.locator(".readiness-verdict")).toHaveCount(0);
 await page.getByRole("tab",{name:"Settings",exact:true}).click();
 await page.getByText(/^Agent and model \(\d+\)$/).click();
 await expect(page.getByText("AI model connected",{exact:true})).toBeVisible();
 await page.getByRole("tab",{name:"Summary",exact:true}).click();
 await expect(page.getByText("AI model connected",{exact:true})).toHaveCount(0);
 await expect(row).toContainText(result.model);
});

test("model and provider drafts have complete review and fit mobile",async({page})=>{
 await page.context().route("**/*", route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/"); await page.getByLabel("Username",{exact:false}).fill("admin"); await page.getByLabel("Password",{exact:false}).fill("admin"); await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json(); const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 await page.goto(`/projects/${id}/configuration`); await page.getByText(/^Agent and model \(\d+\)$/).click();
 await page.getByRole("button",{name:"Edit Provider",exact:true}).click();
 const editor=page.locator(".setting-editor");
 const provider=editor.getByLabel("Provider",{exact:true});
 await expect(provider.locator('option[value="anthropic"]')).toHaveCount(1);
 await expect(editor.getByText(/OPENAI_API_KEY/)).toBeVisible();
 await provider.selectOption("chatgpt");
 await expect(editor.getByText(connectionCopy.en.chatgptNote,{exact:true})).toBeVisible();
 await provider.selectOption("custom");
 await expect(editor.getByText(connectionCopy.en.baseUrlHelp,{exact:true})).toBeVisible();
 await expect(editor.getByText(/ADORE_ENDPOINT_API_KEY/)).toBeVisible();
 await expect(editor.getByRole("button",{name:"Prepare candidate",exact:true})).toBeDisabled();
 await editor.getByLabel("Model",{exact:true}).fill("qwen/qwen3.5-9b");
 await editor.getByLabel("Endpoint base URL",{exact:true}).fill("http://172.27.80.1:1234/v1");
 await expect(editor.getByLabel("Endpoint API type",{exact:true})).toHaveValue("openai-completions");
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await editor.getByRole("button",{name:"Prepare candidate",exact:true}).click();
 const review=page.locator(".candidate-review");
 for (const text of ["custom","qwen/qwen3.5-9b","http://172.27.80.1:1234/v1","openai-completions","Endpoint base URL"]) await expect(review).toContainText(text);
 await review.getByRole("button",{name:"Discard change",exact:true}).click();
 await page.locator('[data-setting-topic="authentication"] > summary').click();
 await page.getByRole("button",{name:"Edit Additional credential variables",exact:true}).click();
 await page.getByLabel("Add credential variable",{exact:true}).selectOption("OPENROUTER_API_KEY");
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click(); await expect(review).toContainText("OPENROUTER_API_KEY");
 await review.getByRole("button",{name:"Discard change",exact:true}).click();
});


test("inline executor editors retain columns and use a credential dropdown",async({page})=>{
 await page.setViewportSize({width:1520,height:900});
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 const model=(await(await page.request.get(`/api/v1/projects/${id}/config`)).json()).config.executor.model;
 await page.goto(`/projects/${id}/configuration`);await page.getByText(/^Agent and model \(\d+\)$/).click();
 await expect(page.locator('[id="setting-executor.default"]')).toHaveCount(0);
 const row=page.locator('[id="setting-executor.model"]');
 const before=await row.locator(':scope > div').nth(1).boundingBox();
 await row.getByRole("button",{name:"Edit Model",exact:true}).click();
 const editor=await row.locator(':scope > form').boundingBox();
 expect(Math.abs(editor!.x-before!.x)).toBeLessThan(2);
 expect(Math.abs(editor!.width-before!.width)).toBeLessThan(2);
 await row.getByLabel("Model",{exact:true}).fill("offline-inline-model");
 await row.getByRole("button",{name:"Prepare candidate",exact:true}).click();
 await expect(page.locator(".candidate-review")).toContainText("offline-inline-model");
 await page.locator(".candidate-review").getByRole("button",{name:"Discard change",exact:true}).click();
 await expect(row.locator("code")).toHaveText(model);
 await page.locator('[data-setting-topic="authentication"] > summary').click();
 await page.getByRole("button",{name:"Edit Additional credential variables",exact:true}).click();
 const names=page.locator('[id="setting-executor.env_keys"]');
 await expect(names.getByRole("checkbox")).toHaveCount(0);
 await names.getByLabel("Add credential variable",{exact:true}).selectOption("OPENROUTER_API_KEY");
 await expect(names.getByRole("button",{name:"Remove OPENROUTER_API_KEY",exact:true})).toBeVisible();
 await expect(names.getByLabel("Add credential variable",{exact:true}).locator('option[value="OPENROUTER_API_KEY"]')).toBeDisabled();
 await names.getByLabel("Add credential variable",{exact:true}).selectOption("GEMINI_API_KEY");
 await names.getByRole("button",{name:"Remove OPENROUTER_API_KEY",exact:true}).click();
 await expect(names.getByRole("button",{name:"Remove OPENROUTER_API_KEY",exact:true})).toHaveCount(0);
 await expect(names.getByRole("button",{name:"Remove GEMINI_API_KEY",exact:true})).toBeVisible();
 await names.getByRole("button",{name:"Cancel",exact:true}).click();
});


test("inline executor and credential dropdown controls preserve four locales",async({page})=>{
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 for(const locale of ["ro","fr","de","en"] as const){
  await page.goto("/account");const saved=page.waitForResponse(r=>r.url().endsWith("/me/preferences")&&r.request().method()!=="GET");
  await page.locator(".form-stack select").first().selectOption(locale);await saved;
  await page.goto(`/projects/${id}/configuration`);await page.locator('[data-setting-purpose="executor"] > summary').click();
  const model=page.locator('[id="setting-executor.model"]');await model.getByRole("button").click();
  await expect(model.getByLabel(agentSettingsCopy[locale].model,{exact:true})).toBeVisible();
  await expect(model).toContainText(agentSettingsCopy[locale].modelHelp);
  await model.locator('button.ghost').click();await page.locator('[data-setting-topic="authentication"] > summary').click();
  const names=page.locator('[id="setting-executor.env_keys"]');await names.getByRole("button").click();
  await names.getByLabel(credentialEditorCopy[locale].add,{exact:true}).selectOption("OPENROUTER_API_KEY");
  await names.getByRole("button",{name:`${credentialEditorCopy[locale].remove} OPENROUTER_API_KEY`,exact:true}).click();
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await names.locator('button.ghost').click();await page.setViewportSize({width:1280,height:720});
 }
});


test("compact review shows only differences above settings and blocks unchanged candidates",async({page,context})=>{
 await context.grantPermissions(["clipboard-read","clipboard-write"]);
 await page.setViewportSize({width:1520,height:900});
 await context.route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 await page.goto(`/projects/${id}/configuration`);await page.getByText(/^Agent and model \(\d+\)$/).click();
 const before=await(await page.request.get(`/api/v1/projects/${id}/config`)).json();
 await page.getByRole("button",{name:"Edit Model",exact:true}).click();
 await page.locator(".setting-editor").getByLabel("Model",{exact:true}).fill("offline-review-model");
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 const review=page.locator(".candidate-review"),changes=review.locator(".candidate-changes tbody tr"),details=review.locator(".candidate-details");
 await expect(changes).toHaveCount(1);await expect(changes).toContainText("Model");
 await expect(details).not.toHaveAttribute("open","");
 const bounds=await review.boundingBox(),groups=await page.locator("#project-settings > .setting-groups").boundingBox();
 expect(bounds!.y+bounds!.height).toBeLessThanOrEqual(groups!.y);expect(bounds!.height).toBeLessThan(420);
 const apply=review.getByRole("button",{name:"Apply change",exact:true}),discard=review.getByRole("button",{name:"Discard change",exact:true});
 expect(Math.abs((await apply.boundingBox())!.y-(await discard.boundingBox())!.y)).toBeLessThan(2);
 await details.locator(":scope > summary").click();await expect(details.locator(".candidate-complete tbody tr")).toHaveCount(4);
 await expect(details).toContainText(connectionCopy.en.providerHelp);
 await details.getByRole("button",{name:"Copy safe review",exact:true}).click();
 const copied=await page.evaluate(()=>navigator.clipboard.readText());expect(copied).toContain("Model: ");expect(copied).toContain("offline-review-model");expect(copied).not.toContain("Default coding agent");
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await discard.click();expect((await(await page.request.get(`/api/v1/projects/${id}/config`)).json()).revision).toBe(before.revision);
 await page.getByRole("button",{name:"Edit Model",exact:true}).click();
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 await expect(review).toContainText("No values have changed.");await expect(apply).toBeDisabled();await expect(changes).toHaveCount(0);
 await discard.click();await expect(review).toHaveCount(0);expect(await(await page.request.get(`/api/v1/projects/${id}/config/pending`)).json()).toBeNull();
 expect((await(await page.request.get(`/api/v1/projects/${id}/config`)).json()).revision).toBe(before.revision);
});

test("estimated prices live in Agent and model for administrators only",async({page})=>{
 await page.context().route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
 const signIn=async(user:string,password:string)=>{await page.goto("/");await page.getByLabel("Username",{exact:false}).fill(user);await page.getByLabel("Password",{exact:false}).fill(password);await page.getByRole("button",{name:"Sign in",exact:true}).click();await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();};
 await signIn("admin","admin");
 const projects=await (await page.request.get("/api/v1/projects")).json();
 const project=projects.find((p:{name:string})=>p.name==="alpha");
 expect(project.executor).toBe("pi");
 const config=(await (await page.request.get(`/api/v1/projects/${project.id}/config`)).json()).config;
 const model=config.executor?.model ?? "";
 expect(model).not.toBe("");
 await page.goto(`/projects/${project.id}/prices`);
 await expect(page).toHaveURL(new RegExp(`/projects/${project.id}/configuration$`));
 await expect(page.getByRole("tab",{name:"Settings",exact:true})).toHaveAttribute("aria-selected","true");
 await expect(page.getByRole("tab",{name:"Prices",exact:true})).toHaveCount(0);
 const group=page.locator('[data-setting-purpose="executor"]');
 await group.locator("> summary").click();
 const prices=group.locator(".executor-prices");
 await expect(prices.getByRole("heading",{name:"Estimated prices",exact:true})).toBeVisible();
 const form=prices.locator("form");
 await expect(form.locator("select, input:not([type=hidden])")).toHaveCount(3);
 await expect(form.getByLabel("Effective from",{exact:false})).toBeVisible();
 await expect(form.locator("select[name=executor], input[name=model]:not([type=hidden])")).toHaveCount(0);
 await form.getByLabel("Input USD / 1M tokens",{exact:false}).fill("1.25");
 await form.getByLabel("Output USD / 1M tokens",{exact:false}).fill("5");
 await form.getByRole("button",{name:"Save",exact:true}).click();
 const row=prices.locator("tbody tr").filter({hasText:String(model)});
 await expect(row).toHaveCount(1);
 await expect(row.locator("td").first()).toHaveText("pi");
 await expect(row).toContainText("1.25");
 await page.context().clearCookies();
 await signIn("developer","test-password");
 await page.goto(`/projects/${project.id}/configuration`);
 await page.locator('[data-setting-purpose="executor"] > summary').click();
 await expect(page.locator('[data-setting-purpose="executor"]')).toBeVisible();
 await expect(page.locator(".executor-prices")).toHaveCount(0);
 await expect(page.getByRole("heading",{name:"Estimated prices",exact:true})).toHaveCount(0);
});

test("an administrator signs the server in with ChatGPT and disconnects it",async({page})=>{
 await page.context().route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
 const fixture=(value:string)=>page.request.post(`/__e2e__/provider?value=${value}`,{headers:{"X-ADORE-E2E":"local-test"}});
 expect((await fixture("chatgpt")).ok()).toBe(true);
 try {
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json();const id=projects.find((p:{name:string})=>p.name==="alpha").id;
  await page.goto(`/projects/${id}/executor`);await page.getByText(/^Agent and model \(\d+\)$/).click();
  await page.locator('[data-setting-topic="authentication"] > summary').click();
  const panel=page.locator("#chatgpt-sign-in"),c=chatgptCopy.en;
  await expect(panel.getByRole("heading",{name:c.title,exact:true})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Provider API key",exact:true})).toHaveCount(0);
  await expect(panel.locator("[data-chatgpt-status]")).toHaveText(c["not-signed-in"]);
  await panel.getByRole("button",{name:c.start,exact:true}).click();
  const link=panel.getByRole("link",{name:c.link,exact:true});
  await expect(link).toHaveAttribute("href",/^https:\/\/auth\.openai\.com\//);
  await expect(link).toHaveAttribute("target","_blank");await expect(link).toHaveAttribute("rel","noopener noreferrer");
  const field=panel.getByLabel(c.field,{exact:true});
  await field.fill("http://127.0.0.1:1455/auth/callback?code=c&state=another-attempt");
  await panel.getByRole("button",{name:c.complete,exact:true}).click();
  await expect(panel.getByRole("alert")).toContainText(errorMessages.en.chatgpt_state_mismatch);
  await expect(link).toBeVisible();await expect(field).toHaveValue("");
  await field.fill("http://127.0.0.1:1455/auth/callback?code=fake-code&state=fake-state-0123456789&client_id=x");
  await panel.getByRole("button",{name:c.complete,exact:true}).click();
  await expect(panel.locator("[data-chatgpt-status]")).toHaveText(c["signed-in"]);
  await expect(panel.getByRole("status")).toHaveText(c.signedIn);await expect(link).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await panel.getByRole("button",{name:c.disconnect,exact:true}).click();
  await expect(panel.locator("[data-chatgpt-status]")).toHaveText(c["not-signed-in"]);
 } finally {
  await page.request.delete("/api/v1/chatgpt-sign-in",{headers:{"X-CSRF-Token":(await(await page.request.get("/api/v1/session")).json()).csrf}}).catch(()=>undefined);
  expect((await fixture("openai")).ok()).toBe(true);
 }
});


for (const manualRace of [false,true]) {
 test(manualRace ? "ChatGPT manual completion waits for an in-flight callback status" : "ChatGPT callback completion appears without a pasted redirect", async ({page}) => {
  const fixture=(value:string)=>page.request.post(`/__e2e__/provider?value=${value}`,{headers:{"X-ADORE-E2E":"local-test"}});
  expect((await fixture("chatgpt")).ok()).toBe(true);
  let started=false, reads=0, pasted=0;
  let releaseStatus=()=>{}, announcePoll=()=>{};
  const released=new Promise<void>(resolve=>{releaseStatus=resolve;});
  const polled=new Promise<void>(resolve=>{announcePoll=resolve;});
  await page.route("**/api/v1/projects/*/chatgpt-sign-in",async route=>{
    started=true;
    await route.fulfill({json:{authorize_url:"https://auth.openai.com/authorize?state=callback-test-state",expires_in:900}});
  });
  await page.route("**/api/v1/chatgpt-sign-in",async route=>{
    if(route.request().method()==="PUT") {
      pasted++; await released;
      await route.fulfill({status:409,json:{detail:{code:"chatgpt_sign_in_not_pending"}}}); return;
    }
    if(route.request().method()!=="GET") { await route.continue(); return; }
    if(started)reads++;
    if(manualRace && started && reads===2) { announcePoll(); await released; }
    await route.fulfill({json:{status:started&&reads>1?"signed-in":"not-signed-in",pending:started&&reads<=1}});
  });
  try {
    await page.goto("/");
    await page.getByLabel("Username",{exact:false}).fill("admin");
    await page.getByLabel("Password",{exact:false}).fill("admin");
    await page.getByRole("button",{name:"Sign in",exact:true}).click();
    await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
    const projects=await(await page.request.get("/api/v1/projects")).json();
    const id=projects.find((p:{name:string})=>p.name==="alpha").id;
    await page.goto(`/projects/${id}/configuration`);
    await page.getByText(/^Agent and model \(\d+\)$/).click();
    await page.locator('[data-setting-topic="authentication"] > summary').click();
    const panel=page.locator("#chatgpt-sign-in"),c=chatgptCopy.en;
    await panel.getByRole("button",{name:c.start,exact:true}).click();
    if(manualRace) {
      await polled;
      await panel.getByLabel(c.field,{exact:true}).fill("http://127.0.0.1:1455/auth/callback?code=fake&state=callback-test-state");
      await panel.getByRole("button",{name:c.complete,exact:true}).click();
      releaseStatus();
    }
    await expect(panel.locator("[data-chatgpt-status]")).toHaveText(c["signed-in"]);
    await expect(panel.getByRole("link",{name:c.link,exact:true})).toHaveCount(0);
    await expect(panel.getByLabel(c.field,{exact:true})).toHaveCount(0);
    expect(pasted).toBe(0);
    await expect(panel.getByRole("alert")).toHaveCount(0);
  } finally { releaseStatus(); expect((await fixture("openai")).ok()).toBe(true); }
 });
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test, expect} from "@playwright/test";

test("executor workspace owns model, credentials and coherent evidence", async ({page}) => {
 await page.context().route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
 await page.goto("/"); await page.getByLabel("Username",{exact:false}).fill("admin"); await page.getByLabel("Password",{exact:false}).fill("admin"); await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await (await page.request.get("/api/v1/projects")).json();
 const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 await page.goto(`/projects/${id}/executor`);
 await expect(page.getByRole("tab",{name:"Settings",exact:true})).toHaveAttribute("aria-selected","true");
 await expect(page.getByRole("tab",{name:"Executor configuration",exact:true})).toHaveCount(0);
 await page.getByText("Agent and model (6)",{exact:true}).click();
 await page.locator('[data-setting-topic="authentication"] > summary').click();
 await expect(page.getByRole("button",{name:"Edit Executor model identifier",exact:true})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Provider API keys",exact:true})).toBeVisible();
 const panel=page.locator("#project-settings");
 await expect(panel.getByRole("heading",{name:"Provider API keys",exact:true})).toBeVisible();
 const heading=panel.getByRole("heading",{name:"AI connection",exact:true});
 const testButton=panel.getByRole("button",{name:"Test AI connection",exact:true});
 const titleBox=await heading.boundingBox(), testBox=await testButton.boundingBox();
 expect(titleBox && testBox).toBeTruthy();
 expect(testBox!.x).toBeGreaterThan(titleBox!.x+titleBox!.width);
 expect(Math.abs((testBox!.y+testBox!.height/2)-(titleBox!.y+titleBox!.height/2))).toBeLessThan(10);
 await panel.getByRole("button",{name:"Edit Default coding agent",exact:true}).click();
 await expect(panel.getByLabel("Default coding agent",{exact:true})).toHaveValue("opencode");
 await panel.getByRole("button",{name:"Cancel",exact:true}).click();
 await panel.getByRole("button",{name:"Edit Executor launch command",exact:true}).click();
 const command=panel.getByLabel("Executor launch command",{exact:true});
 await expect(command).toHaveJSProperty("tagName","SELECT");
 await command.selectOption("opencode run --dir {worktree} -m {model} --format json {prompt}");
 await panel.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 await expect(page.locator(".candidate-review")).toContainText("opencode run --dir {worktree}");
 await page.locator(".candidate-review").getByRole("button",{name:"Discard change",exact:true}).click();
 await page.getByLabel("Credential variable",{exact:true}).selectOption("OPENAI_API_KEY");
 await page.getByLabel("API key",{exact:true}).fill("offline-private-key");
 await page.getByRole("button",{name:"Save API key",exact:true}).click();
 await expect(page.getByText("Key saved. Test AI connection to verify model access.",{exact:true})).toBeVisible();
 await expect(page.getByLabel("API key",{exact:true})).toHaveValue("");
 await page.getByRole("button",{name:"Disconnect project API key",exact:true}).click();
 await expect(page.getByText("Project API key removed.",{exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Edit Executor model identifier",exact:true}).click();
 await page.locator(".setting-editor input").fill("openai/offline-test-model");
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 await expect(page.locator(".candidate-review")).toBeVisible();
 await page.locator(".candidate-review").getByRole("button",{name:"Discard change",exact:true}).click();
 await page.getByRole("tab",{name:"Settings",exact:true}).click();
 await expect(page.getByRole("button",{name:"Edit Executor model identifier",exact:true})).toHaveCount(1);
 await expect(page.getByRole("heading",{name:"Provider API keys",exact:true})).toHaveCount(1);
});

for (const user of ["admin", "developer"]) {
 test(`executor preset editor preserves current commands and role boundaries ${user}`, async ({page}) => {
  await page.context().route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort());
  await page.goto("/"); await page.getByLabel("Username",{exact:false}).fill(user); await page.getByLabel("Password",{exact:false}).fill(user === "admin" ? "admin" : "test-password"); await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json();
  const id=projects.find((p:{name:string})=>p.name==="alpha").id;
  const config=await(await page.request.get(`/api/v1/projects/${id}/config`)).json();
  const current="opencode run --dir {worktree} -m {model} {prompt}";
  config.config.executor.commands.opencode.command=current;
  await page.route("**/projects/*/config", route=>route.fulfill({json:config}));
  await page.goto(`/projects/${id}/executor`);
  await expect(page.getByRole("tab",{name:"Agent and model",exact:true})).toHaveCount(0);
  await page.getByText("Agent and model (6)",{exact:true}).click();
  const panel=page.locator("#project-settings");
  await expect(panel.getByRole("heading",{name:"AI connection",exact:true})).toBeVisible();
  await expect(panel).toContainText(current);
  if (user === "admin") {
   await panel.getByRole("button",{name:"Edit Executor launch command",exact:true}).click();
   const command=panel.getByLabel("Executor launch command",{exact:true});
   await expect(command).toHaveValue(current);
   await expect(panel.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true})).toBeDisabled();
   await command.selectOption(config.settings.find((s:{key:string})=>s.key==="executor.commands.opencode.command").choices[0]);
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
 const result={project_id:id,revision:config.revision,checked_at:new Date().toISOString(),executor:"opencode",model:config.config.executor.commands.opencode.model,ready:true,reason:"ready"};
 await page.route("**/projects/*/config",route=>route.fulfill({json:{...config,model_connection:result}}));
 await page.route("**/readiness-check",route=>route.fulfill({json:{status:"verified",project_id:id,revision:config.revision,checked_at:new Date().toISOString(),context:"api-host",checks:{git:true,forge_cli:true,forge_auth:true,container_runtime:true,executor_cli:true,aegis_files:true,model_endpoint:"not-checked"},model_probe:{context:"executor-container",ready:false,model:result.model,reason:"not-configured"}}}));
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
 await page.getByText("Agent and model (6)",{exact:true}).click();
 await expect(page.getByText("AI model connected",{exact:true})).toBeVisible();
 await page.getByRole("tab",{name:"Summary",exact:true}).click();
 await expect(page.getByText("AI model connected",{exact:true})).toHaveCount(0);
 await expect(row).toContainText(result.model);
});

test("agent and provider drafts have complete review and fit mobile",async({page})=>{
 await page.context().route("**/*", route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/"); await page.getByLabel("Username",{exact:false}).fill("admin"); await page.getByLabel("Password",{exact:false}).fill("admin"); await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
 const projects=await(await page.request.get("/api/v1/projects")).json(); const id=projects.find((p:{name:string})=>p.name==="alpha").id;
 await page.goto(`/projects/${id}/configuration`); await page.getByText("Agent and model (6)",{exact:true}).click();
 await page.getByRole("button",{name:"Edit Default coding agent",exact:true}).click();
 await expect(page.getByLabel("Default coding agent",{exact:true}).locator("option")).toHaveText(["OpenCode","Pi","Codex","Qwen Code"]);
 await page.getByLabel("Default coding agent",{exact:true}).selectOption("codex");
 await expect(page.getByLabel("Executor launch command",{exact:true})).toContainText("codex exec");
 await expect(page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true})).toBeDisabled();
 await page.getByLabel("Executor model identifier",{exact:true}).fill("offline-codex-model");
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 const review=page.locator(".candidate-review"); await expect(review).toContainText("codex"); await expect(review).toContainText("codex exec"); await expect(review).toContainText("offline-codex-model");
 await review.getByRole("button",{name:"Discard change",exact:true}).click();
 await page.locator('[data-setting-topic="authentication"] > summary').click();
 await page.getByRole("button",{name:"Edit Allowed credential variables",exact:true}).click();
 await page.getByRole("checkbox",{name:"OPENROUTER_API_KEY",exact:true}).check();
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click(); await expect(review).toContainText("OPENROUTER_API_KEY");
 await review.getByRole("button",{name:"Discard change",exact:true}).click();
});

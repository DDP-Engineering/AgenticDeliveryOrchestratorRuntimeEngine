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
 await expect(page.getByRole("tab",{name:"Executor configuration",exact:true})).toHaveAttribute("aria-selected","true");
 await expect(page.getByRole("button",{name:"Edit opencode model identifier",exact:true})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Provider credentials",exact:true})).toBeVisible();
 await page.getByLabel("Credential variable",{exact:true}).selectOption("OPENAI_API_KEY");
 await page.getByLabel("API key",{exact:true}).fill("offline-private-key");
 await page.getByRole("button",{name:"Save API key",exact:true}).click();
 await expect(page.getByText("Key saved. Test AI connection to verify model access.",{exact:true})).toBeVisible();
 await expect(page.getByLabel("API key",{exact:true})).toHaveValue("");
 await page.getByRole("button",{name:"Disconnect project API key",exact:true}).click();
 await expect(page.getByText("Project API key removed.",{exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Edit opencode model identifier",exact:true}).click();
 await page.locator(".setting-editor input").fill("openai/offline-test-model");
 await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
 await expect(page.locator(".candidate-review")).toBeVisible();
 await page.locator(".candidate-review").getByRole("button",{name:"Discard change",exact:true}).click();
 await page.getByRole("tab",{name:"Settings",exact:true}).click();
 await expect(page.getByRole("button",{name:"Edit opencode model identifier",exact:true})).toHaveCount(0);
 await expect(page.getByRole("heading",{name:"Provider credentials",exact:true})).toHaveCount(0);
});


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
 await expect(page.locator(".readiness-check").first()).not.toBeVisible();
 await page.getByRole("button",{name:"Check details",exact:true}).click();
 const row=page.locator(".readiness-check").filter({has:page.getByText("AI model connection",{exact:true})});
 await expect(row).toContainText("✓ Passed");await expect(row).not.toContainText("Not checked");
 await expect(row).toContainText(result.model);
 await expect(page.getByText(result.model,{exact:true})).toHaveCount(0);
 await expect(page.locator(".readiness-verdict")).toHaveCount(0);
 await page.getByRole("tab",{name:"Executor configuration",exact:true}).click();
 await expect(page.getByText("AI model connected",{exact:true})).toBeVisible();
 await page.getByRole("tab",{name:"Summary",exact:true}).click();
 await expect(page.getByText("AI model connected",{exact:true})).toHaveCount(0);
 await expect(row).toContainText(result.model);
});

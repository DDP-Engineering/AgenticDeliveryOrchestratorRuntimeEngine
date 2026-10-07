/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect} from "@playwright/test";

test("environment setup puts mode and aligned image controls before advanced settings",async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json(),id=projects.find((p:{name:string})=>p.name==="alpha").id;
  await page.setViewportSize({width:1440,height:1000});
  await page.goto("/projects/"+id+"/configuration");
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  await expect(page.getByRole("button",{name:"Edit Execution backend",exact:true})).toBeInViewport();
  const panel=page.locator(".project-image");
  await expect(panel.getByRole("heading",{name:"Project executor image",exact:true})).toBeInViewport();
  await expect(page.getByText("Npm cache volume",{exact:true})).not.toBeVisible();
  await panel.getByRole("button",{name:"Define image",exact:true}).click();
  await expect(panel.getByLabel("Build downloads",{exact:true})).toBeVisible();
  await expect(panel).toContainText("Save the definition to enable Build and verify");
  const source=await panel.getByLabel("Dockerfile",{exact:true}).boundingBox(),checks=await panel.getByLabel("Tool checks (one command per line)",{exact:true}).boundingBox();
  expect(Math.abs(source!.y-checks!.y)).toBeLessThanOrEqual(1);
  expect(checks!.x-source!.x-source!.width).toBeGreaterThanOrEqual(20);
  await panel.screenshot({path:"test-results/project-image-aligned-desktop.png"});
  await page.setViewportSize({width:390,height:844});
  const mobileSource=await panel.getByLabel("Dockerfile",{exact:true}).boundingBox(),mobileChecks=await panel.getByLabel("Tool checks (one command per line)",{exact:true}).boundingBox();
  expect(mobileChecks!.y).toBeGreaterThan(mobileSource!.y+mobileSource!.height);
  expect(mobileChecks!.x+mobileChecks!.width).toBeLessThanOrEqual(390);
  await panel.screenshot({path:"test-results/project-image-aligned-mobile.png"});
});

test("project image define build verify and reviewed selection stays compact",async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json(), id=projects.find((p:{name:string})=>p.name==="alpha").id;
  await page.goto("/projects/"+id+"/configuration");
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  const panel=page.locator(".project-image");
  await expect(panel.getByRole("heading",{name:"Project executor image",exact:true})).toBeVisible();
  await expect(panel.getByRole("button",{name:"Existing image",exact:true})).toHaveAttribute("aria-pressed","true");
  await expect(panel).toContainText("model access and full run readiness are checked separately");
  await panel.getByRole("button",{name:"Define image",exact:true}).click();
  await expect(panel.getByRole("textbox",{name:"Dockerfile",exact:true})).toHaveValue(/USER adore/);
  const initial=await panel.getByLabel("Dockerfile",{exact:true}).inputValue();
  await panel.getByLabel("Load Dockerfile text",{exact:true}).setInputFiles({name:"invalid.txt",mimeType:"text/plain",buffer:Buffer.from([255])});
  await expect(panel.getByRole("alert")).toContainText("Image request failed");
  await expect(panel.getByLabel("Dockerfile",{exact:true})).toHaveValue(initial);
  await panel.getByLabel("Load Dockerfile text",{exact:true}).setInputFiles({name:"Dockerfile.txt",mimeType:"text/plain",buffer:Buffer.from((await panel.getByLabel("Dockerfile",{exact:true}).inputValue()).replace("USER adore","RUN echo tools\nUSER adore"))});
  await panel.getByLabel("Tool checks (one command per line)",{exact:true}).fill("python3 --version\nrustc --version");
  await expect(panel.getByRole("button",{name:"Build and verify",exact:true})).toBeDisabled();
  await panel.getByRole("button",{name:"Save definition",exact:true}).click();
  await expect(panel.getByText("Definition saved. Build explicitly when ready.",{exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await panel.screenshot({path:"test-results/project-image-definition-mobile.png"});
  expect((await panel.boundingBox())!.width).toBeLessThanOrEqual(390);
  await panel.getByRole("button",{name:"Build and verify",exact:true}).click();
  await expect(panel.getByRole("status").filter({hasText:/^Verified$/})).toBeVisible({timeout:15000});
  await expect(panel).toContainText("rustc --version");
  await panel.getByRole("button",{name:"Use image",exact:true}).click();
  const review=page.locator(".candidate-review");
  await expect(review).toContainText("sha256:"+"c".repeat(64));
  await expect(review).toContainText("rustc --version");
  await review.getByRole("button",{name:"Apply change",exact:true}).click();
  await expect(review).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  const box=await page.locator(".project-image").boundingBox();expect(box!.x+box!.width).toBeLessThanOrEqual(390);
  await page.screenshot({path:"test-results/project-image-mobile.png",fullPage:true});
});

for (const mode of ["developer","local"]) test("image workspace preserves "+mode+" ownership",async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  const developer=mode==="developer";
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill(developer?"developer":"admin");await page.getByLabel("Password",{exact:false}).fill(developer?"test-password":"admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json(),id=projects.find((p:{name:string})=>p.name==="alpha").id;
  if(!developer){
    const config=await(await page.request.get("/api/v1/projects/"+id+"/config")).json();
    config.local_execution={machine:"server",account:"worker",system:"Windows"};
    config.config.execution.backend="local";
    await page.route("**/projects/*/config",route=>route.fulfill({json:config}));
  }
  await page.goto("/projects/"+id+"/configuration");
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  const panel=page.locator(".project-image");
  await expect(panel.getByRole("heading",{name:"Project executor image",exact:true})).toBeVisible();
  for(const name of ["Define image","Build and verify","Use image","Save definition"])
    await expect(panel.getByRole("button",{name,exact:true})).toHaveCount(0);
  if(!developer)await expect(panel).toContainText("this server account's installed tools");
});

test("existing image choice opens the reviewed editor and preserves an unsaved definition",async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json(),id=projects.find((p:{name:string})=>p.name==="alpha").id;
  const config=await(await page.request.get("/api/v1/projects/"+id+"/config")).json();
  await page.goto("/projects/"+id+"/configuration");
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  const panel=page.locator(".project-image");
  await expect(panel).toContainText("Image currently used");
  await expect(panel).toContainText(config.config.container.image);
  await panel.getByRole("button",{name:"Define image",exact:true}).click();
  const source=panel.getByLabel("Dockerfile",{exact:true});
  await expect(source).toHaveAttribute("rows","16");
  await expect(panel.getByLabel("Tool checks (one command per line)",{exact:true})).toHaveAttribute("rows","6");
  await expect(panel).toContainText("between USER root and USER adore");
  await expect(panel).toContainText("exit successfully");
  await panel.getByText("Example: C/C++ compiler and Make",{exact:true}).click();
  await expect(panel).toContainText("build-essential");
  await expect(panel).toContainText("Allow default build network");
  const draft=(await source.inputValue())+"\n# unsaved tooling note\n";
  await source.fill(draft);
  await panel.getByRole("button",{name:"Existing image",exact:true}).click();
  await expect(source).toHaveCount(0);
  await expect(panel.getByRole("button",{name:"Existing image",exact:true})).toHaveAttribute("aria-pressed","true");
  await panel.getByRole("button",{name:"Define image",exact:true}).click();
  await expect(source).toHaveValue(draft);
  await panel.getByRole("button",{name:"Existing image",exact:true}).click();
  await panel.getByRole("button",{name:"Change existing image",exact:true}).click();
  const editor=page.locator('.setting-editor input[type="text"]');
  await expect(editor).toBeFocused();
  await expect(editor).toHaveValue(config.config.container.image);
  await editor.fill("adore-existing:test");
  await panel.getByRole("button",{name:"Change existing image",exact:true}).click();
  await expect(editor).toHaveValue("adore-existing:test");
  await page.locator(".setting-editor").getByRole("button",{name:"Prepare candidate",exact:true}).click();
  const review=page.locator(".candidate-review");
  await expect(review).toContainText("adore-existing:test");
  const pending=await(await page.request.get("/api/v1/projects/"+id+"/config/pending")).json();
  expect(pending.image_build).toBeUndefined();
  expect(pending.key).toBe("container.image");
  const unchanged=await(await page.request.get("/api/v1/projects/"+id+"/config")).json();
  expect(unchanged.revision).toBe(config.revision);
  await review.getByRole("button",{name:"Discard change",exact:true}).click();
  await expect(review).toHaveCount(0);
  await page.route("**/api/v1/projects",route=>route.fulfill({json:projects.map((p:{id:string})=>p.id===id?{...p,paused:false}:p)}));
  await page.reload();
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  await expect(panel).toContainText("Pause pickup in the project controls");
  await expect(panel.getByRole("button",{name:"Change existing image",exact:true})).toBeDisabled();
  await panel.getByRole("button",{name:"Define image",exact:true}).click();
  await expect(source).toBeDisabled();
  await expect(panel.getByLabel("Tool checks (one command per line)",{exact:true})).toBeDisabled();
  await expect(panel.getByRole("button",{name:"Save definition",exact:true})).toBeDisabled();
  await expect(panel.getByRole("button",{name:"Build and verify",exact:true})).toBeDisabled();
});

test("failed build loads bounded output and actionable guidance on entry",async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json(),id=projects.find((p:{name:string})=>p.name==="alpha").id;
  const config=await(await page.request.get("/api/v1/projects/"+id+"/config")).json();
  const view=await(await page.request.get("/api/v1/projects/"+id+"/image-build")).json();
  view.draft={schema:1,project_id:id,dockerfile:view.template,checks:view.template_checks,network:"none",timeout_seconds:600,memory_mib:1024,revision:"b".repeat(64)};
  const operation={id:"a".repeat(32),project_id:id,config_revision:config.revision,draft_revision:view.draft?.revision??"b".repeat(64),runtime:"docker",runtime_identity:"",base_id:"",image_id:"",context_sha256:"",verified_checks:[],phase:"failed",error:"image_tool_check_failed",host:{machine:"server",account:"worker",system:"Linux"},tag:"adore-built-"+id+":"+"a".repeat(32)};
  await page.route("**/api/v1/projects/"+id+"/image-build",route=>route.fulfill({json:{...view,operations:[operation]}}));
  let oversized=false,hold=false;
  let releaseOld:()=>void=()=>{};
  const oldGate=new Promise<void>(resolve=>{releaseOld=resolve;});
  const newer={...operation,id:"c".repeat(32),tag:"adore-built-"+id+":"+"c".repeat(32),error:"image_runtime_unavailable"};
  await page.route("**/api/v1/projects/"+id+"/image-build/operations",route=>route.fulfill({json:{build:newer,operation:{}}}));
  await page.route("**/api/v1/projects/"+id+"/image-build/operations/*",async route=>{
    if(route.request().url().endsWith(newer.id))return route.fulfill({json:{build:newer,log:"new runtime diagnostic"}});
    if(hold)await oldGate;
    return route.fulfill({json:{build:operation,log:oversized?"x".repeat(65537):"pytest: command not found"}});
  });
  await page.goto("/projects/"+id+"/configuration");
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  const panel=page.locator(".project-image");
  await expect(panel).toContainText("Add its installation to Dockerfile");
  await expect(panel.getByText("pytest: command not found",{exact:true})).toBeVisible();
  await expect(panel.getByRole("button",{name:"Use image",exact:true})).toHaveCount(0);
  oversized=true;
  await page.reload();
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  await expect(panel.getByRole("alert")).toContainText("Image request failed");
  await expect(panel.getByText("pytest: command not found",{exact:true})).toHaveCount(0);
  await expect(panel.getByRole("button",{name:"Use image",exact:true})).toHaveCount(0);
  oversized=false;hold=true;
  await page.reload();
  await page.locator("#project-settings > .setting-groups > details > summary").filter({hasText:"Isolated environment"}).click();
  await panel.getByRole("button",{name:"Define image",exact:true}).click();
  await panel.getByRole("button",{name:"Build and verify",exact:true}).click();
  await expect(panel.getByText("new runtime diagnostic",{exact:true})).toBeVisible();
  const oldResponse=page.waitForResponse(response=>response.url().endsWith(operation.id));
  releaseOld();await oldResponse;
  await panel.getByRole("button",{name:"Refresh evidence",exact:true}).click();
  await expect(panel.getByText("new runtime diagnostic",{exact:true})).toBeVisible();
  await expect(panel.getByText("pytest: command not found",{exact:true})).toHaveCount(0);
});

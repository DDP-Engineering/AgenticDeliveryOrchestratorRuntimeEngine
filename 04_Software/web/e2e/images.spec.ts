/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect} from "@playwright/test";

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

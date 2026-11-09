/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect,type Page} from "@playwright/test";
import {setupCopy} from "../src/setupCopy";
import {enrollmentCopy} from "../src/enrollmentCopy";

async function enter(page:Page,locale:"en"|"ro"|"fr"|"de"="en") {
 await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
 await page.goto("/");
 const session=await(await page.request.post("/api/v1/session",{data:{username:"admin",password:"admin"}})).json();
 await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":session.csrf},data:{language:locale}});
 await page.goto("/projects/new");
 await page.locator("#enroll-clone_url").fill("ssh://git@forge.e2e.invalid:2222/team/folder-choice.git");
 await page.getByRole("button",{name:enrollmentCopy[locale].read,exact:true}).click();
 return session.csrf as string;
}

test("compact chooser selects the exact current host folder without extra fields",async({page})=>{
 await enter(page);
 const path=page.getByLabel("Local clone path",{exact:false}),automatic=await path.inputValue();
 await expect(page.getByLabel(setupCopy.en.automatic,{exact:true})).toBeChecked();
 await expect(path).toHaveAttribute("readonly","");
 await page.getByLabel(setupCopy.en.custom,{exact:true}).check();
 await page.getByRole("button",{name:setupCopy.en.choose,exact:true}).click();
 const dialog=page.getByRole("dialog",{name:setupCopy.en.dialog});
 await expect(dialog).toBeVisible();
 await expect(dialog.locator("input")).toHaveCount(1);
 const home=await dialog.getByLabel(setupCopy.en.location,{exact:true}).inputValue();
 await page.screenshot({path:"test-results/compact-folder-desktop.png",fullPage:true});
 await expect(dialog.getByRole("button",{name:setupCopy.en.use,exact:true})).toBeEnabled();
 await dialog.getByRole("button",{name:setupCopy.en.use,exact:true}).click();
 await expect(dialog).not.toBeVisible();
 await expect(path).toHaveValue(home);
 const proposed=home.replace(/[\\/]$/,"")+(home.includes("\\")?"\\":"/")+"new clone with spaces";
 await path.fill(proposed);
 expect((await page.request.get("/api/v1/host-folders",{params:{path:proposed}})).status()).toBe(400);
 await page.getByLabel(setupCopy.en.automatic,{exact:true}).check();
 await expect(path).toHaveValue(automatic);
 await expect(path).toHaveAttribute("readonly","");
});

test("failed folder navigation and cancellation preserve a manually typed destination",async({page})=>{
 await enter(page);
 await page.getByLabel(setupCopy.en.custom,{exact:true}).check();
 const path=page.getByLabel("Local clone path",{exact:false});
 await path.fill("/manual/project");
 await page.getByRole("button",{name:setupCopy.en.choose,exact:true}).click();
 const dialog=page.getByRole("dialog");
 await dialog.getByLabel(setupCopy.en.location,{exact:true}).fill("relative-folder");
 await dialog.getByRole("button",{name:setupCopy.en.go,exact:true}).click();
 await expect(dialog.getByRole("alert")).toContainText(setupCopy.en.unavailable);
 await expect(dialog.getByRole("button",{name:setupCopy.en.use,exact:true})).toBeDisabled();
 await page.keyboard.press("Escape");
 await expect(dialog).not.toBeVisible();
 await expect(path).toHaveValue("/manual/project");
 await expect(page.getByRole("button",{name:setupCopy.en.choose,exact:true})).toBeFocused();
});

test("cancelled folder reads cannot change the clone draft",async({page})=>{
 await enter(page);
 const path=page.getByLabel("Local clone path",{exact:false}),original=await path.inputValue();
 let release!:()=>void;
 const gate=new Promise<void>(resolve=>{release=resolve;});
 await page.route("**/api/v1/host-folders*",async route=>{await gate;try{await route.fulfill({json:{system:"Linux",path:"/stale",parent:"/",roots:["/"],folders:[],truncated:false}});}catch{/* Dialog cancelled the request. */}});
 await page.getByLabel(setupCopy.en.custom,{exact:true}).check();
 await page.getByRole("button",{name:setupCopy.en.choose,exact:true}).click();
 await page.getByRole("dialog").getByRole("button",{name:setupCopy.en.cancel,exact:true}).click();
 release();
 await expect(path).toHaveValue(original);
 await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("a late directory response cannot replace newer navigation or enable a pending selection",async({page})=>{
 await enter(page);
 let release!:()=>void;
 const gate=new Promise<void>(resolve=>{release=resolve;});
 await page.route("**/api/v1/host-folders*",async route=>{
  const path=new URL(route.request().url()).searchParams.get("path") || "/";
  if(path==="/slow")await gate;
  try{await route.fulfill({json:{system:"Linux",path,parent:path==="/"?null:"/",roots:["/"],folders:[],truncated:false}});}catch{/* Superseded request was aborted. */}
 });
 await page.getByLabel(setupCopy.en.custom,{exact:true}).check();
 await page.getByRole("button",{name:setupCopy.en.choose,exact:true}).click();
 const dialog=page.getByRole("dialog"),location=dialog.getByLabel(setupCopy.en.location,{exact:true});
 await expect(location).toHaveValue("/");
 await location.fill("/slow");await dialog.getByRole("button",{name:setupCopy.en.go,exact:true}).click();
 await expect(dialog.getByRole("button",{name:setupCopy.en.use,exact:true})).toBeDisabled();
 await location.fill("/newer");await location.press("Enter");
 await expect(dialog.getByRole("button",{name:setupCopy.en.use,exact:true})).toBeEnabled();
 release();
 await expect(location).toHaveValue("/newer");
 await dialog.getByRole("button",{name:setupCopy.en.use,exact:true}).click();
 await expect(page.locator("#enroll-repo_path")).toHaveValue("/newer");
});

test("directory rows support selection, keyboard opening and successful Back navigation",async({page})=>{
 await enter(page);
 await page.route("**/api/v1/host-folders*",route=>{
  const path=new URL(route.request().url()).searchParams.get("path") || "/";
  return route.fulfill({json:{system:"Linux",path,parent:path==="/"?null:"/",roots:["/"],
   folders:path==="/"?[{name:"Alpha",path:"/Alpha"},{name:"Beta",path:"/Beta"}]:[],truncated:false}});
 });
 await page.getByLabel(setupCopy.en.custom,{exact:true}).check();
 await page.getByRole("button",{name:setupCopy.en.choose,exact:true}).click();
 const dialog=page.getByRole("dialog"),location=dialog.getByLabel(setupCopy.en.location,{exact:true});
 const alpha=dialog.getByRole("option",{name:"Alpha",exact:true}),beta=dialog.getByRole("option",{name:"Beta",exact:true});
 await alpha.click();
 await expect(alpha).toHaveAttribute("aria-selected","true");
 await expect(location).toHaveValue("/");
 await alpha.press("End");await expect(beta).toBeFocused();
 await beta.press("Home");await expect(alpha).toBeFocused();
 await alpha.press("ArrowDown");await expect(beta).toBeFocused();
 await beta.press("ArrowUp");await expect(alpha).toBeFocused();
 await alpha.press("Enter");await expect(location).toHaveValue("/Alpha");
 await dialog.getByRole("button",{name:"Back",exact:true}).click();
 await expect(location).toHaveValue("/");
 await expect(dialog.getByRole("button",{name:"Back",exact:true})).toBeDisabled();
 await dialog.getByRole("option",{name:"Beta",exact:true}).click();
 await dialog.getByRole("button",{name:setupCopy.en.use,exact:true}).click();
 await expect(page.locator("#enroll-repo_path")).toHaveValue("/Beta");
});

for(const locale of ["en","ro","fr","de"] as const) {
 test(`compact folder chooser supports localized Windows and Linux paths on mobile ${locale}`,async({page})=>{
  const csrf=await enter(page,locale),c=setupCopy[locale];
  try {
   await page.setViewportSize({width:390,height:844});
   const windows=locale==="en"||locale==="ro",root=windows?"D:\\":"/",home=windows?"D:\\Projects":"/Projects";
   await page.route("**/api/v1/host-folders*",route=>{
    const requested=new URL(route.request().url()).searchParams.get("path"),current=requested || root;
    return route.fulfill({json:{system:windows?"Windows":"Linux",path:current,parent:current===root?null:root,roots:[root],folders:current===root?[{name:"Projects",path:home}]:[],truncated:current===root}});
   });
   await page.getByLabel(c.custom,{exact:true}).check();
   await page.getByRole("button",{name:c.choose,exact:true}).click();
   const dialog=page.getByRole("dialog",{name:c.dialog}),location=dialog.getByLabel(c.location,{exact:true});
   await expect(dialog.getByText(c.truncated,{exact:true})).toBeVisible();
   const folder=dialog.getByRole("option",{name:"Projects",exact:true});
   await folder.click();
   await expect(location).toHaveValue(root);
   await expect(folder).toHaveAttribute("aria-selected","true");
   expect((await folder.boundingBox())!.height).toBeLessThanOrEqual(48);
   await folder.dblclick();
   await expect(location).toHaveValue(home);
   await expect(dialog.getByText(c.empty,{exact:true})).toBeVisible();
   await expect(dialog.locator("input")).toHaveCount(1);
   await dialog.getByRole("button",{name:c.up,exact:true}).click();
   await expect(location).toHaveValue(root);
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
   await dialog.getByRole("option",{name:"Projects",exact:true}).click();
   if(locale==="ro")await page.screenshot({path:"test-results/folder-picker-ro-mobile.png",fullPage:true});
   await dialog.getByRole("button",{name:c.use,exact:true}).click();
   await expect(page.locator("#enroll-repo_path")).toHaveValue(home);
  } finally {await page.request.patch("/api/v1/me/preferences",{headers:{"X-CSRF-Token":csrf},data:{language:"en"}});}
 });
}

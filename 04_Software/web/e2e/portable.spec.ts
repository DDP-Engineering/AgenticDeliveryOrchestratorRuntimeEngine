/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";

async function openSettings(page: Page, user = "admin") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: false }).fill(user);
  await page.getByLabel("Password", { exact: false }).fill(user === "admin" ? "admin" : "test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".shell")).toBeVisible();
  const session = await (await page.request.get("/api/v1/me")).json();
  await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: "en", theme: "light" } });
  const projects = await (await page.request.get("/api/v1/projects")).json();
  await page.goto(`/projects/${projects.find((item: { name: string }) => item.name === "alpha").id}/configuration`);
  await expect(page.getByRole("heading", { name: "Project settings", exact: true })).toBeVisible();
}

test.beforeEach(async ({ context }) => {
  await context.addInitScript(() => Object.defineProperty(window,"showSaveFilePicker",{configurable:true,writable:true,value:undefined}));
  await context.route("**/*", route => new URL(route.request().url()).origin === "http://127.0.0.1:18765" ? route.continue() : route.abort("blockedbyclient"));
});

test.afterEach(async ({ page }) => {
  const response = await page.request.get("/api/v1/me");
  if (response.ok()) {
    const session = await response.json();
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": session.csrf }, data: { language: "en", theme: "light" } });
  }
});

for (const backend of ["container","local"]) test(`one-click export selects a destination and saves exact ${backend} bytes`, async ({page}) => {
  await page.addInitScript(() => {
    const state = { calls: 0, name: "", bytes: [] as number[] };
    Object.assign(window, { exportSave: state, showSaveFilePicker: async (options: {suggestedName:string}) => {
      state.calls++; state.name=options.suggestedName;
      return { createWritable: async () => ({
        write: async (data:ArrayBuffer) => {state.bytes=Array.from(new Uint8Array(data));},
        close: async () => {}, abort: async () => {},
      }) };
    } });
  });
  await page.route("**/api/v1/projects/*/config",async route => {
    const response=await route.fetch(), body=await response.json();
    body.config.execution.backend=backend;
    await route.fulfill({response,json:body});
  });
  const bytes=backend==="container"?Buffer.from([0x50,0x4b,0x03,0x04,0x01]):Buffer.from("# saved native config\r\n");
  await page.route(backend==="container"?"**/config/raw?download=true&include_build=true":"**/config/raw?download=true",route => route.fulfill({contentType:backend==="container"?"application/zip":"text/plain",body:bytes}));
  await openSettings(page);
  await page.getByRole("button",{name:"Export raw configuration",exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as unknown as {exportSave:{bytes:number[]}}).exportSave.bytes)).toEqual([...bytes]);
  expect(await page.evaluate(()=>(window as unknown as {exportSave:{calls:number;name:string}}).exportSave)).toMatchObject({calls:1,name:backend==="container"?"adore-docker-build.zip":"config.toml"});
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("canceling the destination makes no export request", async ({page}) => {
  await page.addInitScript(()=>Object.assign(window,{showSaveFilePicker:async()=>{throw new DOMException("cancel","AbortError");}}));
  let reads=0;
  await page.route("**/config/raw*",route=>{reads++;return route.abort();});
  await openSettings(page);
  const button=page.getByRole("button",{name:"Export raw configuration",exact:true});
  await button.click();await expect(button).toBeEnabled();
  expect(reads).toBe(0);await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("destination failures abort writes and show a save error without a fallback download", async ({page}) => {
  await page.addInitScript(()=>{
    const state={failPicker:true,aborts:0,closes:0};
    Object.assign(window,{saveFailure:state,showSaveFilePicker:async()=>{
      if(state.failPicker)throw new DOMException("denied","NotAllowedError");
      return {createWritable:async()=>({write:async()=>{throw new DOMException("write failed","AbortError");},
        abort:async()=>{state.aborts++;},close:async()=>{state.closes++;}})};
    }});
  });
  await page.route("**/api/v1/projects/*/config",async route=>{
    const response=await route.fetch(),body=await response.json();body.config.execution.backend="local";
    await route.fulfill({response,json:body});
  });
  await page.route("**/config/raw?download=true",route=>route.fulfill({contentType:"text/plain",body:"# exact native settings\r\n"}));
  let downloads=0;page.on("download",()=>downloads++);
  await openSettings(page);
  for(const failPicker of [true,false]){
    await page.evaluate(value=>{(window as unknown as {saveFailure:{failPicker:boolean}}).saveFailure.failPicker=value;},failPicker);
    await page.getByRole("button",{name:"Export raw configuration",exact:true}).click();
    await expect(page.getByRole("dialog").getByRole("alert")).toContainText("The file could not be saved");
    await page.keyboard.press("Escape");
  }
  expect(downloads).toBe(0);
  expect(await page.evaluate(()=>(window as unknown as {saveFailure:{aborts:number;closes:number}}).saveFailure)).toMatchObject({aborts:1,closes:0});
});

test("a pending destination is single-flight and cannot save after leaving the project", async ({page}) => {
  await page.addInitScript(()=>{
    const state={calls:0,opens:0,release:()=>{}};
    Object.assign(window,{pendingSave:state,showSaveFilePicker:()=>{
      state.calls++;
      return new Promise(resolve=>{state.release=()=>resolve({createWritable:async()=>{state.opens++;return {write:async()=>{},close:async()=>{},abort:async()=>{}};}});});
    }});
  });
  let reads=0;await page.route("**/config/raw*",route=>{reads++;return route.abort();});
  await openSettings(page);
  const button=page.getByRole("button",{name:"Export raw configuration",exact:true});
  await button.click();
  await expect(page.getByRole("button",{name:"Exporting…",exact:true})).toBeDisabled();
  await page.getByRole("button",{name:"Exporting…",exact:true}).evaluate(node=>node.dispatchEvent(new MouseEvent("click",{bubbles:true})));
  await page.getByRole("navigation",{name:"Primary navigation",exact:true}).getByRole("link",{name:"Overview",exact:true}).click();
  await page.evaluate(()=>(window as unknown as {pendingSave:{release:()=>void}}).pendingSave.release());
  expect(await page.evaluate(()=>(window as unknown as {pendingSave:{calls:number;opens:number}}).pendingSave)).toMatchObject({calls:1,opens:0});
  expect(reads).toBe(0);await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("leaving while a file write is pending aborts it before commit", async ({page}) => {
  await page.addInitScript(()=>{
    const state={writing:false,aborts:0,closes:0,release:()=>{}};
    Object.assign(window,{pendingWrite:state,showSaveFilePicker:async()=>({createWritable:async()=>({
      write:()=>{state.writing=true;return new Promise<void>(resolve=>{state.release=resolve;});},
      close:async()=>{state.closes++;},abort:async()=>{state.aborts++;},
    })})});
  });
  await page.route("**/api/v1/projects/*/config",async route=>{
    const response=await route.fetch(),body=await response.json();body.config.execution.backend="local";
    await route.fulfill({response,json:body});
  });
  await page.route("**/config/raw?download=true",route=>route.fulfill({contentType:"text/plain",body:"# saved settings\n"}));
  await openSettings(page);
  await page.getByRole("button",{name:"Export raw configuration",exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as unknown as {pendingWrite:{writing:boolean}}).pendingWrite.writing)).toBe(true);
  await page.getByRole("navigation",{name:"Primary navigation",exact:true}).getByRole("link",{name:"Overview",exact:true}).click();
  await page.evaluate(()=>(window as unknown as {pendingWrite:{release:()=>void}}).pendingWrite.release());
  await expect.poll(()=>page.evaluate(()=>(window as unknown as {pendingWrite:{aborts:number}}).pendingWrite.aborts)).toBe(1);
  expect(await page.evaluate(()=>(window as unknown as {pendingWrite:{closes:number}}).pendingWrite.closes)).toBe(0);
});

test("attach an executor definition in Technical details without editing project settings", async ({page}) => {
  let available = false;
  const status = () => ({image:"sample-executor:1",available,
    missing_images:available?[]:["sample-executor:1"],digest:available?"c".repeat(64):null,
    source:available?"managed":"missing",revision:"b".repeat(64)});
  await page.route("**/api/v1/projects/*/config", async route => {
    const response=await route.fetch(), body=await response.json();
    body.config.execution.backend="container";
    body.config.container.runtime="podman";
    body.config.container.image="sample-executor:1";
    await route.fulfill({response,json:body});
  });
  await page.route("**/executor-recipe", async route => {
    if(route.request().method()==="PUT") {
      const body=route.request().postDataJSON();
      expect(Buffer.from(body.source,"base64").toString()).toBe("FROM scratch\n");
      expect(body.revision).toBe("b".repeat(64));
      expect(body.expected_digest).toBeNull();
      available=true;
    }
    await route.fulfill({json:status()});
  });
  await page.route("**/executor-recipe/preview", route => route.fulfill({json:{...status(),
    available:true,missing_images:[],upload_image:"sample-executor:1",expected_digest:null}}));
  await openSettings(page);
  await page.locator('details[data-setting-purpose="technical"] > summary').click();
  await page.getByRole("button",{name:"Image definition",exact:true}).click();
  const dialog=page.getByRole("dialog");
  await dialog.getByLabel("Definition file",{exact:true}).setInputFiles({name:"Dockerfile",
    mimeType:"text/plain",buffer:Buffer.from("FROM scratch\n")});
  await expect(dialog.getByRole("button",{name:"Save recipe",exact:true})).toBeEnabled();
  await dialog.getByRole("button",{name:"Save recipe",exact:true}).click();
  await expect(dialog).not.toContainText("Include Docker build files");
  await expect(dialog.getByLabel("Definition file",{exact:true})).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(page.locator(".settings-save-bar")).toHaveCount(0);
});

test("invalid or stale recipe evidence cannot save or unlock a complete export", async ({page}) => {
  const status={image:"sample-executor:1",available:false,missing_images:["sample-executor:1"],
    digest:null,source:"missing",revision:"b".repeat(64)};
  let saves=0;
  await page.route("**/api/v1/projects/*/config",async route => {
    const response=await route.fetch(), body=await response.json();
    body.config.execution.backend="container";
    body.config.container.image=status.image;
    await route.fulfill({response,json:body});
  });
  await page.route("**/executor-recipe",route => {
    if(route.request().method()==="PUT") {
      saves++;
      return route.fulfill({status:409,json:{detail:{code:"recipe_changed"}}});
    }
    return route.fulfill({json:status});
  });
  await openSettings(page);
  await page.locator('details[data-setting-purpose="technical"] > summary').click();
  await page.getByRole("button",{name:"Image definition",exact:true}).click();
  const dialog=page.getByRole("dialog"), save=dialog.getByRole("button",{name:"Save recipe",exact:true});
  for(const response of [
    {status:400,json:{detail:{code:"recipe_invalid"}}},
    {status:503,json:{detail:{code:"recipe_store_corrupt",recovery:"executor-recipes"}}},
    {status:200,json:{...status,available:true,missing_images:[],upload_image:status.image,
      expected_digest:"invalid"}},
  ]) {
    await page.route("**/executor-recipe/preview",route => route.fulfill(response));
    await dialog.getByLabel("Definition file",{exact:true}).setInputFiles({name:"Dockerfile",
      mimeType:"text/plain",buffer:Buffer.from("FROM scratch\n")});
    await expect(dialog.getByRole("alert")).toBeVisible();
    if(response.status===503) await expect(dialog.getByRole("alert")).toContainText("all projects");
    await expect(save).toBeDisabled();
    await expect(dialog.getByRole("button",{name:"Export",exact:true})).toHaveCount(0);
    await page.unroute("**/executor-recipe/preview");
  }
  expect(saves).toBe(0);
  await page.route("**/executor-recipe/preview",route => route.fulfill({json:{...status,
    available:true,missing_images:[],upload_image:status.image,expected_digest:null}}));
  await dialog.getByLabel("Definition file",{exact:true}).setInputFiles({name:"Dockerfile",
    mimeType:"text/plain",buffer:Buffer.from("FROM scratch\n")});
  await expect(save).toBeEnabled();
  await save.click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(save).toBeEnabled();
  expect(saves).toBe(1);
  await page.keyboard.press("Escape");
});

test("raw configuration preview and download are original and Settings stays compact", async ({ page }) => {
  await page.route("**/api/v1/projects/*/config", async route => {
    const response=await route.fetch(), body=await response.json();
    body.config.execution.backend="local";
    await route.fulfill({response,json:body});
  });
  await openSettings(page);
  const panel = page.locator("#project-settings");
  await expect(page.locator(".portable-settings, #project-config-editor")).toHaveCount(0);
  await expect(panel.getByText("Set for this project", { exact: true })).toHaveCount(0);
  await expect(panel.getByText(/Prepare one setting at a time/)).toHaveCount(0);
  const original = await page.request.get("/api/v1/projects/alpha/config/raw");
  expect(original.status()).toBe(200);
  const expected = await original.body();
  const download = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Export raw configuration", exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("config.toml");
  expect(await readFile((await file.path())!)).toEqual(expected);
  const preview = panel.getByRole("button", { name: "Preview raw configuration", exact: true });
  await preview.click();
  const dialog = page.getByRole("dialog", { name: "Preview raw configuration", exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator("pre")).toHaveText(expected.toString("utf8"), { useInnerText: false });
  await expect(dialog.getByRole("button", { name: "Close", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(preview).toBeFocused();
  await expect(page.locator(".raw-config-actions pre")).toHaveCount(0);
});

test("container export is a complete download without an application wizard", async ({ page }) => {
  await page.route("**/api/v1/projects/*/config",async route => {
    const response=await route.fetch(),body=await response.json();body.config.execution.backend="container";
    await route.fulfill({response,json:body});
  });
  const bundle=Buffer.from([0x50,0x4b,0x03,0x04,0x00]);
  await page.route("**/config/raw?download=true&include_build=true",route => route.fulfill({contentType:"application/zip",body:bundle}));
  await openSettings(page);
  const actions=page.locator(".raw-config-actions");
  await expect(actions.locator(":scope > button")).toHaveCount(2);
  await expect(actions.locator(":scope > small, :scope > p, :scope > label")).toHaveCount(0);
  const download=page.waitForEvent("download");
  await actions.getByRole("button",{name:"Export raw configuration",exact:true}).click();
  const file=await download;
  expect(file.suggestedFilename()).toBe("adore-docker-build.zip");
  expect(await readFile((await file.path())!)).toEqual(bundle);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("missing or corrupt build sources show a concise export error without recipe controls", async ({page}) => {
  await page.route("**/api/v1/projects/*/config",async route => {
    const response=await route.fetch(),body=await response.json();body.config.execution.backend="container";
    await route.fulfill({response,json:body});
  });
  await openSettings(page);
  const open=page.getByRole("button",{name:"Export raw configuration",exact:true});
  let downloads=0;page.on("download",()=>downloads++);
  for (const width of [1520,390]) {
    await page.setViewportSize({width,height:900});
    for (const reply of [
      {status:400,contentType:"application/json",body:JSON.stringify({detail:{code:"recipe_base_missing"}})},
      {status:200,contentType:"application/zip",body:"invalid archive"},
    ]) {
      await page.route("**/config/raw?download=true&include_build=true",route=>route.fulfill(reply));
      await open.click();
      const dialog=page.getByRole("dialog");
      await expect(dialog.getByRole("alert")).toBeVisible();
      await expect(dialog.getByRole("checkbox")).toHaveCount(0);
      await expect(dialog.locator('input[type="file"]')).toHaveCount(0);
      await expect(dialog.getByRole("button",{name:"Close",exact:true})).toBeFocused();
      const bounds=await dialog.boundingBox();
      expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(width);
      await page.keyboard.press("Escape");await expect(open).toBeFocused();
      await page.unroute("**/config/raw?download=true&include_build=true");
    }
  }
  expect(downloads).toBe(0);
});

test("raw configuration failures and malformed transports expose no preview", async ({ page }) => {
  await openSettings(page);
  const preview = page.getByRole("button", { name: "Preview raw configuration", exact: true });
  for (const response of [
    { status: 503, contentType: "application/json", body: JSON.stringify({ detail: { code: "config_corrupt" } }) },
    { status: 200, contentType: "text/html", body: "<script>window.rawInjected = true</script>" },
    { status: 200, contentType: "text/plain", body: "" },
  ]) {
    await page.route("**/config/raw*", route => route.fulfill(response));
    await preview.click();
    await expect(page.getByRole("dialog").getByRole("alert")).toBeVisible();
    await expect(page.getByRole("dialog").locator("pre")).toHaveCount(0);
    await expect(page.locator(".raw-config-actions > [role=alert]")).toHaveCount(0);
    await page.keyboard.press("Escape");
    await page.unroute("**/config/raw*");
  }
  await preview.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
});

test("raw configuration inline secrets render as text and are cleared on scope change", async ({ page }) => {
  await openSettings(page);
  const original = '# inline fixture\r\n[private]\r\nvalue="<script>window.rawInjected=true</script>"\r\n';
  await page.route("**/config/raw*", route => route.fulfill({ contentType: "text/plain", body: original }));
  await page.getByRole("button", { name: "Preview raw configuration", exact: true }).click();
  const dialog = page.getByRole("dialog");
  expect(await dialog.locator("pre").textContent()).toBe(original);
  expect(await page.evaluate(() => "rawInjected" in window)).toBe(false);
  await page.keyboard.press("Escape");
  let release!: () => void;
  let captured!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const started = new Promise<void>(resolve => { captured = resolve; });
  await page.unroute("**/config/raw*");
  await page.route("**/config/raw*", async route => { captured(); await held; await route.fulfill({ contentType: "text/plain", body: original }).catch(() => undefined); });
  await page.getByRole("button", { name: "Preview raw configuration", exact: true }).click();
  await started;
  await page.keyboard.press("Escape");
  await page.getByRole("navigation", { name: "Primary navigation", exact: true }).getByRole("link", { name: "Overview", exact: true }).click();
  release();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(await page.evaluate(() => Object.values(localStorage).some(value => value.includes("rawInjected")))).toBe(false);
});

test("developer cannot view or download original unredacted configuration", async ({ page }) => {
  await openSettings(page, "developer");
  await expect(page.locator(".raw-config-actions")).toHaveCount(0);
  for (const project of ["alpha", "beta"]) {
    expect((await page.request.get(`/api/v1/projects/${project}/config/raw?download=true`)).status()).toBe(403);
  }
});

for (const [locale, preview, exportName, fileName] of [
  ["en", "Preview raw configuration", "Export raw configuration", "Definition file"],
  ["fr", "Voir la configuration brute", "Exporter la configuration brute", "Fichier de définition"],
  ["de", "Originalkonfiguration anzeigen", "Originalkonfiguration exportieren", "Definitionsdatei"],
  ["ro", "Previzualizare configurație originală", "Exportă configurația brută", "Fișier de definiție"],
]) {
  test(`raw configuration controls support ${locale} at 390px`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.route("**/api/v1/projects/*/config",async route => {
      const response=await route.fetch(), body=await response.json();
      body.config.execution.backend="container";
      await route.fulfill({response,json:body});
    });
    await page.route("**/executor-recipe",route => route.fulfill({json:{image:"sample:1",
      available:false,missing_images:["sample:1"],digest:null,source:"missing",revision:"b".repeat(64)}}));
    await openSettings(page);
    const me = await (await page.request.get("/api/v1/me")).json();
    await page.request.patch("/api/v1/me/preferences", { headers: { "X-CSRF-Token": me.csrf }, data: { language: locale, theme: "dark" } });
    await page.reload();
    await page.getByRole("button", { name: preview, exact: true }).click();
    const dialog = page.getByRole("dialog", { name: preview, exact: true });
    await expect(dialog).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    const bundle=Buffer.from([0x50,0x4b,0x03,0x04,0x00]);
    await page.route("**/config/raw?download=true&include_build=true",route=>route.fulfill({contentType:"application/zip",body:bundle}));
    const download=page.waitForEvent("download");
    await page.getByRole("button",{name:exportName,exact:true}).click();
    expect((await download).suggestedFilename()).toBe("adore-docker-build.zip");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByLabel(fileName,{exact:true})).toHaveCount(0);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  });
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test,expect} from "@playwright/test";
import { saveSettings, settingsSave } from "./settings-actions";
const externalEnvironmentCopy = {
  en: {title:"Executor runs in a container",instructions:"Environment preparation instructions",admin:"Ask the ADORE administrator"},
  ro: {title:"Executorul rulează într-un container",instructions:"Instrucțiuni pentru pregătirea mediului",admin:"Solicită administratorului ADORE"},
  fr: {title:"L’exécuteur fonctionne dans un conteneur",instructions:"Instructions de préparation de l’environnement",admin:"Demander à l’administrateur ADORE"},
  de: {title:"Executor läuft in einem Container",instructions:"Anleitung zur Vorbereitung der Umgebung",admin:"Den ADORE-Administrator"},
};
import type {Locale} from "../src/i18n";

test("container runtime dropdown supports WSL, cancel and manual save", async ({page}) => {
  const wsl = "wsl -d Ubuntu -- docker";
  const wslImage = "adore-executor-base:1.0.0";
  let discoveryAvailable = true;
  await page.route("**/api/v1/executor-runtimes", route => discoveryAvailable
    ? route.fulfill({json: {commands: ["docker", wsl]}})
    : route.fulfill({status: 503}));
  await page.route("**/api/v1/executor-images?*", route => {
    const runtime = new URL(route.request().url()).searchParams.get("runtime");
    return route.fulfill({json: {runtime, available: runtime === wsl,
      images: runtime === wsl ? [wslImage] : []}});
  });
  const session = await page.request.post("/api/v1/session", {data: {username: "admin", password: "admin"}});
  expect(session.ok()).toBeTruthy();
  const projects = await (await page.request.get("/api/v1/projects")).json();
  const id = projects.find((project: {name: string}) => project.name === "alpha").id;
  const configUrl = "/api/v1/projects/" + id + "/config";
  const original = (await (await page.request.get(configUrl)).json()).config.container.runtime;
  await page.goto("/projects/" + id + "/configuration");
  await page.getByRole("tab", {name: "Settings", exact: true}).click();
  const group = page.locator('[data-setting-purpose="executor"]');
  const openGroup = async () => {
    if (await group.getAttribute("open") === null) await group.locator(":scope > summary").click();
  };
  await openGroup();
  const runtime = page.locator('[id="setting-container.runtime"]');
  const picker = runtime.getByRole("combobox", {name: "Container runtime command"});
  const edit = () => runtime.getByRole("button", {name: "Edit Container runtime command"}).click();
  await edit();
  await expect(picker.locator("option", {hasText: wsl})).toHaveCount(1);
  await picker.selectOption(wsl);
  await expect(settingsSave(page)).toBeEnabled();
  expect((await (await page.request.get(configUrl)).json()).config.container.runtime).toBe(original);
  const image = page.locator('[id="setting-container.image"]');
  await image.getByRole("button", {name: "Edit Agent container image"}).click();
  await expect(image.locator("datalist option")).toHaveAttribute("value", wslImage);
  await image.getByRole("button", {name: "Cancel", exact: true}).click();
  await picker.selectOption({label: "Manual runtime command"});
  await expect(runtime.getByRole("textbox", {name: "Manual runtime command"})).toHaveValue(wsl);
  await runtime.getByRole("button", {name: "Cancel", exact: true}).click();
  await expect(settingsSave(page)).toBeDisabled();

  discoveryAvailable = false;
  await edit();
  await expect(runtime.getByText("Could not detect container runtimes.")).toBeVisible();
  const manual = runtime.getByRole("textbox", {name: "Manual runtime command"});
  await expect(manual).toHaveValue(original);
  const custom = "wsl -d Ubuntu --exec docker";
  try {
    await manual.fill(custom);
    await saveSettings(page, true);
    expect((await (await page.request.get(configUrl)).json()).config.container.runtime).toBe(custom);
  } finally {
    if ((await (await page.request.get(configUrl)).json()).config.container.runtime === custom) {
      await openGroup();
      await edit();
      await manual.fill(original);
      await saveSettings(page, true);
    }
  }
});

test("image builds stay external and Agent and model gives container instructions",async({page})=>{
  await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
  await page.goto("/");await page.getByLabel("Username",{exact:false}).fill("admin");await page.getByLabel("Password",{exact:false}).fill("admin");await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("navigation",{name:"Primary navigation",exact:true})).toBeVisible();
  const projects=await(await page.request.get("/api/v1/projects")).json(),id=projects.find((p:{name:string})=>p.name==="alpha").id;
  await page.goto("/projects/"+id+"/configuration");
  await expect(page.locator("#project-settings").getByText(/Isolated environment/i)).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Build and verify",exact:true})).toHaveCount(0);
  await page.getByRole("tab",{name:"Settings",exact:true}).click();
  // Six agent settings plus the chosen backend, runtime and image.
  await page.locator('[data-setting-purpose="executor"] > summary').click();
  const panel=page.locator(".executor-environment");
  await expect(panel.getByRole("heading",{name:"Executor runs in a container",exact:true})).toBeVisible();
  const config=await(await page.request.get("/api/v1/projects/"+id+"/config")).json();
  await expect(panel).toContainText(config.executor_environment.image);
  await expect(panel.getByText("executor/Dockerfile",{exact:true})).toHaveCount(0);
  await panel.getByText("Environment preparation instructions",{exact:true}).click();
  await expect(panel).toContainText("executor/Dockerfile");
  await expect(panel).toContainText(config.executor_environment.config_path);
  await expect(panel).toContainText("USER adore");
  await expect(panel).toContainText("does not start a build");
  await panel.screenshot({path:"test-results/executor-environment-desktop.png"});
  await page.setViewportSize({width:390,height:844});
  const rect=await panel.boundingBox();expect(rect!.x+rect!.width).toBeLessThanOrEqual(390);
  await panel.screenshot({path:"test-results/executor-environment-mobile.png"});
  expect((await(await page.request.get("/api/v1/projects/"+id+"/config")).json()).revision).toBe(config.revision);
});

for (const locale of ["en","ro","fr","de"] as Locale[]) {
  test(`external instructions are localized and hide administrator paths ${locale}`,async({page})=>{
    await page.context().route("**/*",route=>new URL(route.request().url()).origin==="http://127.0.0.1:18765"?route.continue():route.abort());
    await page.addInitScript(value=>localStorage.setItem("adore-language",value),locale);
    await page.goto("/");
    const session=await page.request.post("/api/v1/session",{data:{username:"developer",password:"test-password"}});
    expect(session.ok()).toBeTruthy();
    // A saved account language overrides the browser's: set it for this test and restore it after.
    const headers={"X-CSRF-Token":(await session.json()).csrf};
    const previous=(await(await page.request.get("/api/v1/me/preferences")).json()).language ?? null;
    expect((await page.request.patch("/api/v1/me/preferences",{data:{language:locale},headers})).ok()).toBeTruthy();
    try {
      const projects=await(await page.request.get("/api/v1/projects")).json(),id=projects.find((p:{name:string})=>p.name==="alpha").id;
      await page.goto("/projects/"+id+"/executor");
      await page.locator('[data-setting-purpose="executor"] > summary').click();
      const c=externalEnvironmentCopy[locale],panel=page.locator(".executor-environment");
      await expect(panel.getByRole("heading",{name:c.title,exact:true})).toBeVisible();
      await panel.getByText(c.instructions,{exact:true}).click();
      await expect(panel).toContainText(c.admin);
      await expect(panel).toContainText("executor/Dockerfile");
      await expect(panel).not.toContainText("profiles/alpha/config.toml");
      await expect(panel.getByRole("textbox")).toHaveCount(0);
      const config=await(await page.request.get("/api/v1/projects/"+id+"/config")).json();
      config.executor_environment={backend:"local",image:null,config_path:null};
      config.config.execution.backend="local";
      await page.route("**/api/v1/projects/"+id+"/config",route=>route.fulfill({json:config}));
      await page.reload();
      await expect(page.locator("#project-settings")).toBeVisible();
      await expect(panel).toHaveCount(0);
    } finally {
      // An account without a saved language is left on English, the language other specs expect.
      expect((await page.request.patch("/api/v1/me/preferences",{data:{language:previous ?? "en"},headers})).ok()).toBeTruthy();
    }
  });
}

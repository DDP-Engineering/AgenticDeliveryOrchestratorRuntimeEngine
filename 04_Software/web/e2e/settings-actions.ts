/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {expect, type Page} from "@playwright/test";
import {settingsSaveCopy} from "../src/settingsSave";
import type {Locale} from "../src/i18n";

/** The one configuration Save, distinct from credential and price-record actions. */
export function settingsSave(page: Page, locale: Locale = "en") {
 return page.locator(".settings-save-bar").getByRole("button",{name:settingsSaveCopy[locale].save,exact:true});
}

export function settingsImpact(page: Page) { return page.locator("dialog.settings-impact-dialog"); }

/** Exercise the actual user Save and its optional explicit effect confirmation. */
export async function saveSettings(page: Page, important = false, locale: Locale = "en") {
 await expect(settingsSave(page,locale)).toBeEnabled();
 await settingsSave(page,locale).click();
 if (important) {
  await expect(settingsImpact(page)).toBeVisible();
  await settingsImpact(page).getByRole("button",{name:settingsSaveCopy[locale].confirm,exact:true}).click();
 }
 await expect(settingsImpact(page)).toHaveCount(0);
 await expect(settingsSave(page,locale)).toBeDisabled();
}

/** Close confirmation without publication, then explicitly discard the draft. */
export async function discardSettings(page: Page, locale: Locale = "en") {
 if (await settingsImpact(page).count()) {
  await settingsImpact(page).getByRole("button",{name:settingsSaveCopy[locale].cancel,exact:true}).click();
 }
 const discard=page.locator(".settings-save-bar").getByRole("button",{name:settingsSaveCopy[locale].discard,exact:true});
 await expect(discard).toBeEnabled();
 await discard.click();
 await expect(discard).toBeDisabled();
}

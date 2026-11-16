/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { azureCopy, azureSettingLabel, validAzureNames } from "../src/azureDevops.ts";
import { settingRows, validBatchValues, validPendingConfig, settingPurpose } from "../src/settings.ts";
import { normalizeSettingDraft, settingDraftValue } from "../src/settingsSave.ts";
import { settingHelp } from "../src/settingHelp.ts";

const keys = ["platform.organization", "platform.project", "platform.area_path", "platform.work_item_types", "platform.closed_states"];
test("Azure scope and authentication guidance exists in all interface languages", () => {
  for (const locale of ["en", "fr", "de", "ro"]) {
    for (const key of keys) {
      assert.ok(azureSettingLabel(key, locale).length > 5);
      assert.match(settingHelp(key, locale), /Services/);
      assert.equal(settingPurpose(key), "repository");
    }
    assert.match(azureCopy[locale].auth, /Azure CLI/);
    assert.match(azureCopy[locale].labels, /Work[ -]Item/);
    assert.match(azureCopy[locale].labels, /PR/);
    assert.ok(azureCopy[locale].verified.length > 20);
  }
  assert.equal(azureSettingLabel("platform.login", "en"), null);
});

test("Azure process-name lists support reviewed edits including native names with spaces", () => {
  const key = "platform.work_item_types";
  const config = { platform: { work_item_types: ["Bug", "User Story"] } };
  const [row] = settingRows(config, [{key, edit_key:key, editable:true, restart:true, source:"project", type:"list"}]);
  assert.equal(row.input, "azure-names");
  assert.equal(settingDraftValue(row, config), "Bug\nUser Story");
  assert.equal(normalizeSettingDraft(row, "Bug\nRequirement\nCustom Story"), '["Bug","Requirement","Custom Story"]');
  assert.equal(normalizeSettingDraft(row, "Bug\nBug"), null);
  assert.equal(normalizeSettingDraft(row, ""), null);
  assert.equal(validBatchValues({[key]: ["Bug", "Requirement"]}), true);
  assert.equal(validBatchValues({[key]: [true]}), false);
  const proposed = ["Closed", "Released"];
  const pending = {base_revision:"a".repeat(64), candidate_revision:"b".repeat(64),
    key:"platform.closed_states", value:JSON.stringify(proposed), proposed_value:proposed,
    created_at:"2026-11-15T10:00:00Z", restart_required:true};
  assert.equal(validPendingConfig(pending), true);
  assert.equal(validPendingConfig({...pending, proposed_value:[], value:"[]"}), false);
  for (const value of [null, "Bug", [], [1], [""], [" Bug"], ["Bug", "Bug"], ["bad\u0000"], Array(33).fill("Bug")]) {
    assert.equal(validAzureNames(value), false);
  }
});

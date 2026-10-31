/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { settingVisible, settingPurpose } from "../src/settings.ts";
import { executorSettingLabel } from "../src/executorSettings.ts";

test("package permission has localized container-only agent settings", () => {
  assert.equal(settingVisible("container.system_packages", true, "pi", "container"), true);
  assert.equal(settingVisible("container.system_packages", true, "pi", "local"), false);
  assert.equal(settingPurpose("container.system_packages"), "executor");
  for (const locale of ["en", "fr", "de", "ro"]) {
    assert.ok(executorSettingLabel("container.system_packages", locale)?.length > 10);
  }
});

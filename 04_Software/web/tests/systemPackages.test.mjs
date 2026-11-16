import { test } from "node:test";
import assert from "node:assert/strict";
import { settingVisible, settingPurpose } from "../src/settings.ts";
import { executorSettingLabel } from "../src/executorSettings.ts";

test("package permission has localized container-only agent settings", () => {
  assert.equal(settingVisible("container.system_packages", true, "container"), true);
  assert.equal(settingVisible("container.system_packages", true, "local"), false);
  assert.equal(settingPurpose("container.system_packages"), "executor");
  for (const locale of ["en", "fr", "de", "ro"]) {
    assert.ok(executorSettingLabel("container.system_packages", locale)?.length > 10);
  }
});

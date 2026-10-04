/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SETTING_HELP, settingHelp } from "../src/settingHelp.ts";

const catalog = JSON.parse(readFileSync(new URL("../src/settingKeys.json", import.meta.url), "utf8"));
const locales = ["en", "fr", "de", "ro"];

test("every catalogued setting has a specific help text in every locale", () => {
  for (const locale of locales) {
    for (const key of catalog) {
      const text = SETTING_HELP[locale][key];
      assert.ok(typeof text === "string" && text.trim().length >= 25, `${locale} ${key}`);
    }
  }
});

test("help texts exist only for catalogued settings", () => {
  for (const locale of locales) {
    assert.deepEqual(Object.keys(SETTING_HELP[locale]).sort(), [...catalog].sort(), locale);
  }
});

test("translations differ from the English text", () => {
  for (const locale of ["fr", "de", "ro"]) {
    const same = catalog.filter(key => SETTING_HELP[locale][key] === SETTING_HELP.en[key]);
    assert.deepEqual(same, [], locale);
  }
});

test("named entries resolve to their pattern text; unknown keys have none", () => {
  assert.equal(settingHelp("executor.commands.codex.model", "en"), SETTING_HELP.en["executor.commands.*.model"]);
  assert.equal(settingHelp("container.runtime_env.UV_LINK_MODE", "de"), SETTING_HELP.de["container.runtime_env.*"]);
  assert.equal(settingHelp("workflow.stage_timeout_overrides.build", "fr"), SETTING_HELP.fr["workflow.stage_timeout_overrides.*"]);
  assert.equal(settingHelp("workflow.kind_labels.enhancement", "ro"), SETTING_HELP.ro["workflow.kind_labels.*"]);
  assert.equal(settingHelp("budgets.max_iterations", "en"), SETTING_HELP.en["budgets.max_iterations"]);
  assert.equal(settingHelp("unknown.setting", "en"), undefined);
  assert.equal(settingHelp("container.runtime_env.A.B", "en"), undefined);  // pattern needs the same depth
});

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { editValue, hasDefault, settingGroups, settingRows, validSettingCatalog, validPendingConfig } from "../src/settings.ts";
import { publicationCopy, publicationValue } from "../src/settingsCopy.ts";

test("publication state names exact booleans in every locale", () => {
 for (const locale of ["en", "fr", "de", "ro"]) {
  assert.equal(publicationValue(true, locale), publicationCopy[locale].draft);
  assert.equal(publicationValue("true", locale), publicationCopy[locale].draft);
  assert.equal(publicationValue(false, locale), publicationCopy[locale].ready);
  assert.equal(publicationValue("false", locale), publicationCopy[locale].ready);
  for (const invalid of [null, 0, 1, "False", {}, []]) assert.equal(publicationValue(invalid, locale), null);
 }
});

test("reviewer list alone is editable and pending arrays have exact authority", () => {
 const rows = settingRows(config, [{ ...meta("delivery.reviewers", "project", true), type: "list" }]);
 assert.equal(rows[0].input, "reviewers");
 const candidate = { base_revision: "a".repeat(64), candidate_revision: "b".repeat(64), key: "delivery.reviewers", value: '["alice","bob"]', proposed_value: ["alice", "bob"], created_at: "2026-10-08T18:00:00Z", restart_required: false };
 assert.equal(validPendingConfig(candidate), true);
 for (const bad of [{ ...candidate, value: '["other"]' }, { ...candidate, key: "container.egress.allowlist" }, { ...candidate, proposed_value: [] }, { ...candidate, proposed_value: [1] }, { ...candidate, proposed_value: ["--repo"] }]) assert.equal(validPendingConfig(bad), false);
});

const config = {
  platform: { kind: "gitlab", repo: "group/project" },
  executor: { default: "opencode", commands: { opencode: { command: "opencode run", model: "openai/gpt" } } },
  budgets: { max_iterations: 20, max_cost_usd: 5.5 },
  delivery: { reviewers: ["dan"], draft: true },
  container: { egress: { allowlist: [] } },
};
const meta = (key, source, editable, restart = false, edit_key = key) =>
  ({ key, edit_key, source, editable, restart, default: key === "budgets.max_iterations" ? 20 : null,
    type: key === "budgets.max_iterations" ? "integer" : key === "budgets.max_cost_usd" ? "number" : key === "delivery.draft" ? "boolean" : "text",
    choices: key === "platform.kind" ? ["gitlab", "github", "gitea"] : key === "executor.default" ? ["opencode", "pi", "codex", "qwen"] : [], minimum: null, maximum: null });
const settings = [
  meta("budgets.max_cost_usd", "default", true),
  meta("budgets.max_iterations", "project", true),
  meta("container.egress.allowlist", "default", false, true),
  meta("delivery.draft", "default", true),
  meta("delivery.reviewers", "project", false),
  meta("executor.commands.opencode.command", "project", false, true, "executor.opencode.command"),
  meta("executor.commands.opencode.model", "project", true, true, "executor.opencode.model"),
  meta("executor.default", "default", true, true),
  meta("platform.kind", "project", true, true),
  meta("platform.repo", "project", true, true),
];

test("rows carry value, source, edit key, restart and an input kind", () => {
  const rows = new Map(settingRows(config, settings).map(row => [row.key, row]));
  const model = rows.get("executor.commands.opencode.model");
  assert.deepEqual(
    { group: model.group, value: model.value, source: model.source, editKey: model.editKey, restart: model.restart, input: model.input },
    { group: "executor", value: "openai/gpt", source: "project", editKey: "executor.opencode.model", restart: true, input: "text" },
  );
  assert.equal(rows.get("budgets.max_cost_usd").input, "number");
  assert.equal(rows.get("delivery.draft").input, "boolean");
  assert.equal(rows.get("platform.kind").input, "choice");
  assert.deepEqual(rows.get("platform.kind").choices, ["gitlab", "github", "gitea"]);
  assert.deepEqual(rows.get("executor.default").choices, ["opencode", "pi", "codex", "qwen"]);
  assert.equal(rows.get("budgets.max_iterations").input, "number");
  assert.equal(rows.get("budgets.max_iterations").step, "1");  // whole number, at least 1
  assert.equal(rows.get("budgets.max_iterations").defaultValue, 20);
  assert.equal(rows.get("budgets.max_cost_usd").defaultValue, null);
  assert.equal(rows.get("budgets.max_cost_usd").step, "any");
  assert.equal(rows.get("executor.commands.opencode.model").step, undefined);
  for (const key of ["delivery.reviewers", "executor.commands.opencode.command", "container.egress.allowlist"]) {
    assert.equal(rows.get(key).input, "none", key);
  }
});

test("purpose groups retain every row once in catalog order", () => {
  const groups = settingGroups(settingRows(config, settings), false);
  assert.deepEqual(groups.map(group => group.name), ["repository", "agent", "isolation", "rules", "limits"]);
  const keys = groups.flatMap(group => group.rows.map(row => row.key));
  assert.equal(new Set(keys).size, settings.length);
  assert.deepEqual([...keys].sort(), settings.map(item => item.key).sort());
});

test("the project-set filter keeps project rows and drops empty groups", () => {
  const groups = settingGroups(settingRows(config, settings), true);
  assert.deepEqual(groups.map(group => [group.name, group.rows.map(row => row.key)]), [
    ["repository", ["platform.repo", "platform.kind"]],
    ["agent", ["executor.commands.opencode.command", "executor.commands.opencode.model"]],
    ["rules", ["delivery.reviewers"]],
    ["limits", ["budgets.max_iterations"]],
  ]);
});

test("edit values start from the current value", () => {
  assert.equal(editValue(true), "true");
  assert.equal(editValue(5.5), "5.5");
  assert.equal(editValue(null), "");
  assert.equal(editValue("x"), "x");
});

test("a default is shown unless it is missing or empty", () => {
  for (const value of [null, undefined, "", [], {}]) assert.equal(hasDefault(value), false, JSON.stringify(value));
  for (const value of [0, false, "adore", ["a"], { bug: "fix" }]) assert.equal(hasDefault(value), true, JSON.stringify(value));
});


test("purpose groups and server choices replace inferred browser domains", () => {
  const rows = settingRows(config, settings.map(item => ({ ...item, type: item.key === "budgets.max_iterations" ? "integer" : "text", choices: item.key === "platform.kind" ? ["gitea"] : [], minimum: item.key === "budgets.max_iterations" ? 1 : null, maximum: null })));
  assert.deepEqual(rows.find(row => row.key === "platform.kind").choices, ["gitea"]);
  assert.equal(rows.find(row => row.key === "budgets.max_iterations").minimum, 1);
  assert.deepEqual(settingGroups(rows, false).map(group => group.name), ["repository", "agent", "isolation", "rules", "limits"]);
  const unknown = settingRows(config, [{ ...settings[0], type: "unknown" }]);
  assert.equal(unknown[0].input, "none");
});


test("catalog and candidate transport reject malformed or missing authority", () => {
  assert.equal(validSettingCatalog(settings), true);
  for (const bad of [null, {}, [{ ...settings[0], choices: null }], [{ ...settings[0], minimum: Infinity }], [settings[0], settings[0]], [{ ...settings[0], type: "unknown" }]]) assert.equal(validSettingCatalog(bad), false);
  const candidate = { base_revision: "a".repeat(64), candidate_revision: "b".repeat(64), key: "budgets.max_iterations", value: "12", proposed_value: 12, created_at: "2026-10-05T12:00:00Z", restart_required: false };
  assert.equal(validPendingConfig(candidate), true);
  assert.equal(validPendingConfig(null), true);
  for (const bad of [{}, { ...candidate, proposed_value: {} }, { ...candidate, base_revision: "stale" }, { ...candidate, created_at: "2026-10-05T12:00:00" }, { ...candidate, endpoint: { protocol: "anthropic" } }]) assert.equal(validPendingConfig(bad), false);
});


test("every catalog key has an understandable English label and purpose", async () => {
  const { readFileSync } = await import("node:fs");
  const { settingLabel, settingsCopy } = await import("../src/settingsCopy.ts");
  const { settingPurpose } = await import("../src/settings.ts");
  const catalog = JSON.parse(readFileSync(new URL("../src/settingKeys.json", import.meta.url), "utf8"));
  for (const key of catalog) {
    const label = settingLabel(key);
    assert.ok(label.length > 3 && !label.includes("_"), key);
    assert.ok(settingsCopy.en[settingPurpose(key)], key);
  }
  assert.deepEqual(Object.keys(settingsCopy.fr).sort(), Object.keys(settingsCopy.en).sort());
  assert.deepEqual(Object.keys(settingsCopy.de).sort(), Object.keys(settingsCopy.en).sort());
  assert.deepEqual(Object.keys(settingsCopy.ro).sort(), Object.keys(settingsCopy.en).sort());
});

test("preparation selection requires a complete bound plan before Apply", () => {
  const selection = "prepare.yml#setup@" + "a".repeat(40);
  const candidate = { base_revision: "a".repeat(64), candidate_revision: "b".repeat(64), key: "execution.preparation", value: selection, proposed_value: selection, created_at: "2026-10-07T12:00:00Z", restart_required: true };
  assert.equal(validPendingConfig(candidate), false, "unreviewed preparation enables Apply");
});

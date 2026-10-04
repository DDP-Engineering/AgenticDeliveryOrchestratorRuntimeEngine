/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { COMMON_SETTINGS, editValue, settingGroups, settingRows } from "../src/settings.ts";

const config = {
  platform: { kind: "gitlab", repo: "group/project" },
  executor: { default: "opencode", commands: { opencode: { command: "opencode run", model: "openai/gpt" } } },
  budgets: { max_iterations: 20, max_cost_usd: 5.5 },
  delivery: { reviewers: ["dan"], draft: true },
  container: { egress: { allowlist: [] } },
};
const meta = (key, source, editable, restart = false, edit_key = key) =>
  ({ key, edit_key, source, editable, restart });
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
  assert.equal(rows.get("budgets.max_cost_usd").step, "any");
  assert.equal(rows.get("executor.commands.opencode.model").step, undefined);
  for (const key of ["delivery.reviewers", "executor.commands.opencode.command", "container.egress.allowlist"]) {
    assert.equal(rows.get(key).input, "none", key);
  }
});

test("common settings come first, in their defined order, and only once", () => {
  const groups = settingGroups(settingRows(config, settings), false);
  const present = new Set(settings.map(item => item.key));
  assert.equal(groups[0].name, "common");
  assert.deepEqual(groups[0].rows.map(row => row.key),
    COMMON_SETTINGS.map(item => item.key).filter(key => present.has(key)));
  assert.ok(groups[0].rows.every(row => row.common && row.label && row.help));
  const common = new Set(groups[0].rows.map(row => row.key));
  assert.ok(groups.slice(1).every(group => group.rows.every(row => !common.has(row.key))));
  assert.deepEqual(groups.slice(1).map(group => group.name), ["executor", "budgets", "delivery", "container"]);
});

test("the project-set filter keeps project rows and drops empty groups", () => {
  const groups = settingGroups(settingRows(config, settings), true);
  assert.deepEqual(groups.map(group => [group.name, group.rows.map(row => row.key)]), [
    ["common", ["platform.repo", "platform.kind", "budgets.max_iterations"]],
    ["executor", ["executor.commands.opencode.command", "executor.commands.opencode.model"]],
    ["delivery", ["delivery.reviewers"]],
  ]);
});

test("edit values start from the current value", () => {
  assert.equal(editValue(true), "true");
  assert.equal(editValue(5.5), "5.5");
  assert.equal(editValue(null), "");
  assert.equal(editValue("x"), "x");
});

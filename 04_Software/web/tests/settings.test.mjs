/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { editValue, hasDefault, settingGroups, settingRows, settingPurpose, validSettingCatalog, validPendingConfig } from "../src/settings.ts";
import { publicationCopy, publicationValue, pipelineFailureCopy, pipelineFailureValue, settingLabel } from "../src/settingsCopy.ts";
import { durationParts, implementationDraft } from "../src/implementationSettings.ts";

test("implementation drafts serialize only complete valid human values", () => {
 assert.deepEqual(durationParts("12h"), {amount:"12",unit:"h"});
 assert.deepEqual(durationParts("d"), {amount:"",unit:"d"});
 assert.equal(implementationDraft("duration", "12h"), "12h");
 assert.equal(implementationDraft("retry-delays", "0\n 10\n45\n"), "[0,10,45]");
 assert.equal(implementationDraft("stage-timeouts", '{"validate":3600,"build":5400}'), '{"build":5400,"validate":3600}');
 assert.equal(implementationDraft("stage-timeouts", "{}"), "{}");
 assert.equal(editValue({build:5400,validate:3600}), '{"build":5400,"validate":3600}');
 for (const value of ["0s", "d", "", "1.5h", "-1h", "9007199254740991d", "garbage"])
  assert.equal(implementationDraft("duration", value), null);
 for (const value of ["", "true", "-1", "1.5", "9007199254740992", "5\nabc"])
  assert.equal(implementationDraft("retry-delays", value), null);
 for (const value of ["null", "[]", "{bad", '{"build":0}', '{"build":true}', '{"unknown":10}'])
  assert.equal(implementationDraft("stage-timeouts", value), null);
});

test("publication state names exact booleans in every locale", () => {
 for (const locale of ["en", "fr", "de", "ro"]) {
  assert.equal(publicationValue(true, locale), publicationCopy[locale].draft);
  assert.equal(publicationValue("true", locale), publicationCopy[locale].draft);
  assert.equal(publicationValue(false, locale), publicationCopy[locale].ready);
  assert.equal(publicationValue("false", locale), publicationCopy[locale].ready);
  for (const invalid of [null, 0, 1, "False", {}, []]) assert.equal(publicationValue(invalid, locale), null);
 }
});

test("failed CI action names only exact configured options in every locale", () => {
 for (const locale of ["en", "fr", "de", "ro"]) {
  for (const value of ["revise", "notify", "ignore"]) assert.equal(pipelineFailureValue(value, locale), pipelineFailureCopy[locale][value]);
  for (const invalid of [null, true, 1, "Revise", "toString", "__proto__", {}, []]) assert.equal(pipelineFailureValue(invalid, locale), null);
 }
 assert.equal(settingLabel("review.on_pipeline_failure"), "Action when PR/MR CI checks fail");
});

test("Git flow owns settings by effect rather than technical section", () => {
 const cases = {
  repository: ["platform.repo", "platform.login", "agent.name", "agent.email", "delivery.target_branch", "worktree.branch_template", "worktree.branch_rule"],
  tickets: ["polling.mode", "polling.poll_interval_seconds", "labels.control.hold", "labels.control.exclude", "labels.lifecycle.answered", "labels.lifecycle.ready", "labels.lifecycle.working", "readiness.require_acceptance_criteria", "workflow.default_kind", "workflow.kind_labels.bug"],
  implementation: ["polling.max_concurrent_runs", "budgets.max_cost_usd", "delivery.publish_checkpoints", "workflow.quick_label", "workflow.stage_timeout_overrides.build", "recovery.max_stage_failures", "clarification.max_rounds"],
  reviews: ["review.max_review_rounds", "review.revise_label", "review.on_pipeline_failure", "delivery.reviewers", "delivery.approval_label", "delivery.remove_source_branch"],
  statistics: ["metrics.enabled", "metrics.capture_tokens", "metrics.db_path"],
  technical: ["agent.slug", "state.store_root", "worktree.repo_path", "worktree.root", "workflow.aegis_python", "future.new_key"],
 };
 for (const [purpose, keys] of Object.entries(cases)) for (const key of keys) assert.equal(settingPurpose(key), purpose, key);
});

test("flow visibility omits inactive and external fields and keeps technical rows read-only", async () => {
 const { settingVisible, settingSubgroup, STATUS_LABEL_KEYS } = await import("../src/settings.ts");
 assert.equal(typeof settingVisible, "function");
 assert.equal(settingVisible("polling.mode"), false);
 assert.equal(settingVisible("polling.mode", true), false);
 for (const key of ["polling.poll_interval_seconds", "polling.poll_jitter_seconds", "polling.poll_backoff"]) assert.equal(settingVisible(key), true, key);
 for (const key of ["state.channel", "review.trigger", "review.review_reminder_after", "clarification.reminder_after", "clarification.timeout_state", "metrics.capture_resource", "labels.selection.type_feature", "reconcile.on_ticket_closed", "executor.mode", "container.image", "execution.backend", "local.account", "worktree.future_field"]) assert.equal(settingVisible(key), false, key);
 for (const key of ["worktree.repo_path", "worktree.root", "worktree.branch_template", "worktree.branch_rule", "state.store_root", "agent.slug"]) assert.equal(settingVisible(key), true, key);
 assert.equal(settingVisible("executor.default"), false);
 assert.equal(settingVisible("executor.default", true), true);
 assert.equal(settingVisible("platform.repo", true), false);
 const technical = settingRows({}, ["worktree.repo_path", "worktree.root", "agent.slug", "state.store_root", "workflow.aegis_python", "future.new_key"].map(key => meta(key, "project", true)));
 for (const row of technical) assert.equal(row.input, "none", row.key);
 assert.equal(STATUS_LABEL_KEYS.size, 6);
 assert.equal(STATUS_LABEL_KEYS.has("labels.lifecycle.answered"), true);
 assert.equal(STATUS_LABEL_KEYS.has("labels.lifecycle.ready"), false);
 for (const [key, expected] of [["clarification.max_rounds","clarification"], ["recovery.max_transient_retries","recovery"], ["workflow.stage_timeout_overrides.build","stageLimits"], ["metrics.db_path","statisticsFiles"], ["metrics.capture_tokens",null]]) assert.equal(settingSubgroup(key), expected);
});

test("only branch naming worktree fields get text editors under server authority", () => {
 const keys = ["worktree.branch_template", "worktree.branch_rule"];
 for (const row of settingRows({}, keys.map(key => meta(key, "project", true, true)))) {
  assert.equal(row.input, "text");
  assert.equal(row.restart, true);
 }
 for (const row of settingRows({}, keys.map(key => meta(key, "project", false)))) assert.equal(row.input, "none");
 const group = settingGroups(settingRows({}, [...keys].reverse().map(key => meta(key, "project", true))), false)[0];
 assert.deepEqual(group.rows.map(row => row.key), keys);
});

test("branch preview transport requires exact sample, revision and closed findings", async () => {
 const { validBranchPreview } = await import("../src/settings.ts");
 assert.equal(typeof validBranchPreview, "function");
 const valid = { revision: "a".repeat(64), template: "feature/{slug}-{iid}", rule: "^feature/", slug: "adore", iid: 1, run_id: "sample-run-1", name: "feature/adore-1", valid: true, rule_matches: true, issues: [] };
 assert.equal(validBranchPreview(valid), true);
 assert.equal(validBranchPreview({ ...valid, valid: false, rule_matches: false, issues: ["rule_mismatch"] }), true);
 for (const bad of [null, {}, { ...valid, revision: "bad" }, { ...valid, name: null }, { ...valid, iid: 2 }, { ...valid, rule_matches: null }, { ...valid, issues: ["unknown"] }, { ...valid, issues: ["invalid_rule"] }, { ...valid, valid: "true" }, { ...valid, name: 5 }]) assert.equal(validBranchPreview(bad), false);
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
  assert.deepEqual(groups.map(group => group.name), ["repository", "implementation", "reviews", "executor", "environment"]);
  const keys = groups.flatMap(group => group.rows.map(row => row.key));
  assert.equal(new Set(keys).size, settings.length);
  assert.deepEqual([...keys].sort(), settings.map(item => item.key).sort());
});

test("the project-set filter keeps project rows and drops empty groups", () => {
  const groups = settingGroups(settingRows(config, settings), true);
  assert.deepEqual(groups.map(group => [group.name, group.rows.map(row => row.key)]), [
    ["repository", ["platform.repo", "platform.kind"]],
    ["implementation", ["budgets.max_iterations"]],
    ["reviews", ["delivery.reviewers"]],
    ["executor", ["executor.commands.opencode.command", "executor.commands.opencode.model"]],
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
  assert.deepEqual(settingGroups(rows, false).map(group => group.name), ["repository", "implementation", "reviews", "executor", "environment"]);
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


test("Implementation typed controls keep narrow collection review authority", () => {
 const items = [
  {...meta("clarification.answer_timeout", "project", true), type:"text"},
  {...meta("recovery.retry_backoff_seconds", "project", true), type:"list"},
  {...meta("workflow.stage_timeout_overrides", "project", true), type:"map"},
 ];
 assert.deepEqual(settingRows({}, items).map(row => row.input), ["duration", "retry-delays", "stage-timeouts"]);
 const pending = {base_revision:"a".repeat(64), candidate_revision:"b".repeat(64),
  key:"workflow.stage_timeout_overrides", value:'{"build":300}', proposed_value:{build:300},
  restart_required:false, created_at:"2026-10-09T12:00:00Z"};
 assert.equal(validPendingConfig(pending),true);
 assert.equal(validPendingConfig({...pending,key:"recovery.retry_backoff_seconds",value:"[0,5]",proposed_value:[0,5]}),true);
 for(const bad of [
  {...pending, proposed_value:{unknown:300},value:'{"unknown":300}'},
  {...pending, proposed_value:{build:true},value:'{"build":true}'},
  {...pending, proposed_value:{build:0},value:'{"build":0}'},
  {...pending, value:'{"build":300,"build":300}'},
  {...pending, key:"workflow.kind_labels"},
  {...pending,key:"recovery.retry_backoff_seconds",value:"[]",proposed_value:[]},
  {...pending,key:"recovery.retry_backoff_seconds",value:"[1.5]",proposed_value:[1.5]},
 ]) assert.equal(validPendingConfig(bad),false);
});

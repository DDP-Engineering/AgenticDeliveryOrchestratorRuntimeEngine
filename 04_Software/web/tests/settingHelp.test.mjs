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

test("agent stage limits retain their general-limit fallback in every locale", () => {
  for (const locale of locales) {
    for (const key of ["workflow.stage_timeout_overrides", "workflow.stage_timeout_overrides.*"]) {
      const text = SETTING_HELP[locale][key];
      assert.match(text, /build/, `${locale}: ${key}`);
      assert.match(text, /validate/, `${locale}: ${key}`);
      assert.match(text, /per_gate_timeout_seconds/, `${locale}: fallback`);
    }
  }
});

test("settings without a dedicated name source have a short name in French, German and Romanian", async () => {
  const { localizedSettingLabel } = await import("../src/settingsCopy.ts");
  // The settings whose name was the first sentence of the help text before they got a name of their own.
  const named = ["agent.name", "agent.slug", "agent.email", "platform.login", "state.store_root", "polling.mode",
    "polling.poll_jitter_seconds", "polling.poll_backoff", "polling.quiet_hours", "labels.selection.priority_high",
    "labels.selection.priority_medium", "labels.selection.priority_low", "labels.selection.type_feature",
    "labels.selection.type_bug", "labels.control.hold", "executor.questions_file", "execution.preparation",
    "execution.preparation_step_timeout_seconds", "execution.preparation_total_timeout_seconds",
    "execution.preparation_max_attempts", "container.uv_cache_volume", "container.npm_cache_volume", "container.run_args", "container.runtime_env",
    "container.runtime_env.UV_LINK_MODE", "container.required_tool_checks", "container.selinux_relabel",
    "container.egress.allowlist", "container.egress.no_proxy", "container.egress.proxy_image",
    "container.egress.proxy_port", "container.egress.network_prefix", "worktree.repo_path", "worktree.root",
    "workflow.default_kind", "workflow.kind_labels", "workflow.kind_labels.bug", "workflow.stage_timeout_overrides.build",
    "workflow.aegis_python", "delivery.approval_label", "review.revise_label",
    "metrics.export_jsonl", "metrics.html_out"];
  for (const key of named) {
    assert.ok(key.includes(".") && (catalog.includes(key) || catalog.includes(key.replace(/\.[^.]+$/, ".*"))), key);
    for (const locale of ["fr", "de", "ro"]) {
      const label = localizedSettingLabel(key, locale);
      assert.ok(label, `${locale}: ${key} has no name`);
      assert.ok(label.length <= 70 && !label.includes(". ") && !label.endsWith("."), `${locale}: ${key} is not a short name: ${label}`);
    }
    assert.equal(localizedSettingLabel(key, "en"), undefined);
  }
  assert.equal(localizedSettingLabel("container.runtime_env.UV_LINK_MODE", "ro"), "Mediul containerului: UV_LINK_MODE");
  assert.equal(localizedSettingLabel("workflow.kind_labels.bug", "de"), "Aufgabentyp für das Ticket-Label bug");
  assert.equal(localizedSettingLabel("workflow.kind_labels.", "fr"), undefined);
});

test("named entries resolve to their pattern text; unknown keys have none", () => {
  assert.equal(settingHelp("executor.model", "en"), SETTING_HELP.en["executor.model"]);
  assert.equal(settingHelp("executor.commands.pi.model", "en"), undefined);  // no per-agent tables
  assert.equal(settingHelp("container.runtime_env.UV_LINK_MODE", "de"), SETTING_HELP.de["container.runtime_env.*"]);
  assert.equal(settingHelp("workflow.stage_timeout_overrides.build", "fr"), SETTING_HELP.fr["workflow.stage_timeout_overrides.*"]);
  assert.equal(settingHelp("workflow.kind_labels.enhancement", "ro"), SETTING_HELP.ro["workflow.kind_labels.*"]);
  assert.equal(settingHelp("budgets.max_iterations", "en"), SETTING_HELP.en["budgets.max_iterations"]);
  assert.equal(settingHelp("unknown.setting", "en"), undefined);
  assert.equal(settingHelp("container.runtime_env.A.B", "en"), undefined);  // pattern needs the same depth
});

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { parsePortableResponse, portableFields } from "../src/portable.ts";

const settings = {
  polling: { mode: "loop", poll_interval_seconds: 60, poll_jitter_seconds: 5, poll_backoff: true, max_concurrent_runs: 1 },
  readiness: { require_acceptance_criteria: true, require_priority_label: true, require_known_component: true },
  recovery: { max_stage_failures: 3, max_transient_retries: 3, retry_backoff_seconds: [5, 30, 120] },
  budgets: { max_iterations: 20, max_wall_clock_seconds: 3600, per_gate_timeout_seconds: 1800, max_cost_usd: 5, max_files_touched: 120 },
};
const sorted = value => Array.isArray(value) ? value.map(sorted) : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sorted(value[key])])) : value;
const encode = (alter = () => {}) => {
  const value = { kind: "adore-project-settings", schema_version: 1, source: { product: "ADORE", version: "1.2.3", contract: "portable-rules-v1" }, settings: structuredClone(settings) };
  alter(value);
  value.checksum = createHash("sha256").update(JSON.stringify(sorted(value))).digest("hex");
  return JSON.stringify(sorted(value)) + "\n";
};

test("strict portable response preserves full rules and rejects unknown fields/types", async () => {
  const value = await parsePortableResponse(encode());
  assert.deepEqual(value.settings, settings);
  for (const [section, fields] of Object.entries(portableFields)) assert.deepEqual(Object.keys(settings[section]).sort(), [...fields].sort());
  for (const alter of [p => { p.schema_version = true; }, p => { p.extra = "SECRET"; }, p => { p.source.version = "SECRET"; }, p => { p.settings.budgets.max_iterations = false; }, p => { p.settings.polling.mode = "SECRET"; }, p => { p.settings.recovery.retry_backoff_seconds = []; }, p => { p.settings.budgets.max_cost_usd = -1; }, p => { p.settings.polling.extra = {}; }, p => { delete p.settings.readiness; }, p => { p.settings.budgets.max_files_touched = 1_000_000_001; }]) await assert.rejects(parsePortableResponse(encode(alter)));
  for (const raw of ["", "null", "{}", "[]", "{" , " ".repeat(65537), encode().replace('"max_iterations":20', '"max_iterations":21'), encode().replace('"max_iterations":20', '"max_iterations":20,"max_iterations":20'), encode().replace('"mode":', '"m\\u006fde":')]) await assert.rejects(parsePortableResponse(raw));
});


test("transport does not fold fractional or exponent integer tokens into valid limits", async () => {
  const resign = raw => {
    const body = "{" + raw.slice(raw.indexOf(',"kind"') + 1, -1);
    const checksum = createHash("sha256").update(body).digest("hex");
    return raw.replace(/"checksum":"[0-9a-f]{64}"/, `"checksum":"${checksum}"`);
  };
  for (const raw of [encode().replace('"max_iterations":20', '"max_iterations":20.0'), encode().replace('"schema_version":1', '"schema_version":1.0'), encode().replace('"max_iterations":20', '"max_iterations":2e1'), encode().replace('[5,30,120]', '[5.0,30,120]')]) await assert.rejects(parsePortableResponse(resign(raw)));
});

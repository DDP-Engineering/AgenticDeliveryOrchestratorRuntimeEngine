/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readReadiness, readinessVerdict } from "../src/readiness.ts";
const project = "1".repeat(32);
const evidence = () => ({ status: "verified", project_id: project, revision: "a".repeat(64), context: "api-host", checked_at: "2026-10-06T10:00:00Z",
  checks: { git: true, forge_cli: true, forge_auth: true, container_runtime: true, executor_cli: true, aegis_files: true, model_endpoint: "not-checked" },
  model_probe: { context: "executor-container", ready: false, model: "", reason: "unsupported-executor" } });
test("performed checks preserve unavailable model coverage and partial runtime", () => {
  const value = evidence();
  assert.equal(readinessVerdict(readReadiness(value, project)), "verified");
  value.checks.container_runtime = null; value.status = "partial";
  assert.equal(readinessVerdict(readReadiness(value, project)), "partial");
  value.checks.forge_auth = false; value.status = "failed";
  assert.equal(readinessVerdict(readReadiness(value, project)), "failed");
  value.model_probe.reason = "not-configured";
  assert.equal(readReadiness(value, project).checks.model_endpoint, "not-checked");
});
test("model connection results reflect actual passed and failed probe evidence", () => {
  const value = evidence(); value.model_probe = { context: "executor-container", ready: true, model: "local/model", reason: "ready" };
  value.checks.model_endpoint = true;
  assert.equal(readinessVerdict(readReadiness(value, project)), "verified");
  value.status = "failed"; value.model_probe.ready = false; value.model_probe.reason = "http-401"; value.checks.model_endpoint = false;
  assert.equal(readinessVerdict(readReadiness(value, project)), "failed");
});

test("optional native causes roundtrip and legacy records remain readable", () => {
  const value = evidence(); value.model_probe.context = "executor-local";
  value.checks.executor_cli = false; value.status = "failed";
  assert.equal(readReadiness(value, project).executor_probe, undefined);
  value.executor_probe = {ready: false, reason: "executor-exit", exit_code: 7};
  assert.deepEqual(readReadiness(value, project).executor_probe, value.executor_probe);
  for (const change of [null, {}, {ready: true, reason: "ready", exit_code: 0},
    {ready: false, reason: "PRIVATE", exit_code: 7},
    {ready: false, reason: "executor-exit", exit_code: true},
    {ready: false, reason: "executor-exit", exit_code: 0},
    {ready: false, reason: "executor-exit", exit_code: null},
    {ready: false, reason: "executor-exit", exit_code: 1e20},
    {ready: false, reason: "version-invalid", exit_code: null},
    {ready: false, reason: "executor-exit", exit_code: 7, detail: "PRIVATE"}]) {
    assert.throws(() => readReadiness({...value, executor_probe: change}, project));
  }
  value.model_probe.context = "executor-container";
  assert.throws(() => readReadiness(value, project));
});
test("corrupt scope status keys dates and contradictory probe results fail closed", () => {
  for (const mutate of [v => v.project_id = "other", v => v.status = "unexpected", v => v.context = "other", v => v.revision = "bad",
    v => v.checked_at = "invalid", v => v.checked_at = "2099-01-01T00:00:00Z", v => v.checked_at = "2026-10-06T10:00:00",
    v => delete v.checks.git, v => v.checks.extra = true, v => v.checks.git = "yes", v => v.checks.forge_auth = null,
    v => v.model_probe.reason = "unexpected", v => v.model_probe.model = "secret\nvalue", v => v.model_probe.ready = true,
    v => v.checks.model_endpoint = false, v => v.status = "failed", v => v.model_probe = null]) {
    const value = evidence(); mutate(value);
    assert.throws(() => readReadiness(value, project), error => error.code === "readiness_corrupt");
  }
  for (const value of [null, [], {}, false]) assert.throws(() => readReadiness(value, project), error => error.code === "readiness_corrupt");
});

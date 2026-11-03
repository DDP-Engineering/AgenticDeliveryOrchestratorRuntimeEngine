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
  checks: { git: true, forge_cli: true, forge_auth: true, container_runtime: true, executor_cli: true, aegis_files: true } });
test("performed checks yield verified, partial runtime and failed verdicts", () => {
  const value = evidence();
  assert.equal(readinessVerdict(readReadiness(value, project)), "verified");
  value.checks.container_runtime = null; value.status = "partial";
  assert.equal(readinessVerdict(readReadiness(value, project)), "partial");
  value.checks.forge_auth = false; value.status = "failed";
  assert.equal(readinessVerdict(readReadiness(value, project)), "failed");
});
test("corrupt scope status keys dates and the removed model check fail closed", () => {
  for (const mutate of [v => v.project_id = "other", v => v.status = "unexpected", v => v.context = "other", v => v.revision = "bad",
    v => v.checked_at = "invalid", v => v.checked_at = "2099-01-01T00:00:00Z", v => v.checked_at = "2026-10-06T10:00:00",
    v => delete v.checks.git, v => v.checks.extra = true, v => v.checks.git = "yes", v => v.checks.forge_auth = null,
    v => v.checks.model_endpoint = "not-checked", v => v.checks.aegis_files = "not-checked", v => v.status = "failed"]) {
    const value = evidence(); mutate(value);
    assert.throws(() => readReadiness(value, project), error => error.code === "readiness_corrupt");
  }
  for (const value of [null, [], {}, false]) assert.throws(() => readReadiness(value, project), error => error.code === "readiness_corrupt");
});
test("a ChatGPT project's sign-in check is an optional boolean that decides the verdict", () => {
  const value = evidence();
  value.checks.executor_sign_in = true;
  assert.equal(readinessVerdict(readReadiness(value, project)), "verified");
  value.checks.executor_sign_in = false; value.status = "failed";
  assert.equal(readinessVerdict(readReadiness(value, project)), "failed");
  for (const wrong of [null, "yes", 1]) {
    const bad = evidence(); bad.checks.executor_sign_in = wrong;
    assert.throws(() => readReadiness(bad, project), error => error.code === "readiness_corrupt");
  }
});

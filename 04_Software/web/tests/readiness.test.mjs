/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readReadiness, readinessVerdict, validProjectVerification } from "../src/readiness.ts";
const project = "1".repeat(32);
const evidence = () => ({ status: "verified", auth_bound: true, project_id: project, revision: "a".repeat(64), context: "api-host", checked_at: "2026-10-06T10:00:00Z",
  checks: { git: true, forge_cli: true, forge_auth: true, container_runtime: true, executor_cli: true, aegis_files: true },
  required_checks: ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "aegis_files"] });
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
  value.checks.executor_sign_in = true; value.required_checks.push("executor_sign_in");
  assert.equal(readinessVerdict(readReadiness(value, project)), "verified");
  value.checks.executor_sign_in = false; value.status = "failed";
  assert.equal(readinessVerdict(readReadiness(value, project)), "failed");
  for (const wrong of [null, "yes", 1]) {
    const bad = evidence(); bad.checks.executor_sign_in = wrong; bad.required_checks.push("executor_sign_in");
    assert.throws(() => readReadiness(bad, project), error => error.code === "readiness_corrupt");
  }
});
test("the internet checks are optional booleans that decide the verdict", () => {
  for (const key of ["egress_proxy", "web_search_key"]) {
    const value = evidence();
    value.checks[key] = true; value.required_checks.push(key);
    assert.equal(readinessVerdict(readReadiness(value, project)), "verified");
    value.checks[key] = false; value.status = "failed";
    assert.equal(readinessVerdict(readReadiness(value, project)), "failed");
    for (const wrong of [null, "yes", 1]) {
      const bad = evidence(); bad.checks[key] = wrong; bad.required_checks.push(key);
      assert.throws(() => readReadiness(bad, project), error => error.code === "readiness_corrupt");
    }
  }
});

test("project list rejects fabricated and malformed verification", () => {
  const partial = evidence(); partial.status = "partial"; partial.checks.aegis_files = "not-checked";
  assert.equal(validProjectVerification(partial, project, partial.required_checks), true);
  assert.equal(validProjectVerification({ ...partial, status: "verified" }, project, partial.required_checks), false);
  assert.equal(validProjectVerification({ ...partial, project_id: "other" }, project, partial.required_checks), false);
  const complete = evidence(); complete.checks.executor_sign_in = true; complete.required_checks.push("executor_sign_in");
  const truncated = structuredClone(complete); delete truncated.checks.executor_sign_in; truncated.required_checks.pop();
  assert.equal(validProjectVerification(truncated, project, complete.required_checks), false);
  const missing = evidence(); missing.required_checks.push("egress_proxy");
  assert.equal(validProjectVerification(missing, project, evidence().required_checks), false);
  assert.equal(validProjectVerification({ ...evidence(), required_checks: [] }, project, evidence().required_checks), false);
  assert.equal(validProjectVerification({ status: "unverified", revision: null, checked_at: null }, project, evidence().required_checks), true);
  assert.equal(validProjectVerification({ status: "unverified" }, project, evidence().required_checks), false);
});

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { validExecutionPlan, validPreparationEvidence, preparationCopy } from "../src/executionPlan.ts";
import { validPendingConfig } from "../src/settings.ts";

test("native local plans are closed and refuse container recipes/images", () => {
  const native = { schema: 1, backend: "local", selection: "", image: "", image_source: "local",
    source_sha256: "", fingerprint: "a".repeat(64), steps: [] };
  assert.equal(validExecutionPlan(native), true);
  for (const change of [{image: "image:latest"}, {selection: "recipe.yml#job@" + "a".repeat(40)},
      {steps: [{name: "setup", run: "install"}]}, {image_source: "profile"}, {pid: 42}])
    assert.equal(validExecutionPlan({...native, ...change}), false);
});

const plan = { schema: 1, backend: "container", selection: "prepare.yml#setup@" + "a".repeat(40), image: "project:1", image_source: "recipe", source_sha256: "b".repeat(64), fingerprint: "c".repeat(64), steps: [{ name: "Install", run: "uv sync --locked\nnpm ci" }] };
const step = { index: 0, name: "Install", started_at: "2026-10-07T10:00:00Z", finished_at: "2026-10-07T10:00:02Z", exit_code: 0, timed_out: false, cancelled: false };
const evidence = { status: "success", attempts: 1, image: "project:1", fingerprint: plan.fingerprint, steps: [step] };

test("complete preparation reviews bind every command and candidate selection", () => {
  assert.equal(validExecutionPlan(plan), true);
  const candidate = { base_revision: "a".repeat(64), candidate_revision: "b".repeat(64), key: "execution.preparation", value: plan.selection, proposed_value: plan.selection, created_at: step.started_at, restart_required: true, execution_plan: plan };
  assert.equal(validPendingConfig(candidate), true);
  assert.equal(validPendingConfig({ ...candidate, execution_plan: { ...plan, selection: "other.yml#setup@" + "a".repeat(40) } }), false);
  for (const locale of ["en", "fr", "de", "ro"]) assert.ok(preparationCopy[locale].help.length > 25);
});

test("unknown incomplete and forged preparation reviews fail closed", () => {
  for (const bad of [null, [], { ...plan, schema: true }, { ...plan, backend: "local" }, { ...plan, steps: [] }, { ...plan, source_sha256: "" }, { ...plan, extra: true }, { ...plan, steps: [null] }, { ...plan, image: "--privileged" }]) assert.equal(validExecutionPlan(bad), false);
});

test("recorded success needs complete valid authoritative outcomes", () => {
  assert.equal(validPreparationEvidence(evidence), true);
  assert.equal(validPreparationEvidence({ ...evidence, status: "failed", steps: [{ ...step, exit_code: 1 }] }), true);
  for (const bad of [null, { ...evidence, steps: [null] }, { ...evidence, attempts: 0 }, { ...evidence, steps: [] }, { ...evidence, steps: [{ ...step, exit_code: 124 }] }, { ...evidence, steps: [{ ...step, timed_out: true }] }, { ...evidence, steps: [{ ...step, finished_at: "2026-10-07T10:00:02" }] }]) assert.equal(validPreparationEvidence(bad), false);
});

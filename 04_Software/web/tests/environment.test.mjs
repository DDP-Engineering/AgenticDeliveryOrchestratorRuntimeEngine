/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiError, errorMessages } from "../src/errors.ts";
import { environmentCopy, environmentFailure, readEnvironmentProgress, prepareEnvironment } from "../src/environmentPreparation.ts";

const id = "a".repeat(32);
const running = {id, status:"running", stage:"building_executor", error:null};
const ready = {id, status:"ready", stage:"ready", error:null};

test("progress refuses inconsistent state, untyped failures and unexpected private fields", () => {
  for (const value of [null, {}, {...running, stage:"unknown"}, {...running, status:"ready"},
    {...ready, error:"environment_build_failed"}, {...running, token:"private"}, {...running, id:"other"},
    {...running, status:"failed", stage:"failed", error:"PRIVATE stderr"}])
    assert.throws(() => readEnvironmentProgress(value));
  assert.deepEqual(readEnvironmentProgress(ready), ready);
});

test("preparation progress and recovery codes have text in all four locales", () => {
  for (const locale of ["en", "fr", "de", "ro"]) {
    assert.deepEqual(Object.keys(environmentCopy[locale]).sort(), Object.keys(environmentCopy.en).sort());
    for (const sentence of Object.values(environmentCopy[locale])) assert.ok(sentence.trim());
    for (const code of ["environment_busy", "environment_identity_unavailable", "environment_preparation_failed",
      "environment_build_failed", "environment_executor_invalid", "environment_preparation_expired"])
      assert.ok(errorMessages[locale][code]?.trim(), `${locale}:${code}`);
  }
  assert.equal(environmentFailure(new ApiError("environment_build_failed")), true);
  assert.equal(environmentFailure(new ApiError("stale_config_revision")), false);
});

test("preparation waits for ready and never accepts another operation's result", async t => {
  t.mock.method(globalThis, "setTimeout", callback => { queueMicrotask(callback); return 0; });
  const fetch = t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, `/api/v1/environment-preparations/${id}`);
    assert.equal(options.cache, "no-store");
    return {ok:true, json:async () => ready};
  });
  const stages = [];
  await prepareEnvironment(async () => running, value => stages.push(value.stage), () => true);
  assert.deepEqual(stages, ["building_executor", "ready"]);
  fetch.mock.mockImplementation(async () => ({ok:true, json:async () => ({...ready, id:"b".repeat(32)})}));
  await assert.rejects(prepareEnvironment(async () => running, () => {}, () => true), /unexpected_response/);
});

test("failure enables recovery and unmounted imports do not start preparation", async () => {
  await assert.rejects(prepareEnvironment(async () => ({id, status:"failed", stage:"failed", error:"environment_build_failed"}),
    () => {}, () => true), /environment_build_failed/);
  let started = false;
  await assert.rejects(prepareEnvironment(async () => { started = true; return ready; }, () => {}, () => false), /request_rejected/);
  assert.equal(started, false);
});

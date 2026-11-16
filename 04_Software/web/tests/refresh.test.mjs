/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiError } from "../src/errors.ts";
import { transientReadFailure } from "../src/useSnapshot.ts";
import { readUntilAbort } from "../src/polling.ts";

test("reads settle normally, but abort fences a stalled transport and late fulfillment", async () => {
  const controller = new AbortController();
  assert.equal(await readUntilAbort(Promise.resolve("validated"), controller.signal), "validated");
  let release;
  const stalled = new Promise(resolve => { release = resolve; });
  const read = readUntilAbort(stalled, controller.signal);
  controller.abort();
  await assert.rejects(read, { name: "AbortError" });
  release("late evidence");
  await assert.rejects(readUntilAbort(Promise.resolve("already cancelled"), controller.signal), { name: "AbortError" });
});

test("only classified transport failures permit informational stale retention", () => {
  assert.equal(transientReadFailure(new ApiError("network_error")), true);
  for (const status of [502, 503, 504]) {
    const failure = new ApiError("request_failed"); failure.status = status;
    assert.equal(transientReadFailure(failure), true);
  }
  for (const code of ["authentication_required", "admin_required", "project_not_found", "run_not_found",
    "unexpected_response", "job_snapshot_changed", "job_evidence_corrupt", "web_store_corrupt"]) {
    const failure = new ApiError(code); failure.status = 503;
    assert.equal(transientReadFailure(failure), false, code);
  }
  for (const failure of [new Error("network_error"), new RangeError("invalid evidence"), null, "network_error", new ApiError("request_failed")])
    assert.equal(transientReadFailure(failure), false);
  for (const status of [401, 403, 404, 409, 500]) {
    const failure = new ApiError("request_failed"); failure.status = status;
    assert.equal(transientReadFailure(failure), false);
  }
});

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { auditPolicyPayload } from "../src/auditPolicy.ts";

test("audit limits convert saved values and zero/blank unlimited defaults", () => {
  assert.deepEqual(auditPolicyPayload("30", "64"), { retention_days: 30, max_bytes: 64 * 1024**2 });
  assert.deepEqual(auditPolicyPayload("0", "0"), { retention_days: null, max_bytes: null });
  assert.deepEqual(auditPolicyPayload(" ", ""), { retention_days: null, max_bytes: null });
  assert.deepEqual(auditPolicyPayload("36500", "1024"), { retention_days: 36500, max_bytes: 1024**3 });
  assert.equal(auditPolicyPayload("0", String(250 / 1024**2)).max_bytes, 250);
  assert.equal(auditPolicyPayload("1", "0.1").max_bytes, 104858);
});

test("bad audit limits fail closed rather than disabling retention", () => {
  for (const days of ["-1", "1.5", "36501", "garbage", "Infinity", "NaN"]) {
    assert.throws(() => auditPolicyPayload(days, "64"), RangeError);
  }
  for (const mib of ["-1", "1025", "garbage", "Infinity", "NaN", "0.000000001"]) {
    assert.throws(() => auditPolicyPayload("30", mib), RangeError);
  }
});

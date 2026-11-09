/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { operationResultText } from "../src/ticketCopy.ts";

for (const locale of ["en", "ro", "fr", "de"]) {
  test(`manual start refusal is readable and secret-free in ${locale}`, () => {
    assert.notEqual(operationResultText("start:epic", locale), operationResultText("start:invalid_result", locale));
    const message = operationResultText("start:at_capacity", locale);
    assert.ok(message.length > 15 && !message.includes("start:"));
    assert.ok(!operationResultText("start:PRIVATE", locale).includes("PRIVATE"));
    assert.ok(!operationResultText("start:toString", locale).includes("function"));
    assert.equal(operationResultText("start:__proto__", locale), operationResultText("start:PRIVATE", locale));
    assert.equal(operationResultText("completed", locale), "completed");
    assert.equal(operationResultText("engine rejected operation", locale), "engine rejected operation");
  });
}


for (const locale of ["en", "ro", "fr", "de"]) {
  test(`retry reports persisted causes and rejects unknown reasons in ${locale}`, () => {
    for (const reason of ["lock_held", "executable_missing", "account_mismatch", "permission_denied"]) {
      const message = operationResultText(`retry:${reason}`, locale);
      assert.ok(message.length > 15 && !message.includes("retry:"));
    }
    assert.ok(!operationResultText("retry:PRIVATE", locale).includes("PRIVATE"));
    assert.ok(!operationResultText("retry:toString", locale).includes("function"));
    assert.ok(operationResultText("retry:failed:INFRASTRUCTURE_EXHAUSTED: version-invalid", locale)
      .includes("INFRASTRUCTURE_EXHAUSTED: version-invalid"));
  });
}

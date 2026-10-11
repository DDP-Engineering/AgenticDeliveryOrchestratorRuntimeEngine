/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { sortUsageRows } from "../src/usageSort.ts";

const row = (date, executor, tokens_in, reported_cost_usd = null) => ({ date, executor, model: null, events: 1, tokens_in, tokens_out: 0,
  cache_read_tokens: null, cache_write_tokens: null, reported_cost_usd, estimated_cost_usd: null });
const rows = [row("2026-10-01", "pi", 30, 2), row("2026-10-02", null, null), row("2026-10-03", "codex", 0, 1), row("2026-10-04", "", 10)];

test("numeric columns sort both ways with unknown values last and measured zero kept", () => {
  assert.deepEqual(sortUsageRows(rows, "tokens_in", false).map(item => item.tokens_in), [0, 10, 30, null]);
  assert.deepEqual(sortUsageRows(rows, "tokens_in", true).map(item => item.tokens_in), [30, 10, 0, null]);
  assert.deepEqual(sortUsageRows(rows, "reported_cost_usd", true).map(item => item.date), ["2026-10-01", "2026-10-03", "2026-10-02", "2026-10-04"]);
});

test("text columns sort by locale with missing identities last and the input left unchanged", () => {
  const before = rows.map(item => item.date);
  assert.deepEqual(sortUsageRows(rows, "executor", false, "en").map(item => item.executor), ["codex", "pi", null, ""]);
  assert.deepEqual(sortUsageRows(rows, "executor", true, "en").map(item => item.executor), ["pi", "codex", null, ""]);
  assert.deepEqual(sortUsageRows(rows, "date", true).map(item => item.date), ["2026-10-04", "2026-10-03", "2026-10-02", "2026-10-01"]);
  assert.deepEqual(rows.map(item => item.date), before);
});

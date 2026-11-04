/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { ApiError } from "../src/errors.ts";

const url = new URL("../src/ticketPreferences.ts", import.meta.url);
const reader = existsSync(url) ? (await import(url.href)).readPreferences : undefined;
test("account preferences expose a closed response reader", () => {
  assert.equal(typeof reader, "function", "ticket preference responses are not validated");
});
test("reads both modes and an absent selection without normalizing valid preferences", { skip: !reader }, () => {
  for (const ticket_body_mode of [null, "rendered", "source"]) {
    const input = { language: "ro", theme: "dark", ticket_body_mode };
    assert.deepEqual(reader(input), input);
  }
  assert.deepEqual(reader({ language: null, theme: null, ticket_body_mode: null }), { language: null, theme: null, ticket_body_mode: null });
});
test("refuses malformed preference responses rather than defaulting corrupt modes", { skip: !reader }, () => {
  for (const value of [null, [], "source", {}, { language: null, theme: null },
    ...[undefined, "markdown", "SOURCE", "", false, 0, [], {}].map(ticket_body_mode => ({ language: null, theme: null, ticket_body_mode })),
    { language: "xx", theme: null, ticket_body_mode: "source" },
    { language: null, theme: "sepia", ticket_body_mode: "source" }]) {
    assert.throws(() => reader(value), error => error instanceof ApiError && error.code === "unexpected_response");
  }
});

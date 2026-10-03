/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { PROJECT_NAME_PATTERN } from "../src/projectName.ts";

// Browsers compile the HTML pattern attribute as ^(?:pattern)$ with the v flag
// and silently ignore a pattern that does not compile.
const browserPattern = () => new RegExp(`^(?:${PROJECT_NAME_PATTERN})$`, "v");

test("project name pattern compiles the way browsers compile it", () => {
  assert.doesNotThrow(browserPattern);
});

test("project name pattern accepts profile names and rejects others", () => {
  const pattern = browserPattern();
  for (const name of ["demo", "a.b_c-1", "0lead", "a" + "b".repeat(63)]) assert.ok(pattern.test(name), name);
  for (const name of ["My Project", "-demo", ".demo", "", "a" + "b".repeat(64), "demo/x"]) assert.ok(!pattern.test(name), name);
});

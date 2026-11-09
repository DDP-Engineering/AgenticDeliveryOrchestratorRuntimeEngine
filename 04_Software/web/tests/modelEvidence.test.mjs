/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { modelConnectionCopy, modelGuidance, validModelEvidence } from "../src/modelEvidence.ts";

const project = "1".repeat(32), revision = "a".repeat(64);
const evidence = (reason) => ({ project_id: project, revision, checked_at: "2026-11-01T02:00:00+00:00",
  executor: "pi", model: "openai/model", ready: reason === "ready", reason });
const locales = ["en", "fr", "de", "ro"];

test("a tool-call-failed result is valid evidence and unknown reasons stay rejected", () => {
  assert.equal(validModelEvidence(evidence("tool-call-failed"), project, revision, "pi", "openai/model"), true);
  assert.equal(validModelEvidence(evidence("ready"), project, revision, "pi", "openai/model"), true);
  assert.equal(validModelEvidence(evidence("nonsense"), project, revision, "pi", "openai/model"), false);
  assert.equal(validModelEvidence({ ...evidence("tool-call-failed"), ready: true }, project, revision, "pi", "openai/model"), false);
});

test("tool-call-failed shows shell-permission guidance in every locale", () => {
  for (const locale of locales) {
    const guidance = modelGuidance("tool-call-failed", locale);
    assert.equal(guidance, modelConnectionCopy[locale].tool);
    assert.ok(guidance.length > 20);
    assert.notEqual(guidance, modelConnectionCopy[locale].other);
  }
  assert.equal(modelGuidance("timeout", "en"), modelConnectionCopy.en.timeout);
  assert.equal(modelGuidance("invalid-response", "ro"), modelConnectionCopy.ro.other);
});

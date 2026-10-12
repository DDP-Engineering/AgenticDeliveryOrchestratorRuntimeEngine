/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { messages } from "../src/i18n.ts";

test("delivery glossary and feedback are complete in every supported locale", () => {
  // The delivery term definitions live in the Glossary help topic (tests/help.test.mjs).
  const keys = ["glossary", "help", "helpTopics", "searchHelp", "helpNoMatch", "onThisPage", "helpFor", "loadingData",
    "dataFailed", "noProjectAccess", "noProjectAccessHelp", "noEnrolledProjectsHelp", "skipToContent",
    "primaryNavigation", "projectContext", "jobsScopeHelp", "overviewScopeHelp"];
  for (const [locale, catalog] of Object.entries(messages)) {
    assert.deepEqual(Object.keys(catalog).sort(), Object.keys(messages.en).sort(), locale);
    for (const key of keys) assert.ok(typeof catalog[key] === "string" && catalog[key].trim(), `${locale}: ${key}`);
  }
  assert.equal(messages.en.metrics, "Statistics");
  assert.equal(messages.en.paused, "Pickup stopped");
  assert.equal(messages.en.inReviewStatus, "Human review");
});

test("production branding is the exact approved transparent PNG", () => {
  const reference = new URL("../../../00_Planning/2026-10-05_Web_UX_Redesign/Gitea_Issues/asset-manifest.json", import.meta.url);
  const manifest = JSON.parse(readFileSync(reference, "utf8"));
  const bytes = readFileSync(new URL("../src/assets/DDP_Engineering_logo_dark.png", import.meta.url));
  assert.equal(createHash("sha256").update(bytes).digest("hex"), manifest.files["DDP_Engineering_logo_dark.png"]);
  assert.equal(bytes.readUInt32BE(16), 630);
  assert.equal(bytes.readUInt32BE(20), 300);
  assert.equal(bytes[25], 6, "PNG uses RGBA color type");
});

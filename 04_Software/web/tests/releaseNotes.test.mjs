/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { groupRelease, localText } from "../src/releaseNotes.ts";

const both = (en, ro) => ({ en, fr: en, de: en, ro });
const entry = (category, topic, text) => ({ category, topic: both(topic, topic + " (ro)"), text: both(text, text + " (ro)") });

test("notes group New, Improved, Fixed with topics in first-appearance order", () => {
  const release = { version: "Unreleased", date: null, entries: [
    entry("fixed", "Jobs", "f1"), entry("improved", "Statistics", "i1"), entry("new", "About", "n1"),
    entry("improved", "Jobs", "i2"), entry("improved", "Statistics", "i3"),
  ] };
  assert.deepEqual(groupRelease(release, "ro"), [
    { category: "new", topics: [{ topic: "About (ro)", texts: ["n1 (ro)"] }] },
    { category: "improved", topics: [{ topic: "Statistics (ro)", texts: ["i1 (ro)", "i3 (ro)"] }, { topic: "Jobs (ro)", texts: ["i2 (ro)"] }] },
    { category: "fixed", topics: [{ topic: "Jobs (ro)", texts: ["f1 (ro)"] }] },
  ]);
});

test("a missing or empty locale falls back to English", () => {
  assert.equal(localText({ en: "Hello", fr: "", de: "Hallo" }, "fr"), "Hello");
  assert.equal(localText({ en: "Hello", de: "Hallo" }, "ro"), "Hello");
  assert.equal(localText({ en: "Hello", de: "Hallo" }, "de"), "Hallo");
  assert.deepEqual(groupRelease({ version: "1.0.0", date: "2026-01-01", entries: [] }, "en"), []);
});

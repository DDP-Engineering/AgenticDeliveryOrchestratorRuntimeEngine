/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { OPERATION_REASONS, keptLabels, outcomeText, reasonSentence } from "../src/operationReason.ts";

const locales = ["en", "fr", "de", "ro"];

test("the reason codes match the ones the worker parses from the engine", () => {
  const worker = readFileSync(new URL("../../adore/web/commands.py", import.meta.url), "utf8");
  const codes = worker.match(/not started: "\s*r"\(([a-z_|]+)\)/)[1].split("|");
  assert.deepEqual([...OPERATION_REASONS].sort(), codes.sort());
});

test("every refusal reason has its own sentence in every locale", () => {
  for (const locale of locales) {
    const sentences = OPERATION_REASONS.map(reason => reasonSentence(locale, reason));
    for (const [index, sentence] of sentences.entries()) {
      assert.equal(typeof sentence, "string", `${locale} ${OPERATION_REASONS[index]}`);
      assert.ok(sentence.length > 10 && !sentence.includes("_"), `${locale} ${OPERATION_REASONS[index]}`);
    }
    assert.equal(new Set(sentences).size, sentences.length, `${locale} sentences are distinct`);
  }
});

test("a known reason replaces the stored result text", () => {
  for (const locale of locales) {
    const operation = { status: "failed", result: "engine rejected operation", reason: "at_capacity" };
    assert.equal(outcomeText(locale, operation), reasonSentence(locale, "at_capacity"));
  }
});

test("only a refused Start names the labels it left on the ticket", () => {
  const labels = ["agent-ready", "P1"];
  for (const reason of OPERATION_REASONS) assert.deepEqual(keptLabels({ status: "failed", reason }, labels), labels, reason);
  assert.deepEqual(keptLabels({ status: "failed", reason: "at_capacity" }, []), []);
  assert.deepEqual(keptLabels({ status: "failed", reason: "at_capacity" }, undefined), []);
  // A failure without a known reason may come after the job started: Retry, not pickup, is next.
  for (const reason of [undefined, "", "something_else"]) assert.deepEqual(keptLabels({ status: "failed", reason }, labels), []);
  for (const status of ["pending", "running", "succeeded", "uncertain"]) {
    assert.deepEqual(keptLabels({ status, reason: "at_capacity" }, labels), [], status);
  }
  assert.deepEqual(keptLabels(undefined, labels), []);
});

test("an empty or unknown reason falls back to the stored result", () => {
  for (const reason of [undefined, "", "something_else"]) {
    assert.equal(reasonSentence("en", reason), null);
    assert.equal(outcomeText("en", { status: "failed", result: "engine rejected operation", reason }),
      "engine rejected operation");
  }
  assert.equal(outcomeText("en", { status: "succeeded", result: "completed", reason: "" }), "completed");
  assert.equal(outcomeText("en", { status: "pending" }), "");
});

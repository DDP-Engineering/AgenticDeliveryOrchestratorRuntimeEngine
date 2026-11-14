/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { completedConfiguration } from "../src/configurationTasks.ts";

const accepted = () => Response.json({ id: 41, status: "pending", domain: "configuration_project", project_id: "a".repeat(32) }, { status: 202 });
const record = (changes = {}) => ({ id: 41, action: "configure", domain: "configuration_project", project_id: "a".repeat(32), status: "succeeded", outcome: { status_code: 200, body: { revision: "b".repeat(64) } }, ...changes });

test("acceptance waits for the exact confirmed durable configuration result", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (path, options) => {
    assert.equal(path, "/api/v1/operations/41");
    assert.equal(options.cache, "no-store");
    calls++;
    return Response.json(record(calls === 1 ? { status: "running", outcome: null } : {}));
  };
  try {
    const response = await completedConfiguration(accepted());
    assert.equal(calls, 2);
    assert.deepEqual(await response.json(), { revision: "b".repeat(64) });
  } finally { globalThis.fetch = original; }
});

test("configuration conflicts and uncertainty never become successful saves", async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => Response.json(record({ status: "failed", outcome: {
      status_code: 409, body: { detail: { code: "stale_config_revision" } },
    } }));
    const conflict = await completedConfiguration(accepted());
    assert.equal(conflict.status, 409);
    assert.equal((await conflict.json()).detail.code, "stale_config_revision");
    globalThis.fetch = async () => Response.json(record({ status: "uncertain", outcome: null }));
    assert.equal((await completedConfiguration(accepted())).status, 409);
  } finally { globalThis.fetch = original; }
});

test("mismatched identity, missing result and false success fail closed", async () => {
  const original = globalThis.fetch;
  try {
    for (const changes of [{ id: 42 }, { project_id: "c".repeat(32) }, { outcome: null },
      { outcome: { status_code: 409, body: {} } }, { status: "unknown" }]) {
      globalThis.fetch = async () => Response.json(record(changes));
      await assert.rejects(completedConfiguration(accepted()), /unexpected_response/);
    }
    const controller = new AbortController();
    controller.abort();
    await assert.rejects(completedConfiguration(accepted(), controller.signal), /abort/i);
  } finally { globalThis.fetch = original; }
});

test("ordinary HTTP responses and existing environment preparation stay unchanged", async () => {
  const ready = Response.json({ revision: "a" });
  assert.equal(await completedConfiguration(ready), ready);
  const preparation = Response.json({ id: "environment", status: "queued" }, { status: 202 });
  assert.equal(await completedConfiguration(preparation), preparation);
});

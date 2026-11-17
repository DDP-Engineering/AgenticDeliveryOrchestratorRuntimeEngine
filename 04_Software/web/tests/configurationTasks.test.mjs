import { test } from "node:test";
import assert from "node:assert/strict";
import { completedConfiguration } from "../src/configurationTasks.ts";
import { ApiError } from "../src/errors.ts";

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

/** Record every requested wait and let it pass at once. */
async function withRecordedWaits(run) {
  const fetchBefore = globalThis.fetch, timerBefore = globalThis.setTimeout;
  const waits = [];
  globalThis.setTimeout = (callback, milliseconds) => { waits.push(milliseconds); return timerBefore(callback, 0); };
  try { await run(waits); } finally { globalThis.fetch = fetchBefore; globalThis.setTimeout = timerBefore; }
}

test("a long request is asked about less and less often, two seconds apart at most", async () => {
  await withRecordedWaits(async waits => {
    let calls = 0;
    globalThis.fetch = async () => Response.json(record(++calls <= 12 ? { status: "running", outcome: null } : {}));
    assert.equal((await completedConfiguration(accepted())).status, 200);
    assert.equal(waits.length, 12);
    assert.equal(waits[0], 150);
    assert.ok(waits.every((wait, index) => index === 0 || wait >= waits[index - 1]));
    assert.ok(waits[1] > waits[0] && waits[6] < 2000);
    assert.deepEqual(waits.slice(7), [2000, 2000, 2000, 2000, 2000]);
  });
});

test("a short loss of the server is retried; a lasting one is reported as a network error", async () => {
  await withRecordedWaits(async waits => {
    let calls = 0;
    globalThis.fetch = async () => {
      if (++calls <= 3) throw new TypeError("Failed to fetch");
      return Response.json(record());
    };
    assert.equal((await completedConfiguration(accepted())).status, 200);
    assert.equal(calls, 4);
    assert.equal(waits.length, 3);
    calls = 0;
    globalThis.fetch = async () => { calls++; throw new TypeError("Failed to fetch"); };
    await assert.rejects(completedConfiguration(accepted()), failure =>
      failure instanceof ApiError && failure.code === "network_error" && failure.detail === "Failed to fetch");
    assert.equal(calls, 4);
    // Failures count only when they follow each other.
    calls = 0;
    globalThis.fetch = async () => {
      if (++calls % 2) throw new TypeError("Failed to fetch");
      return Response.json(record(calls < 12 ? { status: "running", outcome: null } : {}));
    };
    assert.equal((await completedConfiguration(accepted())).status, 200);
    assert.equal(calls, 12);
  });
});

test("an unreadable or unexpected answer is a coded error; an abort is not retried", async () => {
  await withRecordedWaits(async () => {
    globalThis.fetch = async () => new Response("<html>", { status: 200 });
    await assert.rejects(completedConfiguration(accepted()), failure =>
      failure instanceof ApiError && failure.code === "unexpected_response");
    const controller = new AbortController();
    let calls = 0;
    globalThis.fetch = async () => { calls++; controller.abort(); throw new DOMException("stopped", "AbortError"); };
    await assert.rejects(completedConfiguration(accepted(), controller.signal), /abort/i);
    assert.equal(calls, 1);
  });
});

test("ordinary HTTP responses and existing environment preparation stay unchanged", async () => {
  const ready = Response.json({ revision: "a" });
  assert.equal(await completedConfiguration(ready), ready);
  const preparation = Response.json({ id: "environment", status: "queued" }, { status: 202 });
  assert.equal(await completedConfiguration(preparation), preparation);
});

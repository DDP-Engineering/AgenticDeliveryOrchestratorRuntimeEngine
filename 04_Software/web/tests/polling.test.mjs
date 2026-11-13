/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { startVisiblePolling } from "../src/polling.ts";
import * as polling from "../src/polling.ts";
import * as errors from "../src/errors.ts";

/** Fake page: controllable visibility and manually advanced interval timers. */
function fakeEnv(visibility = "visible") {
  const listeners = new Set();
  const timers = new Map();
  let nextId = 1;
  const env = {
    document: {
      visibilityState: visibility,
      addEventListener: (type, listener) => { if (type === "visibilitychange") listeners.add(listener); },
      removeEventListener: (type, listener) => { if (type === "visibilitychange") listeners.delete(listener); },
    },
    setInterval: (handler, ms) => { const id = nextId++; timers.set(id, { handler, ms }); return id; },
    clearInterval: id => { timers.delete(id); },
  };
  return {
    env,
    listeners,
    timers,
    elapse: () => { for (const { handler } of [...timers.values()]) handler(); },
    setVisibility: value => { env.document.visibilityState = value; for (const listener of [...listeners]) listener(); },
  };
}

test("polls on the interval while visible", () => {
  const page = fakeEnv();
  let ticks = 0;
  startVisiblePolling(() => { ticks += 1; }, 15000, page.env);
  assert.equal(page.timers.size, 1);
  assert.equal([...page.timers.values()][0].ms, 15000);
  page.elapse(); page.elapse();
  assert.equal(ticks, 2);
});

test("sends nothing while hidden, refreshes at once when shown and resumes", () => {
  const page = fakeEnv();
  let ticks = 0;
  startVisiblePolling(() => { ticks += 1; }, 15000, page.env);
  page.setVisibility("hidden");
  assert.equal(page.timers.size, 0);
  page.elapse();
  assert.equal(ticks, 0);
  page.setVisibility("visible");
  assert.equal(ticks, 1);
  assert.equal(page.timers.size, 1);
  page.elapse();
  assert.equal(ticks, 2);
});

test("starting while hidden waits for visibility and repeated events do not double-poll", () => {
  const page = fakeEnv("hidden");
  let ticks = 0;
  startVisiblePolling(() => { ticks += 1; }, 5000, page.env);
  assert.equal(page.timers.size, 0);
  page.setVisibility("visible");
  page.setVisibility("visible");
  assert.equal(ticks, 1);
  assert.equal(page.timers.size, 1);
});

test("queued periodic callbacks cannot read after hide or stop", () => {
  const page = fakeEnv();
  let ticks = 0;
  const stop = startVisiblePolling(() => { ticks++; }, 15000, page.env);
  const queued = [...page.timers.values()][0].handler;
  page.setVisibility("hidden");
  queued();
  assert.equal(ticks, 0);
  page.setVisibility("visible");
  assert.equal(ticks, 1);
  stop();
  queued();
  assert.equal(ticks, 1);
});

/** A deferred validated read; no server or real clock is involved. */
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

/** Owned deadline clock, independent from the visibility interval fake. */
function readClock() {
  let now = 1000;
  let next = 1;
  const timers = new Map();
  return {
    env: {
      now: () => now,
      setTimeout: (fn, ms) => { const id = next++; timers.set(id, { fn, at: now + ms }); return id; },
      clearTimeout: id => timers.delete(id),
    },
    advance(ms) {
      now += ms;
      for (const [id, timer] of [...timers]) {
        if (timer.at <= now) { timers.delete(id); timer.fn(); }
      }
    },
    timers,
  };
}

function reader(options = {}) {
  assert.equal(typeof polling.createReadController, "function", "bounded read owner is available");
  const clock = readClock();
  const requests = [];
  const states = [];
  const owner = polling.createReadController({
    key: "account:1/project:alpha/query:all",
    deadlineMs: 30000,
    read: signal => { const next = deferred(); requests.push({ ...next, signal }); return next.promise; },
    publish: state => states.push(state),
    env: clock.env,
    ...options,
  });
  return { owner, clock, requests, states, latest: () => states.at(-1) };
}

const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };

async function succeed(h, value) {
  const pending = h.owner.refresh();
  await flush();
  h.requests.at(-1).resolve(value);
  await pending;
}

async function fail(h, error) {
  const pending = h.owner.refresh();
  await flush();
  h.requests.at(-1).reject(error);
  await pending;
}

test("owned reads retain validated content while duplicate triggers join without a backlog", async () => {
  const h = reader();
  const initial = h.owner.refresh();
  assert.deepEqual(h.latest(), { key: "account:1/project:alpha/query:all", status: "loading", data: null,
    refreshing: true, error: null, completedAt: null });
  assert.equal(h.owner.refresh(), initial);
  await flush();
  assert.equal(h.requests.length, 1);
  const rows = [{ id: "one", count: 7 }];
  h.clock.advance(200);
  h.requests[0].resolve(rows);
  await initial;
  assert.equal(h.latest().status, "ready");
  assert.equal(h.latest().data, rows);
  assert.equal(h.latest().completedAt, 1200);
  const refresh = h.owner.refresh();
  assert.equal(h.latest().data, rows);
  assert.equal(h.latest().status, "ready");
  assert.equal(h.latest().refreshing, true);
  assert.equal(h.latest().completedAt, 1200);
  for (let i = 0; i < 10; i++) assert.equal(h.owner.refresh(), refresh);
  await flush();
  assert.equal(h.requests.length, 2);
  h.clock.advance(500);
  h.requests[1].resolve([{ id: "one", count: 8 }]);
  await refresh;
  await flush();
  assert.equal(h.requests.length, 2, "no queued burst after release");
  assert.equal(h.latest().data[0].count, 8);
  assert.equal(h.latest().completedAt, 1700);
  assert.equal(h.latest().refreshing, false);
  assert.equal(h.clock.timers.size, 0);
});

test("informational transport failure stays stale through retry until validated recovery", async () => {
  const h = reader({ policy: "informational" });
  await succeed(h, []);
  const completedAt = h.latest().completedAt;
  h.clock.advance(500);
  const failure = new errors.ReadTransportError();
  await fail(h, failure);
  assert.equal(h.latest().status, "stale");
  assert.deepEqual(h.latest().data, [], "validated empty is still a snapshot");
  assert.equal(h.latest().error, failure);
  assert.equal(h.latest().completedAt, completedAt);
  const retry = h.owner.refresh();
  assert.equal(h.latest().status, "stale");
  assert.equal(h.latest().error, failure);
  assert.equal(h.latest().refreshing, true);
  await flush();
  h.requests.at(-1).resolve([]);
  await retry;
  assert.equal(h.latest().status, "ready");
  assert.equal(h.latest().error, null);
  assert.equal(h.latest().completedAt, 1500, "unchanged valid success records completion");
});

test("initial transport failure and strict authority refresh fail closed", async () => {
  const initial = reader({ policy: "informational" });
  await fail(initial, new errors.ReadTransportError());
  assert.equal(initial.latest().status, "error");
  assert.equal(initial.latest().data, null);
  assert.equal(initial.latest().completedAt, null);
  const strict = reader();
  await succeed(strict, { grants: ["alpha"] });
  await fail(strict, new errors.ReadTransportError());
  assert.equal(strict.latest().status, "error");
  assert.equal(strict.latest().data, null);
  assert.equal(strict.latest().completedAt, null);
});

test("application, corrupt, authorization and unclassified failures cannot retain information", async () => {
  const failures = [new errors.ApiError("network_error"), new errors.ApiError("authentication_required"),
    new errors.ApiError("metrics_corrupt"), new errors.ApiError("job_snapshot_changed"),
    new errors.ApiError("new_server_failure"), new SyntaxError("invalid JSON"), new TypeError("unclassified")];
  for (const failure of failures) {
    const h = reader({ policy: "informational" });
    await succeed(h, { count: 5 });
    await fail(h, failure);
    assert.equal(h.latest().status, "error", failure.message);
    assert.equal(h.latest().data, null, failure.message);
    assert.equal(h.latest().completedAt, null);
    assert.equal(h.latest().error, failure);
  }
});

test("deadline is finite, joins do not extend it, and ignored abort cannot occupy the retry slot", async () => {
  for (const populated of [false, true]) {
    const h = reader({ policy: "informational" });
    if (populated) await succeed(h, { count: 1 });
    const pending = h.owner.refresh();
    await flush();
    const old = h.requests.at(-1);
    h.clock.advance(29999);
    assert.equal(h.owner.refresh(), pending);
    h.clock.advance(1);
    await pending;
    assert.equal(old.signal.aborted, true);
    assert.equal(h.latest().status, populated ? "stale" : "error");
    assert.ok(h.latest().error instanceof errors.ReadDeadlineError);
    await succeed(h, { count: 2 });
    const current = h.latest();
    old.resolve({ count: 999 });
    await flush();
    assert.equal(h.latest(), current, "expired success cannot update values or freshness");
    assert.equal(h.clock.timers.size, 0);
  }
});

test("invalidation cancels old ownership and a late failure cannot replace post-mutation success", async () => {
  const h = reader();
  await succeed(h, { count: 1 });
  const pending = h.owner.refresh();
  await flush();
  const old = h.requests.at(-1);
  h.owner.invalidate();
  await pending;
  assert.equal(old.signal.aborted, true);
  assert.equal(h.latest().data, null);
  assert.equal(h.latest().completedAt, null);
  assert.equal(h.latest().refreshing, false);
  await succeed(h, { count: 2 });
  const current = h.latest();
  old.reject(new errors.ApiError("authentication_required"));
  await flush();
  assert.equal(h.latest(), current);
  assert.equal(h.clock.timers.size, 0);
});

test("dispose cancels a hung read, settles joiners and forbids later reads/publication", async () => {
  const h = reader();
  const pending = h.owner.refresh();
  await flush();
  const old = h.requests[0];
  const count = h.states.length;
  h.owner.dispose();
  h.owner.dispose();
  await pending;
  assert.equal(old.signal.aborted, true);
  await h.owner.refresh();
  h.owner.invalidate();
  old.resolve({ count: 99 });
  h.clock.advance(60000);
  await flush();
  assert.equal(h.states.length, count);
  assert.equal(h.requests.length, 1);
  assert.equal(h.clock.timers.size, 0);
});

test("failed validation aborts sibling work and retry without a snapshot uses initial loading", async () => {
  const h = reader({ policy: "informational" });
  await succeed(h, { count: 1 });
  await fail(h, new errors.ApiError("metrics_corrupt"));
  assert.equal(h.requests.at(-1).signal.aborted, true, "failed attempt must cancel remaining transport work");
  const pending = h.owner.refresh();
  assert.equal(h.latest().status, "loading");
  assert.equal(h.latest().data, null);
  assert.equal(h.latest().error, null);
  await flush();
  h.requests.at(-1).resolve({ count: 2 });
  await pending;
  assert.equal(h.latest().status, "ready");
  assert.equal(h.requests.at(-1).signal.aborted, false);
});

test("a synchronous validator failure closes evidence and invalid deadlines are refused before reading", async () => {
  assert.equal(typeof polling.createReadController, "function");
  const failure = new errors.ApiError("unexpected_response");
  const states = [];
  const owner = polling.createReadController({ key: "scope", deadlineMs: 10000,
    read: () => { throw failure; }, publish: state => states.push(state) });
  await owner.refresh();
  assert.equal(states.at(-1).status, "error");
  assert.equal(states.at(-1).error, failure);
  assert.equal(states.at(-1).data, null);
  for (const deadlineMs of [0, -1, 1.5, NaN, Infinity, 2147483648]) {
    assert.throws(() => polling.createReadController({ key: "scope", deadlineMs,
      read: async () => { assert.fail("invalid owner must never read"); }, publish: () => {} }), RangeError);
  }
});

test("invalidating during publication cannot start an unowned transport", async () => {
  let owner;
  let reads = 0;
  owner = polling.createReadController?.({ key: "alpha", deadlineMs: 30000,
    read: async () => { reads++; return []; },
    publish: state => { if (state.refreshing) owner.dispose(); } });
  assert.ok(owner, "bounded read owner is available");
  await owner.refresh();
  assert.equal(reads, 0);
});

test("stop clears the timer and the visibility listener", () => {
  const page = fakeEnv();
  let ticks = 0;
  const stop = startVisiblePolling(() => { ticks += 1; }, 15000, page.env);
  stop();
  assert.equal(page.timers.size, 0);
  assert.equal(page.listeners.size, 0);
  page.setVisibility("visible");
  assert.equal(ticks, 0);
});

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { startVisiblePolling } from "../src/polling.ts";

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
  assert.equal(ticks, 2);
  assert.equal(page.timers.size, 1);
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

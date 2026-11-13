/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequestScope, rawRequest } from "../src/request.ts";
import { ApiError, ReadTransportError } from "../src/errors.ts";
import { createReadController } from "../src/polling.ts";

const response = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

test("request scope accepts valid JSON and forwards body, CSRF and cancellation", async t => {
  let seen;
  t.mock.method(globalThis, "fetch", async (path, init) => { seen = { path, ...init }; return response({ ok: true }); });
  const scope = createRequestScope(() => assert.fail("unexpected denial"));
  assert.deepEqual(await scope.request("/example", "POST", { value: 7 }, "csrf"), { ok: true });
  assert.equal(seen.path, "/api/v1/example");
  assert.equal(seen.headers["X-CSRF-Token"], "csrf");
  assert.equal(seen.body, '{"value":7}');
  assert.equal(seen.cache, "no-store");
  scope.dispose();
  assert.equal(seen.signal.aborted, true);
  await assert.rejects(scope.request("/example"), { name: "AbortError" });
});

test("disposal rejects late success and late denial even when fetch ignores abort", async t => {
  let finish;
  t.mock.method(globalThis, "fetch", () => new Promise(resolve => { finish = resolve; }));
  for (const status of [200, 403]) {
    const scope = createRequestScope(() => assert.fail("obsolete denial cannot reset a new account"));
    scope.activate();
    const result = scope.request("/users");
    scope.dispose(); finish(response({ detail: { code: "admin_required" } }, status));
    await assert.rejects(result, { name: "AbortError" });
  }
});

test("HTTP denial ends one authenticated scope and cancels sibling work once", async t => {
  let signal;
  t.mock.method(globalThis, "fetch", async (path, init) => {
    if (path.endsWith("/held")) { signal = init.signal; return new Promise(() => {}); }
    return response({ detail: { code: "admin_required" } }, 403);
  });
  let denials = 0;
  const scope = createRequestScope(code => { assert.equal(code, "request_rejected"); denials++; });
  scope.activate(); void scope.request("/held");
  await assert.rejects(scope.request("/users"), ApiError);
  assert.equal(signal.aborted, true);
  await assert.rejects(scope.request("/users"), { name: "AbortError" });
  assert.equal(denials, 1);
});

test("raw and login denial retain useful payload codes without revoking an unauthenticated scope", async t => {
  t.mock.method(globalThis, "fetch", async () => response({ detail: { code: "invalid_credentials", message: "Sign-in refused" } }, 401));
  const scope = createRequestScope(() => assert.fail("login does not own an authenticated principal"));
  for (const request of [rawRequest, scope.request]) {
    await assert.rejects(request("/session", "POST"), error => error instanceof ApiError &&
      error.code === "invalid_credentials" && error.detail === "Sign-in refused");
  }
  assert.equal(scope.disposed(), false);
});

test("login denial is local, untyped HTTP denial is closed and 404 stays resource-local", async t => {
  let status = 401;
  t.mock.method(globalThis, "fetch", async () => new Response("not JSON", { status }));
  let denials = 0;
  const scope = createRequestScope(() => { denials++; });
  await assert.rejects(scope.request("/session", "POST"), ApiError);
  assert.equal(denials, 0);
  scope.activate(); status = 404;
  await assert.rejects(scope.request("/projects/missing"), ApiError);
  assert.equal(denials, 0);
  status = 403;
  await assert.rejects(scope.request("/users"), ApiError);
  assert.equal(denials, 1);
});

/** Status is already authority evidence even when the explanatory body never arrives. */
for (const status of [401, 403]) test(`HTTP ${status} headers immediately revoke scope despite a stalled body and later deadline`, async t => {
  let calls = 0, body;
  const mock = t.mock.method(globalThis, "fetch", async () => ++calls === 1 ? response({ protected: true }) :
    new Response(new ReadableStream({ start(controller) { body = controller; } }), {
      status, headers: { "Content-Type": "application/json" },
    }));
  const flush = async () => { for (let n = 0; n < 25; n++) await Promise.resolve(); };
  let denied = 0, snapshot;
  const scope = createRequestScope(() => { denied++; }); scope.activate();
  const timers = new Map();
  const owner = createReadController({ key: "admin/report", deadlineMs: 30000, policy: "informational",
    read: signal => scope.request("/metrics", "GET", undefined, undefined, signal), publish: value => { snapshot = value; },
    env: { now: () => 1000, setTimeout: fn => { const id = {}; timers.set(id, fn); return id; }, clearTimeout: id => timers.delete(id) },
  });
  try {
    await owner.refresh(); assert.equal(snapshot.status, "ready");
    const pending = owner.refresh(); await flush();
    assert.equal(denied, 1, "deny at headers, before body or deadline");
    assert.equal(scope.disposed(), true);
    await pending;
    assert.equal(snapshot.status, "error"); assert.equal(snapshot.data, null); assert.equal(snapshot.completedAt, null);
    for (const fn of [...timers.values()]) fn(); await flush();
    // A cancelled stream need not accept late bytes. Either way, old evidence cannot revive.
    try { body.enqueue(new TextEncoder().encode('{"detail":{"code":"admin_required"}}')); body.close(); } catch {}
    await flush();
    assert.equal(snapshot.data, null); assert.equal(snapshot.status, "error"); assert.equal(denied, 1);
    await assert.rejects(scope.request("/users"), { name: "AbortError" });
    assert.equal(mock.mock.callCount(), 2);
  } finally { owner.dispose(); scope.dispose(); }
});

test("only fetch transport failure is transient; JSON, media and HTTP evidence are not", async t => {
  const mock = t.mock.method(globalThis, "fetch", async () => { throw new TypeError("offline"); });
  await assert.rejects(rawRequest("/metrics"), ReadTransportError);
  mock.mock.mockImplementation(async () => new Response("broken", { headers: { "Content-Type": "application/json" } }));
  await assert.rejects(rawRequest("/metrics"), error => error instanceof ApiError && !(error instanceof ReadTransportError));
  mock.mock.mockImplementation(async () => new Response("{}"));
  await assert.rejects(rawRequest("/metrics"), error => error.code === "unexpected_response");
  mock.mock.mockImplementation(async () => response({ detail: { code: "network_error" } }, 503));
  await assert.rejects(rawRequest("/metrics"), error => error instanceof ApiError && !(error instanceof ReadTransportError));
});

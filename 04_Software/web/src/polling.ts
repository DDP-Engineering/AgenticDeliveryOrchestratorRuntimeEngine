/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { isInformationalReadFailure, ReadDeadlineError } from "./errors.ts";

export type PollEnv = {
  document: { visibilityState: string; addEventListener(type: string, listener: () => void): void; removeEventListener(type: string, listener: () => void): void };
  setInterval(handler: () => void, ms: number): number;
  clearInterval(id: number): void;
};

/** One validated resource snapshot, bound to an immutable owner/context key. */
export type ReadSnapshot<T> = {
  readonly key: string;
  readonly status: "loading" | "ready" | "stale" | "error";
  readonly data: T | null;
  readonly refreshing: boolean;
  readonly error: unknown;
  readonly completedAt: number | null;
};

/** Injectable clock for finite read deadlines and successful publication times. */
export type ReadEnv = {
  now(): number;
  setTimeout(handler: () => void, ms: number): ReturnType<typeof globalThis.setTimeout>;
  clearTimeout(id: ReturnType<typeof globalThis.setTimeout>): void;
};

export type ReadController = {
  refresh(): Promise<void>;
  invalidate(): void;
  dispose(): void;
};

const readEnv = (): ReadEnv => ({
  now: () => Date.now(),
  setTimeout: (handler, ms) => globalThis.setTimeout(handler, ms),
  clearTimeout: id => globalThis.clearTimeout(id),
});

/**
 * Own one resource/context's validated reads, not writes or authorization decisions.
 * `read` must validate the entire response before resolving. `publish` receives
 * initial/pending, ready, stale or closed-error state; only informational owners
 * may retain a snapshot after a positively classified transport/deadline failure.
 * Repeated refresh calls join the same promise without extending its deadline or
 * queuing more reads. The promise settles after publication or cancellation;
 * read failures are published, not thrown to timer/click callers.
 *
 * Invalidate before an intervening mutation: abort and clear the old snapshot,
 * then explicitly refresh after the write. Dispose on context exit/unmount and
 * stop the owner's visibility scheduler separately. Callers must synchronously
 * gate rendering by `key`; this controller never caches another context's data.
 * Cancellation settles joiners even when a transport ignores its AbortSignal.
 */
export function createReadController<T>(options: {
  key: string;
  read(signal: AbortSignal): Promise<T>;
  publish(snapshot: ReadSnapshot<T>): void;
  deadlineMs: number;
  policy?: "strict" | "informational";
  env?: ReadEnv;
}): ReadController {
  if (!Number.isSafeInteger(options.deadlineMs) || options.deadlineMs <= 0 || options.deadlineMs > 2147483647) {
    throw new RangeError("Read deadline must be a positive timer-safe integer");
  }
  const env = options.env ?? readEnv();
  const empty = (): ReadSnapshot<T> => ({ key: options.key, status: "loading", data: null,
    refreshing: false, error: null, completedAt: null });
  type Outcome = { kind: "success"; data: T } | { kind: "failure"; error: unknown } | { kind: "cancelled" };
  type Attempt = { controller: AbortController; promise: Promise<void>; cancel(): void;
    timer: ReturnType<ReadEnv["setTimeout"]> | null };
  let snapshot = empty();
  let active: Attempt | null = null;
  let disposed = false;

  const clearDeadline = (attempt: Attempt) => {
    if (attempt.timer !== null) { env.clearTimeout(attempt.timer); attempt.timer = null; }
  };
  const cancel = () => {
    const attempt = active;
    active = null; // End publication authority before abort listeners can react.
    if (attempt) { clearDeadline(attempt); attempt.cancel(); attempt.controller.abort(); }
  };

  return {
    refresh() {
      if (disposed) return Promise.resolve();
      if (active) return active.promise;
      let finish!: (outcome: Outcome) => void;
      const outcome = new Promise<Outcome>(resolve => { finish = resolve; });
      const attempt: Attempt = { controller: new AbortController(), promise: Promise.resolve(),
        cancel: () => finish({ kind: "cancelled" }), timer: null };
      active = attempt;
      attempt.timer = env.setTimeout(() => {
        finish({ kind: "failure", error: new ReadDeadlineError() });
        attempt.controller.abort();
      }, options.deadlineMs);
      attempt.promise = outcome.then(result => {
        if (active !== attempt || disposed) return;
        active = null;
        clearDeadline(attempt);
        if (result.kind === "cancelled") return;
        if (result.kind === "success") {
          snapshot = { key: options.key, status: "ready", data: result.data, refreshing: false,
            error: null, completedAt: env.now() };
        } else {
          attempt.controller.abort(); // A failed aggregate must stop remaining sibling reads.
          const retain = options.policy === "informational" && snapshot.completedAt !== null
            && isInformationalReadFailure(result.error);
          snapshot = { ...(retain ? snapshot : empty()), status: retain ? "stale" : "error",
            refreshing: false, error: result.error };
        }
        options.publish(snapshot);
      });
      // Schedule transport after assigning the joined promise; publication may
      // synchronously invalidate/dispose the owner and must not start an old read.
      void Promise.resolve().then(() => {
        if (active === attempt && !disposed) {
          return options.read(attempt.controller.signal).then(
            data => finish({ kind: "success", data }),
            error => finish({ kind: "failure", error }),
          );
        }
      }).catch(error => finish({ kind: "failure", error }));
      snapshot = snapshot.completedAt === null
        ? { ...empty(), refreshing: true }
        : { ...snapshot, refreshing: true };
      options.publish(snapshot);
      return attempt.promise;
    },
    invalidate() {
      if (disposed) return;
      cancel();
      snapshot = empty();
      options.publish(snapshot);
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      cancel();
      snapshot = empty();
    },
  };
}

const browserEnv = (): PollEnv => ({
  document,
  setInterval: (handler, ms) => window.setInterval(handler, ms),
  clearInterval: id => window.clearInterval(id),
});

/**
 * Repeat `tick` every `intervalMs` while the page is visible.
 * Hiding the page stops the timer; a hidden-to-visible transition runs `tick`
 * once and restarts the interval. Duplicate visibility events do not revalidate.
 * Returns a function that stops polling; async resource owners coalesce reads.
 */
export function startVisiblePolling(tick: () => void, intervalMs: number, env: PollEnv = browserEnv()): () => void {
  let timer: number | null = null;
  let visible = env.document.visibilityState === "visible";
  let stopped = false;
  const eligibleTick = () => { if (!stopped && env.document.visibilityState === "visible") tick(); };
  const start = () => { if (!stopped && timer === null) timer = env.setInterval(eligibleTick, intervalMs); };
  const halt = () => { if (timer !== null) { env.clearInterval(timer); timer = null; } };
  const onVisibility = () => {
    const next = env.document.visibilityState === "visible";
    if (stopped || next === visible) return;
    visible = next;
    if (visible) { eligibleTick(); start(); }
    else halt();
  };
  env.document.addEventListener("visibilitychange", onVisibility);
  if (visible) start();
  return () => { stopped = true; env.document.removeEventListener("visibilitychange", onVisibility); halt(); };
}

import { useEffect, useRef, useState } from "react";
import { ApiError } from "./errors.ts";
import { readUntilAbort, startVisiblePolling } from "./polling.ts";

export type Snapshot<T> = {
  key: string | null; data: T | null; reading: boolean; failure: unknown; updatedAt: string | null;
};

/** Only transport outages may retain informational evidence, never rejected or corrupt evidence. */
export function transientReadFailure(cause: unknown): boolean {
  return cause instanceof ApiError && (cause.code === "network_error" ||
    cause.code === "request_failed" && [502, 503, 504].includes(cause.status ?? 0));
}

/**
 * A context-bound, single-flight read. The reader must validate before returning.
 * Context changes hide old data synchronously; cleanup aborts and fences late results.
 * Same-context revalidation keeps component identity, even for identical responses.
 * Authority-bearing resources opt out of stale retention.
 */
export function useSnapshot<T>(key: string | null, read: (signal: AbortSignal) => Promise<T>,
  interval: number | null, revision = 0, retainInformational = true, timeoutMs = 30000) {
  const [snapshot, setSnapshot] = useState<Snapshot<T>>({ key: null, data: null, reading: false, failure: null, updatedAt: null });
  const reader = useRef(read); reader.current = read;
  const reload = useRef<() => Promise<void>>(async () => {});
  useEffect(() => {
    if (key === null) { setSnapshot({ key, data: null, reading: false, failure: null, updatedAt: null }); return; }
    let active = true;
    let flight: Promise<void> | null = null;
    let controller: AbortController | null = null;
    const load = (): Promise<void> => {
      if (flight) return flight;
      controller = new AbortController();
      const current = controller;
      const deadline = window.setTimeout(() => current.abort(), timeoutMs);
      setSnapshot(previous => previous.key === key ? { ...previous, reading: true } :
        { key, data: null, reading: true, failure: null, updatedAt: null });
      flight = (async () => {
        try {
          const data = await readUntilAbort(reader.current(current.signal), current.signal);
          if (!active || current.signal.aborted) return;
          setSnapshot(previous => ({ key,
            data: previous.key === key && JSON.stringify(previous.data) === JSON.stringify(data) ? previous.data : data,
            reading: false, failure: null, updatedAt: new Date().toISOString() }));
        } catch (cause) {
          const failure = current.signal.aborted ? new ApiError("network_error") : cause;
          if (active) setSnapshot(previous => ({ key,
            data: retainInformational && transientReadFailure(failure) && previous.key === key ? previous.data : null,
            reading: false, failure, updatedAt: previous.key === key ? previous.updatedAt : null }));
        } finally { window.clearTimeout(deadline); flight = null; }
      })();
      return flight;
    };
    reload.current = load;
    void load();
    const stop = interval === null ? () => {} : startVisiblePolling(() => void load(), interval);
    return () => { active = false; stop(); controller?.abort(); reload.current = async () => {}; };
  // An operation completion invalidates an older in-flight read. Manual refresh
  // joins it instead; both paths retain the same-context rendered snapshot.
  }, [key, interval, retainInformational, timeoutMs, revision]);
  const visible = snapshot.key === key ? snapshot : { key, data: null, reading: key !== null, failure: null, updatedAt: null };
  return { ...visible, refresh: () => reload.current() };
}

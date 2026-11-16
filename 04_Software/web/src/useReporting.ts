import { useEffect, useRef, useState } from "react";
import { ApiError } from "./errors.ts";
import type { Metrics, Usage } from "./metrics";
import { readUntilAbort, startVisiblePolling } from "./polling.ts";
import { transientReadFailure, type Snapshot } from "./useSnapshot.ts";

export type Reporting = { metrics: Record<string, Metrics>; usage: Record<string, Usage> };
const scopes = (items: Array<Metrics | Usage>) => items.map(item => JSON.stringify([item.scope?.project_ids,
  item.scope?.mode, item.scope?.interval, item.scope?.from, item.scope?.to, item.scope?.timezone,
  item.scope?.granularity, item.scope?.interval_seconds])).sort().join("\0");

/**
 * Keep the two existing read cadences, but publish only a complete reporting cohort.
 * Faster metrics reads stage a replacement until usage is also revalidated. Never
 * combine a newly read source with the previously displayed source. An in-flight
 * counterpart must finish before publication; failures invalidate the whole cohort.
 */
export function useReporting(key: string | null,
  readMetrics: (signal: AbortSignal) => Promise<Record<string, Metrics>>,
  readUsage: (signal: AbortSignal) => Promise<Record<string, Usage>>, metricsInterval: number) {
  const [snapshot, setSnapshot] = useState<Snapshot<Reporting>>({ key: null, data: null, reading: false, failure: null, updatedAt: null });
  const readers = useRef({ metrics: readMetrics, usage: readUsage });
  readers.current = { metrics: readMetrics, usage: readUsage };
  const retry = useRef<() => void>(() => {});
  useEffect(() => {
    if (key === null) { setSnapshot({ key, data: null, reading: false, failure: null, updatedAt: null }); return; }
    let active = true, cohort = 0;
    const pending: Partial<Reporting> = {};
    const flights: Partial<Record<keyof Reporting, AbortController>> = {};
    const fail = (failure: unknown) => {
      cohort += 1;
      flights.metrics?.abort(); flights.usage?.abort();
      delete flights.metrics; delete flights.usage; delete pending.metrics; delete pending.usage;
      setSnapshot(previous => ({ key, data: transientReadFailure(failure) && previous.key === key ? previous.data : null,
        failure, reading: false, updatedAt: previous.key === key ? previous.updatedAt : null }));
    };
    const publish = () => {
      if (!pending.metrics || !pending.usage || flights.metrics || flights.usage) return;
      if (scopes(Object.values(pending.metrics)) !== scopes(Object.values(pending.usage))) { fail(new ApiError("unexpected_response")); return; }
      const data = { metrics: pending.metrics, usage: pending.usage };
      delete pending.metrics; delete pending.usage;
      setSnapshot(previous => ({ key, data: previous.key === key && JSON.stringify(previous.data) === JSON.stringify(data) ? previous.data : data,
        reading: false, failure: null, updatedAt: new Date().toISOString() }));
    };
    const load = async (source: keyof Reporting) => {
      if (flights[source]) return;
      const generation = cohort;
      const controller = new AbortController(); flights[source] = controller;
      const deadline = window.setTimeout(() => controller.abort(), 30000);
      setSnapshot(previous => previous.key === key ? { ...previous, reading: true } :
        { key, data: null, reading: true, failure: null, updatedAt: null });
      try {
        const value = await readUntilAbort<Reporting[keyof Reporting]>(readers.current[source](controller.signal), controller.signal);
        if (!active || generation !== cohort) return;
        if (source === "metrics") pending.metrics = value as Reporting["metrics"];
        else pending.usage = value as Reporting["usage"];
        delete flights[source];
        publish();
        if (!flights.metrics && !flights.usage) setSnapshot(previous => ({ ...previous, reading: false }));
      } catch (cause) {
        const failure = controller.signal.aborted ? new ApiError("network_error") : cause;
        if (active && generation === cohort) fail(failure);
      }
      finally { window.clearTimeout(deadline); }
    };
    const refresh = () => { void load("metrics"); void load("usage"); };
    retry.current = refresh;
    refresh();
    const stopMetrics = startVisiblePolling(() => void load("metrics"), metricsInterval);
    const stopUsage = startVisiblePolling(() => void load("usage"), 30000);
    return () => { active = false; cohort += 1; stopMetrics(); stopUsage(); flights.metrics?.abort(); flights.usage?.abort(); retry.current = () => {}; };
  }, [key, metricsInterval]);
  const visible = snapshot.key === key ? snapshot : { key, data: null, reading: key !== null, failure: null, updatedAt: null };
  return { ...visible, refresh: () => retry.current() };
}

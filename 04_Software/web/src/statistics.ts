/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { aggregateMetrics, aggregateUsage, type Amounts, type JobConsumption, type Metrics, type Usage } from "./metrics.ts";
import { createReadController, type ReadEnv, type ReadSnapshot } from "./polling.ts";

export type ReportingSelection = { from: string; through: string; timezone: string; granularity: string };
type ObjectValue = Record<string, unknown>;
const invalid = () => { throw new RangeError("Invalid statistics response"); };
const object = (value: unknown): ObjectValue => value !== null && typeof value === "object" && !Array.isArray(value) ? value as ObjectValue : invalid();
const count = (value: unknown) => Number.isSafeInteger(value) && Number(value) >= 0 ? Number(value) : invalid();
const amount = (value: unknown) => value === null || typeof value === "number" && Number.isFinite(value) && value >= 0 ? value as number | null : invalid();
const tokens = (value: unknown) => value === null ? null : count(value);
const instant = (value: unknown) => value === null || typeof value === "string" && /T.*(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value)) ? value as string | null : invalid();

/** Preserve server boundaries; validate metadata against the captured request without estimating dates. */
function scope(value: unknown, project: string, selection: ReportingSelection) {
  const row = object(value);
  if (!Array.isArray(row.project_ids) || row.project_ids.length !== 1 || row.project_ids[0] !== project ||
    row.timezone !== selection.timezone || row.granularity !== selection.granularity || row.interval !== "[from,to)" ||
    row.mode !== (selection.from || selection.through ? "interval" : "all_time")) invalid();
  const from = instant(row.from), to = instant(row.to);
  if (Boolean(from) !== Boolean(selection.from) || Boolean(to) !== Boolean(selection.through) ||
    from && to && Date.parse(to) <= Date.parse(from)) invalid();
  if (from && to) { if (count(row.interval_seconds) !== (Date.parse(to) - Date.parse(from)) / 1000) invalid(); }
  else if (row.interval_seconds !== null) invalid();
}

/** Fail closed if a Dev response unexpectedly contains financial projections at any depth. */
function financial(value: unknown, admin: boolean) {
  if (admin || value === null || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    if (/cost|priced|price|usd/i.test(key)) invalid();
    financial(child, false);
  }
}
/** Validate derived totals before render, including pooled safe-integer directions. */
function tokenPair(value: unknown) {
  const row = object(value);
  totalTokens({ tokens_in: tokens(row.tokens_in), tokens_out: tokens(row.tokens_out) });
}
function metricTokens(value: Metrics) {
  for (const row of [value.period, value.totals, ...value.daily]) tokenPair(row);
}
function amounts(value: unknown) {
  const row = object(value);
  count(row.events); tokenPair(row);
  for (const key of ["cache_read_tokens", "cache_write_tokens"]) tokens(row[key]);
  for (const key of ["reported_cost_usd", "estimated_cost_usd"]) if (key in row) amount(row[key]);
}
function jobs(value: unknown, project: string) {
  if (!Array.isArray(value)) invalid();
  const seen = new Set<string>();
  for (const item of value as unknown[]) {
    const row = object(item);
    if (row.project_id !== project || typeof row.run_id !== "string" || !/^[A-Za-z0-9._-]{1,160}$/.test(row.run_id) ||
      seen.has(row.run_id) || !["journal", "summary", "unavailable"].includes(String(row.source))) invalid();
    seen.add(String(row.run_id));
    for (const key of ["lifetime", "in_period", "unallocated"]) amounts(row[key]);
    const coverage = object(row.coverage);
    for (const [key, source] of [["lifetime_usage_events", "lifetime"], ["period_usage_events", "in_period"]]) {
      if (count(coverage[key]) !== object(row[source]).events) invalid();
    }
  }
}

/** Validate the explicit analytical contract before making it visible. */
export function readStatistics(value: unknown, project: string, selection: ReportingSelection, admin: boolean): Metrics {
  const row = object(value);
  scope(row.scope, project, selection); financial(row, admin); jobs(row.jobs, project);
  const stock = object(row.current_stock);
  if (stock.basis !== "current_state") invalid();
  for (const key of ["active_now", "waiting_now", "review_now", "terminal_now", "jobs_now"]) count(stock[key]);
  const period = object(row.period);
  if (period.from !== object(row.scope).from || period.to !== object(row.scope).to) invalid();
  for (const key of ["started", "completed", "failed"]) count(period[key]);
  tokenPair(period);
  const totals = object(row.totals); tokenPair(totals);
  for (const [key, value] of Object.entries(totals)) key.includes("tokens") ? tokens(value) : key.includes("cost") ? amount(value) : count(value);
  const coverage = object(row.coverage);
  for (const key of ["usage_events_with_tokens", "usage_events_without_tokens", "runs_with_usage"]) count(coverage[key]);
  for (const value of Object.values(coverage)) count(value);
  const quality = object(row.quality);
  for (const key of ["reviewed_jobs", "reworked_jobs", "validated_jobs", "first_pass_validations", "human_merged_jobs", "first_pass_merges", "open_review_jobs", "stage_failures", "operator_retries"]) count(quality[key]);
  for (const [rate, numerator, denominator] of [["review_rework_rate", "reworked_jobs", "reviewed_jobs"], ["first_validation_rate", "first_pass_validations", "validated_jobs"], ["first_pass_merge_rate", "first_pass_merges", "human_merged_jobs"]]) {
    const expected = quality[denominator] ? Number(quality[numerator]) / Number(quality[denominator]) : null;
    if (quality[rate] !== expected || expected !== null && expected > 1) invalid();
  }
  if (!Array.isArray(row.daily)) invalid();
  const dates = new Set<string>();
  for (const item of row.daily as unknown[]) {
    const day = object(item);
    if (typeof day.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(day.date) || dates.has(day.date)) invalid();
    dates.add(String(day.date));
    for (const key of ["started", "completed", "failed", "mr_revisions", "pipeline_repairs"]) count(day[key]);
    tokenPair(day);
    for (const [key, value] of Object.entries(day)) if (key !== "date") key.includes("tokens") ? tokens(value) : key.includes("cost") ? amount(value) : count(value);
  }
  const result = row as unknown as Metrics;
  const pooled = aggregateMetrics([result], selection.timezone, selection.from, selection.through);
  for (const source of [object(row.duration), object(period.duration)]) {
    for (const key of ["avg_span_seconds", "median_span_seconds", "sampled_runs", "sum_span_seconds"] as const) if (source[key] !== pooled.duration[key]) invalid();
  }
  return result;
}

/** Project usage has the same canonical scope and composite identity contract. */
export function readConsumption(value: unknown, project: string, selection: ReportingSelection, admin: boolean): Usage {
  const row = object(value);
  scope(row.scope, project, selection); financial(row, admin); jobs(row.jobs, project);
  for (const key of ["totals", "lifetime", "unallocated"]) amounts(row[key]);
  for (const value of Object.values(object(row.coverage))) count(value);
  if (!Array.isArray(row.daily)) invalid();
  const buckets = new Set<string>();
  for (const item of row.daily as unknown[]) {
    const day = object(item); amounts(day);
    if (typeof day.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(day.date) ||
      day.executor !== null && typeof day.executor !== "string" || day.model !== null && typeof day.model !== "string") invalid();
    // One source bucket per tuple; null and empty names remain distinct identities.
    const identity = JSON.stringify([day.date, day.executor, day.model]);
    if (buckets.has(identity)) invalid();
    buckets.add(identity);
  }
  const result = row as unknown as Usage;
  const pooled = aggregateUsage([result]);
  amounts(pooled.totals); pooled.daily.forEach(amounts);
  return result;
}

export type ReportingMask = { metrics?: boolean; usage?: boolean };
export type ReportingReport = {
  metrics: Record<string, Metrics>;
  usage: Record<string, Usage>;
  pooledMetrics: Metrics;
  pooledUsage: Usage;
  metricsAt: number;
  usageAt: number;
  fullReportAt: number;
};
export type ReportingRefresh = {
  /** Cancel pre-result work while retaining display, then read every member anew. */
  revalidate(): Promise<void>;
  refresh(mask?: ReportingMask): Promise<void>;
  invalidate(): void;
  dispose(): void;
};

/**
 * Coordinate validated immutable-ID maps under one context, deadline and commit.
 * Transports return maps for exactly projectIds; each member still passes the
 * complete role/selection validator. A not-due member can only pin the committed
 * baseline, retaining its own time. Due/full triggers promote pins in an active
 * proposal without rereading already requested members or extending its deadline.
 * Failed proposals discard all staged values and require their requested inputs
 * on recovery. Callers own scheduling, synchronous context gates and CSV bindings.
 */
export function createReportingRefresh(options: {
  key: string;
  projectIds: readonly string[];
  selection: ReportingSelection;
  admin: boolean;
  readMetrics(signal: AbortSignal): Promise<unknown>;
  readUsage(signal: AbortSignal): Promise<unknown>;
  publish(snapshot: ReadSnapshot<ReportingReport>): void;
  env?: ReadEnv;
}): ReportingRefresh {
  const ids = [...options.projectIds].sort();
  if (new Set(ids).size !== ids.length || ids.some(id => typeof id !== "string" || !id)) invalid();
  const selection = { ...options.selection };
  const now = options.env?.now ?? (() => Date.now());
  type Mask = { metrics: boolean; usage: boolean };
  type Proposal = {
    requested: Mask;
    started: Mask;
    done: Mask;
    metrics: Record<string, Metrics> | null;
    usage: Record<string, Usage> | null;
    metricsAt: number;
    usageAt: number;
    fullReportAt: number;
    start?: () => void;
  };
  let committed: ReportingReport | null = null;
  let proposal: Proposal | null = null;
  let recovery: Mask = { metrics: false, usage: false };
  let disposed = false;
  const metricMap = (value: unknown) => {
    const map = object(value);
    if (JSON.stringify(Object.keys(map).sort()) !== JSON.stringify(ids)) invalid();
    return Object.fromEntries(ids.map(id => [id, readStatistics(map[id], id, selection, options.admin)]));
  };
  const usageMap = (value: unknown) => {
    const map = object(value);
    if (JSON.stringify(Object.keys(map).sort()) !== JSON.stringify(ids)) invalid();
    return Object.fromEntries(ids.map(id => [id, readConsumption(map[id], id, selection, options.admin)]));
  };
  // Identity is validated by each map member; every project shares these
  // canonical reporting boundaries, not merely its own metrics/usage pair.
  const canonical = (value: Metrics | Usage) => {
    const row = value.scope;
    return JSON.stringify([row?.mode, row?.interval, row?.from, row?.to,
      row?.timezone, row?.granularity, row?.interval_seconds]);
  };
  const owner = createReadController<ReportingReport>({
    key: options.key, deadlineMs: 30000, policy: "informational", env: options.env,
    read: signal => new Promise<ReportingReport>((resolve, reject) => {
      const current = proposal!;
      let settled = false;
      const live = () => !settled && proposal === current && !signal.aborted;
      const fail = (error: unknown) => {
        if (settled) return;
        settled = true; signal.removeEventListener("abort", aborted); reject(error);
      };
      const aborted = () => fail(signal.reason);
      signal.addEventListener("abort", aborted, { once: true });
      const check = () => {
        if (!live() || current.requested.metrics && !current.done.metrics || current.requested.usage && !current.done.usage) return;
        if (!current.metrics || !current.usage) return;
        try {
          const scopes = ids.flatMap(id => [canonical(current.metrics![id]), canonical(current.usage![id])]);
          if (scopes.some(value => value !== scopes[0])) throw new RangeError("Mismatched reporting scopes");
          // Pool inside the owned validation boundary: even individually valid
          // finite amounts can overflow together. Rendering must not discover
          // an aggregate error after ready data/success time has been published.
          const pooledMetrics = aggregateMetrics(Object.values(current.metrics), selection.timezone, selection.from, selection.through);
          const pooledUsage = aggregateUsage(Object.values(current.usage));
          metricTokens(pooledMetrics);
          amounts(pooledUsage.totals); pooledUsage.daily.forEach(amounts);
          settled = true; signal.removeEventListener("abort", aborted);
          resolve({ metrics: current.metrics, usage: current.usage, pooledMetrics, pooledUsage, metricsAt: current.metricsAt,
            usageAt: current.usageAt, fullReportAt: current.requested.metrics && current.requested.usage ? now() : current.fullReportAt });
        } catch (error) { fail(error); }
      };
      current.start = () => {
        if (!live()) return;
        for (const member of ["metrics", "usage"] as const) {
          if (!current.requested[member] || current.started[member]) continue;
          current.started[member] = true;
          // Promise wrapping also handles a synchronous transport/validator error.
          void Promise.resolve().then(() => {
            if (!live()) return;
            return member === "metrics" ? options.readMetrics(signal) : options.readUsage(signal);
          }).then(value => {
            if (!live()) return;
            if (member === "metrics") { current.metrics = metricMap(value); current.metricsAt = now(); }
            else { current.usage = usageMap(value); current.usageAt = now(); }
            current.done[member] = true;
            check();
          }).catch(error => { if (live()) fail(error); });
        }
        check();
      };
      current.start();
    }),
    publish: snapshot => {
      if (!snapshot.refreshing) {
        if (snapshot.status === "ready") {
          committed = snapshot.data; recovery = { metrics: false, usage: false };
        } else if (snapshot.status === "error" || snapshot.status === "stale") {
          if (proposal) recovery = { ...proposal.requested };
          committed = snapshot.data;
        }
        proposal = null;
      }
      options.publish(snapshot);
    },
  });
  return {
    refresh(mask = { metrics: true, usage: true }) {
      if (disposed) return Promise.resolve();
      const requested = { metrics: !committed || recovery.metrics || mask.metrics === true,
        usage: !committed || recovery.usage || mask.usage === true };
      if (!requested.metrics && !requested.usage && !proposal) return Promise.resolve();
      if (proposal) {
        proposal.requested.metrics ||= requested.metrics;
        proposal.requested.usage ||= requested.usage;
        proposal.start?.();
      } else {
        proposal = { requested, started: { metrics: false, usage: false }, done: { metrics: false, usage: false },
          metrics: committed?.metrics ?? null, usage: committed?.usage ?? null, metricsAt: committed?.metricsAt ?? 0,
          usageAt: committed?.usageAt ?? 0, fullReportAt: committed?.fullReportAt ?? 0 };
      }
      return owner.refresh();
    },
    revalidate() {
      if (disposed) return Promise.resolve();
      proposal = null;
      owner.cancel();
      // Both members must come from work begun after the observed result.
      return this.refresh();
    },
    invalidate() {
      committed = null; proposal = null; recovery = { metrics: false, usage: false }; owner.invalidate();
    },
    dispose() { disposed = true; committed = null; proposal = null; owner.dispose(); },
  };
}

/** A complete total needs both directions; known subtotals are presented separately. */
export function totalTokens(value: Pick<Amounts, "tokens_in" | "tokens_out">): number | null {
  if (value.tokens_in === null || value.tokens_out === null) return null;
  const total = value.tokens_in + value.tokens_out;
  return Number.isSafeInteger(total) && total >= 0 ? total : invalid();
}
/** Composite identity preserves equal run IDs in independently owned projects. */
export function consumptionIdentity(job: Pick<JobConsumption, "project_id" | "run_id">) {
  return JSON.stringify([job.project_id, job.run_id]);
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
/** Sum available evidence; absent observations remain unavailable, including empty cohorts. */
function sum(values: Array<number | null | undefined>): number | null {
  const known = values.filter((value): value is number => value != null);
  if (known.some(value => !Number.isFinite(value) || value < 0)) throw new RangeError("Invalid metrics evidence");
  const total = known.length ? known.reduce((total, value) => total + value, 0) : null;
  if (total != null && !Number.isFinite(total)) throw new RangeError("Invalid metrics total");
  return total;
}

function duration(evidence: Duration[]): Duration {
  const spans = evidence.flatMap(row => {
    if (!Array.isArray(row.samples_seconds) || row.samples_seconds.some(value =>
      !Number.isSafeInteger(value) || value < 0) || row.sampled_runs !== row.samples_seconds.length ||
      !Number.isSafeInteger(row.sum_span_seconds) || row.sum_span_seconds < 0 ||
      row.sum_span_seconds !== row.samples_seconds.reduce((total, value) => total + value, 0)) {
      throw new RangeError("Invalid server duration evidence");
    }
    return row.samples_seconds;
  }).sort((a, b) => a - b);
  const count = spans.length;
  const total = spans.reduce((value, span) => value + span, 0);
  // Exact source spans can still overflow when pooled. Refuse before computing
  // means/medians or publishing a rounded duration as fresh evidence.
  if (!Number.isSafeInteger(total)) throw new RangeError("Invalid pooled duration evidence");
  return { sampled_runs: count, sum_span_seconds: total, samples_seconds: spans,
    avg_span_seconds: count ? Math.round(total / count) : null,
    median_span_seconds: count ? (spans[Math.floor((count - 1) / 2)] + spans[Math.floor(count / 2)]) / 2 : null };
}

/** Pool validated project responses, preserving cohort denominators and missing monetary evidence. */
export function aggregateMetrics(items: Metrics[], timezone: string, from: string, through: string): Metrics {
  // Validate the requested zone even for an empty authorized result.
  new Intl.DateTimeFormat("en-CA", { timeZone: timezone });
  const scopes = items.flatMap(item => item.scope ? [item.scope] : []);
  if (scopes.some(scope => scope.timezone !== timezone || scope.from !== scopes[0].from ||
    scope.to !== scopes[0].to || scope.granularity !== scopes[0].granularity)) {
    throw new RangeError("Inconsistent server metric scope");
  }
  const count = (key: string) => items.reduce((total, item) => total + Number(item.quality[key as keyof Quality] || 0), 0);
  const quality = {} as Quality;
  for (const key of ["reviewed_jobs", "reworked_jobs", "open_review_jobs", "validated_jobs", "first_pass_validations",
    "human_merged_jobs", "first_pass_merges", "stage_failures", "operator_retries"] as const) quality[key] = count(key);
  quality.review_rework_rate = quality.reviewed_jobs ? quality.reworked_jobs / quality.reviewed_jobs : null;
  quality.first_validation_rate = quality.validated_jobs ? quality.first_pass_validations / quality.validated_jobs : null;
  quality.first_pass_merge_rate = quality.human_merged_jobs ? quality.first_pass_merges / quality.human_merged_jobs : null;
  quality.cost_efficiency = {};
  for (const key of ["reported_per_completed", "estimated_per_completed", "reported_per_human_merged", "estimated_per_human_merged"]) {
    const evidence = items.flatMap(item => item.quality.cost_efficiency?.[key] ? [item.quality.cost_efficiency[key]] : []);
    const jobs = evidence.reduce((total, item) => total + item.jobs_with_evidence, 0);
    // Unknown money in a contributing cohort cannot be presented as measured zero.
    const known = evidence.every(item => item.jobs_with_evidence === 0 || item.usd_per_job !== null);
    quality.cost_efficiency[key] = { jobs_with_evidence: jobs,
      usd_per_job: jobs && known ? evidence.reduce((total, item) => total + (item.usd_per_job ?? 0) * item.jobs_with_evidence, 0) / jobs : null };
  }
  const totals: Metrics["totals"] = {};
  for (const key of new Set(["runs", "tokens_in", "tokens_out", "mr_revisions", "pipeline_repairs", "cost_usd", "estimated_cost_usd",
    ...items.flatMap(item => Object.keys(item.totals))])) {
    totals[key] = sum(items.map(item => item.totals[key])) ?? (key.includes("tokens") || key.endsWith("cost_usd") ? null : 0);
  }
  const coverage = {} as Metrics["coverage"];
  for (const key of ["summary_only_runs", "runs_without_usage", "usage_events_with_tokens", "usage_events_without_tokens", "lifecycle_started_unallocated", "lifecycle_completed_unallocated", "runs_with_usage", "revision_events_unclassified", "launches_with_reported_tokens",
    "launches_with_unavailable_tokens", "launches_capture_disabled", "launches_with_reported_cost",
    "launches_with_unavailable_cost", "runs_with_reported_cost", "runs_with_estimated_cost", "usage_events_unpriced"] as const) {
    coverage[key] = sum(items.map(item => item.coverage[key])) || 0;
  }
  const days = new Map<string, Metrics["daily"][number]>();
  for (const item of items) for (const day of item.daily) {
    const row = days.get(day.date) || { date: day.date, started: 0, completed: 0, tokens_in: null, tokens_out: null,
      mr_revisions: 0, pipeline_repairs: 0, cost_usd: null, estimated_cost_usd: null };
    for (const key of ["started", "completed", "mr_revisions", "pipeline_repairs"] as const) row[key] += day[key];
    for (const key of ["tokens_in", "tokens_out"] as const) row[key] = sum([row[key], day[key]]);
    row.cost_usd = sum([row.cost_usd, day.cost_usd]);
    row.estimated_cost_usd = sum([row.estimated_cost_usd, day.estimated_cost_usd]);
    days.set(day.date, row);
  }
  const runs = items.flatMap(item => item.runs);
  for (const key of ["failed", "merged"] as const) {
    for (const row of days.values()) row[key] = items.reduce((total, item) => total + (item.daily.find(day => day.date === row.date)?.[key] || 0), 0);
  }
  const period: Metrics["period"] = { from: scopes[0]?.from ?? (from || null), to: scopes[0]?.to ?? (through || null), basis: "dated_events", duration: duration(items.map(item => item.duration)),
    started: 0, completed: 0, tokens_in: 0, tokens_out: 0, mr_revisions: 0, pipeline_repairs: 0,
    cost_usd: sum(items.map(item => item.period.cost_usd)), estimated_cost_usd: sum(items.map(item => item.period.estimated_cost_usd)) };
  for (const key of ["started", "completed", "tokens_in", "tokens_out", "mr_revisions", "pipeline_repairs"] as const) {
    if (key === "tokens_in" || key === "tokens_out") period[key] = sum(items.map(item => item.period[key]));
    else period[key] = items.reduce((total, item) => total + Number(item.period[key]), 0);
  }
  for (const key of ["failed", "merged"] as const) period[key] = items.reduce((total, item) => total + (item.period[key] || 0), 0);
  const financial = items.some(item => "cost_usd" in item.totals);
  if (!financial) {
    delete totals.cost_usd; delete totals.estimated_cost_usd; delete quality.cost_efficiency;
    delete period.cost_usd; delete period.estimated_cost_usd;
    for (const row of days.values()) { delete row.cost_usd; delete row.estimated_cost_usd; }
    for (const key of Object.keys(coverage)) if (key.includes("cost") || key.includes("priced")) delete coverage[key as keyof typeof coverage];
  }
  const current_stock = { active_now: 0, waiting_now: 0, review_now: 0, terminal_now: 0, jobs_now: 0, basis: "current_state" };
  for (const item of items) for (const key of ["active_now", "waiting_now", "review_now", "terminal_now", "jobs_now"] as const) current_stock[key] += item.current_stock?.[key] ?? 0;
  return { totals, quality, duration: duration(items.map(item => item.duration)), runs,
    jobs: items.flatMap(item => item.jobs ?? []), current_stock,
    daily: [...days.values()].sort((a, b) => a.date.localeCompare(b.date)), period, coverage, ...(scopes.length ? { scope: { ...scopes[0], project_ids: scopes.flatMap(scope => scope.project_ids) } } : {}) };
}

/** Pool filtered usage with date/executor/model bucket identity kept intact. */
export function aggregateUsage(items: Usage[]): Usage {
  const totals: Usage["totals"] = { events: 0, tokens_in: 0, tokens_out: 0, cache_read_tokens: null,
    cache_write_tokens: null, reported_cost_usd: null, estimated_cost_usd: null };
  totals.events = items.reduce((total, item) => total + item.totals.events, 0);
  for (const key of ["tokens_in", "tokens_out"] as const) totals[key] = sum(items.map(item => item.totals[key]));
  for (const key of ["cache_read_tokens", "cache_write_tokens", "reported_cost_usd", "estimated_cost_usd"] as const) totals[key] = sum(items.map(item => item.totals[key]));
  const buckets = new Map<string, Usage["daily"][number]>();
  for (const item of items) for (const day of item.daily) {
    const key = JSON.stringify([day.date, day.executor, day.model]);
    const row = buckets.get(key);
    if (!row) { buckets.set(key, { ...day }); continue; }
    row.events += day.events;
    for (const field of ["tokens_in", "tokens_out"] as const) row[field] = sum([row[field], day[field]]);
    for (const field of ["cache_read_tokens", "cache_write_tokens", "reported_cost_usd", "estimated_cost_usd"] as const) row[field] = sum([row[field], day[field]]);
  }
  // A missing contributing count is unknown, not a measured zero. Keep the
  // pooled optional field absent unless every member supplies known evidence.
  if (items.length && items.every(item => item.totals.unpriced_events !== undefined)) {
    totals.unpriced_events = items.reduce((total, item) => total + item.totals.unpriced_events!, 0);
  }
  if (!items.some(item => "reported_cost_usd" in item.totals)) {
    delete totals.reported_cost_usd; delete totals.estimated_cost_usd; delete totals.unpriced_events;
    for (const row of buckets.values()) { delete row.reported_cost_usd; delete row.estimated_cost_usd; }
  }
  return { totals, daily: [...buckets.values()].sort((a, b) => a.date.localeCompare(b.date) ||
    (a.executor || "").localeCompare(b.executor || "") || (a.model || "").localeCompare(b.model || "")) };
}
export type Duration = { sampled_runs: number; avg_span_seconds: number | null; median_span_seconds: number | null; sum_span_seconds: number; samples_seconds: number[]; basis?: string };
export type MetricScope = { project_ids: string[]; mode: "all_time" | "interval"; interval: "[from,to)"; from: string | null; to: string | null; timezone: string; granularity: string; interval_seconds: number | null };
export type CostEvidence = { jobs_with_evidence: number; usd_per_job: number | null };
export type Quality = { reviewed_jobs: number; reworked_jobs: number; review_rework_rate: number | null; open_review_jobs: number; validated_jobs: number; first_pass_validations: number; first_validation_rate: number | null; human_merged_jobs: number; first_pass_merges: number; first_pass_merge_rate: number | null; stage_failures: number; operator_retries: number; cost_efficiency?: Record<string, CostEvidence> };
export type Metrics = { jobs?: JobConsumption[]; current_stock?: CurrentStock; scope?: MetricScope; totals: Record<string, number | null>; duration: Duration; quality: Quality; runs: Array<Record<string, string | number | null>>; daily: Array<{ date: string; started: number; completed: number; failed?: number; merged?: number; tokens_in: number | null; tokens_out: number | null; mr_revisions: number; pipeline_repairs: number; cost_usd?: number | null; estimated_cost_usd?: number | null }>; period: { from: string | null; to: string | null; basis: string; started: number; completed: number; failed?: number; merged?: number; tokens_in: number | null; tokens_out: number | null; mr_revisions: number; pipeline_repairs: number; duration: Duration; cost_usd?: number | null; estimated_cost_usd?: number | null }; revisions?: Array<{ run_id: string; revision: number; trigger: string; date: string | null; tokens_in: number | null; tokens_out: number | null; reported_cost_usd: number | null; estimated_cost_usd: number | null }>; coverage: { summary_only_runs?: number; runs_without_usage?: number; usage_events_with_tokens?: number; usage_events_without_tokens?: number; lifecycle_started_unallocated?: number; lifecycle_completed_unallocated?: number; runs_with_usage: number; revision_events_unclassified: number; launches_with_reported_tokens: number; launches_with_unavailable_tokens: number; launches_capture_disabled: number; launches_with_reported_cost?: number; launches_with_unavailable_cost?: number; runs_with_reported_cost?: number; runs_with_estimated_cost?: number; usage_events_unpriced?: number } };
export type Usage = { jobs?: JobConsumption[]; lifetime?: Amounts; unallocated?: Amounts; coverage?: Record<string, number>; scope?: MetricScope; totals: { events: number; tokens_in: number | null; tokens_out: number | null; cache_read_tokens: number | null; cache_write_tokens: number | null; reported_cost_usd?: number | null; estimated_cost_usd?: number | null; unpriced_events?: number }; daily: Array<{ date: string; executor: string | null; model: string | null; events: number; tokens_in: number | null; tokens_out: number | null; cache_read_tokens: number | null; cache_write_tokens: number | null; reported_cost_usd?: number | null; estimated_cost_usd?: number | null }> };

export type Amounts = { events: number; tokens_in: number | null; tokens_out: number | null; cache_read_tokens: number | null; cache_write_tokens: number | null; reported_cost_usd?: number | null; estimated_cost_usd?: number | null };
export type JobConsumption = { project_id: string; run_id: string; lifetime: Amounts; in_period: Amounts; unallocated: Amounts; source: "journal" | "summary" | "unavailable"; coverage: { lifetime_usage_events: number; period_usage_events: number } };
export type CurrentStock = { active_now: number; waiting_now: number; review_now: number; terminal_now: number; jobs_now: number; basis: string };

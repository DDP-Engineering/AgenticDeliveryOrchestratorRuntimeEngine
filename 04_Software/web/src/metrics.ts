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
  return known.length ? known.reduce((total, value) => total + value, 0) : null;
}

function duration(rows: Metrics["runs"]): Duration {
  const spans = rows.flatMap(row => {
    if (!row.started_at && !row.ended_at && row.span_seconds === 0) return [];
    const elapsed = Date.parse(String(row.ended_at)) - Date.parse(String(row.started_at));
    if (!row.started_at || !row.ended_at || !Number.isSafeInteger(row.span_seconds) || Number(row.span_seconds) < 0 ||
      !Number.isFinite(elapsed) || Math.floor(elapsed / 1000) !== row.span_seconds) throw new RangeError("Invalid duration evidence");
    return [Number(row.span_seconds)];
  }).sort((a, b) => a - b);
  const count = spans.length;
  return { sampled_runs: count,
    avg_span_seconds: count ? Math.round(spans.reduce((total, value) => total + value, 0) / count) : null,
    median_span_seconds: count ? (spans[Math.floor((count - 1) / 2)] + spans[Math.floor(count / 2)]) / 2 : null };
}

/** Pool validated project responses, preserving cohort denominators and missing monetary evidence. */
export function aggregateMetrics(items: Metrics[], timezone: string, from: string, through: string): Metrics {
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
    quality.cost_efficiency[key] = { jobs_with_evidence: jobs,
      usd_per_job: jobs ? evidence.reduce((total, item) => total + (item.usd_per_job || 0) * item.jobs_with_evidence, 0) / jobs : null };
  }
  const totals: Metrics["totals"] = {};
  for (const key of new Set(["runs", "tokens_in", "tokens_out", "mr_revisions", "pipeline_repairs", "cost_usd", "estimated_cost_usd",
    ...items.flatMap(item => Object.keys(item.totals))])) {
    totals[key] = sum(items.map(item => item.totals[key])) ?? (key.endsWith("cost_usd") ? null : 0);
  }
  const coverage = {} as Metrics["coverage"];
  for (const key of ["runs_with_usage", "revision_events_unclassified", "launches_with_reported_tokens",
    "launches_with_unavailable_tokens", "launches_capture_disabled", "launches_with_reported_cost",
    "launches_with_unavailable_cost", "runs_with_reported_cost", "runs_with_estimated_cost", "usage_events_unpriced"] as const) {
    coverage[key] = sum(items.map(item => item.coverage[key])) || 0;
  }
  const days = new Map<string, Metrics["daily"][number]>();
  for (const item of items) for (const day of item.daily) {
    const row = days.get(day.date) || { date: day.date, started: 0, completed: 0, tokens_in: 0, tokens_out: 0,
      mr_revisions: 0, pipeline_repairs: 0, cost_usd: null, estimated_cost_usd: null };
    for (const key of ["started", "completed", "tokens_in", "tokens_out", "mr_revisions", "pipeline_repairs"] as const) row[key] += day[key];
    row.cost_usd = sum([row.cost_usd, day.cost_usd]);
    row.estimated_cost_usd = sum([row.estimated_cost_usd, day.estimated_cost_usd]);
    days.set(day.date, row);
  }
  const runs = items.flatMap(item => item.runs);
  const dateFormat = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" });
  const periodRuns = runs.filter(row => {
    if (!row.ended_at) return false;
    const parts = dateFormat.formatToParts(new Date(String(row.ended_at)));
    const day = ["year", "month", "day"].map(type => parts.find(part => part.type === type)?.value).join("-");
    return (!from || day >= from) && (!through || day <= through);
  });
  const period = { from: from || null, to: through || null, basis: "dated_events", duration: duration(periodRuns),
    started: 0, completed: 0, tokens_in: 0, tokens_out: 0, mr_revisions: 0, pipeline_repairs: 0,
    cost_usd: sum(items.map(item => item.period.cost_usd)), estimated_cost_usd: sum(items.map(item => item.period.estimated_cost_usd)) };
  for (const key of ["started", "completed", "tokens_in", "tokens_out", "mr_revisions", "pipeline_repairs"] as const) {
    period[key] = items.reduce((total, item) => total + item.period[key], 0);
  }
  return { totals, quality, duration: duration(runs), runs,
    daily: [...days.values()].sort((a, b) => a.date.localeCompare(b.date)), period, coverage };
}

/** Pool filtered usage with date/executor/model bucket identity kept intact. */
export function aggregateUsage(items: Usage[]): Usage {
  const totals: Usage["totals"] = { events: 0, tokens_in: 0, tokens_out: 0, cache_read_tokens: null,
    cache_write_tokens: null, reported_cost_usd: null, estimated_cost_usd: null };
  for (const key of ["events", "tokens_in", "tokens_out"] as const) totals[key] = items.reduce((total, item) => total + item.totals[key], 0);
  for (const key of ["cache_read_tokens", "cache_write_tokens", "reported_cost_usd", "estimated_cost_usd"] as const) totals[key] = sum(items.map(item => item.totals[key]));
  const buckets = new Map<string, Usage["daily"][number]>();
  for (const item of items) for (const day of item.daily) {
    const key = JSON.stringify([day.date, day.executor, day.model]);
    const row = buckets.get(key);
    if (!row) { buckets.set(key, { ...day }); continue; }
    for (const field of ["events", "tokens_in", "tokens_out"] as const) row[field] += day[field];
    for (const field of ["cache_read_tokens", "cache_write_tokens", "reported_cost_usd", "estimated_cost_usd"] as const) row[field] = sum([row[field], day[field]]);
  }
  return { totals, daily: [...buckets.values()].sort((a, b) => a.date.localeCompare(b.date) ||
    (a.executor || "").localeCompare(b.executor || "") || (a.model || "").localeCompare(b.model || "")) };
}
export type Duration = { sampled_runs: number; avg_span_seconds: number | null; median_span_seconds: number | null };
export type CostEvidence = { jobs_with_evidence: number; usd_per_job: number | null };
export type Quality = { reviewed_jobs: number; reworked_jobs: number; review_rework_rate: number | null; open_review_jobs: number; validated_jobs: number; first_pass_validations: number; first_validation_rate: number | null; human_merged_jobs: number; first_pass_merges: number; first_pass_merge_rate: number | null; stage_failures: number; operator_retries: number; cost_efficiency?: Record<string, CostEvidence> };
export type Metrics = { totals: Record<string, number | null>; duration: Duration; quality: Quality; runs: Array<Record<string, string | number | null>>; daily: Array<{ date: string; started: number; completed: number; tokens_in: number; tokens_out: number; mr_revisions: number; pipeline_repairs: number; cost_usd?: number | null; estimated_cost_usd?: number | null }>; period: { from: string | null; to: string | null; basis: string; started: number; completed: number; tokens_in: number; tokens_out: number; mr_revisions: number; pipeline_repairs: number; duration: Duration; cost_usd?: number | null; estimated_cost_usd?: number | null }; revisions?: Array<{ run_id: string; revision: number; trigger: string; date: string | null; tokens_in: number; tokens_out: number; reported_cost_usd: number | null; estimated_cost_usd: number | null }>; coverage: { runs_with_usage: number; revision_events_unclassified: number; launches_with_reported_tokens: number; launches_with_unavailable_tokens: number; launches_capture_disabled: number; launches_with_reported_cost?: number; launches_with_unavailable_cost?: number; runs_with_reported_cost?: number; runs_with_estimated_cost?: number; usage_events_unpriced?: number } };
export type Usage = { totals: { events: number; tokens_in: number; tokens_out: number; cache_read_tokens: number | null; cache_write_tokens: number | null; reported_cost_usd?: number | null; estimated_cost_usd?: number | null; unpriced_events?: number }; daily: Array<{ date: string; executor: string | null; model: string | null; events: number; tokens_in: number; tokens_out: number; cache_read_tokens: number | null; cache_write_tokens: number | null; reported_cost_usd?: number | null; estimated_cost_usd?: number | null }> };

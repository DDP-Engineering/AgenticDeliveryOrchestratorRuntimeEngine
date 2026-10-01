/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { aggregateMetrics, aggregateUsage } from "../src/metrics.ts";

const project = (runs, reviewed, reworked, spans = []) => ({
  totals: { runs, tokens_in: runs * 10, cost_usd: null, estimated_cost_usd: null },
  coverage: { runs_with_usage: runs, launches_with_reported_tokens: runs },
  quality: { reviewed_jobs: reviewed, reworked_jobs: reworked, validated_jobs: 0,
    first_pass_validations: 0, human_merged_jobs: 0, first_pass_merges: 0,
    cost_efficiency: { reported_per_completed: { jobs_with_evidence: 0, usd_per_job: null } } },
  duration: {},
  runs: spans.map(span => ({ started_at: "2026-10-01T21:59:00Z",
    ended_at: new Date(Date.parse("2026-10-01T21:59:00Z") + span * 1000).toISOString(), span_seconds: span })),
  daily: [{ date: "2026-10-01", started: runs, completed: runs, tokens_in: runs * 10,
    tokens_out: 0, mr_revisions: reworked, pipeline_repairs: 0, cost_usd: null }],
  period: { from: null, to: null, basis: "dated_events", started: runs, completed: runs,
    tokens_in: runs * 10, tokens_out: 0, mr_revisions: reworked, pipeline_repairs: 0, cost_usd: null },
});

test("platform totals pool cohorts, duration samples and evidence-weighted costs", () => {
  const a = project(1, 1, 1, [0]);
  const b = project(9, 9, 0, [30, 90]);
  a.totals.cost_usd = 0;
  a.quality.cost_efficiency.reported_per_completed = { jobs_with_evidence: 1, usd_per_job: 0 };
  b.quality.cost_efficiency.reported_per_completed = { jobs_with_evidence: 3, usd_per_job: 8 };
  const total = aggregateMetrics([a, b], "UTC", "", "");
  assert.equal(total.totals.runs, 10);
  assert.equal(total.totals.tokens_in, 100);
  assert.equal(total.totals.cost_usd, 0);
  assert.equal(total.totals.estimated_cost_usd, null);
  assert.equal(total.quality.review_rework_rate, 0.1);
  assert.equal(total.quality.first_validation_rate, null);
  assert.deepEqual(total.quality.cost_efficiency.reported_per_completed,
    { jobs_with_evidence: 4, usd_per_job: 6 });
  assert.deepEqual(total.duration, { sampled_runs: 3, avg_span_seconds: 40, median_span_seconds: 30 });
  assert.equal(total.daily.length, 1);
  assert.equal(total.daily[0].started, 10);
  assert.equal(total.daily[0].cost_usd, null);
  assert.equal(total.coverage.runs_with_usage, 10);
});

test("period duration uses completion day in chosen timezone and inclusive bounds", () => {
  const a = project(2, 0, 0, [0, 90]);
  assert.equal(aggregateMetrics([a], "UTC", "2026-10-01", "2026-10-01").period.duration.sampled_runs, 2);
  assert.equal(aggregateMetrics([a], "Europe/Bucharest", "2026-10-01", "2026-10-01").period.duration.sampled_runs, 0);
  assert.equal(aggregateMetrics([a], "Europe/Bucharest", "2026-10-02", "2026-10-02").period.duration.sampled_runs, 2);
});

test("empty cohorts and absent evidence remain unavailable; legacy spans are excluded", () => {
  const a = project(0, 0, 0);
  a.runs.push({ started_at: "", ended_at: "", span_seconds: 0 });
  const total = aggregateMetrics([a], "UTC", "", "");
  assert.equal(total.duration.sampled_runs, 0);
  assert.equal(total.duration.avg_span_seconds, null);
  assert.equal(total.quality.review_rework_rate, null);
  assert.equal(total.totals.cost_usd, null);
  assert.equal(aggregateMetrics([], "UTC", "", "").totals.runs, 0);
});

test("usage retains separate model/executor buckets and nullable financial/cache evidence", () => {
  const usage = model => ({ totals: { events: 1, tokens_in: 4, tokens_out: 2,
    cache_read_tokens: null, cache_write_tokens: null, reported_cost_usd: null, estimated_cost_usd: null },
    daily: [{ date: "2026-10-01", executor: "pi", model, events: 1, tokens_in: 4, tokens_out: 2,
      cache_read_tokens: null, cache_write_tokens: null, reported_cost_usd: null, estimated_cost_usd: null }] });
  const a = usage("m1"), b = usage("m2");
  b.totals.cache_read_tokens = 0;
  const total = aggregateUsage([a, a, b]);
  assert.equal(total.totals.events, 3);
  assert.equal(total.totals.cache_read_tokens, 0);
  assert.equal(total.totals.reported_cost_usd, null);
  assert.equal(total.daily.length, 2);
  assert.equal(total.daily[0].events, 2);
  assert.equal(total.daily[1].model, "m2");
  assert.equal(aggregateUsage([]).totals.events, 0);
});

test("corrupt numeric/duration evidence and invalid timezone fail closed", () => {
  const a = project(1, 0, 0, [30]);
  a.runs[0].span_seconds = -1;
  assert.throws(() => aggregateMetrics([a], "UTC", "", ""), RangeError);
  a.runs[0].span_seconds = 31;
  assert.throws(() => aggregateMetrics([a], "UTC", "", ""), RangeError);
  a.runs[0].span_seconds = 30;
  a.totals.cost_usd = NaN;
  assert.throws(() => aggregateMetrics([a], "UTC", "", ""), RangeError);
  a.totals.cost_usd = null;
  assert.throws(() => aggregateMetrics([a], "invalid-zone", "", ""), RangeError);
});

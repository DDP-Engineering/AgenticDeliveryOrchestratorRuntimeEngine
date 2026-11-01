/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readStatistics, readConsumption, totalTokens, consumptionIdentity } from "../src/statistics.ts";
const selection = { from: "", through: "", timezone: "UTC", granularity: "day" };
const amounts = (input = null, output = null) => ({ events: input === null && output === null ? 0 : 1,
  tokens_in: input, tokens_out: output, cache_read_tokens: null, cache_write_tokens: null });
const job = (id = "alpha") => ({ project_id: id, run_id: "same-run", lifetime: amounts(7, 5), in_period: amounts(0, 0),
  unallocated: amounts(), source: "journal", coverage: { lifetime_usage_events: 1, period_usage_events: 1 } });
const scope = (id = "alpha") => ({ project_ids: [id], mode: "all_time", from: null, to: null, interval: "[from,to)", timezone: "UTC", granularity: "day", interval_seconds: null });
const fixture = () => {
  const duration = { sampled_runs: 2, avg_span_seconds: 60, median_span_seconds: 60, sum_span_seconds: 120, samples_seconds: [0, 120] };
  return { scope: scope(), jobs: [job()], current_stock: { active_now: 1, jobs_now: 1, waiting_now: 0, review_now: 0, terminal_now: 0, basis: "current_state" },
    totals: { runs: 1, started: 1, completed: 1, failed: 1, tokens_in: 0, tokens_out: 0 },
    period: { from: null, to: null, started: 1, completed: 1, failed: 1, tokens_in: 0, tokens_out: 0, mr_revisions: 0, pipeline_repairs: 0, duration }, duration,
    coverage: { usage_events_with_tokens: 1, usage_events_without_tokens: 0, runs_with_usage: 1 },
    quality: { reviewed_jobs: 0, reworked_jobs: 0, validated_jobs: 0, first_pass_validations: 0, human_merged_jobs: 0, first_pass_merges: 0, open_review_jobs: 0, stage_failures: 0, operator_retries: 0,
      review_rework_rate: null, first_validation_rate: null, first_pass_merge_rate: null }, runs: [],
    daily: [{ date: "2026-10-25", started: 1, completed: 1, failed: 1, tokens_in: 0, tokens_out: 0, mr_revisions: 0, pipeline_repairs: 0 }] };
};
test("honest zero, unknown, partial, samples and composite identities retain server meaning", () => {
  const value = readStatistics(fixture(), "alpha", selection, false);
  assert.equal(value.jobs[0].lifetime.tokens_in, 7);
  assert.equal(value.jobs[0].in_period.tokens_in, 0);
  assert.equal(value.duration.avg_span_seconds, 60);
  assert.equal(totalTokens(amounts(0, 0)), 0);
  assert.equal(totalTokens(amounts(7, null)), null);
  assert.equal(totalTokens(amounts()), null);
  assert.notEqual(consumptionIdentity(job("alpha")), consumptionIdentity(job("beta")));
});
test("strict scope, identity and nested financial boundaries fail closed", () => {
  for (const change of [value => { value.scope.timezone = "Europe/Bucharest"; }, value => { value.scope.project_ids = ["beta"]; },
    value => { value.jobs[0].project_id = "beta"; }, value => { value.jobs.push(value.jobs[0]); },
    value => { value.jobs[0].in_period.reported_cost_usd = 0; }, value => { value.scope.from = "not a date"; },
    value => { value.duration.samples_seconds = [0]; }, value => { delete value.jobs; }]) {
    const value = fixture(); change(value); assert.throws(() => readStatistics(value, "alpha", selection, false));
  }
});
test("corrupt values cannot become false zero, fractional tokens or wrong sample means", () => {
  for (const change of [value => { delete value.daily[0].failed; }, value => { value.jobs[0].lifetime.tokens_in = 1.5; },
    value => { value.quality.reviewed_jobs = "0"; }, value => { value.duration.avg_span_seconds = 1000; },
    value => { value.period.tokens_in = -1; }, value => { value.totals.tokens_in = 1.5; },
    value => { delete value.coverage.usage_events_without_tokens; }, value => { value.jobs[0].coverage.period_usage_events = 2; }]) {
    const value = fixture(); change(value); assert.throws(() => readStatistics(value, "alpha", selection, false));
  }
});
test("consumption preserves reported versus estimated and rejects missing or corrupt amounts", () => {
  const value = { scope: scope(), totals: amounts(0, 0), lifetime: amounts(7, 5), unallocated: amounts(), jobs: [job()], daily: [], coverage: {} };
  value.jobs[0].lifetime.reported_cost_usd = 0;
  value.jobs[0].lifetime.estimated_cost_usd = null;
  assert.equal(readConsumption(value, "alpha", selection, true).jobs[0].lifetime.reported_cost_usd, 0);
  assert.throws(() => readConsumption(value, "alpha", selection, false));
  delete value.jobs[0].lifetime.tokens_out;
  assert.throws(() => readConsumption(value, "alpha", selection, true));
});

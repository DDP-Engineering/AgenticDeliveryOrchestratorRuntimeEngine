/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readStatistics, readConsumption, totalTokens, consumptionIdentity } from "../src/statistics.ts";
import * as statistics from "../src/statistics.ts";
import { ReadTransportError } from "../src/errors.ts";
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

test("consumption validates unique date executor model bucket identities", () => {
  const bucket = { date: "2026-10-25", executor: "pi", model: "example", ...amounts(7, 5) };
  const value = { scope: scope(), totals: amounts(7, 5), lifetime: amounts(7, 5), unallocated: amounts(), jobs: [job()],
    daily: [bucket, { ...bucket, model: null }, { ...bucket, model: "" }, { ...bucket, date: "2026-10-26" }], coverage: {} };
  assert.equal(readConsumption(value, "alpha", selection, false).daily.length, 4);
  value.daily.push({ ...bucket, tokens_in: 99 });
  assert.throws(() => readConsumption(value, "alpha", selection, false), /Invalid statistics response/);
});

/** Controlled reporting resources: fixtures still pass through production validators. */
function reporting(overrides = {}) {
  assert.equal(typeof statistics.createReportingRefresh, "function", "coordinated reporting owner is available");
  let now = 1000;
  const timers = new Map();
  const states = [];
  const requests = { metrics: [], usage: [] };
  const read = member => signal => new Promise((resolve, reject) => { requests[member].push({ signal, resolve, reject }); });
  const owner = statistics.createReportingRefresh({ key: "principal:1/alpha/all", projectIds: ["alpha"], selection, admin: false,
    readMetrics: read("metrics"), readUsage: read("usage"), publish: state => states.push(state),
    env: { now: () => now, setTimeout: (fn, ms) => { const id = {}; timers.set(id, { fn, at: now + ms }); return id; },
      clearTimeout: id => timers.delete(id) }, ...overrides });
  return { owner, requests, states, latest: () => states.at(-1),
    advance(ms) { now += ms; for (const [id, timer] of [...timers]) if (timer.at <= now) { timers.delete(id); timer.fn(); } } };
}
const flush = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
const consumption = () => ({ scope: scope(), totals: amounts(0, 0), lifetime: amounts(7, 5), unallocated: amounts(), jobs: [job()], daily: [], coverage: {} });
const memberValue = (member, number) => {
  const value = member === "metrics" ? fixture() : consumption();
  if (member === "metrics") value.period.started = number;
  else value.totals.tokens_in = number;
  return { alpha: value };
};
async function completeReport(h, number = 1) {
  const pending = h.owner.refresh(); await flush();
  h.requests.metrics.at(-1).resolve(memberValue("metrics", number));
  h.requests.usage.at(-1).resolve(memberValue("usage", number));
  await pending;
}

test("reporting stages both validated members in either order before one coherent publication", async () => {
  for (const first of ["metrics", "usage"]) {
    const other = first === "metrics" ? "usage" : "metrics";
    const h = reporting();
    const initial = h.owner.refresh(); await flush();
    h.advance(100);
    h.requests[first][0].resolve(memberValue(first, 1)); await flush();
    assert.equal(h.latest().status, "loading");
    assert.equal(h.latest().data, null);
    h.advance(100);
    h.requests[other][0].resolve(memberValue(other, 1)); await initial;
    const baseline = h.latest().data;
    assert.equal(h.latest().status, "ready");
    assert.equal(baseline.fullReportAt, 1200);
    const pending = h.owner.refresh(); await flush();
    assert.equal(h.latest().data, baseline);
    h.advance(100);
    h.requests[first][1].resolve(memberValue(first, 2)); await flush();
    assert.equal(h.latest().data, baseline, "no fast-half publication");
    h.advance(100);
    h.requests[other][1].resolve(memberValue(other, 2)); await pending;
    assert.equal(h.latest().data.metrics.alpha.period.started, 2);
    assert.equal(h.latest().data.usage.alpha.totals.tokens_in, 2);
    assert.equal(h.latest().data.fullReportAt, 1400);
    assert.equal(h.latest().data[first + "At"], 1300);
    assert.equal(h.latest().data[other + "At"], 1400);
  }
});

test("metrics-only reporting pins usage and never advances usage or full-report success time", async () => {
  const h = reporting(); await completeReport(h);
  const baseline = h.latest().data;
  h.advance(15000);
  const pending = h.owner.refresh({ metrics: true }); await flush();
  assert.equal(h.requests.metrics.length, 2);
  assert.equal(h.requests.usage.length, 1);
  h.advance(100);
  h.requests.metrics[1].resolve(memberValue("metrics", 2)); await pending;
  assert.equal(h.latest().data.metricsAt, 16100);
  assert.equal(h.latest().data.usageAt, baseline.usageAt);
  assert.equal(h.latest().data.fullReportAt, baseline.fullReportAt);
  assert.equal(h.latest().data.usage, baseline.usage);
});

test("a full or due trigger promotes pinned usage in the active proposal without duplicate reads", async () => {
  const h = reporting(); await completeReport(h);
  const baseline = h.latest().data;
  const pending = h.owner.refresh({ metrics: true }); await flush();
  assert.equal(h.requests.usage.length, 1);
  assert.equal(h.owner.refresh({ usage: true }), pending);
  assert.equal(h.owner.refresh(), pending);
  await flush();
  assert.equal(h.requests.metrics.length, 2);
  assert.equal(h.requests.usage.length, 2);
  h.requests.metrics[1].resolve(memberValue("metrics", 2)); await flush();
  assert.equal(h.latest().data, baseline);
  h.requests.usage[1].resolve(memberValue("usage", 2)); await pending;
  await flush();
  assert.equal(h.latest().status, "ready");
  assert.equal(h.requests.metrics.length, 2, "no queued generation burst");
  assert.equal(h.requests.usage.length, 2);
});

test("failed proposals discard staged success and require the failed dependency through recovery", async () => {
  const h = reporting(); await completeReport(h);
  const baseline = h.latest().data;
  const pending = h.owner.refresh(); await flush();
  h.requests.metrics[1].resolve(memberValue("metrics", 999)); await flush();
  h.requests.usage[1].reject(new ReadTransportError()); await pending;
  assert.equal(h.latest().status, "stale");
  assert.equal(h.latest().data, baseline);
  assert.equal(h.requests.metrics[1].signal.aborted, true);
  const retry = h.owner.refresh({ metrics: true }); await flush();
  assert.equal(h.requests.usage.length, 3, "metrics-only trigger must also recover failed usage");
  h.requests.metrics[2].resolve(memberValue("metrics", 2)); await flush();
  assert.equal(h.latest().status, "stale");
  assert.equal(h.latest().data, baseline);
  h.requests.usage[2].resolve(memberValue("usage", 2)); await retry;
  assert.equal(h.latest().status, "ready");
  assert.equal(h.latest().data.metrics.alpha.period.started, 2);
});

test("reporting rejects malformed, foreign, missing and canonically mismatched replacements", async () => {
  for (const change of [value => { delete value.alpha; }, value => { value.beta = value.alpha; },
    value => { value.alpha.jobs[0].project_id = "beta"; }, value => { value.alpha.totals.tokens_out = "0"; },
    value => { value.alpha.scope.timezone = "Europe/Paris"; }]) {
    const h = reporting(); await completeReport(h);
    const pending = h.owner.refresh(); await flush();
    const corrupt = memberValue("usage", 2); change(corrupt);
    h.requests.metrics[1].resolve(memberValue("metrics", 2));
    h.requests.usage[1].resolve(corrupt); await pending;
    assert.equal(h.latest().status, "error");
    assert.equal(h.latest().data, null);
    assert.equal(h.latest().completedAt, null);
  }
});

test("matching request selections still require matching server canonical intervals", async () => {
  const intervalSelection = { ...selection, from: "2026-10-25", through: "2026-10-25" };
  const h = reporting({ selection: intervalSelection });
  const pending = h.owner.refresh(); await flush();
  const metrics = memberValue("metrics", 1), usage = memberValue("usage", 1);
  for (const [value, from, to] of [[metrics.alpha, "2026-10-25T00:00:00Z", "2026-10-26T00:00:00Z"],
    [usage.alpha, "2026-10-25T01:00:00Z", "2026-10-26T01:00:00Z"]]) {
    value.scope = { ...value.scope, mode: "interval", from, to, interval_seconds: 86400 };
    if (value.period) { value.period.from = from; value.period.to = to; }
  }
  // Individually valid for the selection; only the coordinated pair can reject this mismatch.
  readStatistics(metrics.alpha, "alpha", intervalSelection, false);
  readConsumption(usage.alpha, "alpha", intervalSelection, false);
  h.requests.metrics[0].resolve(metrics); h.requests.usage[0].resolve(usage); await pending;
  assert.equal(h.latest().status, "error");
  assert.equal(h.latest().data, null);
  assert.equal(h.latest().completedAt, null);
});

/** Global pairs may each validate while disagreeing with the other project. */
test("global reporting validates common canonical scope and pooled evidence before publication", async () => {
  const intervalSelection = { ...selection, from: "2026-10-25", through: "2026-10-25" };
  for (const failure of ["interval", "metrics aggregate", "usage aggregate"]) {
    const h = reporting({ projectIds: ["alpha", "beta"], selection: intervalSelection, admin: true });
    const values = (bad = false) => {
      const metrics = {}, usage = {};
      for (const id of ["alpha", "beta"]) {
        metrics[id] = fixture(); usage[id] = consumption();
        const hour = bad && failure === "interval" && id === "beta" ? "01" : "00";
        const from = `2026-10-25T${hour}:00:00Z`, to = `2026-10-26T${hour}:00:00Z`;
        for (const value of [metrics[id], usage[id]]) {
          value.scope = { ...scope(id), mode: "interval", from, to, interval_seconds: 86400 };
          value.jobs[0].project_id = id;
        }
        Object.assign(metrics[id].period, { from, to });
        if (bad && failure === "metrics aggregate") metrics[id].totals.cost_usd = 1e308;
        if (bad && failure === "usage aggregate") usage[id].totals.reported_cost_usd = 1e308;
        readStatistics(metrics[id], id, intervalSelection, true);
        readConsumption(usage[id], id, intervalSelection, true);
      }
      return { metrics, usage };
    };
    const complete = async bad => {
      const pending = h.owner.refresh(); await flush();
      const value = values(bad);
      h.requests.metrics.at(-1).resolve(value.metrics); h.requests.usage.at(-1).resolve(value.usage);
      await pending;
    };
    await complete(false);
    assert.equal(h.latest().status, "ready", "matching multi-project control publishes");
    h.advance(100);
    await complete(true);
    assert.equal(h.latest().status, "error", failure);
    assert.equal(h.latest().data, null);
    assert.equal(h.latest().completedAt, null, "invalid replacement cannot record success");
    await complete(false);
    assert.equal(h.latest().status, "ready", "explicit valid recovery publishes");
    h.owner.dispose();
  }
});

/** Each project is valid alone; integer overflow exists only in the pooled report. */
test("reporting rejects pooled token direction and combined totals before any successful publication", async () => {
  for (const member of ["metrics", "usage"]) for (const location of ["totals", "period", "daily"]) {
    if (member === "usage" && location === "period") continue;
    for (const combined of [false, true]) {
      const h = reporting({ projectIds: ["alpha", "beta"] });
      const values = (bad = false) => {
        const metrics = {}, usage = {};
        for (const id of ["alpha", "beta"]) {
          metrics[id] = fixture(); usage[id] = consumption();
          for (const value of [metrics[id], usage[id]]) { value.scope = scope(id); value.jobs[0].project_id = id; }
          usage[id].daily = [{ date: "2026-10-25", executor: "pi", model: "example", ...amounts(0, 0) }];
          if (bad) {
            const value = member === "metrics" ? metrics[id] : usage[id];
            Object.assign(location === "daily" ? value.daily[0] : value[location], {
              tokens_in: combined ? 3e15 : 5e15, tokens_out: combined ? 3e15 : 0,
            });
          }
          // Positive control: neither fixture is individually out of range.
          readStatistics(metrics[id], id, selection, false);
          readConsumption(usage[id], id, selection, false);
        }
        return { metrics, usage };
      };
      const complete = async bad => {
        const pending = h.owner.refresh(); await flush();
        const value = values(bad);
        h.requests.metrics.at(-1).resolve(value.metrics); h.requests.usage.at(-1).resolve(value.usage);
        await pending;
      };
      await complete(true);
      assert.equal(h.latest().status, "error", `${member}/${location}/${combined ? "combined" : "direction"}`);
      assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
      assert.equal(h.states.some(state => state.status === "ready"), false, "no transient ready publication");
      await complete(false); assert.equal(h.latest().status, "ready");
      await complete(true); assert.equal(h.latest().status, "error");
      assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
      await complete(false); assert.equal(h.latest().status, "ready", "valid recovery remains possible");
      h.owner.dispose();
    }
  }
});

test("known combined token overflow fails validation for single-project consumption and job amounts", () => {
  for (const location of ["totals", "lifetime", "unallocated", "daily", "job lifetime", "job in_period", "job unallocated"]) {
    const value = consumption();
    value.daily = [{ date: "2026-10-25", executor: "pi", model: "example", ...amounts(0, 0) }];
    const target = location.startsWith("job ") ? value.jobs[0][location.slice(4)] : location === "daily" ? value.daily[0] : value[location];
    Object.assign(target, { tokens_in: 5e15, tokens_out: 5e15 });
    assert.throws(() => readConsumption(value, "alpha", selection, false), RangeError, location);
    target.tokens_out = null;
    assert.doesNotThrow(() => readConsumption(value, "alpha", selection, false), "unknown combined total stays unknown");
  }
});

/** Quality must never discover malformed run rows after the owner has committed. */
test("reporting validates run collections and review counts before publishing success", async () => {
  const validRuns = [{ review_rounds: 0 }, { review_rounds: 2 }];
  const valid = fixture(); valid.runs = validRuns;
  assert.equal(readStatistics(valid, "alpha", selection, false).runs, validRuns);
  for (const runs of [undefined, null, {}, [null], [[]], [{}], [{ review_rounds: "2" }],
    [{ review_rounds: null }], [{ review_rounds: -1 }], [{ review_rounds: 0.5 }],
    [{ review_rounds: Number.MAX_SAFE_INTEGER + 1 }],
    [{ review_rounds: Number.MAX_SAFE_INTEGER }, { review_rounds: 1 }]]) {
    const h = reporting();
    const complete = async rows => {
      const pending = h.owner.refresh(); await flush();
      const metrics = memberValue("metrics", 1); metrics.alpha.runs = rows;
      h.requests.metrics.at(-1).resolve(metrics);
      h.requests.usage.at(-1).resolve(memberValue("usage", 1));
      await pending;
    };
    await complete(runs);
    assert.equal(h.latest().status, "error");
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    assert.equal(h.states.some(state => state.status === "ready"), false);
    await complete(validRuns); assert.equal(h.latest().status, "ready");
    h.advance(100);
    await complete(runs); assert.equal(h.latest().status, "error");
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    await complete([]); assert.equal(h.latest().status, "ready", "empty run collection is valid");
    h.owner.dispose();
  }
});

/** Optional revision evidence is validated before selected-project Quality can render it. */
test("reporting validates optional revision identities and values before publishing success", async () => {
  const revision = () => ({ project_id: "alpha", run_id: "same-run", revision: 1, trigger: "revise-label",
    date: "2026-10-25", tokens_in: 0, tokens_out: null, reported_cost_usd: 0, estimated_cost_usd: null });
  const validRows = [revision(), { ...revision(), revision: 2, trigger: "pipeline-failed", date: null },
    { ...revision(), run_id: "other-run", trigger: "unclassified", tokens_in: null }];
  const invalidRows = [null, {}, { length: 1 }, [null], [[]], [{}], [revision(), revision()]];
  for (const [key, values] of Object.entries({
    project_id: [undefined, null, "beta"], run_id: [undefined, null, {}, "", "../foreign"],
    revision: [undefined, null, {}, "1", 0, -1, 0.5, Number.MAX_SAFE_INTEGER + 1],
    trigger: [undefined, null, {}, ["revise-label"], "unknown"], date: [undefined, {}, "not a date", "2026-02-30", "2026-10-25T00:00:00Z"],
    tokens_in: [undefined, {}, "0", -1, 0.5, Number.MAX_SAFE_INTEGER + 1],
    tokens_out: [undefined, {}, "0", -1, 0.5, Number.MAX_SAFE_INTEGER + 1],
    reported_cost_usd: [undefined, {}, "0", -1, Infinity, NaN],
    estimated_cost_usd: [undefined, {}, "0", -1, Infinity, NaN],
  })) for (const value of values) invalidRows.push([{ ...revision(), [key]: value }]);
  invalidRows.push([{ ...revision(), tokens_in: 5e15, tokens_out: 5e15 }]);
  for (const rows of [undefined, [], validRows]) {
    const value = fixture();
    if (rows !== undefined) value.revisions = rows;
    assert.equal(readStatistics(value, "alpha", selection, true).revisions, rows);
  }
  for (const rows of invalidRows) {
    const h = reporting({ admin: true });
    const complete = async revisions => {
      const pending = h.owner.refresh(); await flush();
      const metrics = memberValue("metrics", 1); metrics.alpha.revisions = revisions;
      h.requests.metrics.at(-1).resolve(metrics);
      h.requests.usage.at(-1).resolve(memberValue("usage", 1));
      await pending;
    };
    await complete(rows);
    assert.equal(h.latest().status, "error", `invalid revisions: ${JSON.stringify(rows)}`);
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    assert.equal(h.states.some(state => state.status === "ready"), false, "no transient success");
    await complete(validRows); assert.equal(h.latest().status, "ready");
    h.advance(100);
    await complete(rows); assert.equal(h.latest().status, "error");
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    await complete([]); assert.equal(h.latest().status, "ready", "empty revisions recover");
    h.owner.dispose();
  }
});

/** Monetary evidence must validate before eager Quality chip formatting or pooling. */
test("reporting validates optional cost efficiency structures counts and money before success", async () => {
  const keys = ["reported_per_completed", "estimated_per_completed", "reported_per_human_merged", "estimated_per_human_merged"];
  const evidence = () => ({ jobs_with_evidence: 2, usd_per_job: 8 });
  const bad = [undefined, null, [], "costs", 0];
  for (const key of keys) {
    for (const entry of [null, [], "cost", 0, {}, { jobs_with_evidence: 0 }]) bad.push({ [key]: entry });
    for (const count of [undefined, null, {}, "2", -1, 0.5, Number.MAX_SAFE_INTEGER + 1, Infinity, NaN]) {
      bad.push({ [key]: { ...evidence(), jobs_with_evidence: count } });
    }
    for (const money of [undefined, {}, { toString: null }, [], "invalid", "8", -1, Infinity, NaN]) {
      bad.push({ [key]: { ...evidence(), usd_per_job: money } });
    }
  }
  // The collection is optional, but every present entry must carry valid evidence.
  bad.push({ unrecognized_bucket: null }, { reported_per_completed: { jobs_with_evidence: 0, usd_per_job: { toString: null } } });
  const valid = { reported_per_completed: evidence(), estimated_per_completed: { jobs_with_evidence: 1, usd_per_job: 0 },
    reported_per_human_merged: { jobs_with_evidence: 0, usd_per_job: null }, estimated_per_human_merged: { jobs_with_evidence: 2, usd_per_job: null } };
  for (const costs of [undefined, {}, valid]) {
    const value = fixture();
    if (costs !== undefined) value.quality.cost_efficiency = costs;
    assert.equal(readStatistics(value, "alpha", selection, true).quality.cost_efficiency, costs);
  }
  for (const costs of bad) {
    const h = reporting({ admin: true });
    const complete = async costs => {
      const pending = h.owner.refresh(); await flush();
      const metrics = memberValue("metrics", 1);
      metrics.alpha.totals.cost_usd = 0;
      metrics.alpha.quality.cost_efficiency = costs;
      h.requests.metrics.at(-1).resolve(metrics); h.requests.usage.at(-1).resolve(memberValue("usage", 1));
      await pending;
    };
    await complete(costs);
    assert.equal(h.latest().status, "error", `invalid efficiency: ${JSON.stringify(costs)}`);
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    assert.equal(h.states.some(state => state.status === "ready"), false, "no transient success");
    await complete(valid); assert.equal(h.latest().status, "ready");
    h.advance(100);
    await complete(costs); assert.equal(h.latest().status, "error");
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    await complete({}); assert.equal(h.latest().status, "ready", "empty collection recovers");
    h.owner.dispose();
  }
});

test("reporting validates pooled efficiency counts and weighted money including unknown and zero", async () => {
  for (const failure of ["weighted product", "weighted sum", "pooled count"]) {
    const h = reporting({ admin: true, projectIds: ["alpha", "beta"] });
    const complete = async (bad = false, unknown = false) => {
      const pending = h.owner.refresh(); await flush();
      const metrics = {}, usage = {};
      for (const id of ["alpha", "beta"]) {
        metrics[id] = fixture(); usage[id] = consumption();
        for (const value of [metrics[id], usage[id]]) { value.scope = scope(id); value.jobs[0].project_id = id; }
        metrics[id].totals.cost_usd = 0;
        metrics[id].quality.cost_efficiency = { reported_per_completed: {
          jobs_with_evidence: bad ? failure === "pooled count" ? Number.MAX_SAFE_INTEGER : failure === "weighted product" ? 2 : 1 : id === "alpha" ? 1 : 3,
          usd_per_job: unknown ? null : bad ? failure === "pooled count" ? 0 : 1e308 : id === "alpha" ? 0 : 8,
        } };
        readStatistics(metrics[id], id, selection, true);
      }
      h.requests.metrics.at(-1).resolve(metrics); h.requests.usage.at(-1).resolve(usage); await pending;
    };
    await complete(true);
    assert.equal(h.latest().status, "error", failure);
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    assert.equal(h.states.some(state => state.status === "ready"), false);
    await complete(); assert.equal(h.latest().status, "ready");
    assert.deepEqual(h.latest().data.pooledMetrics.quality.cost_efficiency.reported_per_completed,
      { jobs_with_evidence: 4, usd_per_job: 6 }, "valid evidence weighting is unchanged");
    h.advance(100);
    await complete(true); assert.equal(h.latest().status, "error");
    assert.equal(h.latest().data, null); assert.equal(h.latest().completedAt, null);
    await complete(false, true); assert.equal(h.latest().status, "ready");
    assert.equal(h.latest().data.pooledMetrics.quality.cost_efficiency.reported_per_completed.usd_per_job, null, "unknown money is not zero");
    h.owner.dispose();
  }
});

test("empty periodic masks cannot manufacture a new successful read time", async () => {
  const h = reporting(); await completeReport(h);
  const current = h.latest();
  h.advance(15000);
  await h.owner.refresh({}); await flush();
  assert.equal(h.latest(), current);
  assert.equal(h.requests.metrics.length, 1);
  assert.equal(h.requests.usage.length, 1);
});

test("report ownership invalidation releases both reads and cannot publish old success or failure", async () => {
  const h = reporting(); await completeReport(h);
  const pending = h.owner.refresh(); await flush();
  const oldMetric = h.requests.metrics.at(-1), oldUsage = h.requests.usage.at(-1);
  h.owner.invalidate(); await pending;
  assert.equal(oldMetric.signal.aborted, true);
  assert.equal(oldUsage.signal.aborted, true);
  assert.equal(h.latest().data, null);
  await completeReport(h, 2);
  const current = h.latest();
  oldMetric.resolve(memberValue("metrics", 999));
  oldUsage.reject(new Error("obsolete failure")); await flush();
  assert.equal(h.latest(), current);
});

test("post-result reporting revalidation retains presentation but cancels every pre-result member", async () => {
  const h = reporting(); await completeReport(h);
  const baseline = h.latest().data;
  const older = h.owner.refresh({ metrics: true }); await flush();
  const oldMetric = h.requests.metrics.at(-1);
  const replacement = h.owner.revalidate(); await older; await flush();
  assert.equal(oldMetric.signal.aborted, true);
  assert.equal(h.latest().data, baseline);
  assert.equal(h.requests.metrics.length, 3);
  assert.equal(h.requests.usage.length, 2, "result requires a full post-result generation, never a pin");
  oldMetric.resolve(memberValue("metrics", 999)); await flush();
  assert.equal(h.latest().data, baseline);
  h.requests.metrics[2].resolve(memberValue("metrics", 2)); await flush();
  assert.equal(h.latest().data, baseline);
  h.requests.usage[1].resolve(memberValue("usage", 2)); await replacement;
  assert.equal(h.latest().data.metrics.alpha.period.started, 2);
  assert.equal(h.latest().data.usage.alpha.totals.tokens_in, 2);
});

test("one reporting deadline bounds promotions, releases the slot and excludes expired completions", async () => {
  const h = reporting(); await completeReport(h);
  const pending = h.owner.refresh({ metrics: true }); await flush();
  const expired = h.requests.metrics[1];
  h.advance(29999);
  assert.equal(h.owner.refresh(), pending); await flush();
  h.advance(1); await pending;
  assert.equal(h.latest().status, "stale");
  assert.equal(expired.signal.aborted, true);
  await completeReport(h, 2);
  const current = h.latest();
  expired.resolve(memberValue("metrics", 999));
  h.requests.usage[1].resolve(memberValue("usage", 999)); await flush();
  assert.equal(h.latest(), current);
  const cancelled = h.owner.refresh(); await flush();
  h.owner.dispose(); await cancelled;
  const count = h.states.length;
  h.requests.metrics.at(-1).resolve(memberValue("metrics", 999));
  h.requests.usage.at(-1).resolve(memberValue("usage", 999));
  await h.owner.refresh(); await flush();
  assert.equal(h.states.length, count);
});

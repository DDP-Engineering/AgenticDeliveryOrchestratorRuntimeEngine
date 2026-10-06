/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale, MessageKey } from "./i18n";
import type { Amounts, JobConsumption, Metrics } from "./metrics";
import { consumptionIdentity, totalTokens } from "./statistics";
import { statisticsCopy } from "./statisticsCopy";
import { formatRoute } from "./routes";

type Props = { reporting?: import("./statistics").ReportingSelection; metrics: Metrics; locale: Locale; admin: boolean; t: (key: MessageKey) => string };
/** Nullable measurements retain their visible status; zero is observed evidence. */
export function Measurement({ value, locale, partial = false, money = false }: { value: number | null | undefined; locale: Locale; partial?: boolean; money?: boolean }) {
  const copy = statisticsCopy[locale];
  const label = value == null ? copy.unavailable : partial ? copy.partial : value === 0 ? copy.zero : copy.measured;
  return <span className="measurement"><strong>{value == null ? "—" : new Intl.NumberFormat(locale, money ? { style: "currency", currency: "USD" } : {}).format(value)}</strong><small>{label}</small></span>;
}
/** Each value carries direction, scope and provenance rather than an inferred complete total. */
export function JobAmounts({ job, locale, admin, t, compact = false, periodAvailable = true }: { job: JobConsumption; locale: Locale; admin: boolean; t: Props["t"]; compact?: boolean; periodAvailable?: boolean }) {
  const copy = statisticsCopy[locale];
  const amount = (label: string, value: Amounts) => <div className="job-amount"><b>{label}</b><span>{t("tokensIn")}: <Measurement value={value.tokens_in} locale={locale} partial={value.tokens_in !== null && value.tokens_out === null} /> · {t("tokensOut")}: <Measurement value={value.tokens_out} locale={locale} partial={value.tokens_out !== null && value.tokens_in === null} /></span>
    {!compact && <><span>{copy.total}: <Measurement value={totalTokens(value)} locale={locale} /></span>{admin && <span>{copy.reported}: <Measurement value={value.reported_cost_usd} locale={locale} money /> · {copy.estimated}: <Measurement value={value.estimated_cost_usd} locale={locale} money /></span>}</>}<small>{copy.events}: {value.events}</small></div>;
  return <div className="job-consumption" data-identity={consumptionIdentity(job)}><small>{copy.projectId}: {job.project_id} · {copy.runId}: {job.run_id}</small>
    {amount(copy.lifetime, job.lifetime)}{periodAvailable ? amount(copy.selected, job.in_period) : <div><b>{copy.selected}</b><p>{copy.unavailable} · {copy.missingJob}</p></div>}{!compact && amount(copy.undated, job.unallocated)}<small>{copy.source}: {{ journal: copy.sourceJournal, summary: copy.sourceSummary, unavailable: copy.sourceUnavailable }[job.source]}</small></div>;
}

/** Explain initial measures, stock and immutable job consumption from the server-selected interval. */
export function StatisticsEvidence({ metrics, locale, admin, t, reporting }: Props) {
  const copy = statisticsCopy[locale], partial = (metrics.coverage.usage_events_without_tokens ?? 0) > 0;
  const period = metrics.period;
  const cards = [[copy.started, period.started], [copy.completed, period.completed], [copy.failed, period.failed],
    [t("tokensIn"), period.tokens_in], [t("tokensOut"), period.tokens_out], [copy.total, totalTokens(period)]] as const;
  return <>
    <section className="panel statistics-evidence"><h2>{copy.evidence}</h2><p className="muted">{metrics.scope?.mode === "all_time" ? copy.allTime : copy.interval} · {metrics.scope?.timezone}</p>
      <div className="stats-grid">{cards.map(([label, value], index) => <div className="stat-card" key={label}><span>{label}</span>{index < 3 ? <strong>{value}</strong> : <Measurement value={value} locale={locale} partial={partial} />}</div>)}
        {admin && <><div className="stat-card"><span>{copy.reported}</span><Measurement value={period.cost_usd} locale={locale} money /></div><div className="stat-card"><span>{copy.estimated}</span><Measurement value={period.estimated_cost_usd} locale={locale} money /></div></>}
      </div><p>{copy.lifecycle}</p><h3>{copy.coverage}</h3><p>{copy.coverageHelp}</p><p>{copy.events}: {metrics.coverage.usage_events_with_tokens ?? 0} {copy.measured} · {metrics.coverage.usage_events_without_tokens ?? 0} {copy.unavailable} · {metrics.coverage.usage_events_unallocated ?? 0} {copy.undated}</p>
      <p>{copy.unallocatedHelp}</p>{admin && <p>{copy.moneyHelp}</p>}<p>{copy.duration}</p>
      <p className="canonical-scope"><code>{metrics.scope?.interval} {metrics.scope?.from ?? "−∞"} → {metrics.scope?.to ?? "+∞"}</code>{metrics.scope?.interval_seconds != null && <> · {metrics.scope.interval_seconds} s</>}</p>
    </section>
    <section className="panel current-stock"><h2>{copy.stock}</h2><strong>{metrics.current_stock?.active_now}</strong><p>{copy.stockHelp}</p></section>
    <section className="panel" role="region" aria-label={copy.messages}><h2>{copy.messages}</h2><strong>{copy.unavailable}</strong><p>{copy.messageHelp}</p></section>
    <section className="panel"><h2>{copy.jobs}</h2><p>{copy.jobHelp}</p>{metrics.jobs?.length ? <div className="table-scroll"><table className="consumption-table"><caption>{copy.jobs} · {metrics.scope?.mode === "all_time" ? copy.allTime : copy.interval}</caption><thead><tr><th>{copy.projectId}</th><th>{copy.runId}</th><th>{copy.lifetime} / {copy.selected} / {copy.undated}</th></tr></thead><tbody>{metrics.jobs.map(job => <tr key={consumptionIdentity(job)}><td>{job.project_id}</td><td><a href={formatRoute({ view: "jobs", project: job.project_id, run: job.run_id, reporting })}>{job.run_id}</a></td><td><JobAmounts job={job} locale={locale} admin={admin} t={t} /></td></tr>)}</tbody></table></div> : <p>{copy.empty}</p>}</section>
  </>;
}

/** Bars and accessible table use exactly the same server buckets and series. */
export function TrendEvidence({ metrics, locale, admin, t }: Props) {
  const copy = statisticsCopy[locale], rows = metrics.daily;
  const maximum = Math.max(1, ...rows.flatMap(row => [row.started, row.completed, row.failed ?? 0]));
  const series = [["started", copy.started], ["completed", copy.completed], ["failed", copy.failed]] as const;
  return rows.length ? <>
    <figure className="statistics-trend" aria-label={copy.trend}><figcaption>{copy.trend} · {metrics.scope?.timezone} · {metrics.scope?.granularity}</figcaption>
      <div aria-hidden="true">{rows.map(row => <div className="trend-bucket" key={row.date}><b>{row.date}</b>{series.map(([key, label]) => <div className={`trend-series trend-${key}`} key={key}><span>{label}: {row[key] ?? 0}</span><div className="trend-track"><i style={{ width: `${100 * (row[key] ?? 0) / maximum}%` }} /></div></div>)}</div>)}</div>
    </figure><div className="table-scroll"><table><caption>{copy.table}</caption><thead><tr><th>{t("date")}</th>{series.map(([key, label]) => <th key={key}>{label}</th>)}<th>{t("tokensIn")}</th><th>{t("tokensOut")}</th>{admin && <><th>{copy.reported}</th><th>{copy.estimated}</th></>}</tr></thead>
      <tbody>{rows.map(row => <tr key={row.date}><td>{row.date}</td><td>{row.started}</td><td>{row.completed}</td><td>{row.failed ?? 0}</td><td><Measurement value={row.tokens_in} locale={locale} /></td><td><Measurement value={row.tokens_out} locale={locale} /></td>{admin && <><td><Measurement value={row.cost_usd} locale={locale} money /></td><td><Measurement value={row.estimated_cost_usd} locale={locale} money /></td></>}</tr>)}</tbody></table></div>
  </> : <p>{copy.empty}</p>;
}

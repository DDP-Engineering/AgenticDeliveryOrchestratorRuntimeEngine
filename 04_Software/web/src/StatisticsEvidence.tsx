/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale, MessageKey } from "./i18n";
import type { JobConsumption, Metrics } from "./metrics";
import { consumptionIdentity, totalTokens } from "./statistics";
import { statisticsCopy } from "./statisticsCopy";

type Props = { metrics: Metrics; locale: Locale; admin: boolean; t: (key: MessageKey) => string };
/** Nullable measurements retain their visible status; zero is observed evidence. */
export function Measurement({ value, locale, partial = false, money = false }: { value: number | null | undefined; locale: Locale; partial?: boolean; money?: boolean }) {
  const copy = statisticsCopy[locale];
  const label = value == null ? copy.unavailable : partial ? copy.partial : value === 0 ? copy.zero : copy.measured;
  return <span className="measurement"><strong>{value == null ? "—" : new Intl.NumberFormat(locale, money ? { style: "currency", currency: "USD" } : {}).format(value)}</strong><small>{label}</small></span>;
}
/** Lifetime consumption of one job; unknown stays a dash and measured zero stays 0. */
export function JobAmounts({ job, locale, admin, t, compact = false }: { job: JobConsumption; locale: Locale; admin: boolean; t: Props["t"]; compact?: boolean }) {
  const copy = statisticsCopy[locale], value = job.lifetime;
  const amount = (number: number | null | undefined, money = false) => <strong>{number == null ? "—" : new Intl.NumberFormat(locale, money ? { style: "currency", currency: "USD" } : {}).format(number)}</strong>;
  return <div className="job-consumption" data-identity={consumptionIdentity(job)}>
    <span>{t("tokensIn")}: {amount(value.tokens_in)}</span><span>{t("tokensOut")}: {amount(value.tokens_out)}</span>
    {!compact && <><span>{copy.total}: {amount(totalTokens(value))}</span>{admin && <><span>{copy.reported}: {amount(value.reported_cost_usd, true)}</span><span>{copy.estimated}: {amount(value.estimated_cost_usd, true)}</span></>}<small>{copy.events}: {value.events}</small></>}
  </div>;
}

/** Summary measures for the server-selected interval; per-job consumption lives in Jobs. */
export function StatisticsEvidence({ metrics, locale, admin, t }: Props) {
  const copy = statisticsCopy[locale], partial = (metrics.coverage.usage_events_without_tokens ?? 0) > 0;
  const period = metrics.period;
  const cards = [[copy.started, period.started], [copy.completed, period.completed], [copy.failed, period.failed],
    [t("tokensIn"), period.tokens_in], [t("tokensOut"), period.tokens_out], [copy.total, totalTokens(period)]] as const;
  return <section className="panel statistics-evidence">
    <div className="stats-grid">{cards.map(([label, value], index) => <div className="stat-card" key={label}><span>{label}</span>{index < 3 ? <strong>{value}</strong> : <Measurement value={value} locale={locale} partial={partial} />}</div>)}
      {admin && <><div className="stat-card"><span>{copy.reported}</span><Measurement value={period.cost_usd} locale={locale} money /></div><div className="stat-card"><span>{copy.estimated}</span><Measurement value={period.estimated_cost_usd} locale={locale} money /></div></>}
    </div>
  </section>;
}

/** One table per server bucket; count cells carry bars scaled to the largest count. */
export function TrendEvidence({ metrics, locale, admin, t }: Props) {
  const copy = statisticsCopy[locale], rows = metrics.daily;
  const maximum = Math.max(1, ...rows.flatMap(row => [row.started, row.completed, row.failed ?? 0]));
  const series = [["started", copy.started], ["completed", copy.completed], ["failed", copy.failed]] as const;
  const amount = (value: number | null | undefined, money = false) => value == null ? "—" : new Intl.NumberFormat(locale, money ? { style: "currency", currency: "USD" } : {}).format(value);
  return rows.length ? <div className="table-scroll"><table className="trend-table" aria-label={copy.table}><thead><tr><th>{t("date")}</th>{series.map(([key, label]) => <th key={key}>{label}</th>)}<th>{t("tokensIn")}</th><th>{t("tokensOut")}</th>{admin && <><th>{copy.reported}</th><th>{copy.estimated}</th></>}</tr></thead>
    <tbody>{rows.map(row => <tr key={row.date}><td>{row.date}</td>{series.map(([key]) => <td key={key} className={`trend-count trend-${key}`}>{row[key] ?? 0}<i aria-hidden="true" style={{ width: `${100 * (row[key] ?? 0) / maximum}%` }} /></td>)}<td>{amount(row.tokens_in)}</td><td>{amount(row.tokens_out)}</td>{admin && <><td>{amount(row.cost_usd, true)}</td><td>{amount(row.estimated_cost_usd, true)}</td></>}</tr>)}</tbody></table></div> : <p>{copy.empty}</p>;
}

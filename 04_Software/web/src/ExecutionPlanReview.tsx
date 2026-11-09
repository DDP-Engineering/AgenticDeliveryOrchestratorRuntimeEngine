/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";
import { preparationCopy, type ExecutionPlan, type PreparationEvidence } from "./executionPlan";
import { localCopy } from "./localExecution";

/** Exact-plan review inside existing project settings and pending Apply. */
export function ExecutionPlanReview({ plan, locale }: { plan: ExecutionPlan; locale: Locale }) {
  const copy = preparationCopy[locale];
  if (plan.backend === "local") return <section className="execution-plan"><h3>{localCopy[locale].title}</h3><p>{localCopy[locale].notice}</p><p><code>{plan.fingerprint}</code></p></section>;
  return <section className="execution-plan"><h3>{copy.title}</h3><p>{copy.help}</p>
    <dl><div><dt>{copy.image}</dt><dd><code>{plan.image}</code></dd></div><div><dt>{copy.source}</dt><dd>{plan.image_source}</dd></div><div><dt>{copy.selection}</dt><dd><code>{plan.selection || "—"}</code></dd></div></dl>
    <details><summary>{copy.commands} ({plan.steps.length})</summary><ol>{plan.steps.map((step, index) => <li key={index}><strong>{step.name}</strong><pre>{step.run}</pre></li>)}</ol><p>SHA-256: <code>{plan.source_sha256}</code></p><p><code>{plan.fingerprint}</code></p></details>
  </section>;
}

/** Authoritative persisted step outcomes, separate from host/model readiness. */
export function PreparationResults({ evidence, locale }: { evidence: PreparationEvidence; locale: Locale }) {
  const copy = preparationCopy[locale];
  return <section><h3>{copy.title}</h3><p>{copy.status}: <strong>{evidence.status}</strong> · {copy.attempts}: {evidence.attempts}</p><p>{copy.image}: <code>{evidence.image}</code></p>
    <ol>{evidence.steps.map(step => <li key={step.index}><strong>{step.name}</strong>: {step.exit_code} · <time dateTime={step.finished_at}>{new Date(step.finished_at).toLocaleString(locale)}</time>{step.timed_out && " · timeout"}{step.cancelled && " · cancelled"}</li>)}</ol>
    {["failed", "interrupted", "cancelled"].includes(evidence.status) && <p>{copy.recovery}</p>}
  </section>;
}

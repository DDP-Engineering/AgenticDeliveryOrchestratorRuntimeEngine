/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useId, useRef, useState, type ReactNode } from "react";
import type { Locale, MessageKey } from "./i18n";
import { commandAllowed, stableExecutionDrift, type Job } from "./jobModel";
import { budgetCopy, directCopy, jobCopy, sessionCopy } from "./jobCopy";
import { jobDetailsCopy } from "./jobDetailsCopy";
import { recoveryCopy } from "./recoveryCopy";
import { ticketCopy } from "./ticketCopy";
import { ForgeMarkdown } from "./forgeMarkdown";
import { StatusBadge } from "./Presentation";
import { PreparationResults } from "./ExecutionPlanReview";
import { formatRoute } from "./routes";

type Tab = "activity" | "sessions" | "evidence" | "technical";
type Props = {
  job: Job; locale: Locale; t: (key: MessageKey) => string; admin: boolean; busy: boolean;
  onClose: () => void; onCommand: (action: "retry" | "cancel" | "restart", job: Job) => void;
  sessions: ReactNode; consumption: ReactNode; output: ReactNode; timeline: ReactNode; directEvidence?: ReactNode;
  stageLabel: string; stageName: (stage: string) => string; statusLabel: string;
};

/** Present only saved job evidence; commands keep their existing worker-owned authorization. */
export function JobDetails({ job, locale, t, admin, busy, onClose, onCommand, sessions, consumption, output, timeline, directEvidence, stageLabel, stageName, statusLabel }: Props) {
  const copy = jobCopy[locale], text = jobDetailsCopy[locale], budget = budgetCopy[locale];
  const [selected, setSelected] = useState<Tab>("activity");
  const [eventLimit, setEventLimit] = useState(10);
  const prefix = useId(), tabs = useRef<HTMLDivElement>(null);
  const tabList: Tab[] = ["activity", "sessions", "evidence", "technical"];
  const sessionText = sessionCopy[locale];
  const question = job.lifecycle === "parked-clarification";
  const needsHuman = ["parked-clarification", "awaiting-approval", "in-review"].includes(job.lifecycle);
  const actionText = job.waiting.next_action === "answer_question_on_ticket" ? copy.openQuestion : job.waiting.next_action === "review_candidate_on_ticket" ? copy.openApproval : copy.openReview;
  const canNavigate = needsHuman && job.waiting.next_action && job.waiting.evidence_url;
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value)) : copy.unknown;
  const reveal = (tab: Tab) => {
    setSelected(tab);
    document.getElementById(`${prefix}-${tab}-tab`)?.focus({ preventScroll: true });
    tabs.current?.scrollIntoView({ block: "nearest" });
  };
  const commands = (["retry", "cancel", "restart"] as const).filter(action => commandAllowed(job, action));
  const events = job.timeline?.slice().reverse() ?? [];
  const tabName = (tab: Tab) => tab === "activity" ? text.activity : tab === "sessions" ? sessionText.title : tab === "technical" ? sessionText.technical : sessionText.artifacts;
  // Only leading editorial comments are omitted from the readable question. The exact source stays below it.
  const readableQuestion = job.waiting.reason?.replace(/^(?:\s*<!--[\s\S]*?-->\s*)+/, "") ?? "";
  const markdown = (source: string) => <ForgeMarkdown source={source} imageLabel={ticketCopy[locale].imageNotLoaded} codeLabel={ticketCopy[locale].code} tableLabel={ticketCopy[locale].table} />;
  return <section className="panel detail-panel job-details" aria-label={`${t("ticket")} #${job.ticket_iid}`}>
    <header className="job-detail-header">
      <div className="job-detail-commands">    <div className="job-detail-tabs" role="tablist" aria-label={copy.details} ref={tabs}>
      {tabList.map(tab => <button key={tab} id={`${prefix}-${tab}-tab`} role="tab" aria-selected={selected === tab} aria-controls={`${prefix}-${tab}`} tabIndex={selected === tab ? 0 : -1}
        onClick={() => setSelected(tab)} onKeyDown={event => { const index = tabList.indexOf(tab), target = event.key === "Home" ? 0 : event.key === "End" ? 3 : event.key === "ArrowRight" ? (index + 1) % 4 : event.key === "ArrowLeft" ? (index + 3) % 4 : null;
          if (target !== null) { event.preventDefault(); setSelected(tabList[target]); tabs.current?.querySelectorAll<HTMLButtonElement>("button")[target].focus(); } }}>{tabName(tab)}</button>)}
    </div>
{job.ticket_url && <a href={job.ticket_url} target="_blank" rel="noreferrer">{sessionText.showTicket} ↗</a>}<button className="ghost job-detail-close" onClick={onClose}>{t("close")}</button></div>
      <div className="job-detail-title"><h2><span>{t("ticket")} #{job.ticket_iid} · </span>{job.ticket_title || copy.titleUnknown}</h2></div>
      <div className="job-detail-meta"><StatusBadge code={job.lifecycle}>{statusLabel}</StatusBadge><span>{t("stage")}: <strong>{stageLabel}</strong></span><span>{directCopy[locale].workflow}: {job.workflow === "direct" ? directCopy[locale].direct : "AEGIS"}</span><span>{job.project_display_name}</span>
        {commands.length > 0 && <details className="job-actions"><summary>{text.actions}</summary><div className="job-action-menu">
          {commands.map(action => <div key={action}><p className="field-hint">{action === "restart" ? recoveryCopy[locale].help : action === "retry" ? copy.retryHelp : copy.cancelHelp}</p>
            <button className={action === "retry" ? "ghost" : "danger"} disabled={busy} onClick={() => onCommand(action, job)}>{action === "restart" ? recoveryCopy[locale].restart : t(action)}</button></div>)}
        </div></details>}
      </div>
    </header>
    <div className="job-detail-grid">
      <section className="job-human-actions">
        {job.stage_failures > 0 && <p className="notice" role="status">{copy.stageFailures.replace("{count}", String(job.stage_failures))}</p>}
        {question ? <button className="primary" onClick={() => reveal("evidence")}>{text.readQuestion}</button> : canNavigate ? <a className="primary link-button" href={job.waiting.evidence_url!} target="_blank" rel="noreferrer">{actionText} ↗</a> : needsHuman ? <p>{copy.evidenceMissing}</p> : null}
      </section>
      <aside className="job-resources" aria-label={text.resources}>
        {job.budget && <section className="job-budgets" aria-label={budget.title}><h3>{budget.title}</h3>
          <dl><div><dt>{budget.launches}</dt><dd>{job.budget.launches} / {job.budget.max_launches ?? "—"}</dd></div><div><dt>{budget.active}</dt><dd>{Math.floor(job.budget.active_seconds)} / {job.budget.max_active_seconds ?? "—"}</dd></div></dl>
          {job.budget.availability === "unavailable" ? <p className="notice" role="status">{budget.unavailable}</p> :
            (job.budget.launches / job.budget.max_launches >= .9 || job.budget.active_seconds / job.budget.max_active_seconds >= .9) && <p className="notice" role="status">{job.budget.launches >= job.budget.max_launches || job.budget.active_seconds >= job.budget.max_active_seconds ? budget.reached : budget.near}</p>}
          <p className="field-hint">{text.notProgress}</p><details><summary>{copy.details}</summary><p className="field-hint">{budget.timing}</p></details>
          {admin && !job.project_archived && <a href={formatRoute({ view: "projectDetails", project: job.project_id, tab: "configuration" })}>{budget.settings}</a>}
        </section>}
        <section className="job-usage"><h3>{copy.consumption}</h3>{consumption}<p className="field-hint">{text.unknownCost}</p></section>
      </aside>
    </div>
    <section id={`${prefix}-activity`} role="tabpanel" tabIndex={0} aria-labelledby={`${prefix}-activity-tab`} hidden={selected !== "activity"} className="job-detail-content">
      <h3>{text.activity}</h3><p className="field-hint">{copy.observedTimeline}</p>
      {events.length ? <ol className="job-activity">{events.slice(0, eventLimit).map((event, index) => <li key={index}><time dateTime={event.ts || undefined}>{date(event.ts)}</time><div><strong>{text.events[event.event as keyof typeof text.events] || text.recordedEvent}</strong>
        <code>{event.event}</code></div>{event.stage && <span className="job-event-stage">{stageName(event.stage)}</span>}</li>)}</ol> : <p>{copy.unknown}</p>}
      {events.length > eventLimit && <button className="ghost" onClick={() => setEventLimit(events.length)}>{t("all")} ({events.length})</button>}
    </section>
    <section id={`${prefix}-sessions`} role="tabpanel" tabIndex={0} aria-labelledby={`${prefix}-sessions-tab`} hidden={selected !== "sessions"} className="job-detail-content">
      {selected === "sessions" && sessions}
    </section>
    <section id={`${prefix}-evidence`} role="tabpanel" tabIndex={0} aria-labelledby={`${prefix}-evidence-tab`} hidden={selected !== "evidence"} className="job-detail-content job-question">
      <h3>{question ? text.question : copy.artifacts}</h3>
      {question && <><p className="notice">{text.activeQuestion}</p>{readableQuestion ? markdown(readableQuestion) : <p>{text.missingQuestion}</p>}
        {job.waiting.reason && <details className="job-original"><summary>{text.original}</summary><pre className="operation-detail" tabIndex={0}>{job.waiting.reason}</pre></details>}</>}
      {!question && needsHuman && job.waiting.reason && <p>{job.waiting.reason === "candidate_approval_requested" ? copy.approvalReason : job.waiting.reason === "draft_review_open" ? copy.reviewReason : job.waiting.reason}</p>}
      {job.outcome && <><h4>{text.outcome}</h4><p>{job.outcome}</p></>}
      <div className="button-row">{canNavigate && <a className="primary link-button" href={job.waiting.evidence_url!} target="_blank" rel="noreferrer">{actionText} ↗</a>}
        {job.ticket_url && <a className="ghost link-button" href={job.ticket_url} target="_blank" rel="noreferrer">{t("ticket")} ↗</a>}
        {job.mr_url && <a className="ghost link-button" href={job.mr_url} target="_blank" rel="noreferrer">{t("draft")} ↗</a>}</div>
      {!job.ticket_url && !job.mr_url && !canNavigate && <p>{copy.evidenceMissing}</p>}
      {directEvidence}
      {job.preparation && <PreparationResults evidence={job.preparation} locale={locale} />}
    </section>
    <section id={`${prefix}-technical`} role="tabpanel" tabIndex={0} aria-labelledby={`${prefix}-technical-tab`} hidden={selected !== "technical"} className="job-detail-content">
      <h3>{text.diagnostics}</h3>{stableExecutionDrift(job) && <p role="note">{recoveryCopy[locale].drift}</p>}
      {job.outcome && <p>{job.outcome}</p>}
      <dl className="action-explanation"><div><dt>{t("project")}</dt><dd>{job.project_id}</dd></div><div><dt>{t("jobTerm")}</dt><dd>{job.run_id}</dd></div><div><dt>{t("reviewRounds")} / {t("attempts")}</dt><dd>{job.review_rounds} / {job.stage_failures}</dd></div><div><dt>{t("coverage")}</dt><dd>{Object.entries(job.coverage).filter(([key]) => ["ticket", "journal", "title", "last_activity"].includes(key)).map(([key, value]) => `${key}: ${value}`).join(" · ")}</dd></div></dl>
      {output}<details className="job-original"><summary>{text.rawEvents}</summary>{timeline}</details>
    </section>
  </section>;
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { Locale, MessageKey } from "./i18n";
import { commandAllowed, stableExecutionDrift, type Job } from "./jobModel";
import { budgetCopy, directCopy, jobCopy, sessionCopy } from "./jobCopy";
import { jobDetailsCopy } from "./jobDetailsCopy";
import { recoveryCopy } from "./recoveryCopy";
import { ticketCopy } from "./ticketCopy";
import { ForgeMarkdown } from "./forgeMarkdown";
import { StatusBadge } from "./Presentation";
import { PreparationResults } from "./ExecutionPlanReview";
import { PagedTable } from "./PagedTable";
import { conversationCopy } from "./conversationCopy";
import { readSessions, type AgentSession } from "./sessionModel";
import { formatRoute } from "./routes";

type Tab = "activity" | "sessions" | "details";
type Props = {
  job: Job; locale: Locale; t: (key: MessageKey) => string; admin: boolean; busy: boolean;
  onClose: () => void; onCommand: (action: "retry" | "cancel" | "restart", job: Job) => void;
  request:<T>(path:string)=>Promise<T>; sessions: (active:boolean,target?:{id:string;sequence:number},toolbarHost?:HTMLElement|null)=>ReactNode; consumption: ReactNode; output: ReactNode; directEvidence?: ReactNode;
  stageLabel: string; stageName: (stage: string) => string; statusLabel: string;
};

/** Present only saved job evidence; commands keep their existing worker-owned authorization. */
export function JobDetails({ job, locale, t, admin, busy, onClose, onCommand, sessions, request, consumption, output, directEvidence, stageLabel, stageName, statusLabel }: Props) {
  const copy = jobCopy[locale], text = jobDetailsCopy[locale], budget = budgetCopy[locale];
  const [selected, setSelected] = useState<Tab>("activity");
  const [sessionsVisited,setSessionsVisited]=useState(false);
  const [sessionControls,setSessionControls]=useState<HTMLDivElement|null>(null);
  useEffect(()=>{if(selected==="sessions")setSessionsVisited(true);},[selected]);
  const chat = conversationCopy[locale];
  const [activityPage,setActivityPage]=useState(0);
  const [activityEvents,setActivityEvents]=useState(job.timeline||[]);
  useEffect(()=>{if(activityPage===0)setActivityEvents(job.timeline||[]);},[job.timeline,activityPage]);
  const [catalog,setCatalog]=useState<AgentSession[]>([]);
  const [sessionTarget,setSessionTarget]=useState<{id:string;sequence:number}>();
  useEffect(()=>{
    let current=true;
    request(`/jobs/${encodeURIComponent(job.project_id)}/${encodeURIComponent(job.run_id)}/sessions`)
      .then(value=>{const rows=readSessions(value);if(current)setCatalog(rows);}).catch(()=>{if(current)setCatalog([]);});
    return()=>{current=false;};
  },[job.project_id,job.run_id,job.timeline?.length,job.lifecycle]);
  // A job executes one launch at a time. Link only a unique archive/live marker
  // inside one recorded launch interval, including a unique reverse match.
  const launches=(job.timeline||[]).filter(event=>event.event==="stage-launch"&&event.ts&&event.attempt);
  const eventKey=(event:NonNullable<Job["timeline"]>[number])=>`${event.ts}:${event.stage}:${event.attempt}`;
  const assignments=new Map<string,AgentSession[]>();
  const uniqueSessions=new Map<string,AgentSession>();
  for(const row of catalog){const key=row.archive_id||row.id;if(!uniqueSessions.has(key))uniqueSessions.set(key,row);}
  for(const row of uniqueSessions.values()){
    const stamp=Date.parse((row.live?row.start_at:row.end_at)||"");
    const matches=launches.filter((event,index)=>event.stage===row.stage&&event.attempt===row.attempt&&stamp>=Date.parse(event.ts!)&&(!launches[index+1]||stamp<=Date.parse(launches[index+1].ts!)));
    if(matches.length===1)assignments.set(eventKey(matches[0]),[...(assignments.get(eventKey(matches[0]))||[]),row]);
  }
  const eventSession=(event:NonNullable<Job["timeline"]>[number])=>{const rows=assignments.get(eventKey(event));return rows?.length===1?rows[0]:undefined;};
  const prefix = useId(), tabs = useRef<HTMLDivElement>(null);
  const tabList: Tab[] = ["activity", "sessions", "details"];
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
  const events = activityEvents.slice().reverse();
  const tabName = (tab: Tab) => tab === "activity" ? text.activity : tab === "sessions" ? sessionText.title : text.details;
  // Only leading editorial comments are omitted from the readable question. The exact source stays below it.
  const readableQuestion = job.waiting.reason?.replace(/^(?:\s*<!--[\s\S]*?-->\s*)+/, "") ?? "";
  const markdown = (source: string) => <ForgeMarkdown source={source} imageLabel={ticketCopy[locale].imageNotLoaded} codeLabel={ticketCopy[locale].code} tableLabel={ticketCopy[locale].table} />;
  return <section className="panel detail-panel job-details" aria-label={`${t("ticket")} #${job.ticket_iid}`}>
    <header className="job-detail-header">
      <div className="job-detail-commands">    <div className="job-detail-tabs" role="tablist" aria-label={copy.details} ref={tabs}>
      {tabList.map(tab => <button key={tab} id={`${prefix}-${tab}-tab`} role="tab" aria-selected={selected === tab} aria-controls={`${prefix}-${tab}`} tabIndex={selected === tab ? 0 : -1}
        onClick={() => setSelected(tab)} onKeyDown={event => { const index = tabList.indexOf(tab), target = event.key === "Home" ? 0 : event.key === "End" ? tabList.length - 1 : event.key === "ArrowRight" ? (index + 1) % tabList.length : event.key === "ArrowLeft" ? (index + tabList.length - 1) % tabList.length : null;
          if (target !== null) { event.preventDefault(); setSelected(tabList[target]); tabs.current?.querySelectorAll<HTMLButtonElement>("button")[target].focus(); } }}>{tabName(tab)}</button>)}
    </div>
<div className="job-detail-links">{job.ticket_url && <a href={job.ticket_url} target="_blank" rel="noreferrer">{sessionText.showTicket} ↗</a>}<button className="ghost job-detail-close" onClick={onClose}>{t("close")}</button></div></div>
      <div className="job-detail-title"><h2><span>{t("ticket")} #{job.ticket_iid} · </span>{job.ticket_title || copy.titleUnknown}</h2></div>
      <div className="job-detail-meta"><StatusBadge code={job.lifecycle}>{statusLabel}</StatusBadge><span>{t("stage")}: <strong>{stageLabel}</strong></span><span>{directCopy[locale].workflow}: {job.workflow === "direct" ? directCopy[locale].direct : "AEGIS"}</span><span>{job.project_display_name}</span>
        <div ref={setSessionControls} className="job-session-controls" hidden={selected!=="sessions"}/>
        {commands.length > 0 && <details className="job-actions"><summary>{text.actions}</summary><div className="job-action-menu">
          {commands.map(action => <div key={action}><p className="field-hint">{action === "restart" ? recoveryCopy[locale].help : action === "retry" ? copy.retryHelp : copy.cancelHelp}</p>
            <button className={action === "retry" ? "ghost" : "danger"} disabled={busy} onClick={() => onCommand(action, job)}>{action === "restart" ? recoveryCopy[locale].restart : t(action)}</button></div>)}
        </div></details>}
      </div>
    </header>
    <div className="job-detail-grid"><div className="job-detail-main">
      <section className="job-human-actions">
        {stableExecutionDrift(job) && <p className="notice" role="note">{recoveryCopy[locale].drift}</p>}
        {job.stage_failures > 0 && <p className="notice" role="status">{copy.stageFailures.replace("{count}", String(job.stage_failures))}</p>}
        {question ? <div className="button-row"><button className="primary" onClick={() => reveal("details")}>{text.readQuestion}</button>{canNavigate&&<a className="primary link-button" href={job.waiting.evidence_url!} target="_blank" rel="noreferrer">{actionText} ↗</a>}</div> : canNavigate ? <a className="primary link-button" href={job.waiting.evidence_url!} target="_blank" rel="noreferrer">{actionText} ↗</a> : needsHuman ? <p>{copy.evidenceMissing}</p> : null}
      </section>

    <section id={`${prefix}-activity`} role="tabpanel" tabIndex={0} aria-labelledby={`${prefix}-activity-tab`} hidden={selected !== "activity"} className="job-detail-content">
      <PagedTable alwaysControls t={t} onPageChange={setActivityPage}><table className="job-activity-table" aria-label={text.activity}>
        <thead><tr><th>{t("date")}</th><th>{t("timelineEvent")}</th><th>{t("stage")}</th><th>{chat.session}</th></tr></thead>
        <tbody>{events.map((event,index)=>{const linked=eventSession(event);const title=text.events[event.event as keyof typeof text.events] || ({usage:chat.usage,"usage-observation":chat.observation,"executor-artifacts":chat.artifacts}[event.event]) || chat.event;
          return <tr key={index}><td><time dateTime={event.ts||undefined}>{date(event.ts)}</time></td><td>{title}</td><td>{event.stage?stageName(event.stage):"—"}</td><td>{linked?<button className="text-button" onClick={()=>{setSessionTarget(previous=>({id:linked.archive_id||linked.id,sequence:(previous?.sequence||0)+1}));reveal("sessions");}}>{chat.open} ↗</button>:"—"}</td></tr>;})}</tbody>
      </table></PagedTable>
      {!events.length&&<p>{copy.unknown}</p>}
    </section>
    <section id={`${prefix}-sessions`} role="tabpanel" tabIndex={0} aria-labelledby={`${prefix}-sessions-tab`} hidden={selected !== "sessions"} className="job-detail-content">
      {(selected === "sessions" || sessionsVisited) && sessions(selected === "sessions",sessionTarget,sessionControls)}
    </section>
    <section id={`${prefix}-details`} role="tabpanel" tabIndex={0} aria-labelledby={`${prefix}-details-tab`} hidden={selected !== "details"} className="job-detail-content">
      {question&&<section className="job-question"><h3>{text.question}</h3><p className="notice">{text.activeQuestion}</p>{readableQuestion?markdown(readableQuestion):<p>{text.missingQuestion}</p>}</section>}
      {job.outcome&&<section className="job-result"><h3>{text.result}</h3><p>{job.outcome==="merged by human"?text.mergedOutcome:job.outcome==="cancelled"?t("cancelled"):job.outcome}</p></section>}
      <dl className="job-summary">
        <div><dt>{text.branch}</dt><dd>{job.branch?<code>{job.branch}</code>:text.notRecorded}</dd></div>
        {job.published_commit&&<div><dt>{text.publishedCommit}</dt><dd><code>{job.published_commit}</code></dd></div>}
        {job.mr_url&&<div><dt>{text.review}</dt><dd><a href={job.mr_url} target="_blank" rel="noreferrer">MR/PR ↗</a></dd></div>}
        <div><dt>{t("reviewRounds")}</dt><dd>{job.review_rounds}</dd></div>
      </dl>
      {Object.entries(job.coverage).some(([,value])=>value==="missing"||value==="unknown")&&<p className="notice" role="status">{text.dataMissing}: {Object.entries(job.coverage).filter(([,value])=>value==="missing"||value==="unknown").map(([key])=>text.sources[key as keyof typeof text.sources]).join(", ")}</p>}
      <details className="job-diagnostics"><summary>{text.diagnostic}</summary>
        <dl className="job-summary"><div><dt>{t("project")}</dt><dd><code>{job.project_id}</code></dd></div><div><dt>{t("jobTerm")}</dt><dd><code>{job.run_id}</code></dd></div><div><dt>{text.currentFailures}</dt><dd>{job.stage_failures}</dd></div></dl>
        {question&&job.waiting.reason&&<details className="job-original"><summary>{text.original}</summary><pre className="operation-detail" tabIndex={0}>{job.waiting.reason}</pre></details>}
        {directEvidence}
        {job.preparation&&<PreparationResults evidence={job.preparation} locale={locale}/>}
        {output}
      </details>
    </section>
    </div>
      <aside className="job-resources" aria-label={text.resources}>
        {job.budget && <section className="job-budgets" aria-label={budget.title}><h3>{budget.title}</h3>
          <dl><div><dt>{budget.launches}</dt><dd>{job.budget.launches} / {job.budget.max_launches ?? "—"}</dd></div><div><dt>{budget.active}</dt><dd>{Math.floor(job.budget.active_seconds)} / {job.budget.max_active_seconds ?? "—"}</dd></div></dl>
          {job.budget.availability === "unavailable" ? <p className="notice" role="status">{budget.unavailable}</p> :
            (job.budget.launches / job.budget.max_launches >= .9 || job.budget.active_seconds / job.budget.max_active_seconds >= .9) && <p className="notice" role="status">{job.budget.launches >= job.budget.max_launches || job.budget.active_seconds >= job.budget.max_active_seconds ? budget.reached : budget.near}</p>}
          {admin && !job.project_archived && <a href={formatRoute({ view: "projectDetails", project: job.project_id, tab: "configuration" })}>{budget.settings}</a>}
        </section>}
        <section className="job-usage"><h3>{copy.consumption}</h3>{consumption}<p className="field-hint">{text.unknownCost}</p></section>
      </aside>
    </div>
  </section>;
}

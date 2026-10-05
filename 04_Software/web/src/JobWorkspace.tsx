/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, describeError } from "./errors";
import type { Locale, MessageKey } from "./i18n";
import { jobCopy, lifecycleExplanation } from "./jobCopy";
import { activityAge, commandAllowed, IncompleteJobs, lifecycles, readJobDetail, readJobPage, stages, type Job, type JobPage } from "./jobModel";
import { DataFeedback, StatusBadge } from "./Presentation";
import { startVisiblePolling } from "./polling";
import { formatRoute } from "./routes";

export type JobProject = { id: string; name: string; display_name?: string; archived: boolean; paused: boolean };
type Request = <T>(path: string, method?: string, body?: unknown, csrf?: string) => Promise<T>;
type Props = {
  mode: "overview" | "jobs" | "history"; locale: Locale; projects: JobProject[]; scope: string; run?: string;
  csrf: string; request: Request; t: (key: MessageKey) => string; refresh: number;
  onScope: (scope: string) => void; onOpen: (project: string, run: string) => void; onClose: () => void;
  fixedScope?: boolean;
};
type ReadState = "loading" | "ready" | "error" | "incomplete" | "changed";
type Operation = { id: number; status: "pending" | "running" | "succeeded" | "failed" | "uncertain"; result?: string };
type Filters = { q: string; group: string; lifecycle: string; stage: string; executor: string; outcome: string; from: string; to: string; size: 10 | 25 | 50 | "all"; offset: number };
const initialFilters = (mode: Props["mode"]): Filters => ({ q: "", group: mode === "history" ? "terminal" : "", lifecycle: "", stage: "", executor: "", outcome: "", from: "", to: "", size: 10, offset: 0 });
const lifecycleKeys: Record<string, MessageKey> = {
  working: "working", publishing: "publishingStatus", "parked-clarification": "parkedClarificationStatus",
  "awaiting-approval": "awaitingApprovalStatus", "in-review": "inReviewStatus", "handoff-pending": "handoffPendingStatus",
  "handed-off": "handedOffStatus", done: "done", failed: "failed", cancelled: "cancelled",
};
const stageKeys: Record<string, MessageKey> = { frame: "frameStage", specify: "specifyStage", design: "designStage", build: "buildStage", validate: "validateStage", deliver: "deliverStage", done: "done", publishing: "publishingStatus" };
const label = (value: string, keys: Record<string, MessageKey>, t: Props["t"]) => keys[value] ? t(keys[value]) : value;
const normalizeFailure = (cause: unknown) => cause instanceof ApiError ? cause : new ApiError("unexpected_response");
const readOperation = (value: unknown): Operation => {
  const operation = value as Operation;
  if (!operation || !Number.isSafeInteger(operation.id) || operation.id < 1 ||
    !["pending", "running", "succeeded", "failed", "uncertain"].includes(operation.status) ||
    operation.result !== undefined && typeof operation.result !== "string") throw new ApiError("unexpected_response");
  return operation;
};

/** Own complete scoped jobs and observed evidence; the server owns permissions and command execution. */
export function JobWorkspace(props: Props) {
  const { mode, locale, projects, scope, run, csrf, request, t, refresh, onScope, onOpen, onClose, fixedScope } = props;
  const copy = jobCopy[locale];
  const [filters, setFilters] = useState<Filters>(() => initialFilters(mode));
  const [advanced, setAdvanced] = useState(false);
  const [page, setPage] = useState<JobPage | null>(null);
  const [state, setState] = useState<ReadState>("loading");
  const [failure, setFailure] = useState<unknown>(null);
  const [detail, setDetail] = useState<Job | null>(null);
  const [detailState, setDetailState] = useState<ReadState>("loading");
  const [detailFailure, setDetailFailure] = useState<unknown>(null);
  const [ticket, setTicket] = useState("");
  const [operation, setOperation] = useState<Operation | null>(null);
  const [operationError, setOperationError] = useState<unknown>(null);
  const [commandStatusError, setCommandStatusError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const submitLock = useRef(false);
  const mounted = useRef(true);
  const commandGeneration = useRef(0);
  const [reload, setReload] = useState(0);
  const revision = useRef({ key: "", snapshot: "" });
  const [worker, setWorker] = useState("checking");
  const project = projects.find(item => item.id === scope);
  const ids = projects.map(item => item.id).sort().join(",");
  const { offset, ...selection } = filters;
  const baseKey = JSON.stringify([scope, mode, selection, ids]);
  const renderKey = JSON.stringify([baseKey, offset]);
  const [dataKey, setDataKey] = useState("");
  const detailKey = `${scope}/${run || ""}`;
  const [loadedDetailKey, setLoadedDetailKey] = useState("");
  const visible = dataKey === renderKey && state === "ready" ? page : null;
  const visibleDetail = loadedDetailKey === detailKey && detailState === "ready" && ids.split(",").includes(scope) && state !== "changed" ? detail : null;
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : copy.unknown;
  const change = (key: keyof Filters, value: string | number) => setFilters(current => ({ ...current, [key]: value, offset: 0 }));
  const busy = submitting || operation !== null && ["pending", "running"].includes(operation.status);

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; commandGeneration.current += 1; }; }, []);
  useEffect(() => { commandGeneration.current += 1; setTicket(""); setOperation(null); setOperationError(null); setCommandStatusError(false); submitLock.current = false; setSubmitting(false); }, [scope]);

  useEffect(() => {
    let active = true, sequence = 0;
    if (offset > 0 && revision.current.key !== baseKey) { setFilters(current => ({ ...current, offset: 0 })); return; }
    const fetchPage = async () => {
      const current = ++sequence;
      setState("loading"); setDataKey(renderKey); setFailure(null);
      const query = new URLSearchParams({ limit: String(filters.size), offset: String(offset) });
      if (scope) query.set("project_id", scope);
      if (mode === "overview") query.set("attention", "true");
      for (const [key, value] of Object.entries({ q: filters.q.trim(), status_group: filters.group, lifecycle: filters.lifecycle,
        stage: filters.stage, executor: filters.executor.trim(), outcome: filters.outcome.trim(), updated_from: filters.from, updated_to: filters.to })) if (value) query.set(key, value);
      if (offset > 0) query.set("snapshot", revision.current.snapshot);
      try {
        const result = readJobPage(await request(`/jobs-page?${query}`), ids.split(","));
        if (result.offset !== offset || result.items.some(row => scope && row.project_id !== scope)) throw new ApiError("unexpected_response");
        if (!active || sequence !== current) return;
        revision.current = { key: baseKey, snapshot: result.snapshot };
        setPage(result); setState("ready");
      } catch (cause) {
        if (!active || sequence !== current) return;
        setPage(null);
        setState(cause instanceof IncompleteJobs ? "incomplete" : cause instanceof ApiError && cause.code === "job_snapshot_changed" ? "changed" : "error");
        setFailure(normalizeFailure(cause));
      }
    };
    void fetchPage();
    const stop = startVisiblePolling(() => void fetchPage(), 15000);
    return () => { active = false; stop(); };
  }, [renderKey, refresh, reload]);

  useEffect(() => {
    if (!run || !scope || !ids.split(",").includes(scope)) { setDetail(null); return; }
    let active = true, sequence = 0;
    const fetchDetail = async () => {
      const current = ++sequence;
      setDetail(null); setDetailState("loading"); setDetailFailure(null); setLoadedDetailKey(detailKey);
      try {
        const result = readJobDetail(await request(`/jobs/${encodeURIComponent(scope)}/${encodeURIComponent(run)}`), scope, run);
        if (active && sequence === current) { setDetail(result); setDetailState("ready"); }
      } catch (cause) {
        if (active && sequence === current) { setDetailState(cause instanceof IncompleteJobs ? "incomplete" : "error"); setDetailFailure(normalizeFailure(cause)); }
      }
    };
    void fetchDetail();
    const stop = startVisiblePolling(() => void fetchDetail(), 15000);
    return () => { active = false; stop(); };
  }, [detailKey, ids, refresh, reload]);

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        await request("/ready"); if (active) setWorker("ready");
      } catch (cause) { if (active) setWorker(cause instanceof ApiError && cause.code === "worker_unavailable" ? "unavailable" : "error"); }
    };
    void check(); const stop = startVisiblePolling(() => void check(), 5000);
    return () => { active = false; stop(); };
  }, [refresh]);

  useEffect(() => {
    if (!operation || !["pending", "running"].includes(operation.status)) return;
    let active = true;
    const poll = async () => {
      try {
        const current = readOperation(await request(`/operations/${operation.id}`));
        if (current.id !== operation.id) throw new ApiError("unexpected_response");
        if (!active) return;
        setOperation(current); setCommandStatusError(false);
        if (!["pending", "running"].includes(current.status)) setReload(value => value + 1);
      } catch { if (active) setCommandStatusError(true); }
    };
    void poll(); const stop = startVisiblePolling(() => void poll(), 2000);
    return () => { active = false; stop(); };
  }, [operation?.id, operation?.status]);

  const command = async (action: "start" | "retry" | "cancel", job?: Job) => {
    if (submitLock.current || busy || !project || project.archived || action !== "start" && (!job || !commandAllowed(job, action))) return;
    submitLock.current = true; setSubmitting(true); setOperationError(null); setCommandStatusError(false);
    const generation = commandGeneration.current;
    try {
      const body = action === "start" ? { ticket_iid: Number(ticket) } : { run_id: job!.run_id };
      const current = readOperation(await request(`/projects/${encodeURIComponent(scope)}/operations/${action}`, "POST",
        { ...body, idempotency_key: crypto.randomUUID() }, csrf));
      if (mounted.current && generation === commandGeneration.current) { setOperation(current); if (action === "start") setTicket(""); }
    } catch (cause) { if (mounted.current && generation === commandGeneration.current) setOperationError(cause); }
    finally { if (mounted.current && generation === commandGeneration.current) { submitLock.current = false; setSubmitting(false); } }
  };
  const submit = (event: FormEvent) => { event.preventDefault(); void command("start"); };
  const feedback = (status: ReadState, cause: unknown) => status === "incomplete" || status === "changed" ?
    <section className="panel data-feedback" role="alert"><div><h2>{status === "incomplete" ? copy.incomplete : copy.changed}</h2><p>{status === "incomplete" ? copy.incompleteHelp : copy.changedHelp}</p><button className="ghost" onClick={() => { revision.current = { key: "", snapshot: "" }; setFilters(current => ({ ...current, offset: 0 })); setReload(value => value + 1); }}>{copy.reload}</button></div></section> :
    <><DataFeedback state={status === "loading" ? "loading" : "error"} t={t} />{cause && status !== "loading" ? <p className="muted">{describeError(locale, cause)}</p> : null}</>;
  const reason = (job: Job) => job.waiting.reason === "candidate_approval_requested" ? copy.approvalReason : job.waiting.reason === "draft_review_open" ? copy.reviewReason : job.waiting.reason || job.outcome || copy.reasonUnknown;
  const actionText = (job: Job) => job.waiting.next_action === "answer_question_on_ticket" ? copy.openQuestion : job.waiting.next_action === "review_candidate_on_ticket" ? copy.openApproval : copy.openReview;
  const actor = (job: Job) => ({ human_responder: copy.responder, human_approver: copy.approver, human_reviewer: copy.reviewer }[job.waiting.responsible_role || ""] ||
    (["working", "publishing"].includes(job.lifecycle) ? copy.system : ["failed", "stale", "handoff-pending"].includes(job.lifecycle) ? copy.operator : copy.unknown));
  const activity = (job: Job) => <><time dateTime={job.last_activity_at || undefined}>{date(job.last_activity_at)}</time>{activityAge(job.last_activity_at) !== "recent" && <small className="field-hint">{job.last_activity_at ? copy.oldActivity : copy.missingActivity}</small>}</>;
  const open = (event: React.MouseEvent<HTMLAnchorElement>, job: Job) => { if (event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) { event.preventDefault(); onOpen(job.project_id, job.run_id); } };
  const table = (rows: Job[]) => <div className="table-scroll"><table className="action-jobs-table"><thead><tr><th>{t("ticket")}</th><th>{t("project")}</th><th>{t("status")}</th><th>{t("lastActivity")}</th><th>{copy.duration} / {copy.consumption}</th></tr></thead><tbody>{rows.map(job => <tr key={`${job.project_id}/${job.run_id}`}>
    <td><a className="strong" href={formatRoute({ view: "jobs", project: job.project_id, run: job.run_id })} onClick={event => open(event, job)}>#{job.ticket_iid} · {job.ticket_title || copy.titleUnknown}</a><small className="field-hint">{job.run_id}</small></td>
    <td>{job.project_display_name}{job.project_archived && <small className="field-hint">{t("archived")}</small>}</td>
    <td><StatusBadge code={job.lifecycle}>{job.lifecycle === "done" ? copy.completed : job.lifecycle === "stale" ? copy.staleJob : label(job.lifecycle, lifecycleKeys, t)}</StatusBadge><small className="field-hint">{t("stage")}: {label(job.stage, stageKeys, t)}</small><p>{reason(job)}</p>{job.waiting.next_action && job.waiting.evidence_url && <a href={job.waiting.evidence_url} target="_blank" rel="noreferrer">{actionText(job)} ↗</a>}</td>
    <td>{activity(job)}</td><td>{copy.unknown}<small className="field-hint">{copy.unknownTelemetry}</small></td>
  </tr>)}</tbody></table></div>;
  const pager = visible && <div className="table-pagination"><label>{t("rowsPerPage")}<select value={filters.size} onChange={event => change("size", event.target.value === "all" ? "all" : Number(event.target.value))}>{[10, 25, 50].map(size => <option key={size} value={size}>{size}</option>)}<option value="all">{t("all")}</option></select></label><span>{visible.total === 0 ? "0" : `${offset + 1}–${Math.min(offset + visible.items.length, visible.total)}`} / {visible.total}</span><div className="button-row"><button className="ghost" disabled={offset === 0} onClick={() => setFilters(current => ({ ...current, offset: Math.max(0, offset - visible.limit) }))}>{t("previous")}</button><button className="ghost" disabled={offset + visible.items.length >= visible.total || filters.size === "all"} onClick={() => setFilters(current => ({ ...current, offset: offset + visible.limit }))}>{t("next")}</button></div></div>;

  return <div className="job-workspace">
    <section className="panel compact"><div className="workspace-controls">{!fixedScope && <label htmlFor="jobs-project">{copy.scope}<select id="jobs-project" aria-label={copy.scope} value={scope} onChange={event => onScope(event.target.value)}><option value="">{copy.all}</option>{projects.map(item => <option key={item.id} value={item.id}>{item.display_name || item.name}</option>)}</select></label>}<span className="scope-note">{scope ? project?.display_name || project?.name : copy.all}</span>
      <span className="worker-evidence" role="status">{worker === "ready" ? copy.workerReady : worker === "checking" ? copy.workerChecking : worker === "unavailable" ? copy.workerUnavailable : copy.workerError}</span></div>
      <p className="muted"><span>{scope ? copy.scopedHelp : copy.scopeHelp}</span> <span>{copy.workerHelp}</span></p>
    </section>
    {mode === "jobs" && project && !project.archived && <section className="panel compact"><form className="inline-form job-start-form" onSubmit={submit}>
      <p className="form-legend"><span className="required-mark" aria-hidden="true">*</span> {t("requiredLegend")}</p><label htmlFor="job-ticket-number">{t("ticketNumber")}<span className="required-mark" aria-hidden="true"> *</span><input id="job-ticket-number" type="number" min="1" step="1" placeholder={`${t("examplePrefix")} 42`} value={ticket} onChange={event => setTicket(event.target.value)} required aria-describedby="job-ticket-number-help" /></label><button className="primary" disabled={busy} type="submit">{t("start")}</button>
      <p id="job-ticket-number-help" className="field-hint"><span>{t("ticketNumberHelp")}</span> <span>{copy.startHelp}</span></p>
    </form></section>}
    {!!operationError && <p className="alert" role="alert">{describeError(locale, operationError)}</p>}
    {operation && <div className={`notice command-result command-${operation.status}`} role="status">#{operation.id} · {copy[operation.status === "pending" ? "queued" : operation.status]}{operation.result && <p>{operation.result}</p>}{commandStatusError && <p>{copy.commandError}</p>}</div>}
    {mode !== "overview" && <section className="panel compact"><div className="job-filters job-basic-filters"><label htmlFor="job-search">{copy.search}<input id="job-search" type="search" maxLength={80} value={filters.q} onChange={event => change("q", event.target.value)} aria-describedby="job-search-help" /></label><label>{t("status")}<select value={filters.group} onChange={event => change("group", event.target.value)}><option value="">{t("all")}</option>{["active", "waiting", "review", "terminal"].map(group => <option key={group} value={group}>{group === "active" ? t("activeJobs") : group === "waiting" ? copy.waiting : group === "review" ? t("inReviewStatus") : copy.terminal}</option>)}</select></label></div><p id="job-search-help" className="field-hint">{copy.searchHelp}</p>
      <button className="ghost" aria-expanded={advanced} aria-controls="job-advanced-filters" onClick={() => setAdvanced(value => !value)}>{copy.advanced}</button>
      {advanced && <div id="job-advanced-filters" className="job-filters job-text-filters">
        <label>{t("status")}<select value={filters.lifecycle} onChange={event => change("lifecycle", event.target.value)}><option value="">{t("all")}</option>{lifecycles.map(value => <option key={value} value={value}>{label(value, lifecycleKeys, t)}</option>)}</select></label>
        <label>{t("stage")}<select value={filters.stage} onChange={event => change("stage", event.target.value)}><option value="">{t("all")}</option>{stages.map(value => <option key={value} value={value}>{label(value, stageKeys, t)}</option>)}</select></label>
        <label>{t("observedExecutor")}<input aria-label={t("observedExecutor")} type="search" maxLength={200} value={filters.executor} onChange={event => change("executor", event.target.value)} /><small className="field-hint">{t("observedExecutorHelp")}</small></label>
        <label>{t("outcomeContains")}<input aria-label={t("outcomeContains")} type="search" maxLength={80} value={filters.outcome} onChange={event => change("outcome", event.target.value)} /><small className="field-hint">{t("outcomeContainsHelp")}</small></label>
        <label>{t("updatedFrom")}<input type="date" value={filters.from} max={filters.to || undefined} onChange={event => change("from", event.target.value)} /></label><label>{t("updatedTo")}<input type="date" value={filters.to} min={filters.from || undefined} onChange={event => change("to", event.target.value)} /></label>
      </div>}
    </section>}
    {run && !visibleDetail && state !== "changed" && feedback(loadedDetailKey === detailKey ? detailState : "loading", detailFailure)}
    {visibleDetail && <section className="panel detail-panel" aria-label={`${t("ticket")} #${visibleDetail.ticket_iid}`}>
      <div className="panel-heading"><div><p className="eyebrow">{visibleDetail.project_display_name} · #{visibleDetail.ticket_iid}</p><h2>{visibleDetail.ticket_title || copy.titleUnknown}</h2></div><button className="ghost" onClick={onClose}>{t("close")}</button></div>
      <div className="next-action-panel"><h3>{copy.now}</h3><StatusBadge code={visibleDetail.lifecycle}>{visibleDetail.lifecycle === "done" ? copy.completed : visibleDetail.lifecycle === "stale" ? copy.staleJob : label(visibleDetail.lifecycle, lifecycleKeys, t)}</StatusBadge><p>{lifecycleExplanation(locale, visibleDetail.lifecycle)}</p><p>{t("stage")}: <strong>{label(visibleDetail.stage, stageKeys, t)}</strong></p><p>{reason(visibleDetail)}</p>
        <dl className="action-explanation"><div><dt>{copy.who}</dt><dd>{actor(visibleDetail)} · {visibleDetail.waiting.responsible_person || copy.personUnknown}</dd></div><div><dt>{copy.where}</dt><dd>{visibleDetail.waiting.evidence_url && visibleDetail.waiting.next_action ? <a className="primary link-button" href={visibleDetail.waiting.evidence_url} target="_blank" rel="noreferrer">{actionText(visibleDetail)} ↗</a> : copy.evidenceMissing}</dd></div><div><dt>{copy.follows}</dt><dd>{visibleDetail.waiting.next_action ? visibleDetail.lifecycle === "awaiting-approval" ? copy.afterApproval : visibleDetail.lifecycle === "parked-clarification" ? copy.afterClarification : copy.afterReview : copy.unknown}</dd></div></dl>
        <p className="muted">{t("lastActivity")}: {activity(visibleDetail)}</p>
      </div>
      <div className="button-row">{commandAllowed(visibleDetail, "retry") && <div><p className="field-hint">{copy.retryHelp}</p><button className="ghost" disabled={busy} onClick={() => void command("retry", visibleDetail)}>{t("retry")}</button></div>}{commandAllowed(visibleDetail, "cancel") && <div><p className="field-hint">{copy.cancelHelp}</p><button className="danger" disabled={busy} onClick={() => void command("cancel", visibleDetail)}>{t("cancel")}</button></div>}</div>
      <h3>{t("timeline")}</h3><p className="muted">{copy.observedTimeline}</p>{visibleDetail.timeline?.length ? <ObservedTimeline key={detailKey} events={visibleDetail.timeline} date={date} t={t} unknown={copy.unknown} /> : <p>{copy.unknown}</p>}
      <h3>{copy.artifacts}</h3><div className="button-row">{visibleDetail.ticket_url && <a className="ghost link-button" href={visibleDetail.ticket_url} target="_blank" rel="noreferrer">{t("ticket")} ↗</a>}{visibleDetail.mr_url && <a className="ghost link-button" href={visibleDetail.mr_url} target="_blank" rel="noreferrer">{t("draft")} ↗</a>}</div>{!visibleDetail.ticket_url && !visibleDetail.mr_url && <p>{copy.unknown}</p>}
      <details><summary>{copy.technical}</summary><dl className="action-explanation"><div><dt>{t("project")}</dt><dd>{visibleDetail.project_id}</dd></div><div><dt>{t("jobTerm")}</dt><dd>{visibleDetail.run_id}</dd></div><div><dt>{t("reviewRounds")} / {t("attempts")}</dt><dd>{visibleDetail.review_rounds} / {visibleDetail.stage_failures}</dd></div><div><dt>{copy.duration} / {copy.consumption}</dt><dd>{copy.unknown} · {copy.unknownTelemetry}</dd></div><div><dt>{t("coverage")}</dt><dd>{Object.entries(visibleDetail.coverage).filter(([key]) => ["ticket", "journal", "title", "last_activity"].includes(key)).map(([key, value]) => `${key}: ${value}`).join(" · ")}</dd></div></dl></details>
    </section>}
    <section className="panel" aria-label={mode === "overview" ? copy.attention : mode === "history" ? copy.history : t("jobs")}>
      {mode !== "jobs" && <h2>{mode === "overview" ? copy.attention : copy.history}</h2>}
      {mode === "history" && <p className="muted">{copy.historyHelp}</p>}
      {!visible ? feedback(dataKey === renderKey ? state : "loading", failure) : <>{visible.items.length ? table(visible.items) : <div className="empty-state" role="status">{mode === "overview" ? copy.noAttention : Object.values(selection).some(value => typeof value === "string" && value) ? t("noMatchingJobs") : t("noJobs")}</div>}{pager}</>}
    </section>
    {mode === "overview" && visible && <div className="stats-grid">
      {[{ key: "active", text: t("activeJobs"), value: visible.groups.active }, { key: "waiting", text: copy.waiting, value: visible.groups.waiting }, { key: "in-review", text: t("inReviewStatus"), value: visible.counts["in-review"] || 0 }, { key: "failed", text: t("failedJobs"), value: visible.counts.failed || 0 }].map(card =>
        <div className="stat-card overview-card" key={card.key}><span>{card.text}</span><strong>{new Intl.NumberFormat(locale).format(card.value)}</strong><small>{scope ? project?.display_name || project?.name : copy.all}</small></div>)}
    </div>}

  </div>;
}


/** Page actual events in reverse saved order without inferring progress. */
function ObservedTimeline({ events, date, t, unknown }: { events: NonNullable<Job["timeline"]>; date: (value: string | null) => string; t: Props["t"]; unknown: string }) {
  const [size, setSize] = useState<number | "all">(10);
  const [offset, setOffset] = useState(0);
  const rows = events.slice().reverse();
  const start = size === "all" ? 0 : Math.min(offset, Math.max(0, Math.ceil(rows.length / size) - 1) * size);
  const shown = size === "all" ? rows : rows.slice(start, start + size);
  return <><div className="table-scroll"><table className="timeline-table" aria-label={t("timeline")}><thead><tr><th>{t("date")}</th><th>{t("timelineEvent")}</th><th>{t("stage")}</th></tr></thead><tbody>{shown.map((event, index) => <tr key={start + index}><td>{date(event.ts)}</td><td>{event.event}</td><td>{event.stage ? label(event.stage, stageKeys, t) : unknown}</td></tr>)}</tbody></table></div>
    {rows.length > 10 && <div className="table-pagination timeline-pagination"><label>{t("rowsPerPage")}<select value={size} onChange={event => { setSize(event.target.value === "all" ? "all" : Number(event.target.value)); setOffset(0); }}>{[10, 25, 50].map(value => <option key={value} value={value}>{value}</option>)}<option value="all">{t("all")}</option></select></label><span>{start + 1}–{start + shown.length} / {rows.length}</span><div className="button-row"><button className="ghost" disabled={!start || size === "all"} onClick={() => setOffset(start - Number(size))}>{t("previous")}</button><button className="ghost" disabled={size === "all" || start + shown.length >= rows.length} onClick={() => setOffset(start + Number(size))}>{t("next")}</button></div></div>}
  </>;
}

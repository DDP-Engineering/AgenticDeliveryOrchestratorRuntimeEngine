/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ApiError, describeError } from "./errors";
import type { Locale, MessageKey } from "./i18n";
import { operationResultText } from "./ticketCopy";
import { budgetCopy, jobCopy, jobGuidance, lifecycleExplanation } from "./jobCopy";
import { ForgeMarkdown } from "./forgeMarkdown";
import { ticketCopy } from "./ticketCopy";
import { PreparationResults } from "./ExecutionPlanReview";
import { activityAge, commandAllowed, stableExecutionDrift, IncompleteJobs, readJobDetail, readJobPage, readExecutorOutput, type ExecutorOutput, type Job, type JobPage } from "./jobModel";
import { recoveryCopy } from "./recoveryCopy";
import { DataFeedback, StatusBadge } from "./Presentation";
import { startVisiblePolling } from "./polling";
import { outcomeText } from "./operationReason";
import { formatRoute } from "./routes";
import { SortHeader } from "./SortHeader";
import { readConsumption, consumptionIdentity } from "./statistics";
import type { JobConsumption } from "./metrics";
import { JobAmounts } from "./StatisticsEvidence";
import { statisticsCopy } from "./statisticsCopy";

export type JobProject = { id: string; name: string; display_name?: string; archived: boolean; paused: boolean };
type Request = <T>(path: string, method?: string, body?: unknown, csrf?: string) => Promise<T>;
type Props = {
  mode: "overview" | "jobs" | "history"; locale: Locale; projects: JobProject[]; scope: string; run?: string;
  csrf: string; request: Request; t: (key: MessageKey) => string; refresh: number;
  onOpen: (project: string, run: string) => void; onClose: () => void;
  fixedScope?: boolean;
  summaryHeader?: (evidence: JobPage | null) => ReactNode;
  admin: boolean;
};
type ReadState = "loading" | "ready" | "error" | "incomplete" | "changed";
type Operation = { id: number; status: "pending" | "running" | "succeeded" | "failed" | "uncertain"; result?: string; reason?: string; detail?: string };
type JobSort = "ticket" | "project" | "status" | "activity";
type Filters = { q: string; group: string; size: 10 | 25 | 50 | "all"; sort: JobSort; descending: boolean; offset: number };
const initialFilters = (mode: Props["mode"]): Filters => ({ q: "", group: mode === "history" ? "terminal" : "", size: 10, sort: "activity", descending: true, offset: 0 });
const lifecycleKeys: Record<string, MessageKey> = {
  working: "working", publishing: "publishingStatus", "parked-clarification": "parkedClarificationStatus",
  "awaiting-approval": "awaitingApprovalStatus", "in-review": "inReviewStatus", "handoff-pending": "handoffPendingStatus",
  "handed-off": "handedOffStatus", done: "done", failed: "failed", cancelled: "cancelled",
};
const stageKeys: Record<string, MessageKey> = { frame: "frameStage", specify: "specifyStage", design: "designStage", build: "buildStage", validate: "validateStage", done: "done", publishing: "publishingStatus" };
const label = (value: string, keys: Record<string, MessageKey>, t: Props["t"]) => keys[value] ? t(keys[value]) : value;
const normalizeFailure = (cause: unknown) => cause instanceof ApiError ? cause : new ApiError("unexpected_response");
const readOperation = (value: unknown): Operation => {
  const operation = value as Operation;
  if (!operation || !Number.isSafeInteger(operation.id) || operation.id < 1 ||
    !["pending", "running", "succeeded", "failed", "uncertain"].includes(operation.status) ||
    [operation.result, operation.reason, operation.detail].some(value => value !== undefined && typeof value !== "string")) throw new ApiError("unexpected_response");
  return operation;
};

/** Own complete scoped jobs and observed evidence; the server owns permissions and command execution. */
export function JobWorkspace(props: Props) {
  const { mode, locale, projects, scope, run, csrf, request, t, refresh, onOpen, onClose, fixedScope } = props;
  const copy = jobCopy[locale];
  const compactOverview = mode === "overview";
  const [filters, setFilters] = useState<Filters>(() => initialFilters(mode));
  const [page, setPage] = useState<JobPage | null>(null);
  const [activePage, setActivePage] = useState<JobPage | null>(null);
  const [state, setState] = useState<ReadState>("loading");
  const [failure, setFailure] = useState<unknown>(null);
  const [detail, setDetail] = useState<Job | null>(null);
  const [detailState, setDetailState] = useState<ReadState>("loading");
  const [detailFailure, setDetailFailure] = useState<unknown>(null);
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
  const unreadable = visible?.unreadable_projects ?? [];
  const visibleDetail = loadedDetailKey === detailKey && detailState === "ready" && ids.split(",").includes(scope) && state !== "changed" ? detail : null;
  const consumptionProjects = [...new Set([...(visible?.items.map(job => job.project_id) ?? []), ...(visibleDetail ? [visibleDetail.project_id] : [])])].sort().join(",");
  const consumptionKey = JSON.stringify([consumptionProjects, ids, renderKey, detailKey]);
  const [consumption, setConsumption] = useState<{ key: string; state: "loading" | "ready" | "error"; jobs: JobConsumption[] }>({ key: "", state: "loading", jobs: [] });
  const statisticsText = statisticsCopy[locale];
  const consumptionView = (job: Job, full = false) => {
    if (consumption.key !== consumptionKey || consumption.state !== "ready") return <>
      <DataFeedback state={consumption.key === consumptionKey ? consumption.state : "loading"} t={t} />
      {consumption.key === consumptionKey && consumption.state === "error" &&
        <button className="ghost" onClick={() => setReload(value => value + 1)}>{copy.refreshConsumption}</button>}
    </>;
    const usage = consumption.jobs.find(row => consumptionIdentity(row) === consumptionIdentity(job));
    return usage ? <JobAmounts job={usage} locale={locale} admin={props.admin} t={t} compact={!full} /> : <span>{statisticsText.unavailable}</span>;
  };
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value)) : copy.unknown;
  const change = (key: keyof Filters, value: string | number) => setFilters(current => ({ ...current, [key]: value, offset: 0 }));
  const busy = submitting || operation !== null && ["pending", "running"].includes(operation.status);

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; commandGeneration.current += 1; }; }, []);
  useEffect(() => {
    if (compactOverview) return;
    let active = true, sequence = 0;
    const fetchUsage = async () => {
      const current = ++sequence;
      setConsumption({ key: consumptionKey, state: "loading", jobs: [] });
      try {
        // Jobs show lifetime consumption only; reporting periods belong to Statistics.
        const lifetime = { from: "", through: "", timezone: "UTC", granularity: "day" } as const;
        const values = await Promise.all(consumptionProjects.split(",").filter(Boolean).map(async id => {
          if (!ids.split(",").includes(id)) throw new ApiError("unexpected_response");
          return readConsumption(await request(`/projects/${encodeURIComponent(id)}/usage?timezone=UTC&granularity=day`), id, lifetime, props.admin);
        }));
        if (active && current === sequence) setConsumption({ key: consumptionKey, state: "ready", jobs: values.flatMap(value => value.jobs ?? []) });
      } catch { if (active && current === sequence) setConsumption({ key: consumptionKey, state: "error", jobs: [] }); }
    };
    void fetchUsage(); const stop = startVisiblePolling(() => void fetchUsage(), 30000);
    return () => { active = false; stop(); };
  }, [consumptionKey, refresh, reload]);
  useEffect(() => { commandGeneration.current += 1; setOperation(null); setOperationError(null); setCommandStatusError(false); submitLock.current = false; setSubmitting(false); }, [scope]);

  useEffect(() => {
    let active = true, sequence = 0;
    if (offset > 0 && revision.current.key !== baseKey) { setFilters(current => ({ ...current, offset: 0 })); return; }
    const fetchPage = async (background = false) => {
      const current = ++sequence;
      if (!compactOverview || !background) setState("loading");
      setDataKey(renderKey); setFailure(null);
      const query = new URLSearchParams({ limit: String(filters.size), offset: String(offset) });
      if (scope) query.set("project_id", scope);
      if (compactOverview) { query.set("overview", "true"); query.set("attention", "true"); }
      for (const [key, value] of Object.entries({ q: filters.q.trim(), status_group: filters.group })) if (value) query.set(key, value);
      if (mode !== "overview") { query.set("sort", filters.sort); query.set("order", filters.descending ? "desc" : "asc"); }
      if (offset > 0) query.set("snapshot", revision.current.snapshot);
      try {
        const authorized = ids.split(",").filter(id => !scope || id === scope);
        const result = readJobPage(await request(`/jobs-page?${query}`), authorized, compactOverview);
        if (result.offset !== offset) throw new ApiError("unexpected_response");
        let activeResult: JobPage | null = null;
        if (compactOverview) {
          const activeQuery = new URLSearchParams({ overview: "true", limit: "all", offset: "0", status_group: "active" });
          if (scope) activeQuery.set("project_id", scope);
          activeResult = readJobPage(await request(`/jobs-page?${activeQuery}`), authorized, true);
          if (activeResult.offset !== 0 || activeResult.items.length !== activeResult.total ||
            activeResult.items.some(row => !["working", "publishing"].includes(row.lifecycle))) throw new ApiError("unexpected_response");
          if ((result.unreadable_projects ?? []).slice().sort().join() !==
            (activeResult.unreadable_projects ?? []).slice().sort().join()) throw new ApiError("job_snapshot_changed");
        }
        if (!active || sequence !== current) return;
        revision.current = { key: baseKey, snapshot: result.snapshot };
        setPage(result); setActivePage(activeResult); setState("ready");
      } catch (cause) {
        if (!active || sequence !== current) return;
        setPage(null); setActivePage(null);
        setState(cause instanceof IncompleteJobs ? "incomplete" : cause instanceof ApiError && cause.code === "job_snapshot_changed" ? "changed" : "error");
        setFailure(normalizeFailure(cause));
      }
    };
    void fetchPage();
    const stop = startVisiblePolling(() => void fetchPage(true), 15000);
    return () => { active = false; stop(); };
  }, [renderKey, refresh, reload]);

  useEffect(() => {
    if (!run || !scope || !ids.split(",").includes(scope)) { setDetail(null); return; }
    let active = true, sequence = 0;
    const fetchDetail = async (background = false) => {
      const current = ++sequence;
      if (!background) { setDetail(null); setDetailState("loading"); }
      setDetailFailure(null); setLoadedDetailKey(detailKey);
      try {
        const result = readJobDetail(await request(`/jobs/${encodeURIComponent(scope)}/${encodeURIComponent(run)}`), scope, run);
        if (active && sequence === current) { setDetail(result); setDetailState("ready"); }
      } catch (cause) {
        if (active && sequence === current) { setDetailState(cause instanceof IncompleteJobs ? "incomplete" : "error"); setDetailFailure(normalizeFailure(cause)); }
      }
    };
    void fetchDetail();
    const stop = startVisiblePolling(() => void fetchDetail(true), 15000);
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

  const command = async (action: "retry" | "cancel" | "restart", job: Job) => {
    if (submitLock.current || busy || !project || project.archived || !commandAllowed(job, action)) return;
    if (action === "cancel" && !window.confirm(copy.cancelConfirm)) return;
    if (action === "restart" && !window.confirm(recoveryCopy[locale].confirm.replace("{ticket}", String(job.ticket_iid)))) return;
    submitLock.current = true; setSubmitting(true); setOperationError(null); setCommandStatusError(false);
    const generation = commandGeneration.current;
    try {
      const current = readOperation(await request(`/projects/${encodeURIComponent(scope)}/operations/${action}`, "POST",
        { run_id: job.run_id, idempotency_key: crypto.randomUUID(),
          ...(action === "restart" ? { confirmed: true, state_revision: job.state_revision } : action === "cancel" ? { confirmed: true } : {}) }, csrf));
      if (mounted.current && generation === commandGeneration.current) setOperation(current);
    } catch (cause) { if (mounted.current && generation === commandGeneration.current) setOperationError(cause); }
    finally { if (mounted.current && generation === commandGeneration.current) { submitLock.current = false; setSubmitting(false); } }
  };
  const feedback = (status: ReadState, cause: unknown) => status === "incomplete" || status === "changed" ?
    <section className="panel data-feedback" role="alert"><div><h2>{status === "incomplete" ? copy.incomplete : copy.changed}</h2><p>{status === "incomplete" ? copy.incompleteHelp : copy.changedHelp}</p><button className="ghost" onClick={() => { revision.current = { key: "", snapshot: "" }; setFilters(current => ({ ...current, offset: 0 })); setReload(value => value + 1); }}>{copy.reload}</button></div></section> :
    <><DataFeedback state={status === "loading" ? "loading" : "error"} t={t} />{cause && status !== "loading" ? <p className="muted">{describeError(locale, cause)}</p> : null}</>;
  const reason = (job: Job) => job.waiting.reason === "candidate_approval_requested" ? copy.approvalReason : job.waiting.reason === "draft_review_open" ? copy.reviewReason : job.waiting.reason || job.outcome || jobGuidance(locale, job.lifecycle).reason;
  const actionText = (job: Job) => job.waiting.next_action === "answer_question_on_ticket" ? copy.openQuestion : job.waiting.next_action === "review_candidate_on_ticket" ? copy.openApproval : copy.openReview;
  const actor = (job: Job) => ({ human_responder: copy.responder, human_approver: copy.approver, human_reviewer: copy.reviewer }[job.waiting.responsible_role || ""] ||
    (job.lifecycle === "parked-clarification" ? copy.responder : ["working", "publishing"].includes(job.lifecycle) ? copy.system : ["failed", "stale", "handoff-pending"].includes(job.lifecycle) ? copy.operator : copy.unknown));
  const activity = (job: Job) => <><time dateTime={job.last_activity_at || undefined}>{date(job.last_activity_at)}</time>{activityAge(job.last_activity_at) !== "recent" && <small className="field-hint">{job.last_activity_at ? copy.oldActivity : copy.missingActivity}</small>}</>;
  // Inside a project hub, job links address the hub's Jobs tab so new tabs and copied links stay there.
  const jobHref = (job: Job) => fixedScope ? formatRoute({ view: "projectDetails", project: job.project_id, tab: "jobs", run: job.run_id }) :
    formatRoute({ view: "jobs", project: job.project_id, run: job.run_id });
  const open = (event: React.MouseEvent<HTMLAnchorElement>, job: Job) => { if (event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) { event.preventDefault(); onOpen(job.project_id, job.run_id); } };
  // A new column starts newest-first for activity and A-Z otherwise; the same column flips direction.
  const sortBy = (key: JobSort) => setFilters(current => ({ ...current, sort: key, descending: current.sort === key ? !current.descending : key === "activity", offset: 0 }));
  const heading = (key: JobSort, label: string) => <SortHeader label={label} sortKey={key} activeKey={filters.sort} descending={filters.descending} onSort={sortBy} />;
  const table = (rows: Job[]) => <div className="table-scroll"><table className="action-jobs-table"><thead><tr>{heading("ticket", t("ticket"))}{heading("project", t("project"))}{heading("status", t("status"))}{heading("activity", t("lastActivity"))}<th>{copy.consumption}</th></tr></thead><tbody>{rows.map(job => <tr key={`${job.project_id}/${job.run_id}`}>
    <td><a className="strong" href={jobHref(job)} onClick={event => open(event, job)}>#{job.ticket_iid} · {job.ticket_title || copy.titleUnknown}</a></td>
    <td>{job.project_display_name}{job.project_archived && <small className="field-hint">{t("archived")}</small>}</td>
    <td><StatusBadge code={job.lifecycle}>{job.lifecycle === "done" ? copy.completed : job.lifecycle === "stale" ? copy.staleJob : label(job.lifecycle, lifecycleKeys, t)}</StatusBadge><small className="field-hint">{t("stage")}: {label(job.stage, stageKeys, t)}</small>{job.waiting.next_action && job.waiting.evidence_url && <a href={job.waiting.evidence_url} target="_blank" rel="noreferrer">{actionText(job)} ↗</a>}</td>
    <td><time dateTime={job.last_activity_at || undefined}>{date(job.last_activity_at)}</time></td><td>{consumptionView(job)}</td>
  </tr>)}</tbody></table></div>;
  const compactTable = (rows: Job[]) => <div className="table-scroll"><table className="overview-jobs-table"><thead><tr><th>{t("jobTerm")}</th><th>{t("status")}</th><th>{copy.details}</th></tr></thead><tbody>{rows.map(job => <tr key={`${job.project_id}/${job.run_id}`}>
    <td><a className="strong" href={jobHref(job)} onClick={event => open(event, job)}>{job.ticket_title || copy.titleUnknown}</a><small className="field-hint">{job.project_display_name} · #{job.ticket_iid}{job.project_archived ? ` · ${t("archived")}` : ""}</small></td>
    <td><StatusBadge code={job.lifecycle}>{job.lifecycle === "stale" ? copy.staleJob : label(job.lifecycle, lifecycleKeys, t)}</StatusBadge></td>
    <td><a className="ghost link-button" href={jobHref(job)} onClick={event => open(event, job)}>{copy.details}</a></td>
  </tr>)}</tbody></table></div>;
  const pager = visible && <div className="table-pagination"><label>{t("rowsPerPage")}<select value={filters.size} onChange={event => change("size", event.target.value === "all" ? "all" : Number(event.target.value))}>{[10, 25, 50].map(size => <option key={size} value={size}>{size}</option>)}<option value="all">{t("all")}</option></select></label><span>{visible.total === 0 ? "0" : `${offset + 1}–${Math.min(offset + visible.items.length, visible.total)}`} / {visible.total}</span><div className="button-row"><button className="ghost" disabled={offset === 0} onClick={() => setFilters(current => ({ ...current, offset: Math.max(0, offset - visible.limit) }))}>{t("previous")}</button><button className="ghost" disabled={offset + visible.items.length >= visible.total || filters.size === "all"} onClick={() => setFilters(current => ({ ...current, offset: offset + visible.limit }))}>{t("next")}</button></div></div>;

  return <div className={`job-workspace${compactOverview ? " overview-workspace" : ""}${props.summaryHeader ? " project-summary-window" : ""}`}>
    {props.summaryHeader?.(unreadable.length ? null : visible)}
    {/* Scope selection lives with the page; worker status appears only when it needs attention. */}
    {["unavailable", "error"].includes(worker) && <div className="overview-controls"><span className="worker-evidence alert" role="status">{worker === "unavailable" ? copy.workerUnavailable : copy.workerError}</span></div>}
    {!!operationError && <p className="alert" role="alert">{describeError(locale, operationError)}</p>}
    {operation && <div className={`notice command-result command-${operation.status}`} role="status">#{operation.id} · {copy[operation.status === "pending" ? "queued" : operation.status]}{(operation.reason ? outcomeText(locale, operation) : operationResultText(operation.result || "", locale)) && <p>{(operation.reason ? outcomeText(locale, operation) : operationResultText(operation.result || "", locale))}</p>}{operation.status !== "succeeded" && operation.detail && <pre className="operation-detail" tabIndex={0}>{operation.detail}</pre>}{operation.status === "pending" && <p>{t("workerQueueHelp")}</p>}{commandStatusError && <p>{copy.commandError}</p>}</div>}
    {mode !== "overview" && <section className="panel compact"><div className="job-filters job-basic-filters"><label htmlFor="job-search">{copy.search}<input id="job-search" type="search" maxLength={80} value={filters.q} onChange={event => change("q", event.target.value)} aria-describedby="job-search-help" /></label><label>{t("status")}<select value={filters.group} onChange={event => change("group", event.target.value)}><option value="">{t("all")}</option>{["active", "waiting", "review", "terminal"].map(group => <option key={group} value={group}>{group === "active" ? t("activeJobs") : group === "waiting" ? copy.waiting : group === "review" ? t("inReviewStatus") : copy.terminal}</option>)}</select></label></div><p id="job-search-help" className="field-hint">{copy.searchHelp}</p>
    </section>}
    {run && !visibleDetail && state !== "changed" && feedback(loadedDetailKey === detailKey ? detailState : "loading", detailFailure)}
    {visibleDetail && <section className="panel detail-panel" aria-label={`${t("ticket")} #${visibleDetail.ticket_iid}`}>
      <div className="panel-heading"><div><p className="eyebrow">{visibleDetail.project_display_name} · #{visibleDetail.ticket_iid}</p><h2>{visibleDetail.ticket_title || copy.titleUnknown}</h2></div><button className="ghost" onClick={onClose}>{t("close")}</button></div>
      <div className="next-action-panel"><h3>{copy.now}</h3><StatusBadge code={visibleDetail.lifecycle}>{visibleDetail.lifecycle === "done" ? copy.completed : visibleDetail.lifecycle === "stale" ? copy.staleJob : label(visibleDetail.lifecycle, lifecycleKeys, t)}</StatusBadge><p>{lifecycleExplanation(locale, visibleDetail.lifecycle)}</p><p>{t("stage")}: <strong>{label(visibleDetail.stage, stageKeys, t)}</strong></p>{visibleDetail.lifecycle === "parked-clarification" && visibleDetail.waiting.reason ?
          <ForgeMarkdown source={visibleDetail.waiting.reason} imageLabel={ticketCopy[locale].imageNotLoaded} codeLabel={ticketCopy[locale].code} tableLabel={ticketCopy[locale].table} /> : <p>{reason(visibleDetail)}</p>}
        {visibleDetail.stage_failures > 0 && <p className="notice" role="status">{copy.stageFailures.replace("{count}", String(visibleDetail.stage_failures))}</p>}
        <dl className="action-explanation"><div><dt>{copy.who}</dt><dd>{actor(visibleDetail)}{visibleDetail.waiting.responsible_person ? ` · ${visibleDetail.waiting.responsible_person}` : visibleDetail.waiting.responsible_role ? ` · ${copy.personUnknown}` : ""}</dd></div><div><dt>{copy.where}</dt><dd>{visibleDetail.waiting.evidence_url && visibleDetail.waiting.next_action ? <a className="primary link-button" href={visibleDetail.waiting.evidence_url} target="_blank" rel="noreferrer">{actionText(visibleDetail)} ↗</a> : jobGuidance(locale, visibleDetail.lifecycle).where}</dd></div><div><dt>{copy.follows}</dt><dd>{visibleDetail.waiting.next_action ? visibleDetail.lifecycle === "awaiting-approval" ? copy.afterApproval : visibleDetail.lifecycle === "parked-clarification" ? copy.afterClarification : copy.afterReview : jobGuidance(locale, visibleDetail.lifecycle).follows}</dd></div></dl>
        <p className="muted">{t("lastActivity")}: {activity(visibleDetail)}</p>
      </div>
      <div className="button-row">{commandAllowed(visibleDetail, "retry") && <div><p className="field-hint">{copy.retryHelp}</p><button className="ghost" disabled={busy} onClick={() => void command("retry", visibleDetail)}>{t("retry")}</button></div>}{commandAllowed(visibleDetail, "cancel") && <div><p className="field-hint">{copy.cancelHelp}</p><button className="danger" disabled={busy} onClick={() => void command("cancel", visibleDetail)}>{t("cancel")}</button></div>}</div>
      {stableExecutionDrift(visibleDetail) && <p role="note">{recoveryCopy[locale].drift}</p>}
      {commandAllowed(visibleDetail, "restart") && <div><p className="field-hint">{recoveryCopy[locale].help}</p><button className="danger" disabled={busy} onClick={() => void command("restart", visibleDetail)}>{recoveryCopy[locale].restart}</button></div>}
      {visibleDetail.budget && <section className="job-budgets" aria-label={budgetCopy[locale].title}>
        <h3>{budgetCopy[locale].title}</h3>
        <dl className="action-explanation">
          <div><dt>{budgetCopy[locale].launches}</dt><dd>{visibleDetail.budget.launches} / {visibleDetail.budget.max_launches ?? "—"}</dd></div>
          <div><dt>{budgetCopy[locale].active}</dt><dd>{Math.floor(visibleDetail.budget.active_seconds)} / {visibleDetail.budget.max_active_seconds ?? "—"}</dd></div>
        </dl>
        {visibleDetail.budget.availability === "unavailable" ? <p className="notice" role="status">{budgetCopy[locale].unavailable}</p> :
          (visibleDetail.budget.launches / visibleDetail.budget.max_launches >= .9 || visibleDetail.budget.active_seconds / visibleDetail.budget.max_active_seconds >= .9) &&
          <p className="notice" role="status">{visibleDetail.budget.launches >= visibleDetail.budget.max_launches || visibleDetail.budget.active_seconds >= visibleDetail.budget.max_active_seconds ? budgetCopy[locale].reached : budgetCopy[locale].near}</p>}
        <p className="field-hint">{budgetCopy[locale].timing}</p>
        {props.admin && !visibleDetail.project_archived && <a href={formatRoute({view:"projectDetails",project:visibleDetail.project_id,tab:"configuration"})}>{budgetCopy[locale].settings}</a>}
      </section>}
      <h3>{copy.consumption}</h3>{consumptionView(visibleDetail, true)}
      {visibleDetail.preparation && <PreparationResults evidence={visibleDetail.preparation} locale={locale} />}
      <h3>{t("timeline")}</h3><p className="muted">{copy.observedTimeline}</p>{visibleDetail.timeline?.length ? <ObservedTimeline key={detailKey} events={visibleDetail.timeline} date={date} t={t} unknown={copy.unknown} /> : <p>{copy.unknown}</p>}
      <h3>{copy.artifacts}</h3><div className="button-row">{visibleDetail.ticket_url && <a className="ghost link-button" href={visibleDetail.ticket_url} target="_blank" rel="noreferrer">{t("ticket")} ↗</a>}{visibleDetail.mr_url && <a className="ghost link-button" href={visibleDetail.mr_url} target="_blank" rel="noreferrer">{t("draft")} ↗</a>}</div>{!visibleDetail.ticket_url && !visibleDetail.mr_url && <p>{copy.unknown}</p>}
      <ExecutorOutputView key={`output:${detailKey}`} job={visibleDetail} locale={locale} request={request} t={t} />
      <details><summary>{copy.technical}</summary><dl className="action-explanation"><div><dt>{t("project")}</dt><dd>{visibleDetail.project_id}</dd></div><div><dt>{t("jobTerm")}</dt><dd>{visibleDetail.run_id}</dd></div><div><dt>{t("reviewRounds")} / {t("attempts")}</dt><dd>{visibleDetail.review_rounds} / {visibleDetail.stage_failures}</dd></div><div><dt>{t("coverage")}</dt><dd>{Object.entries(visibleDetail.coverage).filter(([key]) => ["ticket", "journal", "title", "last_activity"].includes(key)).map(([key, value]) => `${key}: ${value}`).join(" · ")}</dd></div></dl></details>
    </section>}
    <div className={props.summaryHeader ? "panel summary-job-window" : undefined}>
    <section className="panel" aria-label={mode === "overview" ? copy.attention : mode === "history" ? copy.history : t("jobs")}>
      {mode !== "jobs" && <h2>{mode === "overview" ? copy.attention : copy.history}</h2>}
      {mode === "history" && <p className="muted">{copy.historyHelp}</p>}
      {projects.filter(item => unreadable.includes(item.id)).map(item => <p key={item.id} className="alert" role="alert">
        <strong>{item.display_name || item.name}</strong>{" · "}{describeError(locale, new ApiError("run_state_corrupt"))}
      </p>)}
      {!visible ? feedback(dataKey === renderKey ? state : "loading", failure) : <>{visible.items.length ? compactOverview ? compactTable(visible.items) : table(visible.items) : unreadable.length === 0 && <div className="empty-state" role="status">{mode === "overview" ? copy.noAttention : (selection.q.trim() || selection.group !== initialFilters(mode).group) ? t("noMatchingJobs") : t("noJobs")}</div>}{(!compactOverview || visible.total > 10) && pager}</>}
    </section>
    {compactOverview && visible && activePage && (activePage.items.length > 0 || unreadable.length === 0) && <section className="panel" aria-label={t("activeJobs")}><h2>{t("activeJobs")}</h2>{activePage.items.length ? compactTable(activePage.items) : <div className="empty-state" role="status">{copy.noActive}</div>}</section>}

    </div>
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


/** Fetch on demand, discarding completions after the selected job is unmounted. */
function ExecutorOutputView({job, locale, request, t}: {job:Job;locale:Locale;request:Request;t:Props["t"]}) {
  const [state,setState]=useState<"idle"|"loading"|"ready"|"changed"|"error">("idle");
  const [output,setOutput]=useState<ExecutorOutput|null>(null);
  const generation=useRef(0);
  useEffect(()=>()=>{generation.current++;},[]);
  const load=async()=>{
    const current=++generation.current;
    setState("loading");
    try {
      const value=readExecutorOutput(await request(`/jobs/${encodeURIComponent(job.project_id)}/${encodeURIComponent(job.run_id)}/executor-output`),job.project_id,job.run_id);
      if(current===generation.current){setOutput(value);setState("ready");}
    }catch(cause){
      if(current===generation.current){
        if(cause instanceof ApiError && ["authentication_required","password_change_required","project_not_found","run_not_found"].includes(cause.code)) setOutput(null);
        setState(cause instanceof ApiError && cause.code==="job_snapshot_changed"?"changed":"error");
      }
    }
  };
  const copy=jobCopy[locale];
  const stale=output && (state!=="ready" || output.state_revision!==job.state_revision);
  return <section className="executor-output">
    <button className="ghost" disabled={state==="loading"} onClick={()=>void load()}>{copy.executorOutput}</button>
    {state!=="idle" && <p className="field-hint">{copy.outputHelp}</p>}
    {state==="loading" && <p role="status">{t("loadingData")}</p>}
    {state==="error" && <p role="alert">{copy.outputFailed}</p>}
    {state==="changed" && <p role="status">{copy.outputChanged} <button className="text-button" onClick={()=>void load()}>{t("retry")}</button></p>}
    {stale && <p className="notice" role="status">{copy.outputStale}</p>}
    {output?.in_progress && <p role="status">{copy.outputRunning}</p>}
    {output?.availability==="missing" && <p role="status">{copy.outputMissing}</p>}
    {output?.availability==="observed" && <>
      <p className="executor-output-summary">
        <strong>{output.timed_out ? copy.timedOut : output.exit_code===0 ? copy.outputSucceeded : copy.outputUnsuccessful}</strong>
        <span>{t("attempts")}: {output.attempt}</span>
        {output.stage && <span>{t("stage")}: {label(output.stage,stageKeys,t)}</span>}
        <time dateTime={output.recorded_at}>{new Intl.DateTimeFormat(locale,{dateStyle:"medium",timeStyle:"medium"}).format(new Date(output.recorded_at))}</time>
        <span>{copy.exitCode}: {output.exit_code}</span>
      </p>
      {!output.stderr && <p className="field-hint">{copy.outputNoStderr}</p>}
      {!output.stdout && !output.stderr && <p className="field-hint">{copy.outputEmpty}</p>}
      {(["stdout","stderr"] as const).map(stream=>output[stream] && <details key={stream}>
        <summary>{stream}</summary><pre className="operation-detail" tabIndex={0}>{output[stream]}</pre>
      </details>)}
    </>}
  </section>;
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { Fragment, useEffect, useRef, useState } from "react";
import { ApiError, describeError } from "./errors";
import { messages, type Locale } from "./i18n";
import { safeEvidenceLink } from "./jobModel";
import { startVisiblePolling } from "./polling";
import { keptLabels, outcomeText } from "./operationReason";
import { jobCopy } from "./jobCopy";
import { fill, ticketCopy, operationResultText } from "./ticketCopy";
import { HelpLink } from "./HelpCenter";
import { CONTEXT_TOPICS } from "./help/topics.ts";
import { ForgeMarkdown } from "./forgeMarkdown";
import type { TicketBodyMode } from "./ticketPreferences";

type Request = <T>(path: string, method?: string, body?: unknown, csrf?: string) => Promise<T>;
type TicketJob = { run_id: string; lifecycle: string };
type Ticket = {
  iid: number; title: string; description: string; labels: string[]; author: string; web_url: string;
  updated_at: string; startable: boolean; reason: string | null; job: TicketJob | null;
  can_start: boolean; blocked_by: string | null; adds_ready_label: boolean; needs_priority: boolean;
};
type TicketList = { read_at: string; truncated: boolean; ready_label: string; priority_labels: string[]; tickets: Ticket[] };
type StartResult = { operation_id: number; status: Operation["status"]; labels_added: string[] };
type Comment = { author: string; created_at: string; body: string };
type Operation = { id: number; status: "pending" | "running" | "succeeded" | "failed" | "uncertain"; result?: string; reason?: string; detail?: string };
type StopResult = { cancel_operation_id: number | null; ready_label: "removed" | "absent" | "failed"; ready_label_error: string | null };
/** A notice follows one queued operation; `labels` are those its Start added to the ticket. */
type Notice = { lines: string[]; operation?: Operation; labels?: string[] };
type CommentState = { state: "loading" } | { state: "ready"; comments: Comment[] } | { state: "error"; error: unknown };
type Project = { id: string; name: string; display_name?: string; archived: boolean };
type Props = {
  /** One project in the hub or for a selected scope; every authorized project for All projects. */
  projects: Project[]; showProject?: boolean; locale: Locale; csrf: string; request: Request;
  bodyMode: TicketBodyMode; modeBusy: boolean; onBodyMode: (mode: TicketBodyMode) => void;
};
/** One ticket row keeps its owning project and that project's label policy. */
type Row = { key: string; project: Project; list: TicketList; ticket: Ticket };
type StartRequest = { row: Row; addsReady: boolean; needsPriority: boolean };

const FINISHED = ["done", "failed", "cancelled", "handed-off", "handoff-pending"];
const REASONS = ["epic", "not_open", "missing_ready_label", "held", "excluded", "has_job", "missing_priority_label", "missing_acceptance_criteria"];
// Stopped pickup blocks Start without changing a ticket's pickup eligibility.
const PICKUP_PAUSED = "pickup_paused";
const BLOCKERS = [...REASONS, PICKUP_PAUSED];
const text = (value: unknown): value is string => typeof value === "string";
const pickupPaused = (failure: unknown) => failure instanceof ApiError && failure.code === "ticket_not_startable" && failure.detail === PICKUP_PAUSED;
const invalid = () => new ApiError("unexpected_response");

/** Validate the ticket list: forge-derived values arrive as untrusted strings. */
function readTicketList(value: unknown): TicketList {
  const list = value as TicketList;
  if (!list || !text(list.read_at) || typeof list.truncated !== "boolean" || !text(list.ready_label) || !Array.isArray(list.tickets) ||
    !Array.isArray(list.priority_labels) || !list.priority_labels.every(text)) throw invalid();
  for (const item of list.tickets) {
    const job = item?.job;
    if (!item || !Number.isSafeInteger(item.iid) || item.iid < 1 || ![item.title, item.description, item.author, item.web_url, item.updated_at].every(text) ||
      !Array.isArray(item.labels) || !item.labels.every(text) || typeof item.startable !== "boolean" ||
      !(item.reason === null || REASONS.includes(item.reason)) || item.startable !== (item.reason === null) ||
      !(job === null || job && text(job.run_id) && text(job.lifecycle)) ||
      ![item.can_start, item.adds_ready_label, item.needs_priority].every(flag => typeof flag === "boolean") ||
      !item.can_start && (item.adds_ready_label || item.needs_priority) ||
      !(item.blocked_by === null ? item.can_start : !item.can_start && BLOCKERS.includes(item.blocked_by))) throw invalid();
  }
  return list;
}

/** Mark the tickets Start could prepare as blocked once the server reports stopped pickup. */
function withPickupPaused(items: Array<{ project: Project; list: TicketList }>, projectId: string) {
  return items.map(item => item.project.id !== projectId ? item : { ...item, list: { ...item.list, tickets: item.list.tickets.map(ticket =>
    ticket.can_start ? { ...ticket, can_start: false, blocked_by: PICKUP_PAUSED, adds_ready_label: false, needs_priority: false } : ticket) } });
}

function readComments(value: unknown, iid: number): Comment[] {
  const data = value as { iid: number; comments: Comment[] };
  if (!data || data.iid !== iid || !Array.isArray(data.comments) || !data.comments.every(item => item && [item.author, item.created_at, item.body].every(text))) throw invalid();
  return data.comments;
}

function readOperation(value: unknown): Operation {
  const operation = value as Operation;
  if (!operation || !Number.isSafeInteger(operation.id) || operation.id < 1 ||
    !["pending", "running", "succeeded", "failed", "uncertain"].includes(operation.status) ||
    [operation.result, operation.reason, operation.detail].some(value => value !== undefined && !text(value))) throw invalid();
  return operation;
}

function readStart(value: unknown): StartResult {
  const result = value as StartResult;
  if (!result || !Number.isSafeInteger(result.operation_id) || result.operation_id < 1 ||
    !["pending", "running", "succeeded", "failed", "uncertain"].includes(result.status) ||
    !Array.isArray(result.labels_added) || !result.labels_added.every(text)) throw invalid();
  return result;
}

function readStop(value: unknown): StopResult {
  const result = value as StopResult;
  if (!result || !(result.cancel_operation_id === null || Number.isSafeInteger(result.cancel_operation_id)) ||
    !["removed", "absent", "failed"].includes(result.ready_label) || !(result.ready_label_error === null || text(result.ready_label_error))) throw invalid();
  return result;
}

/** Tickets sub-tab: reads open forge tickets only on request and starts or stops one at a time. */
export function TicketWorkspace({ projects, showProject = false, locale, csrf, request, bodyMode, modeBusy, onBodyMode }: Props) {
  const copy = ticketCopy[locale];
  const t = messages[locale];
  const [lists, setLists] = useState<Array<{ project: Project; list: TicketList }> | null>(null);
  const [reading, setReading] = useState(false);
  const [readErrors, setReadErrors] = useState<Array<{ project: Project; error: unknown }>>([]);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [comments, setComments] = useState<Record<string, CommentState>>({});
  const [confirm, setConfirm] = useState<Row | null>(null);
  const [starting, setStarting] = useState<StartRequest | null>(null);
  const [priority, setPriority] = useState("");
  // A read returns up to 500 tickets; they are shown a page at a time.
  const [size, setSize] = useState<number | "all">(10);
  const [offset, setOffset] = useState(0);
  // Tickets started since the last read stay unavailable for Start until the next read.
  const [queued, setQueued] = useState<string[]>([]);
  const [busyProjects, setBusyProjects] = useState<Set<string>>(new Set());
  const busyFor=(id:string)=>busyProjects.has(id);
  const setBusy=(id:string,busy:boolean)=>setBusyProjects(previous=>{const next=new Set(previous);if(busy)next.add(id);else next.delete(id);return next;});
  const [notice, setNotice] = useState<Notice | null>(null);
  const [commandStatusError, setCommandStatusError] = useState(false);
  const [actionError, setActionError] = useState<{ error: unknown; project: Project } | null>(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const base = (project: Project) => `/projects/${encodeURIComponent(project.id)}`;
  const projectName = (project: Project) => project.display_name || project.name;
  // Several projects can share ticket numbers, so messages name the project when more than one is shown.
  const named = (row: Row, line: string) => showProject ? `${projectName(row.project)} · ${line}` : line;
  const when = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date);
  };

  const read = async () => {
    if (reading) return;
    setReading(true); setReadErrors([]); setStarting(null); setConfirm(null);
    const results = await Promise.allSettled(projects.map(async project => ({ project, list: readTicketList(await request(`${base(project)}/tickets`)) })));
    if (mounted.current) {
      setLists(results.flatMap(result => result.status === "fulfilled" ? [result.value] : []));
      setReadErrors(results.flatMap((result, index) => result.status === "rejected" ? [{ project: projects[index], error: result.reason }] : []));
      setComments({}); setExpanded([]); setQueued([]); setOffset(0); setReading(false);
    }
  };
  const rows: Row[] = (lists ?? []).flatMap(({ project, list }) => list.tickets.map(ticket => ({ key: `${project.id}:${ticket.iid}`, project, list, ticket })));
  const latestRead = (lists ?? []).map(item => item.list.read_at).sort().at(-1);
  const pages = size === "all" ? 1 : Math.max(1, Math.ceil(rows.length / size));
  const first = size === "all" ? 0 : Math.min(offset, (pages - 1) * size);
  const shown = size === "all" ? rows : rows.slice(first, first + size);
  // A confirmation belongs to a visible row; another page closes it.
  useEffect(() => { setStarting(null); setConfirm(null); }, [first, size]);

  const toggle = async (row: Row) => {
    if (expanded.includes(row.key)) { setExpanded(items => items.filter(item => item !== row.key)); return; }
    setExpanded(items => [...items, row.key]);
    if (comments[row.key]?.state === "ready") return;
    setComments(items => ({ ...items, [row.key]: { state: "loading" } }));
    try {
      const value = readComments(await request(`${base(row.project)}/tickets/${row.ticket.iid}/comments`), row.ticket.iid);
      if (mounted.current) setComments(items => ({ ...items, [row.key]: { state: "ready", comments: value } }));
    } catch (cause) { if (mounted.current) setComments(items => ({ ...items, [row.key]: { state: "error", error: cause } })); }
  };

  // Start adds missing ready/priority labels server-side; a label change is confirmed first.
  const start = async (row: Row, chosen = "") => {
    const iid = row.ticket.iid;
    if (busyFor(row.project.id) || row.project.archived) return;
    setBusy(row.project.id,true); setCommandStatusError(false); setActionError(null); setNotice(null); setStarting(null);
    try {
      const result = readStart(await request(`${base(row.project)}/tickets/${iid}/start`, "POST", { idempotency_key: crypto.randomUUID(), ...(chosen ? { priority: chosen } : {}) }, csrf));
      const lines = [...(result.labels_added.length ? [fill(copy.labelsAdded, { labels: result.labels_added.join(", ") })] : []), named(row, fill(copy.startQueued, { iid, id: result.operation_id })), copy.startEffect];
      if (mounted.current) { setNotice({ lines, operation: { id: result.operation_id, status: result.status }, labels: result.labels_added }); setQueued(items => [...items, row.key]); }
    } catch (cause) {
      if (!mounted.current) return;
      setActionError({ error: cause, project: row.project });
      if (pickupPaused(cause)) setLists(items => items && withPickupPaused(items, row.project.id));
    }
    finally { if (mounted.current) setBusy(row.project.id,false); }
  };
  const requestStart = (row: Row) => {
    setConfirm(null);
    if (!row.ticket.adds_ready_label && !row.ticket.needs_priority) { void start(row); return; }
    setPriority(row.list.priority_labels.at(-1) ?? "");
    setStarting({ row, addsReady: row.ticket.adds_ready_label, needsPriority: row.ticket.needs_priority });
  };

  const retry = async (row: Row) => {
    const { ticket } = row;
    if (busyFor(row.project.id) || row.project.archived || !ticket.job) return;
    setBusy(row.project.id,true); setCommandStatusError(false); setActionError(null); setNotice(null);
    try {
      const operation = readOperation(await request(`${base(row.project)}/operations/retry`, "POST", { run_id: ticket.job.run_id, idempotency_key: crypto.randomUUID() }, csrf));
      if (mounted.current) { setNotice({ lines: [named(row, fill(copy.retryQueued, { iid: ticket.iid, id: operation.id }))], operation }); setQueued(items => [...items, row.key]); }
    } catch (cause) { if (mounted.current) setActionError({ error: cause, project: row.project }); }
    finally { if (mounted.current) setBusy(row.project.id,false); }
  };

  const stop = async (row: Row) => {
    const iid = row.ticket.iid;
    if (busyFor(row.project.id) || row.project.archived) return;
    setBusy(row.project.id,true); setCommandStatusError(false); setActionError(null); setNotice(null); setConfirm(null); setStarting(null);
    try {
      const result = readStop(await request(`${base(row.project)}/tickets/${iid}/stop`, "POST", { idempotency_key: crypto.randomUUID(), confirmed: true }, csrf));
      const label = result.ready_label === "removed" ? copy.labelRemoved : result.ready_label === "absent" ? copy.labelAbsent :
        fill(copy.labelFailed, { reason: describeError(locale, new ApiError(result.ready_label_error || "unexpected_response")) });
      const cancel = result.cancel_operation_id ? fill(copy.cancelQueued, { iid, id: result.cancel_operation_id }) : fill(copy.noCancel, { iid });
      if (mounted.current) setNotice({ lines: [named(row, cancel), label], operation: result.cancel_operation_id ? { id: result.cancel_operation_id, status: "pending" } : undefined });
    } catch (cause) { if (mounted.current) setActionError({ error: cause, project: row.project }); }
    finally { if (mounted.current) setBusy(row.project.id,false); }
  };

  // Follow the queued operation until the worker settles it.
  const operation = notice?.operation;
  useEffect(() => {
    if (!operation || !["pending", "running"].includes(operation.status)) return;
    let active = true, sequence = 0;
    const poll = async () => {
      const currentSequence = ++sequence;
      try {
        const current = readOperation(await request(`/operations/${operation.id}`));
        if (current.id !== operation.id) throw invalid();
        if (active && currentSequence === sequence) { setCommandStatusError(false); setNotice(value => value && value.operation?.id === current.id ? { ...value, operation: current } : value); }
      } catch { if (active && currentSequence === sequence) setCommandStatusError(true); }
    };
    void poll();
    const stopPolling = startVisiblePolling(() => void poll(), 2000);
    return () => { active = false; stopPolling(); };
  }, [operation?.id, operation?.status]);

  const status = ({ ticket, list }: Row) => ticket.job ? fill(copy.job, { lifecycle: ticket.job.lifecycle }) :
    ticket.blocked_by === PICKUP_PAUSED ? copy.pickup_paused :
    ticket.reason === null ? copy.startable : fill(copy[(ticket.blocked_by ?? ticket.reason) as keyof typeof copy] as string, { label: list.ready_label });
  const pausedLists = (lists ?? []).filter(({ list }) => list.tickets.some(ticket => ticket.blocked_by === PICKUP_PAUSED));
  const failure = notice?.operation && ["failed", "uncertain"].includes(notice.operation.status) ? notice.operation : null;
  const stoppable = ({ ticket, list }: Row) => !!ticket.job && !FINISHED.includes(ticket.job.lifecycle) || ticket.labels.includes(list.ready_label);
  const columns = showProject ? 6 : 5;
  const body = (source: string) => bodyMode === "source"
    ? <pre className="ticket-source forge-scroll" tabIndex={0} role="region" aria-label={copy.markdownSource}>{source}</pre>
    : <ForgeMarkdown source={source} imageLabel={copy.imageNotLoaded} codeLabel={copy.code} tableLabel={copy.table} />;

  return <div className="ticket-workspace">
    <section className="panel compact">
      <div className="panel-heading ticket-toolbar">
        <button className="primary" type="button" onClick={() => void read()} disabled={reading || projects.length === 0} aria-busy={reading}>{reading ? copy.reading : copy.read}</button>
        {latestRead && <span className="muted">{fill(copy.lastRead, { time: when(latestRead) })}</span>}
        <HelpLink topic={CONTEXT_TOPICS.tickets} locale={locale} />
      </div>
      {readErrors.map(({ project, error }) => <p className="alert" role="alert" key={project.id}>{showProject ? `${projectName(project)}: ` : ""}{describeError(locale, error)}</p>)}
      {actionError !== null && <p className="alert" role="alert">{showProject ? `${projectName(actionError.project)}: ` : ""}{pickupPaused(actionError.error) ? copy.pickupStopped : describeError(locale, actionError.error)}</p>}
      {pausedLists.map(({ project }) => <p className="notice ticket-pickup-stopped" role="status" key={project.id}>{showProject ? `${projectName(project)}: ` : ""}{copy.pickupStopped}</p>)}
      {notice && <div className="notice ticket-notice" role="status">{notice.lines.map(line => <p key={line}>{line}</p>)}
        {notice.operation && <p className="muted">#{notice.operation.id} · {copy.operation[notice.operation.status]}{(notice.operation.reason ? outcomeText(locale, notice.operation) : operationResultText(notice.operation.result || "", locale)) ? ` · ${(notice.operation.reason ? outcomeText(locale, notice.operation) : operationResultText(notice.operation.result || "", locale))}` : ""}</p>}
        {notice.operation?.status === "pending" && <p>{messages[locale].workerQueueHelp}</p>}
        {commandStatusError && <p role="alert">{jobCopy[locale].commandError}</p>}
        {failure?.detail && <pre className="operation-detail" tabIndex={0}>{failure.detail}</pre>}
        {keptLabels(notice.operation, notice.labels).length > 0 && <p>{fill(copy.labelsKept, { labels: keptLabels(notice.operation, notice.labels).join(", ") })}</p>}
      </div>}

      {!lists && !reading && readErrors.length === 0 && <p className="muted">{copy.notRead}</p>}
      {lists && lists.length > 0 && rows.length === 0 && <p className="muted">{copy.none}</p>}
      {(lists ?? []).filter(item => item.list.truncated).map(({ project }) => <p className="muted" key={project.id}>{showProject ? `${projectName(project)}: ` : ""}{copy.truncated}</p>)}
      {rows.length > 0 && <div className="table-scroll"><table className="ticket-table">
        <thead><tr><th>{copy.number}</th>{showProject && <th>{copy.project}</th>}<th>{copy.title}</th><th>{copy.labels}</th><th>{copy.status}</th><th>{copy.actions}</th></tr></thead>
        <tbody>{shown.map(row => {
          const { ticket, project } = row;
          const link = safeEvidenceLink(ticket.web_url);
          const open = expanded.includes(row.key);
          const thread = comments[row.key];
          const detailId = `ticket-detail-${project.id}-${ticket.iid}`;
          return <Fragment key={row.key}>
            <tr className="ticket-row">
              <td>#{ticket.iid}</td>
              {showProject && <td>{projectName(project)}</td>}
              <td>{link ? <a href={link} target="_blank" rel="noopener noreferrer">{ticket.title}</a> : <span>{ticket.title}</span>}</td>
              <td><span className="ticket-labels">{ticket.labels.map(label => <span className="ticket-label" key={label}>{label}</span>)}</span></td>
              <td>{status(row)}</td>
              <td><div className="button-row ticket-actions">
                {ticket.job?.lifecycle === "failed"
                  ? <button className="primary" type="button" disabled={busyFor(project.id) || project.archived || queued.includes(row.key)} onClick={() => void retry(row)}>{copy.retry}</button>
                  : <button className="primary" type="button" disabled={busyFor(project.id) || project.archived || !ticket.can_start || queued.includes(row.key)} onClick={() => requestStart(row)}>{copy.start}</button>}
                <button className="ghost" type="button" disabled={busyFor(project.id) || project.archived || !stoppable(row)} onClick={() => { setStarting(null); setConfirm(row); }}>{copy.stop}</button>
                <button className="ghost" type="button" aria-expanded={open} aria-controls={detailId} onClick={() => void toggle(row)}>{open ? copy.hide : copy.details}</button>
              </div></td>
            </tr>
            {/* A confirmation opens directly under the ticket it acts on. */}
            {starting?.row.key === row.key && <tr className="ticket-confirm-row"><td colSpan={columns}><div className="ticket-start-confirm" role="alertdialog" aria-label={copy.startTicket}>
              <p>{named(row, fill(copy.startConfirm, { iid: ticket.iid, labels: [...(starting.addsReady ? [row.list.ready_label] : []), ...(starting.needsPriority && priority ? [priority] : [])].join(", ") }))}</p>
              {starting.needsPriority && <label>{copy.priority}<select aria-label={copy.priority} value={priority} onChange={event => setPriority(event.target.value)}>{row.list.priority_labels.map(label => <option key={label} value={label}>{label}</option>)}</select></label>}
              <div className="button-row"><button className="primary" type="button" disabled={busyFor(row.project.id) || starting.needsPriority && !priority} onClick={() => void start(row, starting.needsPriority ? priority : "")}>{copy.startTicket}</button><button className="ghost" type="button" onClick={() => setStarting(null)}>{copy.keep}</button></div>
            </div></td></tr>}
            {confirm?.key === row.key && <tr className="ticket-confirm-row"><td colSpan={columns}><div className="ticket-stop-confirm" role="alertdialog" aria-label={copy.stopTicket}>
              <p>{named(row, fill(copy.stopConfirm, { iid: ticket.iid, label: row.list.ready_label }))}</p>
              <div className="button-row"><button className="danger" type="button" disabled={busyFor(row.project.id)} onClick={() => void stop(row)}>{copy.stopTicket}</button><button className="ghost" type="button" onClick={() => setConfirm(null)}>{copy.keepRunning}</button></div>
            </div></td></tr>}
            {open && <tr className="ticket-detail-row"><td colSpan={columns}><div className="ticket-detail" id={detailId}>
              <div className="ticket-body-heading">
                <h3>{copy.description}</h3>
                <label htmlFor={`${detailId}-mode`}>{copy.bodyDisplay}
                  <select id={`${detailId}-mode`} value={bodyMode} aria-disabled={modeBusy} aria-busy={modeBusy}
                    onChange={event => { if (!modeBusy) onBodyMode(event.target.value as TicketBodyMode); }}>
                    <option value="rendered">{copy.rendered}</option><option value="source">{copy.markdownSource}</option>
                  </select>
                </label>
                {modeBusy && <small role="status">{copy.savingMode}</small>}
              </div>
              {ticket.description ? body(ticket.description) : <p className="ticket-text">{copy.noDescription}</p>}
              <h3>{copy.comments}</h3>
              {(!thread || thread.state === "loading") && <p className="muted" role="status">{copy.loadingComments}</p>}
              {thread?.state === "error" && <p className="alert" role="alert">{describeError(locale, thread.error)}</p>}
              {thread?.state === "ready" && (thread.comments.length === 0 ? <p className="muted">{copy.noComments}</p> :
                <ol className="ticket-comments">{thread.comments.map((comment, index) => <li key={`${comment.created_at}-${index}`}>
                  <small className="muted">{fill(copy.by, { author: comment.author, time: when(comment.created_at) })}</small>
                  {body(comment.body)}
                </li>)}</ol>)}
            </div></td></tr>}
          </Fragment>;
        })}</tbody>
      </table></div>}
      {rows.length > 10 && <div className="table-pagination ticket-pagination">
        <label>{t.rowsPerPage}<select value={size} onChange={event => { setSize(event.target.value === "all" ? "all" : Number(event.target.value)); setOffset(0); }}>
          {[10, 25, 50].map(value => <option key={value} value={value}>{value}</option>)}<option value="all">{t.all}</option>
        </select></label>
        <span>{first + 1}–{first + shown.length} / {rows.length}</span>
        {size !== "all" && <>
          <span>{fill(copy.page, { page: first / size + 1, pages })}</span>
          <div className="button-row">
            <button className="ghost" type="button" disabled={first === 0} onClick={() => setOffset(first - size)}>{t.previous}</button>
            <button className="ghost" type="button" disabled={first + shown.length >= rows.length} onClick={() => setOffset(first + size)}>{t.next}</button>
          </div>
        </>}
      </div>}
    </section>
  </div>;
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { Fragment, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ApiError, describeError } from "./errors";
import { messages, type Locale } from "./i18n";
import { safeEvidenceLink } from "./jobModel";
import { createReadController, startVisiblePolling, type ReadController } from "./polling";
import { keptLabels, outcomeText } from "./operationReason";
import { jobCopy } from "./jobCopy";
import { fill, ticketCopy, operationResultText } from "./ticketCopy";
import { HelpLink } from "./HelpCenter";
import { CONTEXT_TOPICS } from "./help/topics.ts";
import { ForgeMarkdown } from "./forgeMarkdown";
import type { TicketBodyMode } from "./ticketPreferences";

type Request = <T>(path: string, method?: string, body?: unknown, csrf?: string, signal?: AbortSignal) => Promise<T>;
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
type Notice = { projectId: string; authority: number; lines: string[]; operation?: Operation; labels?: string[] };
type CommentState = { state: "loading" } | { state: "ready"; comments: Comment[] } | { state: "error"; error: unknown };
type Project = { id: string; name: string; display_name?: string; archived: boolean };
type Props = {
  /** One project in the hub or for a selected scope; every authorized project for All projects. */
  projects: Project[]; principal: string; showProject?: boolean; locale: Locale; csrf: string; request: Request;
  bodyMode: TicketBodyMode; modeBusy: boolean; onBodyMode: (mode: TicketBodyMode) => void;
  /** Notify the metadata owner after an observed result; never reread forge bodies. */
  onOperationComplete: (projectId: string) => void;
};
/** One ticket row keeps its owning project and that project's label policy. */
type Row = { key: string; project: Project; list: TicketList; ticket: Ticket };
type StartRequest = { row: Row; addsReady: boolean; needsPriority: boolean };
/** One principal/project authority owns read and response lifetimes. */
type ProjectOwner = { binding: string; epoch: number; reads: Set<ReadController>; writes: Set<AbortController> };
type TicketSnapshot = { project: Project; list: TicketList; principal: string; authority: number };

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
function withPickupPaused<T extends { project: Project; list: TicketList }>(items: T[], projectId: string) {
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
export function TicketWorkspace({ projects, principal, showProject = false, locale, csrf, request, bodyMode, modeBusy, onBodyMode, onOperationComplete }: Props) {
  const copy = ticketCopy[locale];
  const t = messages[locale];
  const [lists, setLists] = useState<TicketSnapshot[] | null>(null);
  const [reading, setReading] = useState(false);
  const [scopeRemoved, setScopeRemoved] = useState(false);
  const [readErrors, setReadErrors] = useState<Array<{ project: Project; error: unknown; principal: string }>>([]);
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
  const [busy, setBusy] = useState(false);
  const [noticeValue, setNotice] = useState<Notice | null>(null);
  const [commandStatusError, setCommandStatusError] = useState(false);
  const [actionError, setActionError] = useState<{ error: unknown; project: Project; authority: number } | null>(null);
  const mounted = useRef(true);
  const owners = useRef(new Map<string, ProjectOwner>());
  const epoch = useRef(0);
  const readBatch = useRef(0);
  const readingNow = useRef(false);
  const writing = useRef<ProjectOwner | null>(null);
  const commentReads = useRef(new Set<string>());
  const [reviewEpoch, setReviewEpoch] = useState<number | null>(null);
  const live = useRef({ projects, principal, csrf });
  live.current = { projects, principal, csrf };
  const binding = (project: Project) => JSON.stringify([live.current.principal, live.current.csrf, project.id, project.name, project.archived]);
  const currentOwner = (projectId: string) => {
    const project = live.current.projects.find(item => item.id === projectId), owner = owners.current.get(projectId);
    return project && owner?.binding === binding(project) ? owner : null;
  };
  const valid = (projectId: string, owner: ProjectOwner) => mounted.current && currentOwner(projectId) === owner;
  const visibleLists = (lists ?? []).filter(item => item.principal === principal && projects.some(project => project.id === item.project.id && project.name === item.project.name));
  const notice = noticeValue && currentOwner(noticeValue.projectId)?.epoch === noticeValue.authority ? noticeValue : null;
  const scope = JSON.stringify([principal, csrf, projects.map(project => [project.id, project.name, project.archived]).sort()]);
  useLayoutEffect(() => {
    for (const [id, owner] of owners.current) {
      if (currentOwner(id) === owner) continue;
      owner.reads.forEach(reader => reader.dispose()); owner.writes.forEach(controller => controller.abort());
      owners.current.delete(id);
      if (writing.current === owner) { writing.current = null; setBusy(false); }
    }
    projects.forEach(project => {
      if (!owners.current.has(project.id)) owners.current.set(project.id, { binding: binding(project), epoch: ++epoch.current, reads: new Set(), writes: new Set() });
    });
    // Permanently prune removed identities. Archive alone retains readable bodies
    // but its changed authority cannot restore a previously invalidated review.
    if (lists?.some(item => item.principal !== principal || !projects.some(project => project.id === item.project.id && project.name === item.project.name))) setScopeRemoved(true);
    setLists(items => items && items.filter(item => item.principal === principal && projects.some(project => project.id === item.project.id && project.name === item.project.name)));
    setReadErrors(items => items.filter(item => item.principal === principal && projects.some(project => project.id === item.project.id && project.name === item.project.name)));
    setComments(items => Object.fromEntries(Object.entries(items).filter(([key]) => projects.some(project => key.startsWith(`${project.id}:`)))));
    if (starting && currentOwner(starting.row.project.id)?.epoch !== reviewEpoch || confirm && currentOwner(confirm.project.id)?.epoch !== reviewEpoch) setReviewEpoch(null);
  }, [scope]);
  useLayoutEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false; readBatch.current++;
      owners.current.forEach(owner => { owner.reads.forEach(reader => reader.dispose()); owner.writes.forEach(controller => controller.abort()); });
      owners.current.clear();
    };
  }, []);
  /** Explicit reads are finite and cancellable, never automatically scheduled. */
  const readOwned = async <T,>(project: Project, owner: ProjectOwner, path: string, validate: (value: unknown) => T): Promise<T> => {
    let result: T | undefined, failure: unknown = invalid(), succeeded = false;
    const reader = createReadController<T>({ key: `${owner.binding}:${path}`, deadlineMs: 30000,
      read: async signal => validate(await request(path, "GET", undefined, undefined, signal)),
      publish: snapshot => {
        if (snapshot.refreshing) return;
        if (snapshot.status === "ready") { result = snapshot.data!; succeeded = true; }
        if (snapshot.status === "error") failure = snapshot.error;
      },
    });
    owner.reads.add(reader);
    try {
      await reader.refresh();
      if (!valid(project.id, owner)) throw new DOMException("Superseded", "AbortError");
      if (!succeeded) throw failure;
      return result!;
    } finally { owner.reads.delete(reader); reader.dispose(); }
  };
  const operationPending = !!notice?.operation && ["pending", "running"].includes(notice.operation.status);
  const base = (project: Project) => `/projects/${encodeURIComponent(project.id)}`;
  const projectName = (project: Project) => project.display_name || project.name;
  // Several projects can share ticket numbers, so messages name the project when more than one is shown.
  const named = (row: Row, line: string) => showProject ? `${projectName(row.project)} · ${line}` : line;
  const when = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date);
  };

  const read = async () => {
    if (readingNow.current) return;
    readingNow.current = true;
    const batch = ++readBatch.current;
    owners.current.forEach(owner => owner.reads.forEach(reader => reader.dispose()));
    commentReads.current.clear();
    const captured = projects.flatMap(project => { const owner = currentOwner(project.id); return owner ? [{ project, owner }] : []; });
    setReading(true); setScopeRemoved(false); setReadErrors([]); setStarting(null); setConfirm(null);
    const results = await Promise.allSettled(captured.map(async ({ project, owner }) => ({ project, principal, authority: owner.epoch, list: await readOwned(project, owner, `${base(project)}/tickets`, readTicketList) })));
    if (mounted.current && batch === readBatch.current) {
      setLists(results.flatMap((result, index) => result.status === "fulfilled" && valid(captured[index].project.id, captured[index].owner) ? [result.value] : []));
      setReadErrors(results.flatMap((result, index) => result.status === "rejected" && valid(captured[index].project.id, captured[index].owner) ? [{ project: captured[index].project, error: result.reason, principal }] : []));
      setComments({}); setExpanded([]); setQueued([]); setOffset(0); setReading(false); readingNow.current = false;
    }
  };
  const rows: Row[] = visibleLists.flatMap(({ project: captured, list }) => {
    const project = projects.find(project => project.id === captured.id)!;
    return list.tickets.map(ticket => ({ key: `${project.id}:${ticket.iid}`, project, list, ticket }));
  });
  const latestRead = visibleLists.map(item => item.list.read_at).sort().at(-1);
  const pages = size === "all" ? 1 : Math.max(1, Math.ceil(rows.length / size));
  const first = size === "all" ? 0 : Math.min(offset, (pages - 1) * size);
  const shown = size === "all" ? rows : rows.slice(first, first + size);
  // A confirmation belongs to a visible row; another page closes it.
  useEffect(() => { setStarting(null); setConfirm(null); }, [first, size]);

  const liveRow = (row: Row) => rows.some(item => item.key === row.key && item.ticket === row.ticket);
  const canAct = (row: Row) => liveRow(row) && visibleLists.some(item => item.list === row.list && item.authority === currentOwner(row.project.id)?.epoch) && !live.current.projects.find(project => project.id === row.project.id)?.archived;
  const reviewValid = (row: Row) => canAct(row) && currentOwner(row.project.id)?.epoch === reviewEpoch;
  const toggle = async (row: Row) => {
    const owner = currentOwner(row.project.id), batch = readBatch.current;
    if (!owner || !liveRow(row)) return;
    if (expanded.includes(row.key)) { setExpanded(items => items.filter(item => item !== row.key)); return; }
    setExpanded(items => [...items, row.key]);
    if (comments[row.key]?.state === "ready" || commentReads.current.has(row.key)) return;
    commentReads.current.add(row.key);
    setComments(items => ({ ...items, [row.key]: { state: "loading" } }));
    try {
      const value = await readOwned(row.project, owner, `${base(row.project)}/tickets/${row.ticket.iid}/comments`, value => readComments(value, row.ticket.iid));
      if (valid(row.project.id, owner) && batch === readBatch.current) setComments(items => ({ ...items, [row.key]: { state: "ready", comments: value } }));
    } catch (cause) { if (valid(row.project.id, owner) && batch === readBatch.current) setComments(items => ({ ...items, [row.key]: { state: "error", error: cause } })); }
    finally { commentReads.current.delete(row.key); }
  };

  /** A write is not retried or timed out here; abort only ends obsolete UI ownership. */
  const beginWrite = (row: Row) => {
    if (writing.current || operationPending || !canAct(row) || readingNow.current) return null;
    const owner = currentOwner(row.project.id)!;
    const controller = new AbortController(); owner.writes.add(controller); writing.current = owner;
    setBusy(true); setCommandStatusError(false); setActionError(null); setNotice(null);
    return { owner, controller };
  };
  const finishWrite = ({ owner, controller }: { owner: ProjectOwner; controller: AbortController }) => {
    owner.writes.delete(controller);
    if (writing.current === owner) { writing.current = null; if (mounted.current) setBusy(false); }
  };
  // Start adds missing ready/priority labels server-side; a label change is confirmed first.
  const start = async (row: Row, chosen = "") => {
    if (!row.ticket.can_start || (starting?.row.key === row.key && !reviewValid(row)) || (chosen && !row.list.priority_labels.includes(chosen))) return;
    const write = beginWrite(row); if (!write) return;
    const { owner, controller } = write, iid = row.ticket.iid;
    setStarting(null);
    try {
      const result = readStart(await request(`${base(row.project)}/tickets/${iid}/start`, "POST", { idempotency_key: crypto.randomUUID(), ...(chosen ? { priority: chosen } : {}) }, csrf, controller.signal));
      const lines = [...(result.labels_added.length ? [fill(copy.labelsAdded, { labels: result.labels_added.join(", ") })] : []), named(row, fill(copy.startQueued, { iid, id: result.operation_id })), copy.startEffect];
      if (valid(row.project.id, owner)) {
        setNotice({ projectId: row.project.id, authority: owner.epoch, lines, operation: { id: result.operation_id, status: result.status }, labels: result.labels_added });
        setQueued(items => [...items, row.key]);
        if (!["pending", "running"].includes(result.status)) onOperationComplete(row.project.id);
      }
    } catch (cause) {
      if (!valid(row.project.id, owner)) return;
      setActionError({ error: cause, project: row.project, authority: owner.epoch });
      if (pickupPaused(cause)) setLists(items => items && withPickupPaused(items, row.project.id));
    } finally { finishWrite(write); }
  };
  const requestStart = (row: Row) => {
    if (!canAct(row) || !row.ticket.can_start || writing.current || operationPending) return;
    setConfirm(null); setReviewEpoch(currentOwner(row.project.id)!.epoch);
    if (!row.ticket.adds_ready_label && !row.ticket.needs_priority) { void start(row); return; }
    setPriority(row.list.priority_labels.at(-1) ?? "");
    setStarting({ row, addsReady: row.ticket.adds_ready_label, needsPriority: row.ticket.needs_priority });
  };

  const retry = async (row: Row) => {
    const { ticket } = row;
    if (ticket.job?.lifecycle !== "failed") return;
    const write = beginWrite(row); if (!write) return;
    const { owner, controller } = write;
    try {
      const operation = readOperation(await request(`${base(row.project)}/operations/retry`, "POST", { run_id: ticket.job.run_id, idempotency_key: crypto.randomUUID() }, csrf, controller.signal));
      if (valid(row.project.id, owner)) {
        setNotice({ projectId: row.project.id, authority: owner.epoch, lines: [named(row, fill(copy.retryQueued, { iid: ticket.iid, id: operation.id }))], operation });
        setQueued(items => [...items, row.key]);
        if (!["pending", "running"].includes(operation.status)) onOperationComplete(row.project.id);
      }
    } catch (cause) { if (valid(row.project.id, owner)) setActionError({ error: cause, project: row.project, authority: owner.epoch }); }
    finally { finishWrite(write); }
  };

  const stop = async (row: Row) => {
    if (!reviewValid(row) || !stoppable(row)) return;
    const write = beginWrite(row); if (!write) return;
    const { owner, controller } = write, iid = row.ticket.iid;
    setConfirm(null); setStarting(null);
    try {
      const result = readStop(await request(`${base(row.project)}/tickets/${iid}/stop`, "POST", { idempotency_key: crypto.randomUUID(), confirmed: true }, csrf, controller.signal));
      const label = result.ready_label === "removed" ? copy.labelRemoved : result.ready_label === "absent" ? copy.labelAbsent :
        fill(copy.labelFailed, { reason: describeError(locale, new ApiError(result.ready_label_error || "unexpected_response")) });
      const cancel = result.cancel_operation_id ? fill(copy.cancelQueued, { iid, id: result.cancel_operation_id }) : fill(copy.noCancel, { iid });
      if (valid(row.project.id, owner)) {
        setNotice({ projectId: row.project.id, authority: owner.epoch, lines: [named(row, cancel), label], operation: result.cancel_operation_id ? { id: result.cancel_operation_id, status: "pending" } : undefined });
        if (!result.cancel_operation_id) onOperationComplete(row.project.id);
      }
    } catch (cause) { if (valid(row.project.id, owner)) setActionError({ error: cause, project: row.project, authority: owner.epoch }); }
    finally { finishWrite(write); }
  };

  // One bounded owner follows pending -> running without restarting or queuing
  // ticks. A failed status read is unknown completion, never a successful result.
  const operation = notice?.operation;
  const operationKey = operation && operationPending && notice && projects.some(project => project.id === notice.projectId)
    ? JSON.stringify([principal, csrf, notice.authority, notice.projectId, operation.id]) : "";
  const liveOperation = useRef({ key: operationKey, request, onOperationComplete });
  liveOperation.current = { key: operationKey, request, onOperationComplete };
  useLayoutEffect(() => {
    if (!operationKey || !operation || !notice) return;
    const key = operationKey, id = operation.id, projectId = notice.projectId;
    const reader = createReadController<Operation>({ key, deadlineMs: 30000,
      read: async signal => {
        const current = readOperation(await liveOperation.current.request(`/operations/${id}`, "GET", undefined, undefined, signal));
        if (current.id !== id) throw invalid();
        return current;
      },
      publish: snapshot => {
        if (key !== liveOperation.current.key || snapshot.refreshing) return;
        if (snapshot.status === "error") { setCommandStatusError(true); return; }
        if (snapshot.status !== "ready" || !snapshot.data) return;
        const current = snapshot.data;
        setCommandStatusError(false);
        setNotice(value => value?.operation?.id === id && value.projectId === projectId ? { ...value, operation: current } : value);
        if (!["pending", "running"].includes(current.status)) liveOperation.current.onOperationComplete(projectId);
      },
    });
    void reader.refresh();
    const stopPolling = startVisiblePolling(() => { void reader.refresh(); }, 2000);
    return () => { stopPolling(); reader.dispose(); };
  }, [operationKey]);

  const status = ({ ticket, list }: Row) => ticket.job ? fill(copy.job, { lifecycle: ticket.job.lifecycle }) :
    ticket.blocked_by === PICKUP_PAUSED ? copy.pickup_paused :
    ticket.reason === null ? copy.startable : fill(copy[(ticket.blocked_by ?? ticket.reason) as keyof typeof copy] as string, { label: list.ready_label });
  const pausedLists = visibleLists.filter(({ list }) => list.tickets.some(ticket => ticket.blocked_by === PICKUP_PAUSED));
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
      {scopeRemoved && <p className="notice" role="status">{describeError(locale, new ApiError("project_not_found"))}</p>}
      {readErrors.filter(item => item.principal === principal && projects.some(project => project.id === item.project.id && project.name === item.project.name)).map(({ project, error }) => <p className="alert" role="alert" key={project.id}>{showProject ? `${projectName(project)}: ` : ""}{describeError(locale, error)}</p>)}
      {actionError !== null && currentOwner(actionError.project.id)?.epoch === actionError.authority && <p className="alert" role="alert">{showProject ? `${projectName(actionError.project)}: ` : ""}{pickupPaused(actionError.error) ? copy.pickupStopped : describeError(locale, actionError.error)}</p>}
      {!starting && !confirm && visibleLists.filter(item => item.authority !== currentOwner(item.project.id)?.epoch).map(({ project }) => <p className="alert" role="alert" key={project.id}>{showProject ? `${projectName(project)}: ` : ""}{copy.reviewChanged}</p>)}
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
      {visibleLists.filter(item => item.list.truncated).map(({ project }) => <p className="muted" key={project.id}>{showProject ? `${projectName(project)}: ` : ""}{copy.truncated}</p>)}
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
                  ? <button className="primary" type="button" disabled={busy || operationPending || reading || !canAct(row) || queued.includes(row.key)} onClick={() => void retry(row)}>{copy.retry}</button>
                  : <button className="primary" type="button" disabled={busy || operationPending || reading || !canAct(row) || !ticket.can_start || queued.includes(row.key)} onClick={() => requestStart(row)}>{copy.start}</button>}
                <button className="ghost" type="button" disabled={busy || operationPending || reading || !canAct(row) || !stoppable(row)} onClick={() => { if (!canAct(row)) return; setReviewEpoch(currentOwner(row.project.id)!.epoch); setStarting(null); setConfirm(row); }}>{copy.stop}</button>
                <button className="ghost" type="button" aria-expanded={open} aria-controls={detailId} onClick={() => void toggle(row)}>{open ? copy.hide : copy.details}</button>
              </div></td>
            </tr>
            {/* A confirmation opens directly under the ticket it acts on. */}
            {starting?.row.key === row.key && <tr className="ticket-confirm-row"><td colSpan={columns}><div className="ticket-start-confirm" role="alertdialog" aria-label={copy.startTicket}>
              <p>{named(row, fill(copy.startConfirm, { iid: ticket.iid, labels: [...(starting.addsReady ? [row.list.ready_label] : []), ...(starting.needsPriority && priority ? [priority] : [])].join(", ") }))}</p>
              {starting.needsPriority && <label>{copy.priority}<select aria-label={copy.priority} value={priority} onChange={event => setPriority(event.target.value)}>{row.list.priority_labels.map(label => <option key={label} value={label}>{label}</option>)}</select></label>}
              {!reviewValid(row) && <p className="alert" role="alert">{copy.reviewChanged}</p>}
              <div className="button-row"><button className="primary" type="button" disabled={busy || operationPending || !reviewValid(row) || starting.needsPriority && !priority} onClick={() => void start(row, starting.needsPriority ? priority : "")}>{copy.startTicket}</button><button className="ghost" type="button" onClick={() => setStarting(null)}>{copy.keep}</button></div>
            </div></td></tr>}
            {confirm?.key === row.key && <tr className="ticket-confirm-row"><td colSpan={columns}><div className="ticket-stop-confirm" role="alertdialog" aria-label={copy.stopTicket}>
              <p>{named(row, fill(copy.stopConfirm, { iid: ticket.iid, label: row.list.ready_label }))}</p>
              {!reviewValid(row) && <p className="alert" role="alert">{copy.reviewChanged}</p>}
              <div className="button-row"><button className="danger" type="button" disabled={busy || operationPending || !reviewValid(row)} onClick={() => void stop(row)}>{copy.stopTicket}</button><button className="ghost" type="button" onClick={() => setConfirm(null)}>{copy.keepRunning}</button></div>
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

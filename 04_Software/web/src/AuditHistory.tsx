/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { Fragment, useEffect, useRef, useState } from "react";
import { messages, type Locale } from "./i18n";
import { auditCopy } from "./auditCopy";

type Row = { id: number; actor_id: number | null; actor: string | null; action: string; project: string;
  project_id: string | null; resource_type: string | null; resource_id: string | null; created_at: string;
  phase: string | null; result: string | null; before: unknown; after: unknown; operation_id: number | null;
  base_revision: string | null; candidate_revision: string | null; correlation: string | null };
type Filters = { actor: string; project: string; type: string; from: string; to: string };
const empty: Filters = { actor: "", project: "", type: "", from: "", to: "" };

/** Validate the closed noncredential value projection before rendering transport data. */
function safeValue(value: unknown, depth = 0): boolean {
  if (depth > 10) return false;
  if (value === null || typeof value === "boolean" || typeof value === "number" && Number.isFinite(value)) return true;
  if (typeof value === "string") return ["admin", "developer", "active", "stopped", "[redacted]"].includes(value);
  if (Array.isArray(value)) return value.length <= 1000 && value.every(item => safeValue(item, depth + 1));
  if (typeof value === "object") return Object.entries(value as Record<string, unknown>).every(([key, item]) =>
    key === "project_ids" ? Array.isArray(item) && item.every(id => typeof id === "string" && /^[0-9a-f]{32}$/.test(id)) :
    ["exists", "disabled", "role", "granted", "pickup", "retention_days", "max_bytes", "value", "password_change_required"].includes(key) && safeValue(item, depth + 1));
  return false;
}
function validRow(value: unknown): value is Row {
  if (!value || typeof value !== "object") return false;
  const row = value as Row;
  return Number.isSafeInteger(row.id) && row.id > 0 && (row.actor_id === null || Number.isSafeInteger(row.actor_id) && row.actor_id > 0) &&
    (row.actor === null || typeof row.actor === "string" && /^[\p{L}\p{N}_]{1,64}$/u.test(row.actor)) &&
    typeof row.action === "string" && /^[a-z][a-z0-9-]{0,79}$/.test(row.action) &&
    typeof row.project === "string" && /^$|^[a-z0-9][a-z0-9._-]{0,63}$/.test(row.project) &&
    (row.project_id === null || typeof row.project_id === "string" && /^[0-9a-f]{32}$/.test(row.project_id)) &&
    (row.resource_id === null || typeof row.resource_id === "string" && /^[A-Za-z0-9._-]{1,160}$/.test(row.resource_id)) &&
    (row.resource_type === null || ["account", "access", "config", "project", "operation", "policy"].includes(row.resource_type)) &&
    typeof row.created_at === "string" && Number.isFinite(Date.parse(row.created_at)) && /(?:Z|[+-]00:00)$/.test(row.created_at) &&
    (row.phase === null || ["prepare", "apply", "discard"].includes(row.phase)) &&
    (row.result === null || ["prepared", "applied", "discarded", "rejected", "uncertain"].includes(row.result)) &&
    (row.operation_id === null || Number.isSafeInteger(row.operation_id) && row.operation_id > 0) &&
    [row.base_revision, row.candidate_revision, row.correlation].every(item => item === null || typeof item === "string" && /^[0-9a-f]{64}$/.test(item)) &&
    (row.result !== "applied" || row.phase === "apply") && (row.result !== "prepared" || row.phase === "prepare") &&
    (row.result !== "discarded" || row.phase === "discard") &&
    (!["uncertain", "rejected"].includes(row.result || "") || row.after === null) &&
    safeValue(row.before) && safeValue(row.after);
}

/** Like a short Git hash: the first 12 characters, with the full value on hover. */
const short = (hex: string) => <code title={hex}>{hex.slice(0, 12)}</code>;

/** Filtered server pages are isolated by principal and project via the parent key. */
export function AuditHistory({ locale, projects, fixedProject, read }: {
  locale: Locale; projects: Array<{ id: string; name: string; display_name?: string }>;
  fixedProject?: string; read: (path: string) => Promise<unknown>;
}) {
  const c = auditCopy[locale];
  const [draft, setDraft] = useState<Filters>({ ...empty, project: fixedProject || "" });
  const [filters, setFilters] = useState(draft);
  const [open, setOpen] = useState<number[]>([]);
  const [size, setSize] = useState("10");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [invalid, setInvalid] = useState(false);
  const reader = useRef(read); reader.current = read;
  useEffect(() => {
    let active = true;
    setState("loading"); setRows([]); setTotal(0);
    const query = new URLSearchParams({ limit: size, offset: String(offset) });
    if (filters.actor) query.set("actor_id", filters.actor);
    if (filters.project) query.set("project_id", filters.project);
    if (filters.type) query.set("action", filters.type);
    if (filters.from) query.set("from", filters.from + ":00Z");
    if (filters.to) query.set("to", filters.to + ":00Z");
    reader.current(`/audit-page?${query}`).then(value => {
      const page = value as { items: unknown[]; total: number; offset: number; limit: number | null };
      if (!page || !Array.isArray(page.items) || !Number.isSafeInteger(page.total) || page.total < 0 ||
          page.offset !== offset || page.limit !== (size === "all" ? null : Number(size)) ||
          page.items.length > page.total || size !== "all" && page.items.length > Number(size) ||
          page.items.some(row => !validRow(row) || filters.project && row.project_id !== filters.project) ||
          new Set(page.items.map(row => (row as Row).id)).size !== page.items.length) throw new Error("invalid evidence");
      if (active) { setRows(page.items as Row[]); setTotal(page.total); setState("ready"); }
    }).catch(() => { if (active) { setRows([]); setTotal(0); setState("error"); } });
    return () => { active = false; };
  }, [filters, size, offset, refresh]);
  const input = (key: keyof Filters, label: string, type = "text") => <label>{label}<input type={type} value={draft[key]} onChange={event => setDraft(current => ({ ...current, [key]: event.target.value }))} /></label>;
  return <section className="panel wide-panel audit-evidence" aria-label={c.title}>
    <div className="panel-heading"><h2>{c.title}</h2><button type="button" className="ghost" onClick={() => setRefresh(value => value + 1)}>{c.refresh}</button></div>
    <form className="audit-filters" onSubmit={event => {
      event.preventDefault();
      if (draft.actor && !/^[1-9][0-9]*$/.test(draft.actor) || draft.type && !/^[a-z][a-z0-9-]{0,79}$/.test(draft.type) ||
          draft.from && draft.to && draft.from >= draft.to) { setInvalid(true); return; }
      setInvalid(false); setOffset(0); setFilters({ ...draft });
    }}>
      {input("actor", c.actor, "number")}
      {!fixedProject && <label>{c.project}<select value={draft.project} onChange={event => setDraft(current => ({ ...current, project: event.target.value }))}><option value="">{c.allProjects}</option>{projects.map(project => <option key={project.id} value={project.id}>{project.display_name || project.name} · {project.id}</option>)}</select></label>}
      {input("type", c.type)}{input("from", c.from, "datetime-local")}{input("to", c.to, "datetime-local")}
      <button type="submit" className="primary">{c.apply}</button>
    </form>
    {invalid && <p role="alert">{c.invalid}</p>}
    {state === "loading" ? <p role="status">{c.loading}</p> : state === "error" ? <div role="alert"><p>{messages[locale].dataFailed}</p><p>{c.error}</p></div> : <>
      <p role="status">{total} {c.matched}</p>
      {rows.length ? <div className="table-scroll"><table><thead><tr><th>{c.who}</th><th>{c.what}</th><th>{c.when}</th><th>{c.result}</th><th>{c.evidence}</th></tr></thead><tbody>{rows.map(row => { const expanded = open.includes(row.id), detailId = `audit-detail-${row.id}`; return <Fragment key={row.id}><tr>
        <td>{row.actor || c.unknown}{row.actor_id && <small>#{row.actor_id}</small>}</td>
        <td>{row.action}<small>{row.project || row.project_id || c.unknown}</small><small>{row.resource_type} {row.resource_id}</small></td>
        <td><time dateTime={row.created_at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(row.created_at))}</time></td>
        <td><strong>{row.result ? c[row.result] : c.unknown}</strong><small>{row.phase ? c[{prepare: "preparePhase", apply: "applyPhase", discard: "discardPhase"}[row.phase] || "unknown"] : c.unknown}</small></td>
        <td><button type="button" className="text-button audit-toggle" aria-expanded={expanded} aria-controls={detailId} onClick={() => setOpen(items => expanded ? items.filter(id => id !== row.id) : [...items, row.id])}>{c.evidence}</button></td>
      </tr>
      {/* Evidence opens on its own full-width row so the table columns keep their widths. */}
      {expanded && <tr className="audit-detail-row"><td colSpan={5} id={detailId}><dl><dt>{c.before}</dt><dd>{row.before === null ? c.beforeMissing : JSON.stringify(row.before)}</dd><dt>{c.after}</dt><dd>{row.after === null ? c.afterMissing : JSON.stringify(row.after)}</dd><dt>{c.operation}</dt><dd>{row.operation_id ? `#${row.operation_id}` : row.correlation ? short(row.correlation) : c.unknown}</dd>{row.base_revision && <><dt>{c.base}</dt><dd>{short(row.base_revision)}</dd></>}{row.candidate_revision && <><dt>{c.candidate}</dt><dd>{short(row.candidate_revision)}</dd></>}</dl></td></tr>}
      </Fragment>; })}</tbody></table></div> : <p className="empty">{c.empty}</p>}
      <div className="table-pager"><label>{c.pageSize}<select value={size} onChange={event => { setSize(event.target.value); setOffset(0); }}>{["10", "25", "50", "all"].map(value => <option key={value} value={value}>{value === "all" ? c.all : value}</option>)}</select></label><button type="button" className="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - Number(size)))}>{c.previous}</button><button type="button" className="ghost" disabled={size === "all" || offset + rows.length >= total} onClick={() => setOffset(offset + Number(size))}>{c.next}</button></div>
    </>}
  </section>;
}

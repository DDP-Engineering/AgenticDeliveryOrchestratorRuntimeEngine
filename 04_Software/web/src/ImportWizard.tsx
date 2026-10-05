/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale, MessageKey } from "./i18n";
import { ApiError, describeError } from "./errors";
import { enrollmentCopy } from "./enrollmentCopy";
import { importCopy } from "./importCopy";

type Finding = { code: string; field: string; remediation: string };
type Draft = { name: string; display_name: string; description: string; config_text: string };
type Review = { name: string; display_name: string; description: string; config_path: string;
  paths: Record<string, string>; resolved_paths: Record<string, string>;
  platform: Record<string, string>; target_branch: string;
  agent: Record<string, string>; executor: { default: string; model: string; env_keys: string[]; stage_host_auth: boolean };
  container: Record<string, string> };
type Preview = { revision: string; config_revision: string; review: Review | null;
  validation: { structural_valid: boolean; issues: Finding[] }; issues: string[] };
type Evidence = { status: "failed" | "partial" | "verified"; revision: string; config_revision: string;
  checked_at: string; context: string; checks: Record<string, boolean | null | "not-checked"> };
type Created = { id: string; name: string; display_name: string; paused: boolean; pickup_state: string };
const paths = ["worktree.repo_path", "worktree.root", "state.store_root", "metrics.db_path", "metrics.export_jsonl", "metrics.html_out"];
const digest = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
const findingsValid = (v: unknown): v is Finding[] => Array.isArray(v) && v.every(x =>
  x && typeof x.code === "string" && typeof x.field === "string" && typeof x.remediation === "string");
const stringRecord = (value: unknown, keys: string[]) => value && typeof value === "object" &&
  !Array.isArray(value) && Object.keys(value).length === keys.length &&
  keys.every(key => typeof (value as Record<string, unknown>)[key] === "string");
class ImportError extends ApiError {
  constructor(code: string, readonly findings: Finding[] = []) { super(code); }
}
/** Memory-only exact enrollment; the server owns validation, probing and locked publication. */
export function ImportWizard({ locale, csrf, t, onCancel, onOpen, onCreated, registerGuard }: {
  locale: Locale; csrf: string; t: (key: MessageKey) => string; onCancel: () => void;
  onOpen: (id: string) => void; onCreated: () => void;
  registerGuard: (guard: (() => boolean) | null) => void;
}) {
  const c = importCopy[locale], e = enrollmentCopy[locale];
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Draft>({ name: "", display_name: "", description: "", config_text: "" });
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [reviewed, setReviewed] = useState<{ draft: Draft; preview: Preview } | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [failure, setFailure] = useState<unknown>(null);
  const [localFailure, setLocalFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  const [created, setCreated] = useState<Created | null>(null);
  const generation = useRef(0), operation = useRef<"read" | "preview" | "probe" | "enroll" | null>(null);
  const alive = useRef(true), dirty = useRef(false), target = useRef<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null), summary = useRef<HTMLDivElement>(null);
  const guard = () => {
    if (operation.current === "enroll") { heading.current?.focus(); return false; }
    if (!dirty.current || window.confirm(c.loss)) { dirty.current = false; return true; }
    return false;
  };
  useEffect(() => {
    registerGuard(guard);
    const unload = (event: BeforeUnloadEvent) => {
      if (dirty.current || operation.current === "enroll") { event.preventDefault(); event.returnValue = ""; }
    };
    const click = (event: MouseEvent) => {
      const link = (event.target as Element).closest?.("a[href]") as HTMLAnchorElement | null;
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.getAttribute("href")?.startsWith("#")) return;
      if (!guard()) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener("beforeunload", unload); document.addEventListener("click", click, true);
    return () => { registerGuard(null); window.removeEventListener("beforeunload", unload); document.removeEventListener("click", click, true); };
  }, [locale, registerGuard]);
  useEffect(() => { alive.current = true; return () => { alive.current = false; generation.current++; }; }, []);
  useEffect(() => {
    if (target.current) { document.getElementById(target.current)?.focus(); target.current = null; }
    else heading.current?.focus({ preventScroll: true });
  }, [step]);
  useEffect(() => { if (failure || localFailure || findings.length) summary.current?.focus(); }, [failure, localFailure, findings]);

  const invalidate = () => {
    generation.current++; setStale(true); setPreview(null); setEvidence(null); setReviewed(null);
    setFailure(null); setLocalFailure(null); setFindings([]); operation.current = null; setBusy(false);
  };
  const move = (next: number, focus?: string) => {
    if (operation.current === "enroll") return;
    if (next < step) invalidate();
    target.current = focus ?? null; setStep(next);
    if (next === step && focus) document.getElementById(focus)?.focus();
  };
  const change = (key: keyof Draft, value: string) => {
    dirty.current = true; invalidate(); setDraft(current => ({ ...current, [key]: value }));
  };
  const decode = async (source: File) => {
    if (!source.size || source.size > 524288) throw new Error("file size");
    return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(await source.arrayBuffer());
  };
  const selectFile = async (source: File | null) => {
    dirty.current = true; invalidate(); setFile(source); setDraft(current => ({ ...current, config_text: "" }));
    if (!source) return;
    const token = generation.current; operation.current = "read"; setBusy(true);
    try {
      const text = await decode(source);
      if (alive.current && token === generation.current) setDraft(current => ({ ...current, config_text: text }));
    } catch { if (alive.current && token === generation.current) setLocalFailure(c.invalidFile); }
    finally { if (alive.current && token === generation.current) { operation.current = null; setBusy(false); } }
  };
  const sourceUnchanged = async (expected: string) => {
    try { if (file && await decode(file) === expected) return true; } catch { /* unreadable source rejects confirmation */ }
    invalidate(); setLocalFailure(c.changed); setStep(0); return false;
  };
  const call = async (path: string, body: unknown) => {
    let response: Response;
    try { response = await fetch("/api/v1/projects/" + path, { method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) }); }
    catch { throw new ApiError("network_error"); }
    const value = await response.json().catch(() => { throw new ApiError("unexpected_response"); });
    if (!response.ok) {
      if (typeof value?.detail?.code !== "string") throw new ApiError("unexpected_response");
      throw new ImportError(value.detail.code, findingsValid(value.detail.issues) ? value.detail.issues : []);
    }
    return value;
  };
  const reject = (cause: unknown) => { setFailure(cause); setFindings(cause instanceof ImportError ? cause.findings : []); };
  const localValid = () => {
    const issues: Finding[] = [];
    if (!/^[a-z0-9][a-z0-9._-]{0,63}$/.test(draft.name)) issues.push({ code: "invalid_input", field: "name", remediation: e.identity });
    if (!draft.display_name || draft.display_name.trim() !== draft.display_name || draft.display_name.length > 120 ||
      /[\p{Cc}\p{Cf}]/u.test(draft.display_name)) issues.push({ code: "invalid_input", field: "display_name", remediation: e.identity });
    setFindings(issues); return !issues.length;
  };
  const inspect = async () => {
    if (operation.current || !localValid() || !file || !draft.config_text) return;
    const token = generation.current; operation.current = "preview"; setBusy(true); setFailure(null); setLocalFailure(null);
    setPreview(null); setEvidence(null); setReviewed(null);
    try {
      if (!await sourceUnchanged(draft.config_text) || token !== generation.current) return;
      const value = await call("import-preview", draft) as Preview;
      if (!alive.current || token !== generation.current) return;
      if (!digest(value?.revision) || !digest(value?.config_revision) || !findingsValid(value.validation?.issues) ||
        typeof value.validation.structural_valid !== "boolean" || !Array.isArray(value.issues) || value.issues.some(x => typeof x !== "string") ||
        value.validation.structural_valid !== (value.validation.issues.length === 0) ||
        value.issues.length !== value.validation.issues.length ||
        value.validation.structural_valid && (!value.review || value.review.name !== draft.name ||
          value.review.display_name !== draft.display_name || value.review.description !== draft.description ||
          typeof value.review.config_path !== "string" || paths.some(key => typeof value.review?.paths?.[key] !== "string" ||
            typeof value.review?.resolved_paths?.[key] !== "string") ||
          !stringRecord(value.review.platform, ["kind", "repo", "login"]) ||
          !stringRecord(value.review.agent, ["name", "slug", "email"]) ||
          !stringRecord(value.review.container, ["runtime", "image", "egress"]) ||
          typeof value.review.target_branch !== "string" || typeof value.review.executor?.stage_host_auth !== "boolean" ||
          Object.keys(value.review.executor).length !== 4 ||
          typeof value.review.executor?.default !== "string" || typeof value.review.executor?.model !== "string" ||
          !Array.isArray(value.review.executor.env_keys) || value.review.executor.env_keys.some(key =>
            typeof key !== "string" || !/^[A-Z][A-Z0-9_]{0,63}$/.test(key))))
        throw new ApiError("unexpected_response");
      setPreview(value); setFindings(value.validation.issues); setStale(false);
    } catch (cause) { if (alive.current && token === generation.current) reject(cause); }
    finally { if (alive.current && token === generation.current) { operation.current = null; setBusy(false); } }
  };
  const probe = async () => {
    if (operation.current || !preview?.validation.structural_valid) return;
    const token = generation.current; operation.current = "probe"; setBusy(true); setEvidence(null); setFailure(null);
    try {
      if (!await sourceUnchanged(draft.config_text) || token !== generation.current) return;
      const value = await call("import-check", { ...draft, revision: preview.revision }) as Evidence;
      if (!alive.current || token !== generation.current) return;
      const keys = ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "aegis_files", "model_endpoint"];
      if (!value || value.revision !== preview.revision || value.config_revision !== preview.config_revision || value.context !== "api-host" ||
        typeof value.checked_at !== "string" || !Number.isFinite(Date.parse(value.checked_at)) || !value.checks ||
        Object.keys(value.checks).length !== keys.length || keys.some(key => !(key in value.checks) ||
          typeof value.checks[key] !== "boolean" && !(key === "container_runtime" && value.checks[key] === null ||
            key === "model_endpoint" && value.checks[key] === "not-checked"))) throw new ApiError("unexpected_response");
      const status = Object.values(value.checks).some(v => v === false) ? "failed" :
        Object.values(value.checks).some(v => typeof v !== "boolean") ? "partial" : "verified";
      if (status !== value.status) throw new ApiError("unexpected_response");
      setEvidence(value);
    } catch (cause) { if (alive.current && token === generation.current) reject(cause); }
    finally { if (alive.current && token === generation.current) { operation.current = null; setBusy(false); } }
  };
  const confirm = async () => {
    if (operation.current || !reviewed || !reviewed.preview.validation.structural_valid) return;
    const token = generation.current; operation.current = "enroll"; setBusy(true); setFailure(null); setLocalFailure(null);
    try {
      if (!await sourceUnchanged(reviewed.draft.config_text) || token !== generation.current) return;
      const value = await call("import", { ...reviewed.draft, revision: reviewed.preview.revision }) as Created;
      if (!alive.current || token !== generation.current) return;
      if (!value || value.name !== reviewed.draft.name || value.display_name !== reviewed.draft.display_name ||
        !/^[0-9a-f]{32}$/.test(value.id) || value.paused !== true || value.pickup_state !== "stopped") throw new ApiError("unexpected_response");
      dirty.current = false; setDraft({ name: "", display_name: "", description: "", config_text: "" });
      setFile(null); setPreview(null); setReviewed(null); setEvidence(null); setCreated(value); setStep(5); onCreated();
    } catch (cause) { if (alive.current && token === generation.current) { setReviewed(null); setPreview(null); setEvidence(null); setStale(true); reject(cause); } }
    finally { if (alive.current && token === generation.current) { operation.current = null; setBusy(false); } }
  };
  const status = stale ? e.stale : evidence ? ({ failed: e.failedCheck, partial: e.partial, verified: e.verified })[evidence.status] : e.unverified;
  const correct = (field: string) => move(["name", "display_name", "description"].includes(field) ? 1 : 0,
    ["name", "display_name", "description"].includes(field) ? "import-" + field : "import-file");
  const locationList = (review: Review) => <dl><div><dt>{c.destination}</dt><dd>{review.config_path}</dd></div>
    {paths.map(key => <div key={key}><dt>{key}</dt><dd>{review.paths[key]}
      {review.paths[key].replaceAll("\\", "/") !== review.resolved_paths[key].replaceAll("\\", "/") &&
        <p>resolved_paths.{key}: {review.resolved_paths[key]}</p>}</dd></div>)}</dl>;
  return <section className="panel enrollment-wizard">
    <nav aria-label={e.stepsLabel}><ol className="enrollment-steps">{c.steps.map((label, index) =>
      <li key={label} aria-current={step === index ? "step" : undefined}><span>{index + 1}. {label}</span></li>)}</ol></nav>
    <h2 tabIndex={-1} ref={heading}>{c.steps[step]}</h2>
    {(failure || localFailure || findings.length > 0) && <div role="alert" tabIndex={-1} ref={summary} className="enrollment-errors">
      <h3>{e.errorTitle}</h3>{!!failure && <p>{describeError(locale, failure)} {e.failed}</p>}{localFailure && <p>{localFailure}</p>}
      <ul>{findings.map((item, index) => <li key={index}><button className="text-button" onClick={() => correct(item.field)}>
        {item.field} — {c.correction}</button><p>{item.code} · {c.correctionHelp}</p></li>)}</ul>
    </div>}
    {created ? <><p role="status">{c.stopped}</p><button className="primary" onClick={() => onOpen(created.id)}>{e.open}</button></> : <>
      <fieldset disabled={busy} className="enrollment-fields">
        {step === 0 && <><p>{c.source}</p><p>{c.exact}</p><p>{c.history}</p><p>{e.noSecrets}</p>
          <label htmlFor="import-file">{c.file}<input id="import-file" type="file" accept=".toml,.txt" aria-describedby="import-file-help"
            onChange={event => void selectFile(event.target.files?.[0] ?? null)} /></label><p id="import-file-help">{c.paths}</p>
          {file && <p>{c.selected}: {file.name}</p>}
        </>}
        {step === 1 && <><p id="import-identity-help">{e.identity}</p><p>{c.paths}</p>
          <div className="enrollment-grid">{(["name", "display_name", "description"] as const).map(key => <label htmlFor={"import-" + key} key={key}>
            {{ name: e.id, display_name: e.display, description: t("description") }[key]}
            <input id={"import-" + key} value={draft[key]} maxLength={key === "name" ? 64 : key === "display_name" ? 120 : 500}
              aria-describedby="import-identity-help" aria-invalid={findings.some(item => item.field === key)} onChange={event => change(key, event.target.value)} />
          </label>)}</div><button type="button" className="ghost" onClick={() => void inspect()}>{c.read}</button>
          {preview?.review && locationList(preview.review)}
        </>}
        {step === 2 && <><p>{c.structural}</p><button className="primary" onClick={() => void inspect()}>{c.validate}</button>
          {preview?.validation.structural_valid && <p role="status">{c.valid}</p>}<p role="status">{status}</p></>}
        {step === 3 && <><p>{e.effects}</p><p>{e.noSecrets}</p><p role="status">{status}</p>
          <button className="ghost" disabled={!preview?.validation.structural_valid} onClick={() => void probe()}>{evidence ? e.recheck : e.check}</button>
          {evidence && <><p>{e.checked}: {evidence.checked_at}</p><ul>{Object.entries(evidence.checks).map(([key, value]) =>
            <li key={key}><strong>{key}</strong>: {value === true ? e.checkPassed : value === false ? e.checkFailed : e.notChecked}
              {value !== true && <><p>{e.checkHelp[key as keyof typeof e.checkHelp]}</p>
                <button className="text-button" onClick={() => move(0, "import-file")}>{c.correction}</button></>}</li>)}</ul></>}
          <button className="primary" disabled={!preview?.validation.structural_valid} onClick={() => {
            if (!preview?.validation.structural_valid) return;
            setReviewed({ draft: structuredClone(draft), preview: structuredClone(preview) }); move(4);
          }}>{e.review}</button>
        </>}
        {step === 4 && reviewed?.preview.review && <><p>{c.exact}</p><p>{c.history}</p><p>{e.reviewHelp}</p><p>{e.status}: {status}</p>
          <div className="import-review"><section className="enrollment-review"><h3>{c.steps[1]}</h3><dl>
            {Object.entries({ name: reviewed.draft.name, display_name: reviewed.draft.display_name, description: reviewed.draft.description,
              ...reviewed.preview.review.platform, target_branch: reviewed.preview.review.target_branch }).map(([key, value]) =>
                <div key={key}><dt>{key}</dt><dd>{value || "—"}</dd></div>)}</dl></section>
            <section className="enrollment-review"><h3>{e.paths}</h3>{locationList(reviewed.preview.review)}</section>
            <section className="enrollment-review"><h3>{c.settings}</h3><dl>{Object.entries({
              ...Object.fromEntries(Object.entries(reviewed.preview.review.agent).map(([key, value]) => ["agent." + key, value])),
              ...Object.fromEntries(Object.entries(reviewed.preview.review.executor).map(([key, value]) => ["executor." + key, value])),
              ...Object.fromEntries(Object.entries(reviewed.preview.review.container).map(([key, value]) => ["container." + key, value])),
            }).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{Array.isArray(value) ? value.join(", ") : String(value)}</dd></div>)}</dl></section></div>
          <p className="enrollment-digest">{e.revision}: {reviewed.preview.revision}</p>
          <p className="enrollment-digest">SHA-256 config.toml: {reviewed.preview.config_revision}</p><p>{c.effect}</p>
          <button className="text-button" onClick={() => move(1)}>{c.change}</button>
          <button className="primary" onClick={() => void confirm()}>{c.enroll}</button>
        </>}
      </fieldset>
      <div className="button-row">{step > 0 && <button className="ghost" disabled={busy} onClick={() => move(step - 1)}>{e.back}</button>}
        {step < 3 && <button className="primary" disabled={busy || step === 0 && !draft.config_text || step === 2 && !preview?.validation.structural_valid}
          onClick={() => { if (step === 1 && !localValid()) return; move(step + 1); }}>{e.continue}</button>}
        <button className="ghost" disabled={operation.current === "enroll"} onClick={() => { if (guard()) onCancel(); }}>{e.cancel}</button>
      </div>{busy && <p role="status">{e.busy}</p>}
    </>}
  </section>;
}

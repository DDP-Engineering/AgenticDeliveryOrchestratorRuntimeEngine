/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import { ApiError, describeError } from "./errors";
import type { Locale } from "./i18n";
import { importCopy } from "./importCopy";

type Finding = { code: string; field: string };
type Candidate = { name: string; display_name: string; config_text: string; revision: string };
type Preview = Omit<Candidate, "config_text"> & {
  config_revision: string;
  validation: { structural_valid: boolean; issues: Finding[] };
  review: { name: string; display_name: string } | null;
};
const digest = (value: unknown) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const findingsValid = (value: unknown): value is Finding[] => Array.isArray(value) && value.every(item =>
  item && typeof item.code === "string" && typeof item.field === "string");

class ImportError extends ApiError {
  constructor(code: string, readonly findings: Finding[] = []) { super(code); }
}

async function readFile(file: File) {
  if (!file.size || file.size > 524288) throw new ApiError("config_invalid");
  return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(await file.arrayBuffer());
}

/** Validate each selection and confirm only its exact, server-bound candidate. */
export function RawImportDialog({ locale, csrf, onClose, onImported, registerGuard }: {
  locale: Locale; csrf: string; onClose: () => void; onImported: () => void;
  registerGuard: (guard: (() => boolean) | null) => void;
}) {
  const c = importCopy[locale];
  const [ready, setReady] = useState("");
  const [failure, setFailure] = useState<{ message: string; findings: Finding[] } | null>(null);
  const [busy, setBusy] = useState<"validate" | "import" | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const selected = useRef<File | null>(null);
  const reviewed = useRef<Candidate | null>(null);
  const validation = useRef<AbortController | null>(null);
  const alive = useRef(false), importing = useRef(false);

  useEffect(() => {
    const node = dialog.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    alive.current = true;
    node?.showModal();
    registerGuard(() => !importing.current);
    const unload = (event: BeforeUnloadEvent) => {
      if (importing.current) { event.preventDefault(); event.returnValue = ""; }
    };
    window.addEventListener("beforeunload", unload);
    return () => {
      alive.current = false;
      validation.current?.abort();
      registerGuard(null);
      window.removeEventListener("beforeunload", unload);
      node?.close();
      if (trigger?.isConnected) trigger.focus();
    };
  }, [registerGuard]);

  async function call(path: "import" | "import-preview", body: unknown, signal?: AbortSignal) {
    let response: Response;
    try {
      response = await fetch("/api/v1/projects/" + path, { method: "POST", credentials: "same-origin", cache: "no-store", signal,
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) });
    } catch { throw new ApiError("network_error"); }
    const value = await response.json().catch(() => { throw new ApiError("unexpected_response"); });
    if (!response.ok) {
      if (typeof value?.detail?.code !== "string") throw new ApiError("unexpected_response");
      throw new ImportError(value.detail.code, findingsValid(value.detail.issues) ? value.detail.issues : []);
    }
    return value;
  }

  const reject = (cause: unknown) => setFailure({
    message: cause instanceof ApiError && cause.code === "stale_import_preview" ? c.stale : describeError(locale, cause),
    findings: cause instanceof ImportError ? cause.findings : [],
  });
  const select = async (file: File | null) => {
    if (importing.current) return;
    validation.current?.abort();
    selected.current = file;
    reviewed.current = null;
    setReady(""); setFailure(null); setBusy(file ? "validate" : null);
    if (!file) return;
    const controller = new AbortController();
    validation.current = controller;
    const current = () => alive.current && validation.current === controller && !controller.signal.aborted;
    try {
      let text: string;
      try { text = await readFile(file); }
      catch {
        if (current()) setFailure({ message: c.invalidFile, findings: [] });
        return;
      }
      if (!current()) return;
      const value = await call("import-preview", { config_text: text }, controller.signal) as Preview;
      if (!current()) return;
      if (!digest(value?.revision) || !digest(value?.config_revision) ||
        typeof value.validation?.structural_valid !== "boolean" || !findingsValid(value.validation.issues) ||
        value.validation.structural_valid !== (value.validation.issues.length === 0))
        throw new ApiError("unexpected_response");
      if (!value.validation.structural_valid) throw new ImportError("config_invalid", value.validation.issues);
      if (typeof value.name !== "string" || !/^[a-z0-9][a-z0-9._-]{0,63}$/.test(value.name) ||
        typeof value.display_name !== "string" || !value.display_name || [...value.display_name].length > 120 ||
        value.display_name.trim() !== value.display_name || /[\p{Cc}\p{Cf}]/u.test(value.display_name) ||
        !value.review || value.review.name !== value.name || value.review.display_name !== value.display_name)
        throw new ApiError("unexpected_response");
      reviewed.current = { name: value.name, display_name: value.display_name, config_text: text, revision: value.revision };
      setReady(value.display_name);
    } catch (cause) { if (current()) reject(cause); }
    finally { if (current()) { validation.current = null; setBusy(null); } }
  };
  const confirm = async () => {
    const candidate = reviewed.current, file = selected.current;
    if (importing.current || !candidate || !file) return;
    importing.current = true;
    reviewed.current = null;
    setBusy("import"); setFailure(null); setReady("");
    try {
      const text = await readFile(file).catch(() => null);
      if (!alive.current) return;
      if (text !== candidate.config_text) { setFailure({ message: c.changed, findings: [] }); return; }
      const value = await call("import", candidate);
      if (!alive.current) return;
      if (!value || value.name !== candidate.name || value.display_name !== candidate.display_name ||
        typeof value.id !== "string" || !/^[0-9a-f]{32}$/.test(value.id) ||
        value.paused !== true || value.pickup_state !== "stopped") throw new ApiError("unexpected_response");
      onImported();
    } catch (cause) { if (alive.current) reject(cause); }
    finally { importing.current = false; if (alive.current) setBusy(null); }
  };

  return <dialog ref={dialog} className="project-delete-dialog" aria-labelledby="raw-import-title"
    onCancel={event => { event.preventDefault(); if (!importing.current) onClose(); }}>
    <div className="form-stack">
      <h2 id="raw-import-title">{c.title}</h2>
      <label>{c.file}<input type="file" accept=".toml" autoFocus disabled={busy === "import"}
        onClick={event => { event.currentTarget.value = ""; void select(null); }}
        onChange={event => void select(event.target.files?.[0] ?? null)} /></label>
      {busy && <p role="status">{busy === "validate" ? c.validating : c.importing}</p>}
      {ready && <p role="status">{c.ready} <strong>{ready}</strong></p>}
      {failure && <div role="alert" className="alert">
        {failure.findings.length > 0 ? <ul>{failure.findings.map((item, index) => {
          const message = Object.hasOwn(c.issues, item.code) ? c.issues[item.code as keyof typeof c.issues] : c.correctFile;
          return <li key={index}><code>{item.field}</code> {message}</li>;
        })}</ul> : <p>{failure.message}</p>}
      </div>}
      <div className="button-row">
        <button type="button" className="primary" disabled={!ready || !!busy} onClick={() => void confirm()}>{c.confirm}</button>
        <button type="button" className="ghost" disabled={busy === "import"} onClick={onClose}>{c.cancel}</button>
      </div>
    </div>
  </dialog>;
}

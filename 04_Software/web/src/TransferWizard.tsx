/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState, type ComponentProps } from "react";
import { EnrollmentWizard } from "./EnrollmentWizard";
import { transferCopy, validTransferSettings, type TransferSelection, type TransferSource } from "./transferCopy";
import { ApiError, describeError } from "./errors";
import { enrollmentCopy } from "./enrollmentCopy";

type Props = ComponentProps<typeof EnrollmentWizard> & {
  projects: { id: string; display_name: string }[]; onExact: () => void;
};

/** Source review and method selection; target corrections remain owned by the guided wizard. */
export function TransferWizard(props: Props) {
  const c = transferCopy[props.locale];
  const [method, setMethod] = useState<"guided" | "file" | "project">("guided");
  const [selection, setSelection] = useState<TransferSelection>({ method: "file" });
  const [source, setSource] = useState<TransferSource | null>(null);
  const [target, setTarget] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const generation = useRef(0), alive = useRef(true), childGuard = useRef<(() => boolean) | null>(null);
  const operation = useRef(false), dirty = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null), error = useRef<HTMLDivElement>(null);
  const selectedFile = useRef<File | null>(null);
  const guard = () => {
    if (childGuard.current) return childGuard.current();
    if (dirty.current && !window.confirm(enrollmentCopy[props.locale].loss)) return false;
    dirty.current = false; return true;
  };
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; generation.current++; };
  }, []);
  useEffect(() => {
    if (method === "guided" || target) return;
    props.registerGuard(guard);
    const unload = (event: BeforeUnloadEvent) => {
      if (dirty.current) { event.preventDefault(); event.returnValue = ""; }
    };
    const click = (event: MouseEvent) => {
      const link = (event.target as Element).closest?.("a[href]");
      if (link && !link.getAttribute("href")?.startsWith("#") && !guard()) {
        event.preventDefault(); event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", unload); document.addEventListener("click", click, true);
    return () => { props.registerGuard(null); window.removeEventListener("beforeunload", unload);
      document.removeEventListener("click", click, true); };
  }, [method, target, props.locale, props.registerGuard]);
  useEffect(() => { if (failure) error.current?.focus(); }, [failure]);
  useEffect(() => { heading.current?.focus(); }, [method, target]);

  const select = (next: typeof method) => {
    if (!guard()) return;
    generation.current++; operation.current = false; childGuard.current = null; dirty.current = false;
    setBusy(false); setMethod(next); setTarget(false); setSource(null); setFailure(null);
    selectedFile.current = null;
    setSelection({ method: next === "project" ? "project" : "file" });
  };
  const invalidate = () => {
    generation.current++; operation.current = false; dirty.current = true;
    setBusy(false); setSource(null); setFailure(null);
  };
  const file = async (value?: File) => {
    invalidate(); setSelection({ method: "file" });
    selectedFile.current = value ?? null;
    if (!value) return;
    const token = generation.current;
    try {
      if (value.size > 65536) throw new ApiError("portable_settings_invalid");
      const raw = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(await value.arrayBuffer());
      if (alive.current && token === generation.current) setSelection({ method: "file", file_text: raw });
    } catch { if (alive.current && token === generation.current) setFailure(new ApiError("portable_settings_invalid")); }
  };
  const review = async () => {
    if (operation.current) return;
    const token = generation.current; operation.current = true; setBusy(true); setSource(null); setFailure(null);
    try {
      const exactSelection = selection.method === "file" && selectedFile.current ? {
        method: "file" as const, file_text: new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(await selectedFile.current.arrayBuffer()),
      } : selection;
      if (!alive.current || token !== generation.current) return;
      setSelection(exactSelection);
      const response = await fetch("/api/v1/projects/transfer-source", {
        method: "POST", cache: "no-store", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": props.csrf }, body: JSON.stringify(exactSelection),
      });
      const value = await response.json().catch(() => { throw new ApiError("unexpected_response"); });
      if (!response.ok) throw new ApiError(typeof value?.detail?.code === "string" ? value.detail.code : "unexpected_response");
      if (!value || Object.keys(value).length !== 2 || !/^[0-9a-f]{64}$/.test(value.source_revision) ||
        !validTransferSettings(value.settings)) throw new ApiError("unexpected_response");
      if (alive.current && token === generation.current) setSource({ ...value, selection: structuredClone(exactSelection) });
    } catch (cause) { if (alive.current && token === generation.current) setFailure(cause instanceof ApiError ? cause : new ApiError("network_error")); }
    finally { if (alive.current && token === generation.current) { operation.current = false; setBusy(false); } }
  };
  return <>
    <section className="panel" aria-label={c.method}>
      <div className="enrollment-actions">{(["guided", "file", "project"] as const).map(value =>
        <button type="button" key={value} className="ghost" aria-pressed={method === value} onClick={() => select(value)}>{c[value]}</button>)}
        <button type="button" className="ghost" onClick={() => { if (guard()) props.onExact(); }}>{c.exact}</button>
      </div>
    </section>
    {method === "guided" ? <EnrollmentWizard {...props} registerGuard={value => { childGuard.current = value; props.registerGuard(value); }} /> :
      target && source ? <EnrollmentWizard {...props} transfer={source}
        checkSource={async () => {
          if (source.selection.method !== "file") return;
          try {
            if (!selectedFile.current || new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
              await selectedFile.current.arrayBuffer()) !== source.selection.file_text)
              throw new ApiError("portable_settings_changed");
          } catch { throw new ApiError("portable_settings_changed"); }
        }}
        registerGuard={value => { childGuard.current = value; props.registerGuard(value); }}
        onSourceReview={() => { if (guard()) { childGuard.current = null; dirty.current = true; setTarget(false); setSource(null); } }} /> :
        <section className="panel enrollment">
          <h2 tabIndex={-1} ref={heading}>{c.title}</h2><p>{c.help}</p><p>{c.exclusions}</p><p>{c.integrity}</p>
          {method === "project" ? <><label htmlFor="transfer-project">{c.source}</label>
            <select id="transfer-project" value={selection.source_id ?? ""} onChange={event => {
              invalidate(); setSelection({ method: "project", source_id: event.target.value || undefined });
            }}><option value="">{c.choose}</option>{props.projects.map(item =>
              <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></> :
            <><label htmlFor="transfer-file">{c.upload}</label><input id="transfer-file" type="file" accept=".json,application/json"
              onChange={event => void file(event.target.files?.[0])} /></>}
          {failure ? <div role="alert" tabIndex={-1} ref={error}><p>{describeError(props.locale, failure)}</p><p>{c.blocked}</p></div> : null}
          <div className="enrollment-actions"><button className="primary" type="button" disabled={busy ||
            !(selection.file_text || selection.source_id)} onClick={() => void review()}>{c.review}</button>
            <button className="ghost" onClick={() => { if (guard()) props.onCancel(); }}>{c.cancel}</button></div>
          {busy && <p role="status">{c.loading}</p>}
          {source && <><h3>{c.recognized}</h3><dl className="enrollment-review">{Object.entries(source.settings).flatMap(([section, settings]) =>
            Object.entries(settings).map(([key, value]) => <div key={section + key}><dt>{section}.{key}</dt><dd>{JSON.stringify(value)}</dd></div>))}</dl>
            <p className="enrollment-digest">{c.revision}: {source.source_revision}</p>
            <button className="primary" onClick={() => setTarget(true)}>{c.target}</button></>}
        </section>}
  </>;
}

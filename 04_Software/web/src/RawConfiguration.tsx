/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useId, useRef, useState } from "react";
import { ApiError, describeError } from "./errors";
import type { Locale } from "./i18n";

const labels = {
  en: { preview: "Preview raw configuration", download: "Export raw configuration", close: "Close",
    export: "Export", cancel: "Cancel", loading: "Loading saved configuration…",
    saved: "Download the saved project configuration.", include: "Include Docker build files",
    unavailable: "This project's image has no linked build files. The project configuration can still be exported." },
  fr: { preview: "Voir la configuration brute", download: "Exporter la configuration brute", close: "Fermer",
    export: "Exporter", cancel: "Annuler", loading: "Chargement de la configuration enregistrée…",
    saved: "Télécharger la configuration enregistrée du projet.", include: "Inclure les fichiers de build Docker",
    unavailable: "L’image du projet n’a pas de fichiers de build associés. Sa configuration reste exportable." },
  de: { preview: "Originalkonfiguration anzeigen", download: "Originalkonfiguration exportieren", close: "Schließen",
    export: "Exportieren", cancel: "Abbrechen", loading: "Gespeicherte Konfiguration wird geladen…",
    saved: "Gespeicherte Projektkonfiguration herunterladen.", include: "Docker-Build-Dateien einschließen",
    unavailable: "Dem Projekt-Image sind keine Build-Dateien zugeordnet. Die Projektkonfiguration bleibt exportierbar." },
  ro: { preview: "Previzualizare configurație originală", download: "Exportă configurația brută", close: "Închide",
    export: "Exportă", cancel: "Anulează", loading: "Se încarcă configurația salvată…",
    saved: "Descarcă configurația salvată a proiectului.", include: "Include fișierele de build Docker",
    unavailable: "Imaginea proiectului nu are fișiere de build asociate. Configurația proiectului poate fi exportată." },
};

/** Admin dialogs keep saved settings and export feedback scoped to the selected project. */
export function RawConfiguration({ project, locale, dockerBuild }: { project: string; locale: Locale; dockerBuild?: boolean }) {
  const copy = labels[locale];
  const id = useId();
  const [view, setView] = useState<"preview" | "export" | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [includeBuild, setIncludeBuild] = useState(false);
  const active = useRef(true), pending = useRef(false), generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const dialog = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLElement | null>(null);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; generation.current++; controller.current?.abort(); };
  }, []);
  useEffect(() => {
    if (view === null) return;
    const node = dialog.current;
    node?.showModal();
    return () => { node?.close(); if (trigger.current?.isConnected) trigger.current.focus(); };
  }, [view]);

  function close() {
    generation.current++;
    controller.current?.abort();
    pending.current = false;
    setBusy(false); setPreview(null); setError(null); setView(null);
  }

  function open(next: "preview" | "export") {
    trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setError(null); setPreview(null); setIncludeBuild(false); setView(next);
    if (next === "preview") void read(false);
  }

  async function read(download: boolean) {
    if (pending.current) return;
    const current = ++generation.current;
    const isCurrent = () => active.current && current === generation.current;
    pending.current = true; setBusy(true); setError(null);
    controller.current = new AbortController();
    try {
      const bundle = download && dockerBuild === true && includeBuild;
      const query = bundle ? "?download=true&include_build=true" : download ? "?download=true" : "";
      const response = await fetch(`/api/v1/projects/${encodeURIComponent(project)}/config/raw${query}`, {
        credentials: "same-origin", cache: "no-store", signal: controller.current.signal,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new ApiError(typeof body?.detail?.code === "string" ? body.detail.code : "request_failed");
      }
      const mediaType = bundle ? "application/zip" : "text/plain";
      if (!response.headers.get("content-type")?.startsWith(mediaType)) throw new ApiError("unexpected_response");
      const raw = await response.arrayBuffer();
      if (!raw.byteLength || raw.byteLength > (bundle ? 18 * 1024 * 1024 : 524288)) throw new ApiError("unexpected_response");
      const text = bundle ? null : new TextDecoder("utf-8", { fatal: true }).decode(raw);
      if (bundle && (raw.byteLength < 4 || new DataView(raw).getUint32(0) !== 0x504b0304)) throw new ApiError("unexpected_response");
      if (!isCurrent()) return;
      if (download) {
        const url = URL.createObjectURL(new Blob([raw], { type: mediaType }));
        const link = document.createElement("a"); link.href = url; link.download = bundle ? "adore-docker-build.zip" : "config.toml";
        document.body.appendChild(link); link.click(); link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        close();
      } else setPreview(text);
    } catch (cause) {
      if (isCurrent()) { setPreview(null); setError(cause instanceof ApiError ? cause : new ApiError("request_failed")); }
    } finally {
      if (isCurrent()) { pending.current = false; setBusy(false); }
    }
  }

  return <div className="inline-actions raw-config-actions">
    <button type="button" className="ghost" onClick={() => open("preview")}>{copy.preview}</button>
    <button type="button" className="ghost" onClick={() => open("export")}>{copy.download}</button>
    {view !== null && <dialog ref={dialog} className="project-delete-dialog raw-config-dialog"
      aria-labelledby={`${id}-title`} onCancel={event => { event.preventDefault(); close(); }}>
      <div className="panel-heading">
        <h2 id={`${id}-title`}>{view === "preview" ? copy.preview : copy.download}</h2>
        {view === "preview" && <button type="button" autoFocus className="ghost" onClick={close}>{copy.close}</button>}
      </div>
      {view === "preview" ? <>
        {busy && <p role="status">{copy.loading}</p>}
        {preview !== null && <pre className="config-preview">{preview}</pre>}
      </> : <>
        <p className="muted">{copy.saved}</p>
        {dockerBuild !== undefined && <div className="raw-config-docker">
          <label className="raw-config-option">
            <input type="checkbox" checked={includeBuild} disabled={busy || !dockerBuild}
              aria-describedby={dockerBuild ? undefined : `${id}-unavailable`}
              onChange={event => setIncludeBuild(event.target.checked)} />{copy.include}
          </label>
          {!dockerBuild && <p className="field-hint" id={`${id}-unavailable`}>{copy.unavailable}</p>}
        </div>}
      </>}
      {error !== null && <p role="alert" className="alert">{describeError(locale, error)}</p>}
      {view === "export" && <div className="button-row">
        <button type="button" autoFocus className="ghost" onClick={close}>{copy.cancel}</button>
        <button type="button" className="primary" disabled={busy} onClick={() => void read(true)}>{copy.export}</button>
      </div>}
    </dialog>}
  </div>;
}

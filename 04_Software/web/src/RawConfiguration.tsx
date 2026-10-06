/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import { ApiError, describeError } from "./errors";
import type { Locale } from "./i18n";

const labels = {
  en: { preview: "Preview raw configuration", download: "Download raw configuration", close: "Close" },
  fr: { preview: "Voir la configuration brute", download: "Télécharger la configuration brute", close: "Fermer" },
  de: { preview: "Originalkonfiguration anzeigen", download: "Originalkonfiguration herunterladen", close: "Schließen" },
  ro: { preview: "Previzualizare configurație originală", download: "Descarcă configurația originală", close: "Închide" },
};

/** Admin-only controls: original bytes live in memory until dismissed/unmounted. */
export function RawConfiguration({ project, locale }: { project: string; locale: Locale }) {
  const copy = labels[locale];
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const active = useRef(true), pending = useRef(false), controller = useRef<AbortController | null>(null);
  const dialog = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLElement | null>(null);
  useEffect(() => { active.current = true; return () => { active.current = false; controller.current?.abort(); }; }, []);
  useEffect(() => {
    if (preview === null) return;
    const node = dialog.current;
    node?.showModal();
    return () => { node?.close(); if (trigger.current?.isConnected) trigger.current.focus(); };
  }, [preview]);

  async function read(download: boolean) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError(null); setPreview(null);
    trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    controller.current = new AbortController();
    try {
      const response = await fetch(`/api/v1/projects/${encodeURIComponent(project)}/config/raw${download ? "?download=true" : ""}`, {
        credentials: "same-origin", cache: "no-store", signal: controller.current.signal,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new ApiError(typeof body?.detail?.code === "string" ? body.detail.code : "request_failed");
      }
      if (!response.headers.get("content-type")?.startsWith("text/plain")) throw new ApiError("unexpected_response");
      const raw = await response.arrayBuffer();
      if (!raw.byteLength || raw.byteLength > 524288) throw new ApiError("unexpected_response");
      const text = new TextDecoder("utf-8", { fatal: true }).decode(raw);
      if (!active.current) return;
      if (download) {
        const url = URL.createObjectURL(new Blob([raw], { type: "text/plain" }));
        const link = document.createElement("a"); link.href = url; link.download = "config.toml";
        document.body.appendChild(link); link.click(); link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      } else setPreview(text);
    } catch (cause) {
      if (active.current) { setPreview(null); setError(cause instanceof ApiError ? cause : new ApiError("request_failed")); }
    } finally { pending.current = false; if (active.current) setBusy(false); }
  }

  return <div className="inline-actions raw-config-actions">
    <button type="button" className="ghost" disabled={busy} onClick={() => void read(false)}>{copy.preview}</button>
    <button type="button" className="ghost" disabled={busy} onClick={() => void read(true)}>{copy.download}</button>
    {error !== null && <p role="alert" className="alert">{describeError(locale, error)}</p>}
    {preview !== null && <dialog ref={dialog} className="project-delete-dialog" aria-label={copy.preview} onCancel={event => { event.preventDefault(); setPreview(null); }}>
      <div className="panel-heading"><h2>{copy.preview}</h2><button type="button" autoFocus className="ghost" onClick={() => setPreview(null)}>{copy.close}</button></div>
      <pre className="config-preview">{preview}</pre>
    </dialog>}
  </div>;
}

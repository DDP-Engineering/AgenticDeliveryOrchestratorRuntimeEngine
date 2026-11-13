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
    manage: "Image definition", exporting: "Exporting…", loading: "Loading saved configuration…",
    ready: "The image definition is ready for export.", required: "Definition required for",
    file: "Definition file", format: "Choose a Dockerfile or a ZIP containing its build files.",
    checking: "Checking definition…", save: "Save recipe", saving: "Saving recipe…", change: "Change definition",
    shared: "This definition is shared by projects using the same image. Running jobs stay unchanged.",
    recovery: "On the server, delete the named recipe data to start fresh:",
    reset: "This removes saved image definitions for all projects. Configurations, credentials and jobs stay unchanged.",
  },
  fr: { preview: "Voir la configuration brute", download: "Exporter la configuration brute", close: "Fermer",
    manage: "Définition de l’image", exporting: "Exportation…", loading: "Chargement de la configuration enregistrée…",
    ready: "La définition de l’image est prête à être exportée.", required: "Définition requise pour",
    file: "Fichier de définition", format: "Choisissez un Dockerfile ou un ZIP contenant ses fichiers de build.",
    checking: "Vérification de la définition…", save: "Enregistrer la recette", saving: "Enregistrement…", change: "Changer la définition",
    shared: "La définition est partagée par les projets utilisant cette image. Les tâches en cours restent inchangées.",
    recovery: "Sur le serveur, supprimez les données de recette indiquées pour recommencer :",
    reset: "Cela supprime les définitions d’image enregistrées pour tous les projets. Configurations, identifiants et tâches restent inchangés.",
  },
  de: { preview: "Originalkonfiguration anzeigen", download: "Originalkonfiguration exportieren", close: "Schließen",
    manage: "Image-Definition", exporting: "Export wird gespeichert…", loading: "Gespeicherte Konfiguration wird geladen…",
    ready: "Die Image-Definition ist zum Export bereit.", required: "Definition erforderlich für",
    file: "Definitionsdatei", format: "Wählen Sie eine Dockerfile oder eine ZIP-Datei mit den Build-Dateien.",
    checking: "Definition wird geprüft…", save: "Rezept speichern", saving: "Rezept wird gespeichert…", change: "Definition ändern",
    shared: "Projekte mit diesem Image teilen die Definition. Laufende Aufträge bleiben unverändert.",
    recovery: "Löschen Sie die genannten Rezeptdaten auf dem Server für einen Neuanfang:",
    reset: "Gespeicherte Image-Definitionen aller Projekte werden entfernt. Konfigurationen, Zugangsdaten und Aufträge bleiben unverändert.",
  },
  ro: { preview: "Previzualizare configurație originală", download: "Exportă configurația brută", close: "Închide",
    manage: "Definiția imaginii", exporting: "Se exportă…", loading: "Se încarcă configurația salvată…",
    ready: "Definiția imaginii este pregătită pentru export.", required: "Este necesară definiția pentru",
    file: "Fișier de definiție", format: "Alege un Dockerfile sau un ZIP care conține fișierele de construire.",
    checking: "Se verifică definiția…", save: "Salvează rețeta", saving: "Se salvează rețeta…", change: "Schimbă definiția",
    shared: "Definiția este comună proiectelor care folosesc aceeași imagine. Joburile în curs rămân neschimbate.",
    recovery: "Pe server, șterge datele de rețetă indicate pentru a începe din nou:",
    reset: "Se elimină definițiile de imagine salvate pentru toate proiectele. Configurațiile, autentificările și joburile rămân neschimbate.",
  },
};

type RecipeStatus = { image: string; available: boolean; missing_images: string[];
  digest: string | null; source: string; revision: string };
type Attachment = { image: string; source: string; revision: string; expected_digest: string | null };
const digest = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
function recipeValue(value: unknown): RecipeStatus {
  const data = value as Partial<RecipeStatus> | null;
  if (!data || typeof data.image !== "string" || !data.image || data.image.length > 255 ||
      typeof data.available !== "boolean" || !Array.isArray(data.missing_images) ||
      data.missing_images.length > 32 || !data.missing_images.every(image => typeof image === "string" && image.length <= 255) ||
      data.available !== (data.missing_images.length === 0) ||
      !(data.digest === null || digest(data.digest)) || !digest(data.revision) ||
      !["managed", "git", "builtin", "missing"].includes(String(data.source))) throw new ApiError("unexpected_response");
  return data as RecipeStatus;
}

async function encodeDefinition(file: File): Promise<string> {
  if (!file.size || file.size > 18 * 1024 * 1024) throw new ApiError("recipe_invalid");
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let index = 0; index < bytes.length; index += 32768)
    binary += String.fromCharCode(...bytes.subarray(index, index + 32768));
  return btoa(binary);
}

interface SaveHandle {
  createWritable(): Promise<{
    write(data: ArrayBuffer): Promise<void>;
    close(): Promise<void>;
    abort(): Promise<void>;
  }>;
}

/** Admin dialogs keep saved settings and export feedback scoped to the selected project. */
export function RawConfiguration({ project, locale, dockerBuild, image, csrf, revision, definitionOnly = false }: {
  project: string; locale: Locale; dockerBuild?: boolean; image: string; csrf: string; revision: string; definitionOnly?: boolean;
}) {
  const copy = labels[locale];
  const id = useId();
  const [view, setView] = useState<"preview" | "definition" | "error" | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [recipe, setRecipe] = useState<RecipeStatus | null>(null);
  const [recipeBusy, setRecipeBusy] = useState<"load" | "preview" | "save" | null>(null);
  const [editingRecipe, setEditingRecipe] = useState(false);
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const sourceGeneration = useRef(0), sourceController = useRef<AbortController | null>(null);
  const active = useRef(true), pending = useRef(false), generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const dialog = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLElement | null>(null);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; generation.current++; controller.current?.abort();
      sourceGeneration.current++; sourceController.current?.abort(); };
  }, []);
  useEffect(() => {
    if (view === null) return;
    const node = dialog.current;
    node?.showModal();
    node?.querySelector<HTMLButtonElement>("[data-dialog-initial]")?.focus();
    return () => { node?.close(); if (trigger.current?.isConnected) trigger.current.focus(); };
  }, [view]);

  function close() {
    if (recipeBusy === "save") return;
    generation.current++;
    controller.current?.abort();
    sourceGeneration.current++; sourceController.current?.abort();
    pending.current = false;
    setBusy(false); setPreview(null); setError(null); setView(null);
    setRecipe(null); setAttachment(null); setRecipeBusy(null); setEditingRecipe(false);
  }

  function open(next: "preview" | "definition") {
    trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setError(null); setPreview(null); setView(next);
    setRecipe(null); setAttachment(null); setEditingRecipe(false);
    if (next === "preview") void read(false);
    else if (dockerBuild) void loadRecipe();
  }

  async function recipeRequest(method: "GET" | "POST" | "PUT", body?: Attachment, signal?: AbortSignal) {
    const suffix = method === "POST" ? "/preview" : "";
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(project)}/executor-recipe${suffix}`, {
      method, credentials:"same-origin",cache:"no-store",signal,
      headers:body?{"Content-Type":"application/json","X-CSRF-Token":csrf}:undefined,
      body:body?JSON.stringify(body):undefined,
    });
    const value = await response.json().catch(() => { throw new ApiError("unexpected_response"); });
    if (!response.ok) {
      const recovery = typeof value?.detail?.recovery === "string" &&
        (value.detail.recovery === "executor-recipes" || value.detail.recovery.startsWith("executor-recipes/"))
        ? `${copy.recovery} ${value.detail.recovery}${value.detail.recovery === "executor-recipes"?" "+copy.reset:""}` : "";
      throw new ApiError(typeof value?.detail?.code === "string"?value.detail.code:"request_failed",recovery);
    }
    return value;
  }

  async function loadRecipe() {
    const current = ++sourceGeneration.current;
    sourceController.current?.abort(); sourceController.current = new AbortController();
    setRecipeBusy("load");
    try {
      const result = recipeValue(await recipeRequest("GET",undefined,sourceController.current.signal));
      if (active.current && current === sourceGeneration.current) setRecipe(result);
    } catch (cause) {
      if (active.current && current === sourceGeneration.current) {
        setError(cause instanceof ApiError?cause:new ApiError("request_failed"));
        if (image && digest(revision)) setRecipe({image,available:false,missing_images:[image],digest:null,source:"missing",revision});
      }
    } finally {
      if (active.current && current === sourceGeneration.current) setRecipeBusy(null);
    }
  }

  const targetImage = editingRecipe ? (recipe?.image ?? image) : (recipe?.missing_images[0] ?? recipe?.image ?? image);
  async function selectDefinition(file: File | null) {
    if (recipeBusy === "save") return;
    const current = ++sourceGeneration.current;
    sourceController.current?.abort(); sourceController.current = new AbortController();
    setAttachment(null); setError(null); setRecipeBusy(file?"preview":null);
    if (!file) return;
    try {
      const source = await encodeDefinition(file);
      if (!active.current || current !== sourceGeneration.current) return;
      const body:Attachment={image:targetImage,source,revision:recipe!.revision,expected_digest:null};
      const value = await recipeRequest("POST",body,sourceController.current.signal);
      recipeValue(value);
      if (!(value.expected_digest === null || digest(value.expected_digest)) || value.upload_image !== targetImage)
        throw new ApiError("unexpected_response");
      if (active.current && current === sourceGeneration.current)
        setAttachment({...body,expected_digest:value.expected_digest});
    } catch (cause) {
      if (active.current && current === sourceGeneration.current) setError(cause instanceof ApiError?cause:new ApiError("request_failed"));
    } finally {
      if (active.current && current === sourceGeneration.current) setRecipeBusy(null);
    }
  }

  async function saveRecipe() {
    if (!attachment || recipeBusy !== null) return;
    const current = ++sourceGeneration.current;
    sourceController.current = new AbortController(); setRecipeBusy("save"); setError(null);
    try {
      const result = recipeValue(await recipeRequest("PUT",attachment,sourceController.current.signal));
      if (active.current && current === sourceGeneration.current) {
        setRecipe(result); setAttachment(null); setEditingRecipe(false);
      }
    } catch (cause) {
      if (active.current && current === sourceGeneration.current) setError(cause instanceof ApiError?cause:new ApiError("request_failed"));
    } finally {
      if (active.current && current === sourceGeneration.current) setRecipeBusy(null);
    }
  }

  async function read(download: boolean) {
    if (pending.current || recipeBusy === "save") return;
    const current = ++generation.current;
    const isCurrent = () => active.current && current === generation.current;
    pending.current = true; setBusy(true); setError(null);
    controller.current = new AbortController();
    let phase: "choose" | "read" | "write" = "read";
    try {
      const bundle = download && dockerBuild === true;
      const filename = bundle ? "adore-docker-build.zip" : "config.toml";
      const picker = (window as Window & {showSaveFilePicker?: (options: {suggestedName:string; types:{description:string; accept:Record<string,string[]>}[]}) => Promise<SaveHandle>}).showSaveFilePicker;
      const usePicker = download && typeof picker === "function";
      if (usePicker) phase = "choose";
      const handle = usePicker ? await picker.call(window, {
        suggestedName: filename,
        types: [{description: bundle ? "ZIP" : "TOML", accept: bundle ? {"application/zip":[".zip"]} : {"text/plain":[".toml"]}}],
      }) : null;
      phase = "read";
      if (!isCurrent()) return;
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
        if (handle) {
          phase = "write";
          const writable = await handle.createWritable();
          try {
            if (!isCurrent()) { await writable.abort(); return; }
            await writable.write(raw);
            if (!isCurrent()) { await writable.abort(); return; }
            await writable.close();
          } catch (cause) {
            await writable.abort().catch(() => undefined);
            throw cause;
          }
        } else {
          const url = URL.createObjectURL(new Blob([raw], { type: mediaType }));
          const link = document.createElement("a"); link.href = url; link.download = filename;
          document.body.appendChild(link); link.click(); link.remove();
          window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
        close();
      } else setPreview(text);
    } catch (cause) {
      if (isCurrent() && !(phase === "choose" && cause instanceof DOMException && cause.name === "AbortError")) {
        setPreview(null); setError(cause instanceof ApiError ? cause : new ApiError(phase === "read" ? "request_failed" : "export_save_failed"));
        if (download) setView("error");
      }
    } finally {
      if (isCurrent()) { pending.current = false; setBusy(false); }
    }
  }

  return <div className={definitionOnly ? "recipe-management" : "inline-actions raw-config-actions"}>
    {definitionOnly ? <button type="button" className="ghost" onClick={() => open("definition")}>{copy.manage}</button> : <>
      <button type="button" className="ghost" disabled={busy} onClick={() => open("preview")}>{copy.preview}</button>
      <button type="button" className="ghost" disabled={busy} onClick={() => {
        trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        void read(true);
      }}>{busy && view === null ? copy.exporting : copy.download}</button>
    </>}
    {view !== null && <dialog ref={dialog} className="project-delete-dialog raw-config-dialog"
      aria-labelledby={`${id}-title`} onCancel={event => { event.preventDefault(); close(); }}>
      <div className="panel-heading">
        <h2 id={`${id}-title`}>{view === "preview" ? copy.preview : view === "definition" ? copy.manage : copy.download}</h2>
        <button type="button" data-dialog-initial autoFocus className="ghost" disabled={recipeBusy === "save"} onClick={close}>{copy.close}</button>
      </div>
      {view === "preview" && <>
        {busy && <p role="status">{copy.loading}</p>}
        {preview !== null && <pre className="config-preview">{preview}</pre>}
      </>}
      {view === "definition" && <div className="raw-config-recipe">
        {recipeBusy === "load" && <p role="status">{copy.checking}</p>}
        {recipe && !editingRecipe && recipe.source !== "missing" && <>
          {recipe.available && <p className="field-hint" role="status">{copy.ready}</p>}
          <button type="button" className="text-button" disabled={busy || recipeBusy !== null}
            onClick={() => {setEditingRecipe(true);setAttachment(null);setError(null);}}>{copy.change}</button>
        </>}
        {recipe && (!recipe.available || editingRecipe) && <>
          <p>{copy.required} <code>{targetImage}</code></p>
          <label>{copy.file}<input key={targetImage} type="file" disabled={busy || recipeBusy === "save"}
            onChange={event => void selectDefinition(event.target.files?.[0] ?? null)} /></label>
          <p className="field-hint">{copy.format}</p>
          <p className="field-hint">{copy.shared}</p>
          {recipeBusy === "preview" && <p role="status">{copy.checking}</p>}
          <button type="button" className="ghost" disabled={busy || recipeBusy !== null || !attachment}
            onClick={() => void saveRecipe()}>{recipeBusy === "save"?copy.saving:copy.save}</button>
        </>}
      </div>}
      {error !== null && <p role="alert" className="alert">{describeError(locale, error)}</p>}
    </dialog>}
  </div>;
}

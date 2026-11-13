/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { ApiError } from "./errors.ts";
import type { Locale } from "./i18n";

export const environmentStages = ["waiting", "checking_runtime", "checking_images", "building_executor", "building_proxy", "verifying", "ready", "failed"] as const;
const failures = ["container_runtime_unavailable", "executor_image_unavailable", "environment_identity_unavailable", "environment_busy", "environment_preparation_failed", "environment_build_failed", "environment_executor_invalid"];
export type EnvironmentProgress = {
  id: string; status: "running" | "ready" | "failed";
  stage: typeof environmentStages[number]; error: string | null;
};
export const environmentCopy: Record<Locale, Record<typeof environmentStages[number] | "title" | "help" | "automatic", string>> = {
  en: { title: "Preparing execution environment", help: "The first import may take several minutes and downloads the shared tools. Later imports reuse the images. If preparation fails, retry the import.",
    automatic: "This shared image will be prepared automatically when you import the project.",
    waiting: "Waiting for another import to finish preparing the shared images…", checking_runtime: "Checking the container service…", checking_images: "Checking existing images…", building_executor: "Preparing the shared executor image…", building_proxy: "Preparing the shared network proxy…", verifying: "Verifying the executor…", ready: "Execution environment ready.", failed: "Preparation failed." },
  ro: { title: "Pregătirea mediului de execuție", help: "Primul import poate dura câteva minute și descarcă instrumentele comune. Importurile următoare reutilizează imaginile. Dacă pregătirea eșuează, reîncearcă importul.",
    automatic: "Această imagine comună va fi pregătită automat la importul proiectului.",
    waiting: "Se așteaptă pregătirea imaginilor comune de către alt import…", checking_runtime: "Se verifică serviciul de containere…", checking_images: "Se verifică imaginile existente…", building_executor: "Se pregătește imaginea comună de execuție…", building_proxy: "Se pregătește proxy-ul comun de rețea…", verifying: "Se verifică executorul…", ready: "Mediul de execuție este pregătit.", failed: "Pregătirea a eșuat." },
  fr: { title: "Préparation de l’environnement d’exécution", help: "Le premier import peut prendre plusieurs minutes et télécharge les outils communs. Les imports suivants réutilisent les images. En cas d’échec, réessayez l’import.",
    automatic: "Cette image commune sera préparée automatiquement lors de l’import du projet.",
    waiting: "Un autre import prépare les images communes…", checking_runtime: "Vérification du service de conteneurs…", checking_images: "Vérification des images existantes…", building_executor: "Préparation de l’image d’exécution commune…", building_proxy: "Préparation du proxy réseau commun…", verifying: "Vérification de l’exécuteur…", ready: "Environnement d’exécution prêt.", failed: "La préparation a échoué." },
  de: { title: "Ausführungsumgebung wird vorbereitet", help: "Der erste Import kann einige Minuten dauern und lädt gemeinsame Werkzeuge herunter. Weitere Importe verwenden die Images erneut. Bei einem Fehler den Import erneut versuchen.",
    automatic: "Dieses gemeinsame Image wird beim Import des Projekts automatisch vorbereitet.",
    waiting: "Ein anderer Import bereitet die gemeinsamen Images vor…", checking_runtime: "Container-Dienst wird geprüft…", checking_images: "Vorhandene Images werden geprüft…", building_executor: "Gemeinsames Ausführungsimage wird vorbereitet…", building_proxy: "Gemeinsamer Netzwerkproxy wird vorbereitet…", verifying: "Ausführungsumgebung wird geprüft…", ready: "Ausführungsumgebung ist bereit.", failed: "Vorbereitung fehlgeschlagen." },
};

export function readEnvironmentProgress(value: unknown): EnvironmentProgress {
  const item = value as EnvironmentProgress;
  if (!item || typeof item !== "object" || Object.keys(item).sort().join() !== "error,id,stage,status"
      || typeof item.id !== "string" || !/^[0-9a-f]{32}$/.test(item.id)
      || !environmentStages.includes(item.stage)
      || !(item.status === "ready" && item.stage === "ready" && item.error === null
        || item.status === "failed" && item.stage === "failed" && typeof item.error === "string" && failures.includes(item.error)
        || item.status === "running" && !["ready", "failed"].includes(item.stage) && item.error === null))
    throw new ApiError("unexpected_response");
  return item;
}

export function environmentFailure(cause: unknown): boolean {
  return cause instanceof ApiError && (failures.includes(cause.code) || cause.code === "environment_preparation_expired");
}

/** Preparation completes before the caller publishes its still-reviewed import. */
export async function prepareEnvironment(start: () => Promise<unknown>, onProgress: (value: EnvironmentProgress) => void,
  current: () => boolean): Promise<void> {
  if (!current()) throw new ApiError("request_rejected");
  let progress = readEnvironmentProgress(await start());
  const id = progress.id, deadline = Date.now() + 2 * 60 * 60 * 1000;
  while (current()) {
    onProgress(progress);
    if (progress.status === "ready") return;
    if (progress.status === "failed") throw new ApiError(progress.error!);
    if (Date.now() > deadline) throw new ApiError("environment_preparation_expired");
    await new Promise(resolve => setTimeout(resolve, 1000));
    if (!current()) break;
    let response: Response;
    try { response = await fetch(`/api/v1/environment-preparations/${id}`, { credentials: "same-origin", cache: "no-store" }); }
    catch { throw new ApiError("network_error"); }
    const value = await response.json().catch(() => { throw new ApiError("unexpected_response"); });
    if (!response.ok) throw new ApiError(typeof value?.detail?.code === "string" ? value.detail.code : "request_failed");
    progress = readEnvironmentProgress(value);
    if (progress.id !== id) throw new ApiError("unexpected_response");
  }
  throw new ApiError("request_rejected");
}

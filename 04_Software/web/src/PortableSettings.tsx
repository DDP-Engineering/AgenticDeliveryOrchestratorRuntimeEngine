/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";
import { ApiError, describeError } from "./errors";
import { parsePortableResponse, type PortablePackage } from "./portable";

export const portableCopy = {
  en: { title: "Export portable settings", purpose: "Reuse working rules as defaults for a new project on a compatible ADORE version. Preview reads validated active settings; pending changes are excluded.", included: "Includes: polling cadence and capacity, readiness checks, retry limits/backoff and job budgets, including the reported-cost cap.", excluded: "Excludes: project/display identity, repository/branches, host paths, jobs/history, users/access/audit, prices, secrets and all credential/endpoint references. Supply and confirm target-host credentials and endpoints separately.", limits: "JSON schema 1 requires the exact source ADORE version. SHA-256 detects changes; it does not authenticate an untrusted file. New-project import and copying settings are not available in this screen. Exact server TOML enrollment and statistics CSV are separate formats.", preview: "Preview active rules", download: "Download portable JSON", source: "Source ADORE version", checksum: "Change-detection checksum", busy: "Reading active rules…", ready: "Portable preview is ready. Download uses the unchanged portable values." },
  fr: { title: "Exporter les paramètres portables", purpose: "Réutilisez les règles comme valeurs initiales d’un nouveau projet avec une version ADORE compatible. L’aperçu lit les paramètres actifs validés ; les modifications en attente sont exclues.", included: "Inclus : cadence et capacité de collecte, critères de sélection, limites et délais de reprise, budgets des tâches et plafond du coût déclaré.", excluded: "Exclus : identité du projet et nom affiché, dépôt et branches, chemins hôte, tâches et historique, utilisateurs et accès, audit, tarifs, secrets et références d’identifiants ou de points d’accès. Configurez et confirmez ces références sur l’hôte cible.", limits: "Le schéma JSON 1 exige la même version ADORE que la source. SHA-256 détecte les changements sans authentifier le fichier. L’import de nouveaux projets et la copie ne sont pas disponibles ici. L’inscription TOML exacte et les CSV statistiques sont distincts.", preview: "Prévisualiser les règles actives", download: "Télécharger le JSON portable", source: "Version ADORE source", checksum: "Empreinte de détection des changements", busy: "Lecture des règles actives…", ready: "L’aperçu est prêt. Le téléchargement utilise les mêmes valeurs portables." },
  de: { title: "Portable Einstellungen exportieren", purpose: "Arbeitsregeln als Vorgaben für ein neues Projekt mit kompatibler ADORE-Version verwenden. Die Vorschau liest validierte aktive Einstellungen; ausstehende Änderungen sind ausgeschlossen.", included: "Enthalten: Abfrageintervall und Kapazität, Auswahlprüfungen, Wiederholungsgrenzen und Wartezeiten sowie Auftragsbudgets einschließlich der gemeldeten Kostengrenze.", excluded: "Ausgeschlossen: Projektidentität und Anzeigename, Repository und Branches, Hostpfade, Aufträge und Verlauf, Benutzer und Rechte, Audit, Preise, Geheimnisse sowie Zugangsdaten- und Endpunktreferenzen. Diese auf dem Zielhost separat einrichten und bestätigen.", limits: "JSON-Schema 1 verlangt die genaue ADORE-Version der Quelle. SHA-256 erkennt Änderungen und bestätigt keine Echtheit. Import und Kopieren für neue Projekte sind hier nicht verfügbar. Exakte TOML-Registrierung und Statistik-CSV sind getrennte Formate.", preview: "Aktive Regeln ansehen", download: "Portables JSON herunterladen", source: "ADORE-Quellversion", checksum: "Prüfsumme zur Änderungserkennung", busy: "Aktive Regeln werden gelesen…", ready: "Vorschau bereit. Der Download verwendet dieselben portablen Werte." },
  ro: { title: "Exportă setările portabile", purpose: "Reutilizează regulile ca valori inițiale pentru un proiect nou cu o versiune ADORE compatibilă. Previzualizarea citește setările active validate; modificările în așteptare sunt excluse.", included: "Include: ritmul și capacitatea preluării, criteriile de selecție, limitele și intervalele reîncercărilor, bugetele joburilor și plafonul costului raportat.", excluded: "Exclude: identitatea și numele afișat, depozitul și ramurile, căile gazdei, joburile și istoricul, utilizatorii și accesul, auditul, tarifele, secretele și toate referințele la credențiale sau endpoint-uri. Configurează și confirmă separat credențialele și endpoint-urile pe gazda țintă.", limits: "Schema JSON 1 cere versiunea ADORE exactă a sursei. SHA-256 detectează schimbări, fără să autentifice fișierul. Importul unui proiect nou și copierea nu sunt disponibile aici. Înrolarea TOML exactă și statisticile CSV sunt formate separate.", preview: "Previzualizează regulile active", download: "Descarcă JSON portabil", source: "Versiunea ADORE sursă", checksum: "Checksum pentru detectarea schimbărilor", busy: "Se citesc regulile active…", ready: "Previzualizarea este gata. Descărcarea folosește aceleași valori portabile." },
};

/** Memory-only panel, keyed by authorized session/project/config scope by App. */
export function PortableSettings({ project, locale }: { project: string; locale: Locale }) {
  const copy = portableCopy[locale];
  const [preview, setPreview] = useState<PortablePackage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const active = useRef(true), inFlight = useRef(false), controller = useRef<AbortController | null>(null);
  useEffect(() => { active.current = true; return () => { active.current = false; controller.current?.abort(); }; }, []);

  async function read(download: boolean) {
    if (inFlight.current || download && !preview) return;
    inFlight.current = true; setBusy(true); setError(null);
    controller.current = new AbortController();
    try {
      const query = download ? `?download=true&checksum=${preview!.checksum}` : "";
      const response = await fetch(`/api/v1/projects/${encodeURIComponent(project)}/config/portable-settings${query}`, { credentials: "same-origin", cache: "no-store", signal: controller.current.signal });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new ApiError(typeof body?.detail?.code === "string" ? body.detail.code : "request_failed");
      }
      if (!response.headers.get("content-type")?.includes("application/json")) throw new ApiError("unexpected_response");
      const raw = await response.text();
      let parsed: PortablePackage;
      try { parsed = await parsePortableResponse(raw); } catch { throw new ApiError("unexpected_response"); }
      if (download && parsed.checksum !== preview!.checksum) throw new ApiError("portable_settings_changed");
      if (!active.current) return;
      setPreview(parsed);
      if (download) {
        const url = URL.createObjectURL(new Blob([raw], { type: "application/json" }));
        const link = document.createElement("a"); link.href = url; link.download = "adore-project-settings.json";
        document.body.appendChild(link); link.click(); link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (cause) {
      if (active.current) { setPreview(null); setError(cause instanceof ApiError ? cause : new ApiError("network_error")); }
    } finally { inFlight.current = false; if (active.current) setBusy(false); }
  }

  return <section className="panel wide-panel portable-settings" aria-labelledby="portable-title">
    <h2 id="portable-title">{copy.title}</h2><p>{copy.purpose}</p><p>{copy.included}</p><p>{copy.excluded}</p><p className="muted">{copy.limits}</p>
    <div className="inline-actions"><button type="button" className="ghost" disabled={busy} onClick={() => void read(false)}>{copy.preview}</button><button type="button" className="primary" disabled={busy || !preview} onClick={() => void read(true)}>{copy.download}</button></div>
    <p role="status">{busy ? copy.busy : preview ? copy.ready : ""}</p>
    {error !== null && <p role="alert" className="alert">{describeError(locale, error)}</p>}
    {preview && <><p>{copy.source}: {preview.source.version}</p><p className="project-verification-evidence">{copy.checksum}: {preview.checksum}</p><pre className="config-preview">{JSON.stringify(preview.settings, null, 2)}</pre></>}
  </section>;
}

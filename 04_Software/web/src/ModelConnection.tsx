/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";
import { ApiError } from "./errors";

const copy = {
 en: {title: "Test AI connection", busy: "Testing AI connection…", help: "Sends one short request through the configured coding agent in a temporary container. Provider charges may apply. This checks model access, not a complete job or tool support.", passed: "AI model connected", failed: "AI connection could not be verified", timeout: "The model did not respond within the time limit.", image: "Install the configured container image locally.", cli: "The selected coding agent is missing from the image.", auth: "Check the selected model's credentials on the ADORE server.", model: "The configured model is unavailable.", other: "Check model settings, credentials, network access and the installed agent version.", error: "The test could not complete. Check that the project is idle and its settings are valid."},
 ro: {title: "Testează conexiunea AI", busy: "Se testează conexiunea AI…", help: "Trimite o cerere scurtă prin agentul configurat într-un container temporar. Furnizorul poate percepe un cost. Verifică accesul la model, nu un job complet sau suportul pentru instrumente.", passed: "Model AI conectat", failed: "Conexiunea AI nu a putut fi verificată", timeout: "Modelul nu a răspuns în timpul alocat.", image: "Instalează local imaginea de container configurată.", cli: "Agentul selectat lipsește din imagine.", auth: "Verifică pe serverul ADORE credențialele modelului selectat.", model: "Modelul configurat nu este disponibil.", other: "Verifică setările modelului, credențialele, accesul la rețea și versiunea agentului instalat.", error: "Testul nu s-a încheiat. Verifică dacă proiectul este inactiv și setările sunt valide."},
 fr: {title: "Tester la connexion IA", busy: "Test de connexion IA…", help: "Envoie une courte requête via l’agent configuré dans un conteneur temporaire. Des frais peuvent s’appliquer. Vérifie l’accès au modèle, pas une tâche complète ni ses outils.", passed: "Modèle IA connecté", failed: "Connexion IA non vérifiée", timeout: "Le modèle n’a pas répondu à temps.", image: "Installez l’image du conteneur localement.", cli: "L’agent sélectionné manque dans l’image.", auth: "Vérifiez les identifiants du modèle sur le serveur ADORE.", model: "Le modèle configuré est indisponible.", other: "Vérifiez le modèle, les identifiants, le réseau et la version de l’agent.", error: "Test interrompu. Vérifiez que le projet est inactif et sa configuration valide."},
 de: {title: "KI-Verbindung testen", busy: "KI-Verbindung wird getestet…", help: "Sendet eine kurze Anfrage über den konfigurierten Agenten in einem temporären Container. Anbietergebühren können anfallen. Prüft Modellzugriff, keinen vollständigen Job oder Werkzeuge.", passed: "KI-Modell verbunden", failed: "KI-Verbindung nicht bestätigt", timeout: "Das Modell hat nicht rechtzeitig geantwortet.", image: "Installieren Sie das konfigurierte Container-Image lokal.", cli: "Der gewählte Agent fehlt im Image.", auth: "Prüfen Sie die Modell-Zugangsdaten auf dem ADORE-Server.", model: "Das konfigurierte Modell ist nicht verfügbar.", other: "Prüfen Sie Modell, Zugangsdaten, Netzwerk und Agent-Version.", error: "Test fehlgeschlagen. Das Projekt muss inaktiv und gültig konfiguriert sein."},
};
export type ModelEvidence = {project_id: string; revision: string; checked_at: string; executor: string; model: string; ready: boolean; reason: string};
const reasons = new Set(["ready", "timeout", "image-missing", "cli-missing", "credential-invalid", "model-unavailable", "connection-failed", "invalid-response", "runtime-error"]);

/** Closed model evidence, bound to the current identity/model/configuration. */
export function validModelEvidence(value: unknown, project:string, revision:string, executor:string, model:string):value is ModelEvidence {
 const v=value as ModelEvidence;
 return !!v && Object.keys(v).sort().join()==="checked_at,executor,model,project_id,ready,reason,revision" && v.project_id===project && v.revision===revision && /^[a-f0-9]{64}$/.test(v.revision) && v.executor===executor && v.model===model && typeof v.checked_at==="string" && Number.isFinite(Date.parse(v.checked_at)) && /Z$|[+]00:00$/.test(v.checked_at) && Date.parse(v.checked_at)<=Date.now()+60000 && typeof v.ready==="boolean" && reasons.has(v.reason) && v.ready===(v.reason==="ready");
}

/** Explicit billable model test; closed results remain bound to the selected project. */
export function ModelConnection({project, revision, executor, model, locale, test, saved=null, onResult, readOnly=false}: {project: string; revision: string; executor: string; model: string; locale: Locale; test?: () => Promise<unknown>; saved?:ModelEvidence|null; onResult?:(value:ModelEvidence)=>void; readOnly?:boolean}) {
 const text = copy[locale];
 const [busy, setBusy] = useState(false);
 const [result, setResult] = useState<ModelEvidence | null>(saved && validModelEvidence(saved,project,revision,executor,model) ? saved : null);
 const [error, setError] = useState(false);
 const active = useRef(true), pending = useRef(false);
 useEffect(() => {active.current = true; return () => {active.current = false;};}, []);
 const run = async () => {
  if (pending.current || !test) return;
  pending.current = true; setBusy(true); setResult(null); setError(false);
  try {
   const value = await test() as ModelEvidence;
   if (!active.current) return;
   if (!validModelEvidence(value,project,revision,executor,model)) throw new ApiError("model_test_failed");
   setResult(value); onResult?.(value);
  } catch { if (active.current) setError(true); }
  finally { if (active.current) {pending.current = false; setBusy(false);} }
 };
 const guidance = result?.reason === "timeout" ? text.timeout : result?.reason === "image-missing" ? text.image : result?.reason === "cli-missing" ? text.cli : result?.reason === "credential-invalid" ? text.auth : result?.reason === "model-unavailable" ? text.model : text.other;
 return <div className="model-connection">
  {!readOnly && <button type="button" className="ghost" disabled={busy} title={text.help} onClick={() => void run()}>{busy ? text.busy : text.title}</button>}
  {!readOnly && <p className="muted model-test-help">{text.help}</p>}
  {busy && <p role="status">{text.busy}</p>}
  {error && <p role="alert" className="alert">{text.error}</p>}
  {result && <div role="status" className={result.ready ? "success" : "alert"}><strong>{result.ready ? text.passed : text.failed}</strong><p>{result.executor} · {result.model}</p>{!result.ready && <p>{guidance}</p>}</div>}
 </div>;
}

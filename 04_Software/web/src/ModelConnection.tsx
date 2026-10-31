/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";
import { ApiError } from "./errors";
import { modelFailureText, modelTestHelp } from "./localDiagnostics";

const copy = {
 en: {title: "Test AI connection", busy: "Testing AI connection…", passed: "AI model connected", failed: "AI connection could not be verified", error: "The test could not complete. Check that the project is idle and its settings are valid."},
 ro: {title: "Testează conexiunea AI", busy: "Se testează conexiunea AI…", passed: "Model AI conectat", failed: "Conexiunea AI nu a putut fi verificată", error: "Testul nu s-a încheiat. Verifică dacă proiectul este inactiv și setările sunt valide."},
 fr: {title: "Tester la connexion IA", busy: "Test de connexion IA…", passed: "Modèle IA connecté", failed: "Connexion IA non vérifiée", error: "Test interrompu. Vérifiez que le projet est inactif et sa configuration valide."},
 de: {title: "KI-Verbindung testen", busy: "KI-Verbindung wird getestet…", passed: "KI-Modell verbunden", failed: "KI-Verbindung nicht bestätigt", error: "Test fehlgeschlagen. Das Projekt muss inaktiv und gültig konfiguriert sein."},
};
export type ModelEvidence = {project_id: string; revision: string; checked_at: string; executor: string; model: string; ready: boolean; reason: string};
const reasons = new Set(["ready", "timeout", "image-missing", "cli-missing", "credential-invalid", "model-unavailable", "connection-failed", "invalid-response", "runtime-error"]);

/** Closed model evidence, bound to the current identity/model/configuration. */
export function validModelEvidence(value: unknown, project:string, revision:string, executor:string, model:string):value is ModelEvidence {
 const v=value as ModelEvidence;
 return !!v && Object.keys(v).sort().join()==="checked_at,executor,model,project_id,ready,reason,revision" && v.project_id===project && v.revision===revision && /^[a-f0-9]{64}$/.test(v.revision) && v.executor===executor && v.model===model && typeof v.checked_at==="string" && Number.isFinite(Date.parse(v.checked_at)) && /Z$|[+]00:00$/.test(v.checked_at) && Date.parse(v.checked_at)<=Date.now()+60000 && typeof v.ready==="boolean" && reasons.has(v.reason) && v.ready===(v.reason==="ready");
}

/** Explicit billable model test; closed results remain bound to the selected project. */
export function ModelConnection({project, revision, executor, model, locale, test, saved=null, onResult, readOnly=false, heading, local=false}: {local?:boolean;heading?:string; project: string; revision: string; executor: string; model: string; locale: Locale; test?: () => Promise<unknown>; saved?:ModelEvidence|null; onResult?:(value:ModelEvidence)=>void; readOnly?:boolean}) {
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
 const guidance = modelFailureText(locale, result?.reason || "runtime-error");
 const help = modelTestHelp(locale, local);
 return <div className="model-connection">
  {heading ? <div className="panel-heading"><h2>{heading}</h2>{!readOnly && <button type="button" className="ghost" disabled={busy} title={help} onClick={() => void run()}>{busy ? text.busy : text.title}</button>}</div>
    : !readOnly && <button type="button" className="ghost" disabled={busy} title={help} onClick={() => void run()}>{busy ? text.busy : text.title}</button>}
  {!readOnly && <p className="muted model-test-help">{help}</p>}
  {busy && <p role="status">{text.busy}</p>}
  {error && <p role="alert" className="alert">{text.error}</p>}
  {result && <div role="status" className={result.ready ? "success" : "alert"}><strong>{result.ready ? text.passed : text.failed}</strong><p>{result.executor} · {result.model}</p>{!result.ready && <p>{guidance}</p>}</div>}
 </div>;
}

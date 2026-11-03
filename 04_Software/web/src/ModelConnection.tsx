/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";
import { modelConnectionCopy, modelGuidance, validModelEvidence, type ModelEvidence } from "./modelEvidence";
import { ApiError } from "./errors";
import { modelFailureText, modelTestHelp } from "./localDiagnostics";

export { validModelEvidence, type ModelEvidence } from "./modelEvidence";

/** Explicit billable model test; closed results remain bound to the selected project. */
export function ModelConnection({project, revision, executor, model, locale, test, saved=null, onResult, readOnly=false, heading, local=false}: {local?:boolean;heading?:string; project: string; revision: string; executor: string; model: string; locale: Locale; test?: () => Promise<unknown>; saved?:ModelEvidence|null; onResult?:(value:ModelEvidence)=>void; readOnly?:boolean}) {
 const text = modelConnectionCopy[locale];
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
 const guidance = result ? (local && result.reason !== "tool-call-failed"
   ? modelFailureText(locale, result.reason) : modelGuidance(result.reason, locale)) : text.other;
 const help = local ? modelConnectionCopy[locale].help : modelTestHelp(locale, local);
 return <div className="model-connection">
  {heading ? <div className="panel-heading"><h2>{heading}</h2>{!readOnly && <button type="button" className="ghost" disabled={busy} title={help} onClick={() => void run()}>{busy ? text.busy : text.title}</button>}</div>
    : !readOnly && <button type="button" className="ghost" disabled={busy} title={help} onClick={() => void run()}>{busy ? text.busy : text.title}</button>}
  {!readOnly && <p className="muted model-test-help">{help}</p>}
  {busy && <p role="status">{text.busy}</p>}
  {error && <p role="alert" className="alert">{text.error}</p>}
  {result && <div role="status" className={result.ready ? "success" : "alert"}><strong>{result.ready ? text.passed : text.failed}</strong><p>{result.executor} · {result.model}</p>{!result.ready && <p>{guidance}</p>}</div>}
 </div>;
}

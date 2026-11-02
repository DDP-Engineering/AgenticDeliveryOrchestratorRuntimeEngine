/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {useEffect, useRef, useState, type FormEvent} from "react";
import type {Locale} from "./i18n";

export const executorCopy = {
 en: {tab:"Agent and model", title:"Provider API keys", help:"Save a provider API key for this project. The selected variable must be allowed by its executor configuration. Saving a key does not test sign-in. Changes require monitoring paused and no active work.", variable:"Credential variable", key:"API key", save:"Save API key", remove:"Disconnect project API key", saved:"Key saved. Test AI connection to verify model access.", removed:"Project API key removed.", error:"Could not update credentials. Check monitoring is paused, the project is idle and no candidate is pending.", missing:"Not set", project:"Saved for this project", environment:"Set on the ADORE server; manage it externally", modelHelp:"Enter a model ID supported by Pi and the provider. Model lists are not fetched automatically. New jobs use applied settings; active jobs keep their saved configuration."},
 ro: {tab:"Agent și model", title:"Chei API furnizor", help:"Salvează o cheie API pentru acest proiect. Variabila trebuie permisă de configurația executorului. Salvarea cheii nu testează autentificarea. Modificările cer monitorizarea oprită și fără lucru activ.", variable:"Variabilă credențiale", key:"Cheie API", save:"Salvează cheia API", remove:"Deconectează cheia API a proiectului", saved:"Cheie salvată. Testează conexiunea AI pentru verificarea accesului la model.", removed:"Cheia API a proiectului a fost eliminată.", error:"Credențialele nu au putut fi actualizate. Verifică monitorizarea oprită, proiectul inactiv și lipsa unei propuneri în așteptare.", missing:"Nesetată", project:"Salvată pentru proiect", environment:"Setată pe serverul ADORE; administrată extern", modelHelp:"Introdu un ID de model suportat de Pi și de furnizor. Lista modelelor nu se preia automat. Joburile noi folosesc setările aplicate; cele active păstrează configurația lor."},
 fr: {tab:"Agent et modèle", title:"Clés API du fournisseur", help:"Enregistrez une clé API pour ce projet, dans une variable autorisée. Cela ne teste pas la connexion. Le projet doit être inactif et sa surveillance suspendue.", variable:"Variable d’identification", key:"Clé API", save:"Enregistrer la clé API", remove:"Déconnecter la clé API du projet", saved:"Clé enregistrée. Testez la connexion IA pour vérifier l’accès au modèle.", removed:"Clé API du projet supprimée.", error:"Mise à jour impossible. Vérifiez que le projet est inactif, la surveillance suspendue et aucune proposition en attente.", missing:"Non définie", project:"Enregistrée pour ce projet", environment:"Définie sur le serveur ADORE ; gestion externe", modelHelp:"Saisissez un ID de modèle pris en charge par Pi et le fournisseur. Aucun catalogue automatique. Les nouvelles tâches utilisent les paramètres appliqués ; les tâches actives conservent leur configuration."},
 de: {tab:"Agent und Modell", title:"Anbieter-API-Schlüssel", help:"Speichern Sie einen API-Schlüssel für dieses Projekt in einer erlaubten Variable. Das prüft die Anmeldung nicht. Überwachung muss pausiert und das Projekt inaktiv sein.", variable:"Zugangsdaten-Variable", key:"API-Schlüssel", save:"API-Schlüssel speichern", remove:"Projekt-API-Schlüssel entfernen", saved:"Schlüssel gespeichert. Testen Sie die KI-Verbindung für den Modellzugriff.", removed:"Projekt-API-Schlüssel entfernt.", error:"Aktualisierung fehlgeschlagen. Projekt muss inaktiv, Überwachung pausiert und kein Vorschlag offen sein.", missing:"Nicht gesetzt", project:"Für dieses Projekt gespeichert", environment:"Auf dem ADORE-Server gesetzt; extern verwalten", modelHelp:"Geben Sie eine von Pi und dem Anbieter unterstützte Modell-ID ein. Keine automatische Modellliste. Neue Aufträge nutzen angewendete Einstellungen ; aktive behalten ihre Konfiguration."},
};
type Credentials = {project_id:string; revision:string; variables:Array<{name:string; source:"project"|"environment"|"missing"}>};
const emptyCredentialCopy={en:"No API key variables are allowed. Select the required names in Allowed credential variables.",ro:"Nu sunt permise variabile pentru chei API. Selectează numele necesare în Variabile de autentificare permise.",fr:"Aucune variable de clé API autorisée. Choisissez les noms nécessaires dans Variables d’identification autorisées.",de:"Keine API-Schlüsselvariablen erlaubt. Wählen Sie benötigte Namen unter Erlaubte Zugangsdaten-Variablen."};
const keys = new Set(["OPENAI_API_KEY","ANTHROPIC_API_KEY","GEMINI_API_KEY","GOOGLE_API_KEY","OPENROUTER_API_KEY","DASHSCOPE_API_KEY","AZURE_OPENAI_API_KEY","MISTRAL_API_KEY","XAI_API_KEY","GROQ_API_KEY"]);

/** Identify model-related settings within the project Settings category. */
export const isExecutorSetting = (key:string) => key.startsWith("executor.");

/** Secret drafts stay in component memory and are cleared after every mutation attempt. */
export function ExecutorCredentials({project,revision,locale,read,write,onChanged,disabled,embedded=false}: {embedded?:boolean;project:string;revision:string;locale:Locale;read:()=>Promise<unknown>;write:(method:string,body:unknown)=>Promise<unknown>;onChanged:()=>void;disabled:boolean}) {
 const c=executorCopy[locale];
 const [value,setValue]=useState<Credentials|null>(null), [variable,setVariable]=useState(""), [token,setToken]=useState(""), [busy,setBusy]=useState(false), [notice,setNotice]=useState(""), [error,setError]=useState(false);
 const active=useRef(true), pending=useRef(false);
 const parse=(raw:unknown):Credentials=>{
  const item=raw as Credentials;
  if (!item || Object.keys(item).sort().join()!=="project_id,revision,variables" || item.project_id!==project || item.revision!==revision || !Array.isArray(item.variables) || item.variables.some(v=>!v || Object.keys(v).sort().join()!=="name,source" || !keys.has(v.name) || !["project","environment","missing"].includes(v.source)) || new Set(item.variables.map(v=>v.name)).size!==item.variables.length) throw Error("invalid response");
  return item;
 };
 useEffect(()=>{active.current=true; void read().then(raw=>{if(active.current){const item=parse(raw);setValue(item);setVariable(item.variables[0]?.name||"");}}).catch(()=>{if(active.current)setError(true);});return()=>{active.current=false;};},[]);
 const current=value?.variables.find(v=>v.name===variable);
 const mutate=async(method:string)=>{
  if(pending.current || disabled || !value || !variable)return;
  pending.current=true;setBusy(true);setError(false);setNotice("");
  try {const raw=await write(method,{revision,variable,...(method==="PUT"?{token}: {})}); if(!active.current)return;setValue(parse(raw));setNotice(method==="PUT"?c.saved:c.removed);onChanged();}
  catch {if(active.current)setError(true);}
  finally {if(active.current){setToken("");setBusy(false);pending.current=false;}}
 };
 const submit=(e:FormEvent)=>{e.preventDefault();void mutate("PUT");};
 return <section className={embedded ? "executor-credentials-embedded" : "panel wide-panel"} id="executor-credentials">{embedded ? <h3>{c.title}</h3> : <h2>{c.title}</h2>}<p className="muted">{c.help}</p>
  {value?.variables.length===0 ? <p role="note">{emptyCredentialCopy[locale]}</p> : <form className="form-stack" onSubmit={submit}><fieldset disabled={disabled||busy||!value}>
   <label>{c.variable}<select aria-label={c.variable} value={variable} onChange={e=>{setVariable(e.target.value);setToken("");setNotice("");}}>{value?.variables.map(v=><option key={v.name} value={v.name}>{v.name}</option>)}</select></label>
   {current&&<p>{c[current.source]}</p>}
   <label>{c.key}<input aria-label={c.key} type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="new-password" maxLength={4096} required disabled={current?.source==="environment"}/></label>
   <div className="button-row"><button className="primary" disabled={!variable||current?.source==="environment"}>{c.save}</button><button className="ghost" type="button" disabled={current?.source!=="project"} onClick={()=>void mutate("DELETE")}>{c.remove}</button></div>
  </fieldset></form>}
  {notice&&<p role="status">{notice}</p>}{error&&<p role="alert" className="alert">{c.error}</p>}
 </section>;
}

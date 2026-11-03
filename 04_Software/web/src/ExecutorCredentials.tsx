/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {useEffect, useRef, useState, type FormEvent} from "react";
import type {Locale} from "./i18n";
import {CHATGPT, connectionCopy} from "./agentConnection";

export const executorCopy = {
 en: {tab:"Agent and model", title:"Provider API key", help:"Save the API key of the configured provider for this project. It is kept in the project's credential store and reaches Pi only as the provider's variable, never in the configuration file. Saving a key does not test it. Changes require monitoring paused and no active work.", variable:"Credential variable", key:"API key", save:"Save API key", remove:"Disconnect project API key", saved:"Key saved. Test AI connection to verify model access.", removed:"Project API key removed.", error:"Could not update credentials. Check monitoring is paused, the project is idle and no candidate is pending.", missing:"Not set", project:"Saved for this project", environment:"Set on the ADORE server; manage it externally", modelHelp:"Provider, model and endpoint change together through one reviewed change. New jobs use applied settings; active jobs keep their saved configuration."},
 ro: {tab:"Agent și model", title:"Cheia API a furnizorului", help:"Salvează cheia API a furnizorului configurat pentru acest proiect. Se păstrează în depozitul de credențiale al proiectului și ajunge la Pi doar ca variabila furnizorului, niciodată în fișierul de configurare. Salvarea cheii nu o testează. Modificările cer monitorizarea oprită și fără lucru activ.", variable:"Variabilă credențiale", key:"Cheie API", save:"Salvează cheia API", remove:"Deconectează cheia API a proiectului", saved:"Cheie salvată. Testează conexiunea AI pentru verificarea accesului la model.", removed:"Cheia API a proiectului a fost eliminată.", error:"Credențialele nu au putut fi actualizate. Verifică monitorizarea oprită, proiectul inactiv și lipsa unei propuneri în așteptare.", missing:"Nesetată", project:"Salvată pentru proiect", environment:"Setată pe serverul ADORE; administrată extern", modelHelp:"Furnizorul, modelul și endpointul se schimbă împreună printr-o singură modificare revizuită. Joburile noi folosesc setările aplicate; cele active păstrează configurația lor."},
 fr: {tab:"Agent et modèle", title:"Clé API du fournisseur", help:"Enregistrez la clé API du fournisseur configuré pour ce projet. Elle reste dans le magasin d’identifiants du projet et n’atteint Pi que par la variable du fournisseur, jamais dans le fichier de configuration. Cela ne la teste pas. Le projet doit être inactif et sa surveillance suspendue.", variable:"Variable d’identification", key:"Clé API", save:"Enregistrer la clé API", remove:"Déconnecter la clé API du projet", saved:"Clé enregistrée. Testez la connexion IA pour vérifier l’accès au modèle.", removed:"Clé API du projet supprimée.", error:"Mise à jour impossible. Vérifiez que le projet est inactif, la surveillance suspendue et aucune proposition en attente.", missing:"Non définie", project:"Enregistrée pour ce projet", environment:"Définie sur le serveur ADORE ; gestion externe", modelHelp:"Fournisseur, modèle et point de terminaison changent ensemble en une seule modification revue. Les nouvelles tâches utilisent les paramètres appliqués ; les tâches actives conservent leur configuration."},
 de: {tab:"Agent und Modell", title:"API-Schlüssel des Anbieters", help:"Speichern Sie den API-Schlüssel des konfigurierten Anbieters für dieses Projekt. Er bleibt im Zugangsdatenspeicher des Projekts und erreicht Pi nur als Variable des Anbieters, nie in der Konfigurationsdatei. Das prüft ihn nicht. Überwachung muss pausiert und das Projekt inaktiv sein.", variable:"Zugangsdaten-Variable", key:"API-Schlüssel", save:"API-Schlüssel speichern", remove:"Projekt-API-Schlüssel entfernen", saved:"Schlüssel gespeichert. Testen Sie die KI-Verbindung für den Modellzugriff.", removed:"Projekt-API-Schlüssel entfernt.", error:"Aktualisierung fehlgeschlagen. Projekt muss inaktiv, Überwachung pausiert und kein Vorschlag offen sein.", missing:"Nicht gesetzt", project:"Für dieses Projekt gespeichert", environment:"Auf dem ADORE-Server gesetzt; extern verwalten", modelHelp:"Anbieter, Modell und Endpunkt ändern sich gemeinsam in einer geprüften Änderung. Neue Aufträge nutzen angewendete Einstellungen; aktive behalten ihre Konfiguration."},
};
type Credentials = {project_id:string; revision:string; variables:Array<{name:string; source:"project"|"environment"|"missing"}>};
const emptyCredentialCopy={en:"This provider needs no API key here.",ro:"Acest furnizor nu are nevoie aici de o cheie API.",fr:"Ce fournisseur n’a pas besoin de clé API ici.",de:"Dieser Anbieter braucht hier keinen API-Schlüssel."};
// The server names the configured provider's variable; the browser checks only its shape.
const variableName=(name:unknown)=>typeof name==="string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(name);

/** Identify model-related settings within the project Settings category. */
export const isExecutorSetting = (key:string) => key.startsWith("executor.");

/** Secret drafts stay in component memory and are cleared after every mutation attempt. */
export function ExecutorCredentials({project,revision,locale,read,write,onChanged,disabled,embedded=false,provider=""}: {embedded?:boolean;provider?:string;project:string;revision:string;locale:Locale;read:()=>Promise<unknown>;write:(method:string,body:unknown)=>Promise<unknown>;onChanged:()=>void;disabled:boolean}) {
 const c=executorCopy[locale];
 const [value,setValue]=useState<Credentials|null>(null), [variable,setVariable]=useState(""), [token,setToken]=useState(""), [busy,setBusy]=useState(false), [notice,setNotice]=useState(""), [error,setError]=useState(false);
 const active=useRef(true), pending=useRef(false);
 const parse=(raw:unknown):Credentials=>{
  const item=raw as Credentials;
  if (!item || Object.keys(item).sort().join()!=="project_id,revision,variables" || item.project_id!==project || item.revision!==revision || !Array.isArray(item.variables) || item.variables.some(v=>!v || Object.keys(v).sort().join()!=="name,source" || !variableName(v.name) || !["project","environment","missing"].includes(v.source)) || new Set(item.variables.map(v=>v.name)).size!==item.variables.length) throw Error("invalid response");
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
  {value?.variables.length===0 ? <p role="note">{provider===CHATGPT ? connectionCopy[locale].chatgptNote : emptyCredentialCopy[locale]}</p> : <form className="form-stack" onSubmit={submit}><fieldset disabled={disabled||busy||!value}>
   <label>{c.variable}<select aria-label={c.variable} value={variable} onChange={e=>{setVariable(e.target.value);setToken("");setNotice("");}}>{value?.variables.map(v=><option key={v.name} value={v.name}>{v.name}</option>)}</select></label>
   {current&&<p>{c[current.source]}</p>}
   <label>{c.key}<input aria-label={c.key} type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="new-password" maxLength={4096} required disabled={current?.source==="environment"}/></label>
   <div className="button-row"><button className="primary" disabled={!variable||current?.source==="environment"}>{c.save}</button><button className="ghost" type="button" disabled={current?.source!=="project"} onClick={()=>void mutate("DELETE")}>{c.remove}</button></div>
  </fieldset></form>}
  {notice&&<p role="status">{notice}</p>}{error&&<p role="alert" className="alert">{c.error}</p>}
 </section>;
}

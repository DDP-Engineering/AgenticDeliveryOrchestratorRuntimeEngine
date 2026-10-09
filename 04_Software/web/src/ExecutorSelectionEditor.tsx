/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type {Locale} from "./i18n";
import type {SettingMeta} from "./settings";
import {agentNames,agentSettingsCopy,codingAgents,executorSelectionDraft,type ExecutorSelection} from "./executorSettings";

/** One atomic draft follows agent selection and server-authoritative launch presets. */
export function ExecutorSelectionEditor({value,config,settings,locale,disabled,onChange}:{value:string;config:Record<string,unknown>;settings:SettingMeta[];locale:Locale;disabled:boolean;onChange:(value:string)=>void}) {
 const c=agentSettingsCopy[locale];
 let draft:ExecutorSelection;
 try {draft=JSON.parse(value);} catch {draft=executorSelectionDraft(config);}
 const choices=(settings.find(s=>s.key===`executor.commands.${draft.agent}.command`)?.choices || []).map(String);
 const change=(next:ExecutorSelection)=>onChange(JSON.stringify(next));
 return <div className="executor-selection-editor">
  <p className="muted">{c.setup}</p>
  <label>{c.agent}<select aria-label={c.agent} disabled={disabled} value={draft.agent} onChange={e=>{
   const next=executorSelectionDraft(config,e.target.value);
   next.command ||= String(settings.find(s=>s.key===`executor.commands.${next.agent}.command`)?.choices?.[0] || "");
   change(next);
  }}>{codingAgents.map(agent=><option key={agent} value={agent}>{agentNames[agent]}</option>)}</select></label>
  <label className="executor-launch-field">{c.command}{choices.length ? <select aria-label={c.command} disabled={disabled} value={draft.command} onChange={e=>change({...draft,command:e.target.value})}>
   {!choices.includes(draft.command)&&<option value={draft.command}>{draft.command || "—"}</option>}
   {choices.map(command=><option key={command} value={command}>{command}</option>)}
  </select> : <input aria-label={c.command} disabled={disabled} value={draft.command} maxLength={4096} required onChange={e=>change({...draft,command:e.target.value})}/>}</label>
  <label>{c.model}<input aria-label={c.model} disabled={disabled} value={draft.model} maxLength={200} required onChange={e=>change({...draft,model:e.target.value})}/></label>
  <p className="muted">{c.modelHelp}</p>
 </div>;
}

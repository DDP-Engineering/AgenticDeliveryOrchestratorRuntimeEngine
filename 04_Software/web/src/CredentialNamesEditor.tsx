/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type {Locale} from "./i18n";
import {credentialEditorCopy,validCredentialNames} from "./executorSettings";

/** Native dropdown adds distinct names; selected values remain visible and removable. */
export function CredentialNamesEditor({value,choices,locale,disabled,onChange}:{value:string;choices:string[];locale:Locale;disabled:boolean;onChange:(value:string)=>void}) {
 const c=credentialEditorCopy[locale];
 let names:string[]=[];
 try {const parsed=JSON.parse(value);if(validCredentialNames(parsed)) names=parsed;} catch {/* Invalid drafts cannot enable preparation. */}
 return <div className="credential-names-editor">
  <select aria-label={c.add} aria-describedby="help-executor.env_keys" disabled={disabled} value="" onChange={event=>{
   const name=event.target.value;
   if(choices.includes(name)&&!names.includes(name)&&names.length<32) onChange(JSON.stringify([...names,name]));
  }}>
   <option value="" disabled>{c.choose}</option>
   {choices.map(name=><option key={name} value={name} disabled={names.includes(name)||names.length>=32}>{name}</option>)}
  </select>
  {names.length>0&&<ul aria-label={c.selected}>{names.map(name=><li key={name}><code>{name}</code><button type="button" className="text-button" aria-label={`${c.remove} ${name}`} disabled={disabled} onClick={()=>onChange(JSON.stringify(names.filter(item=>item!==name)))}>×</button></li>)}</ul>}
 </div>;
}

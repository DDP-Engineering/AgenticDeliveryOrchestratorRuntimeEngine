/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { validConnection } from "./agentConnection.ts";

/** Only editable strings and the reviewed base revision survive a tab refresh. */
export type SavedDraft = { revision: string; drafts: Record<string,string>; editing: string[] };
type Storage = Pick<globalThis.Storage,"getItem"|"setItem"|"removeItem">;
const prefix = "adore-project-draft:";
const key = (account:number,project:string) => `${prefix}${account}:${project}`;
const safeKey = (value:string) => /^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/.test(value)
  && !/(?:^|\.)(?:secret|password|token|access_token|api_key|credentials)(?:\.|$)/.test(value);
function safeValue(name:string,text:string):boolean {
  if(name!=="executor.connection")return true;
  try{return validConnection(JSON.parse(text));}catch{return false;}
}
function valid(value:unknown):value is SavedDraft {
  const row=value as SavedDraft;
  return !!row && typeof row==="object" && Object.keys(row).sort().join() === "drafts,editing,revision"
    && typeof row.revision==="string" && /^[a-f0-9]{64}$/.test(row.revision)
    && !!row.drafts && typeof row.drafts==="object" && !Array.isArray(row.drafts)
    && Object.keys(row.drafts).length<=128
    && Object.entries(row.drafts).every(([name,text])=>safeKey(name) && typeof text==="string" && text.length<=8192 && safeValue(name,text))
    && Array.isArray(row.editing) && row.editing.length<=128 && row.editing.every(name=>typeof name==="string" && safeKey(name));
}

/** Refuse damaged current-format evidence until explicit Discard; never reinterpret it. */
export function readDraft(storage:Storage,account:number,project:string):SavedDraft|{corrupt:true}|null {
  try {
    const raw=storage.getItem(key(account,project)); if(raw===null)return null;
    if(raw.length>131072)return {corrupt:true};
    const value:unknown=JSON.parse(raw); return valid(value)?value:{corrupt:true};
  } catch {return {corrupt:true};}
}
export function writeDraft(storage:Storage,account:number,project:string,value:SavedDraft):boolean {
  if(!valid(value))return false;
  const raw=JSON.stringify(value); if(raw.length>131072)return false;
  try {storage.setItem(key(account,project),raw);return true;}catch{return false;}
}
export function clearDraft(storage:Storage,account:number,project:string):void {
  try {storage.removeItem(key(account,project));}catch{/* The caller retains its in-memory draft. */}
}
/** Logout clears this tab's private draft evidence across all projects/accounts. */
export function clearPrivateDrafts(storage:globalThis.Storage):void {
  try {
    for(let index=storage.length-1;index>=0;index--){const name=storage.key(index);if(name?.startsWith(prefix))storage.removeItem(name);}
  } catch {/* Unavailable tab storage must not prevent account sign-out. */}
}

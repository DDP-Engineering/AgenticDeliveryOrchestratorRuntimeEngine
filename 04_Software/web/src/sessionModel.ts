/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { ApiError } from "./errors.ts";

export type AgentSession = {id:string;stage:string;attempt:number;start_at:string|null;end_at:string;outcome:"succeeded"|"failed"|"timed_out";exit_code:number};
export type SessionItem = {kind:"prompt"|"assistant"|"reasoning"|"tool_call"|"tool_result"|"turn"|"usage"|"notice";text:string;tool?:string;call_id?:string;is_error?:boolean;parts?:SessionItem[];usage?:Record<string,number|Record<string,number>>};
export type SessionPage = {session:AgentSession;items:SessionItem[];next_cursor:number|null};
const attempt = /^(frame|specify|design|build|validate)-attempt-([1-9][0-9]*)-attempt1(?:-([2-9]|[1-9][0-9]+))?$/;
const bounded = (value:unknown):value is string => typeof value === "string" && new TextEncoder().encode(value).length <= 16*1024;
const invalid = () => new ApiError("unexpected_response");

/** Validate server metadata before rendering an attempt or constructing its path. */
function session(value:unknown):AgentSession {
  const item=value as AgentSession, match=typeof item?.id==="string"?attempt.exec(item.id):null;
  if(!match || item.stage!==match[1] || !Number.isSafeInteger(item.attempt) || item.attempt!==Number(match[2]) ||
    item.start_at!==null && (typeof item.start_at!=="string" || !Number.isFinite(Date.parse(item.start_at))) ||
    typeof item.end_at!=="string" || !Number.isFinite(Date.parse(item.end_at)) || !Number.isSafeInteger(item.exit_code) ||
    !["succeeded","failed","timed_out"].includes(item.outcome)) throw invalid();
  return item;
}

export function readSessions(value:unknown):AgentSession[] {
  const data=value as {sessions:unknown[]};
  if(!data || !Array.isArray(data.sessions) || data.sessions.length>10000) throw invalid();
  const rows=data.sessions.map(session);
  if(new Set(rows.map(row=>row.id)).size!==rows.length) throw invalid();
  return rows;
}

/** Reject malformed transport, unsafe cursors and nonfinite usage at the API boundary. */
export function readSessionPage(value:unknown,id:string,cursor:number,admin:boolean):SessionPage {
  const data=value as SessionPage;
  if(!data || session(data.session).id!==id || !Array.isArray(data.items) || data.items.length>200 ||
    !(data.next_cursor===null || Number.isSafeInteger(data.next_cursor) && data.next_cursor>cursor)) throw invalid();
  const flattened: SessionItem[]=[];
  for(const item of data.items) {
    if(item?.parts!==undefined) {
      if(item.kind!=="assistant" || item.text!=="" || !Array.isArray(item.parts) || item.parts.length<2 || item.parts.length>3 || item.parts.some(part=>!part || part.parts!==undefined || !["assistant","reasoning","usage"].includes(part.kind))) throw invalid();
      flattened.push(...item.parts);
    } else flattened.push(item);
  }
  for(const item of flattened) {
    if(!item || !["prompt","assistant","reasoning","tool_call","tool_result","turn","usage","notice"].includes(item.kind) || !bounded(item.text)) throw invalid();
    if(["tool_call","tool_result"].includes(item.kind) && (!bounded(item.tool) || !bounded(item.call_id))) throw invalid();
    if(item.kind==="tool_result" && typeof item.is_error!=="boolean") throw invalid();
    if(item.kind==="usage") {
      if(!item.usage || typeof item.usage!=="object" || Array.isArray(item.usage)) throw invalid();
      for(const [key,value] of Object.entries(item.usage)) {
        if(key==="cost") {
          if(!admin || !value || typeof value!=="object" || Array.isArray(value) || Object.values(value).some(number=>typeof number!=="number" || !Number.isFinite(number) || number<0)) throw invalid();
        } else if(!["input","output","cacheRead","cacheWrite","reasoning","totalTokens"].includes(key) || !Number.isSafeInteger(value) || Number(value)<0) throw invalid();
      }
    }
  }
  return data;
}

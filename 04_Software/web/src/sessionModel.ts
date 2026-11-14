/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { ApiError } from "./errors.ts";

export type AgentSession = {id:string;stage:string;attempt:number;start_at:string|null;end_at:string|null;outcome:"succeeded"|"failed"|"timed_out"|null;exit_code:number|null;live?:boolean;archive_id?:string};
export type SessionItem = {kind:"prompt"|"assistant"|"reasoning"|"tool_call"|"tool_result"|"turn"|"usage"|"notice";text:string;tool?:string;call_id?:string;is_error?:boolean;parts?:SessionItem[];usage?:Record<string,number|Record<string,number>>};
export type SessionPage = {session:AgentSession;items:SessionItem[];next_cursor:number|null;session_ended?:false;continuity?:string;thinking?:boolean|null;read_bound?:boolean};
export type EndedSession = {session_ended:true;archive_id:string|null;items:SessionItem[];next_cursor:null};
export type SessionActivity = {thinking:boolean;tools:Record<string,string>};
export const shouldPollSession = (lifecycle:string,active:boolean,visible:boolean,live:boolean) => lifecycle==="working" && active && visible && live;

/** Apply completed tool boundaries and bounded thinking hints across cursor pages. */
export function applySessionActivity(previous:SessionActivity,page:Pick<SessionPage,"items"|"thinking">):SessionActivity {
  const tools:Record<string,string>=Object.assign(Object.create(null),previous.tools);
  for(const item of page.items.flatMap(item=>item.parts||[item])) {
    if(item.kind==="tool_call")tools[item.call_id!]=item.tool!;
    if(item.kind==="tool_result")delete tools[item.call_id!];
  }
  return {tools,thinking:page.thinking??previous.thinking};
}

const attempt = /^(frame|specify|design|build|validate)-attempt-([1-9][0-9]*)-attempt1(?:-([2-9]|[1-9][0-9]+))?$/;
const liveId = /^live-[a-f0-9]{32}$/;
const bounded = (value:unknown):value is string => typeof value === "string" && new TextEncoder().encode(value).length <= 16*1024;
const invalid = () => new ApiError("unexpected_response");

/** Validate server metadata before rendering an attempt or constructing its path. */
function session(value:unknown):AgentSession {
  const item=value as AgentSession;
  if(item?.live!==undefined&&typeof item.live!=="boolean")throw invalid();
  if(item?.live===true) {
    const match=typeof item.archive_id==="string"?attempt.exec(item.archive_id):null;
    if(!liveId.test(item.id) || !match || item.stage!==match[1] || item.attempt!==Number(match[2]) ||
      !Number.isSafeInteger(item.attempt) || typeof item.start_at!=="string" || !Number.isFinite(Date.parse(item.start_at)) ||
      item.end_at!==null || item.outcome!==null || item.exit_code!==null)throw invalid();
  } else {
    const match=typeof item?.id==="string"?attempt.exec(item.id):null;
    if(!match || item.stage!==match[1] || !Number.isSafeInteger(item.attempt) || item.attempt!==Number(match[2]) ||
      item.start_at!==null && (typeof item.start_at!=="string" || !Number.isFinite(Date.parse(item.start_at))) ||
      typeof item.end_at!=="string" || !Number.isFinite(Date.parse(item.end_at)) || !Number.isSafeInteger(item.exit_code) ||
      !["succeeded","failed","timed_out"].includes(item.outcome!)) throw invalid();
  }
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
export function readSessionPage(value:unknown,id:string,cursor:number,admin:boolean):SessionPage|EndedSession {
  const ended=value as EndedSession;
  if(ended?.session_ended===true) {
    if(!liveId.test(id) || !(ended.archive_id===null || typeof ended.archive_id==="string" && attempt.test(ended.archive_id)) ||
      !Array.isArray(ended.items) || ended.items.length || ended.next_cursor!==null)throw invalid();
    return ended;
  }
  const data=value as SessionPage;
  if(!data || session(data.session).id!==id || !Array.isArray(data.items) || data.items.length>200 ||
    !(data.next_cursor===null || Number.isSafeInteger(data.next_cursor) && (data.session.live?data.next_cursor>=cursor:data.next_cursor>cursor))) throw invalid();
  if(data.session.live && (data.session_ended!==false ||
    !(data.read_bound===true && data.next_cursor===null || typeof data.continuity==="string" && /^[a-f0-9]{64}$/.test(data.continuity)) ||
    !(data.thinking===null || typeof data.thinking==="boolean")))throw invalid();
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

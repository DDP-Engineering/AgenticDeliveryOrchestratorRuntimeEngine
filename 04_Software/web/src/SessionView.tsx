/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type {Locale,MessageKey} from "./i18n";
import {sessionCopy,workflowStageLabel} from "./jobCopy";
import {readSessions,readSessionPage,type AgentSession,type SessionItem} from "./sessionModel";
type Request=<T>(path:string,method?:string,body?:unknown,csrf?:string)=>Promise<T>;

/** On-demand history only; stale completions cannot replace another selected attempt. */
export function SessionView({project,run,workflow,locale,admin,request,t}:{project:string;run:string;workflow:"aegis"|"direct";locale:Locale;admin:boolean;request:Request;t:(key:MessageKey)=>string}) {
  const copy=sessionCopy[locale];
  const [sessions,setSessions]=useState<AgentSession[]>([]),[selected,setSelected]=useState("");
  const [items,setItems]=useState<SessionItem[]>([]),[cursor,setCursor]=useState<number|null>(null);
  const [loading,setLoading]=useState(true),[pageLoading,setPageLoading]=useState(false),[error,setError]=useState(false),[pageError,setPageError]=useState(false);
  const [reload,setReload]=useState(0);
  const generation=useRef(0),pending=useRef(false);
  const base=`/jobs/${encodeURIComponent(project)}/${encodeURIComponent(run)}/sessions`;
  useEffect(()=>{
    let active=true;
    setLoading(true);setError(false);setSessions([]);setSelected("");
    request(base).then(value=>{
      const rows=readSessions(value);
      if(active){setSessions(rows);setSelected(rows[0]?.id||"");setLoading(false);}
    }).catch(()=>{if(active){setError(true);setLoading(false);}});
    return()=>{active=false;generation.current++;};
  },[base,reload]);
  const load=async(id:string,offset:number,append:boolean)=>{
    if(pending.current)return;
    pending.current=true;const current=++generation.current;
    setPageLoading(true);setPageError(false);
    try {
      const page=readSessionPage(await request(`${base}/${encodeURIComponent(id)}?cursor=${offset}&limit=200`),id,offset,admin);
      if(current===generation.current){setItems(previous=>{const visible=page.items.flatMap(item=>item.parts||[item]);return append?[...previous,...visible]:visible;});setCursor(page.next_cursor);}
    }catch{if(current===generation.current)setPageError(true);}
    finally{if(current===generation.current){setPageLoading(false);pending.current=false;}}
  };
  useEffect(()=>{
    generation.current++;pending.current=false;setItems([]);setCursor(null);setPageError(false);setPageLoading(false);
    if(selected)void load(selected,0,false);
    return()=>{generation.current++;pending.current=false;};
  },[selected,base]);
  const date=(value:string)=>new Intl.DateTimeFormat(locale,{dateStyle:"medium",timeStyle:"medium"}).format(new Date(value));
  const renderItem=(item:SessionItem,index:number)=>{
    const label=copy[item.kind];
    if(item.kind==="reasoning")return <li key={index}><details><summary>{label}</summary><pre tabIndex={0}>{item.text}</pre></details></li>;
    if(item.kind==="tool_call" || item.kind==="tool_result")return <li key={index}><details className="session-tool"><summary>{label} · {item.tool}{item.is_error?` · ${t("failed")}`:""} · {item.text.slice(0,100)}</summary><pre tabIndex={0}>{item.text}</pre></details></li>;
    return <li key={index} className={`session-${item.kind}`}><strong>{label}</strong>{item.kind==="usage"?<dl className="session-usage">{Object.entries(item.usage||{}).map(([key,value])=><div key={key}><dt>{copy.counters[key as keyof typeof copy.counters]||key}</dt><dd>{typeof value==="object"?Object.entries(value).map(([name,amount])=>`${name}: ${amount}`).join(" · "):value}</dd></div>)}</dl>:<pre tabIndex={0}>{item.kind==="turn"?(item.text==="turn_start"?copy.turnStart:copy.turnEnd):item.text}</pre>}</li>;
  };
  return <section className="agent-sessions" aria-label={copy.title}>
    <p className="field-hint">{copy.help}</p>
    {loading&&<p role="status">{t("loadingData")}</p>}
    {error&&<p role="alert">{copy.failed} <button className="ghost" onClick={()=>setReload(value=>value+1)}>{t("retry")}</button></p>}
    {!loading&&!error&&!sessions.length&&<p role="status">{copy.empty}</p>}
    {sessions.length>0&&<label>{copy.attempt}<select aria-label={copy.attempt} value={selected} onChange={event=>setSelected(event.target.value)}>{sessions.map(row=><option value={row.id} key={row.id}>{workflowStageLabel(row.stage,workflow,t)} · {row.attempt} · {date(row.end_at)} · {copy[row.outcome === "failed" ? "failedOutcome" : row.outcome]}</option>)}</select></label>}
    {selected&&<p className="field-hint">{copy.startUnknown}</p>}
    <ol className="session-timeline">{items.map(renderItem)}</ol>
    {pageLoading&&<p role="status">{t("loadingData")}</p>}
    {pageError&&<p role="alert">{copy.failed} <button className="ghost" onClick={()=>void load(selected,cursor??0,items.length>0)}>{t("retry")}</button></p>}
    {cursor!==null&&!pageError&&<button className="ghost" disabled={pageLoading} onClick={()=>void load(selected,cursor,true)}>{copy.more}</button>}
  </section>;
}

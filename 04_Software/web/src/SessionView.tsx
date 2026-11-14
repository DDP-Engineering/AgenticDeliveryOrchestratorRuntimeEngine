/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type {Locale,MessageKey} from "./i18n";
import {sessionCopy,workflowStageLabel} from "./jobCopy";
import {readSessions,readSessionPage,shouldPollSession,applySessionActivity,type AgentSession,type SessionItem,type SessionActivity} from "./sessionModel";

type Request=<T>(path:string,method?:string,body?:unknown,csrf?:string)=>Promise<T>;

/** Follow a launch with fenced cursor reads; explicit history selection owns the view. */
export function SessionView({project,run,workflow,locale,admin,request,t,lifecycle,active}:{project:string;run:string;workflow:"aegis"|"direct";locale:Locale;admin:boolean;request:Request;t:(key:MessageKey)=>string;lifecycle:string;active:boolean}) {
  const copy=sessionCopy[locale];
  const [sessions,setSessions]=useState<AgentSession[]>([]),[selected,setSelected]=useState("");
  const [items,setItems]=useState<SessionItem[]>([]),[cursor,setCursor]=useState<number|null>(null);
  const [activity,setActivity]=useState<SessionActivity>({thinking:false,tools:{}});
  const [loading,setLoading]=useState(true),[pageLoading,setPageLoading]=useState(false),[error,setError]=useState(false),[pageError,setPageError]=useState(false);
  const [visible,setVisible]=useState(document.visibilityState!=="hidden");
  const [reload,setReload]=useState(0),[pageVersion,setPageVersion]=useState(0);
  const generation=useRef(0),pending=useRef(false),accepted=useRef(false),proof=useRef<string|undefined>(undefined),following=useRef(true);
  const base=`/jobs/${encodeURIComponent(project)}/${encodeURIComponent(run)}/sessions`;
  const latest=useRef({sessions,selected,cursor,lifecycle,active,visible});
  latest.current={sessions,selected,cursor,lifecycle,active,visible};
  const refresh=async(endedArchive?:string|null)=>{
    const current=generation.current;
    try {
      const rows=readSessions(await request(base));
      if(current!==generation.current)return;
      setSessions(rows);setLoading(false);setError(false);
      const old=latest.current.selected;
      if(following.current && (endedArchive!==undefined || !old)) {
        const next=rows.find(row=>row.live)?.id || (endedArchive && rows.find(row=>row.id===endedArchive)?.id) || rows[0]?.id || "";
        setSelected(next);
        if(next===old&&endedArchive!==undefined&&rows.some(row=>row.id===next&&row.live))setPageVersion(value=>value+1);
      }
    }catch{if(current===generation.current){setLoading(false);setError(true);}}
  };
  const load=async(id:string,offset:number,append:boolean)=>{
    if(pending.current)return;
    pending.current=true;const current=generation.current;
    const row=latest.current.sessions.find(row=>row.id===id);
    const query=new URLSearchParams({cursor:String(offset),limit:"200"});
    if(row?.live){query.set("archive_id",row.archive_id!);if(proof.current)query.set("continuity",proof.current);}
    setPageLoading(true);setPageError(false);
    try {
      const page=readSessionPage(await request(`${base}/${encodeURIComponent(id)}?${query}`),id,offset,admin);
      if(current!==generation.current)return;
      if(page.session_ended===true) {
        proof.current=undefined;
        // Reload completed evidence from zero, including the launch's unseen tail.
        await refresh(page.archive_id);
      } else {
        setItems(previous=>{const visible=page.items.flatMap(item=>item.parts||[item]);return append?[...previous,...visible]:visible;});
        setCursor(page.next_cursor);proof.current=page.continuity;accepted.current=true;
        setActivity(previous=>applySessionActivity(previous,page));
      }
    }catch{if(current===generation.current)setPageError(true);}
    finally{if(current===generation.current){setPageLoading(false);pending.current=false;}}
  };
  const poll=useRef(()=>{});
  poll.current=()=>{
    const state=latest.current,row=state.sessions.find(row=>row.id===state.selected);
    if(!shouldPollSession(state.lifecycle,state.active,state.visible,following.current)||pending.current)return;
    if(row?.live && state.cursor!==null)void load(row.id,state.cursor,true);
    else if(!row?.live)void refresh(null);
  };
  useEffect(()=>{
    const changed=()=>setVisible(document.visibilityState!=="hidden");
    document.addEventListener("visibilitychange",changed);
    return()=>document.removeEventListener("visibilitychange",changed);
  },[]);
  useEffect(()=>{
    if(!active||!visible||lifecycle!=="working")return;
    const timer=window.setInterval(()=>poll.current(),3000);
    return()=>window.clearInterval(timer);
  },[active,visible,lifecycle]);
  useEffect(()=>{
    generation.current++;pending.current=false;setPageLoading(false);
    if(active&&visible)void refresh();
    return()=>{generation.current++;pending.current=false;};
  },[base,reload,active,visible]);
  useEffect(()=>{
    if(!selected)return;
    generation.current++;pending.current=false;proof.current=undefined;accepted.current=false;
    setItems([]);setCursor(null);setActivity({thinking:false,tools:{}});setPageError(false);setPageLoading(false);
    if(selected&&active&&visible)void load(selected,0,false);
    return()=>{generation.current++;pending.current=false;};
  },[selected,base,pageVersion]);
  // Live resumes at its cursor. Accepted archives keep their exact pages,
  // including EOF; only an unaccepted initial history read needs resuming.
  useEffect(()=>{
    const row=latest.current.sessions.find(row=>row.id===selected);
    if(active&&visible&&selected&&!pending.current&&(row?.live||!accepted.current))
      void load(selected,cursor??0,cursor!==null);
  },[active,visible]);
  useEffect(()=>{
    const row=latest.current.sessions.find(row=>row.id===latest.current.selected);
    if(lifecycle!=="working"&&active&&visible&&row?.live) {
      generation.current++;pending.current=false;
      void load(row.id,latest.current.cursor??0,true);
    }
  },[lifecycle]);
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
    {sessions.length>0&&<label>{copy.attempt}<select aria-label={copy.attempt} value={selected} onChange={event=>{following.current=Boolean(sessions.find(row=>row.id===event.target.value)?.live);setSelected(event.target.value);}}>{sessions.map(row=><option value={row.id} key={row.id}>{workflowStageLabel(row.stage,workflow,t)} · {row.attempt} · {row.live?copy.live:date(row.end_at!)} · {row.live?copy.live:copy[row.outcome === "failed" ? "failedOutcome" : row.outcome!]}</option>)}</select></label>}
    {selected&&!sessions.find(row=>row.id===selected)?.live&&<p className="field-hint">{copy.startUnknown}</p>}
    {sessions.find(row=>row.id===selected)?.live&&(activity.thinking||Object.keys(activity.tools).length>0)&&<p role="status">{copy.working.replace("{activity}",Object.values(activity.tools).at(-1)||copy.thinking)}</p>}
    <ol className="session-timeline">{items.map(renderItem)}</ol>
    {pageLoading&&<p role="status">{t("loadingData")}</p>}
    {pageError&&<p role="alert">{copy.failed} <button className="ghost" onClick={()=>void load(selected,cursor??0,items.length>0)}>{t("retry")}</button></p>}
    {cursor!==null&&!sessions.find(row=>row.id===selected)?.live&&!pageError&&<button className="ghost" disabled={pageLoading} onClick={()=>void load(selected,cursor,true)}>{copy.more}</button>}
  </section>;
}

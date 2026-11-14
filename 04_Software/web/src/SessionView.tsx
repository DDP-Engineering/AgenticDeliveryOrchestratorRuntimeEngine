/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type {Locale,MessageKey} from "./i18n";
import {InstructionComposer} from "./InstructionComposer";
import type {Instruction} from "./instructionModel";
import {instructionCopy} from "./instructionCopy";
import {conversationCopy} from "./conversationCopy";
import {ForgeMarkdown} from "./forgeMarkdown";
import {ticketCopy} from "./ticketCopy";
import {sessionCopy,workflowStageLabel} from "./jobCopy";
import {readSessions,readSessionPage,shouldPollSession,applySessionActivity,type AgentSession,type SessionItem,type SessionActivity} from "./sessionModel";

type Request=<T>(path:string,method?:string,body?:unknown,csrf?:string)=>Promise<T>;

/** Follow a launch with fenced cursor reads; explicit history selection owns the view. */
export function SessionView({project,run,workflow,locale,admin,request,t,lifecycle,active,csrf,target}:{csrf:string;target?:{id:string;sequence:number};project:string;run:string;workflow:"aegis"|"direct";locale:Locale;admin:boolean;request:Request;t:(key:MessageKey)=>string;lifecycle:string;active:boolean}) {
  const copy=sessionCopy[locale],chat=conversationCopy[locale],instructionsText=instructionCopy[locale];
  const [instructions,setInstructions]=useState<Instruction[]>([]);
  const [newMessages,setNewMessages]=useState(false);
  const chatWindow=useRef<HTMLDivElement>(null),stickToBottom=useRef(true),appliedTarget=useRef(0);
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
  useEffect(()=>{
    if(!target||target.sequence===appliedTarget.current)return;
    const row=sessions.find(row=>row.id===target.id||row.archive_id===target.id);
    if(row){appliedTarget.current=target.sequence;following.current=Boolean(row.live);setSelected(row.id);}
  },[target,sessions]);
  useEffect(()=>{
    if(active&&visible&&selected&&cursor!==null&&!pageLoading&&!pageError&&!sessions.find(row=>row.id===selected)?.live)
      void load(selected,cursor,true);
  },[cursor,pageLoading,pageError,selected,active,visible]);
  useEffect(()=>{stickToBottom.current=true;setNewMessages(false);},[selected]);
  const date=(value:string)=>new Intl.DateTimeFormat(locale,{dateStyle:"medium",timeStyle:"medium"}).format(new Date(value));
  const selectedSession=sessions.find(row=>row.id===selected);
  const liveSession=sessions.find(row=>row.live);
  const currentView=Boolean(selectedSession?.live||following.current&&!liveSession);
  const end=selectedSession?.end_at?Date.parse(selectedSession.end_at):Infinity;
  const preceding=sessions.filter(row=>row.end_at&&Date.parse(row.end_at)<end).map(row=>Date.parse(row.end_at!));
  const start=selectedSession?.start_at?Date.parse(selectedSession.start_at):preceding.length?Math.max(...preceding):-Infinity;
  const represented=new Set(items.map(item=>item.instruction_id).filter(Boolean));
  const extra=instructions.filter(row=>!represented.has(row.id)&&(currentView&&!row.delivery||row.delivery&&Date.parse(row.delivery.at)>start&&Date.parse(row.delivery.at)<=end));
  const entries=items.filter(item=>item.kind!=="turn"&&item.kind!=="usage").map((item,index)=>{const instruction=instructions.find(row=>row.id===item.instruction_id);return {item:instruction?{...item,at:instruction.created_at}:item,key:`event-${index}`,instruction};});
  entries.push(...extra.map(row=>({item:{kind:"prompt" as const,text:row.text,at:row.created_at,instruction_id:row.id},key:row.id,instruction:row})));
  if(entries.every(entry=>entry.item.at))entries.sort((a,b)=>Date.parse(a.item.at!)-Date.parse(b.item.at!));
  const messageVersion=entries.map(entry=>`${entry.key}:${entry.item.text.length}:${Boolean(entry.instruction?.delivery)}:${entry.instruction?.last_error||""}`).join(",");
  useEffect(()=>{
    if(!active)return;
    if(stickToBottom.current){const frame=requestAnimationFrame(()=>{if(chatWindow.current)chatWindow.current.scrollTop=chatWindow.current.scrollHeight;});return()=>cancelAnimationFrame(frame);}
    setNewMessages(true);
  },[messageVersion,active]);
  const results=new Map(items.filter(item=>item.kind==="tool_result").map(item=>[item.call_id,item]));
  const calls=new Set(items.filter(item=>item.kind==="tool_call").map(item=>item.call_id));
  const markdown=(source:string)=><ForgeMarkdown source={source} imageLabel={ticketCopy[locale].imageNotLoaded} codeLabel={ticketCopy[locale].code} tableLabel={ticketCopy[locale].table}/>;
  const renderItem=(entry:typeof entries[number],index:number)=>{
    const {item,instruction,key}=entry;
    if(item.kind==="tool_result"&&calls.has(item.call_id))return null;
    if(item.kind==="reasoning")return <li key={key} className="session-reasoning"><details><summary>{copy.reasoning}</summary><pre tabIndex={0}>{item.text}</pre></details></li>;
    if(item.kind==="tool_call"||item.kind==="tool_result"){
      const result=item.kind==="tool_call"?results.get(item.call_id):undefined;
      return <li key={key} className="session-tool"><details><summary>{item.tool} {(item.is_error||result?.is_error)&&<span className="error">· {t("failed")}</span>}</summary><pre tabIndex={0}>{item.text}</pre>{result&&<><strong>{copy.tool_result}</strong><pre tabIndex={0}>{result.text}</pre></>}</details></li>;
    }
    const initial=item.kind==="prompt"&&!item.instruction_id&&entries.findIndex(entry=>entry.item.kind==="prompt"&&!entry.item.instruction_id)===index;
    return <li key={key} className={`session-message session-${item.kind}`}>
      <div className="session-message-meta"><strong>{instruction?instruction.user.username:item.kind==="assistant"?chat.agent:copy[item.kind]}</strong>{item.at&&<time dateTime={item.at}>{date(item.at)}</time>}{instruction&&<span className="session-delivery">{instruction.last_error?t("failed"):instruction.delivery?chat.received:instructionsText.queued}</span>}</div>
      {initial?<details className="session-initial" open={item.text.length<2000}><summary>{chat.initial}</summary>{markdown(item.text)}</details>:item.kind==="assistant"?markdown(item.text):<pre tabIndex={0}>{instruction?.text||item.text}</pre>}
      {instruction?.last_error&&<p role="status">{instructionsText.rejected}</p>}
    </li>;
  };
  const latestSession=()=>{following.current=true;stickToBottom.current=true;if(liveSession)setSelected(liveSession.id);else void refresh(null);};
  return <section className="agent-sessions" aria-label={copy.title}>
    <div className="session-toolbar">
      {sessions.length>0&&<label>{chat.session}<select aria-label={chat.session} value={selected} onChange={event=>{following.current=Boolean(sessions.find(row=>row.id===event.target.value)?.live);setSelected(event.target.value);}}>{sessions.map(row=><option value={row.id} key={row.id}>{workflowStageLabel(row.stage,workflow,t)} · {row.attempt} · {row.live?copy.live:date(row.end_at!)} · {row.live?copy.live:copy[row.outcome === "failed" ? "failedOutcome" : row.outcome!]}</option>)}</select></label>}
      {lifecycle==="working"&&!selectedSession?.live&&<button className="ghost" onClick={latestSession}>{chat.current}</button>}
      {selectedSession?.live&&<span className="session-live" role="status">● {copy.live}{activity.thinking||Object.keys(activity.tools).length?` · ${Object.values(activity.tools).at(-1)||copy.thinking}`:""}</span>}
    </div>
    {loading&&<p role="status">{t("loadingData")}</p>}
    {error&&<p role="alert">{copy.failed} <button className="ghost" onClick={()=>setReload(value=>value+1)}>{t("retry")}</button></p>}
    {!loading&&!error&&!sessions.length&&<p role="status">{copy.empty}</p>}
    <div className="session-chat-window" ref={chatWindow} onScroll={()=>{const node=chatWindow.current;if(node){stickToBottom.current=node.scrollHeight-node.scrollTop-node.clientHeight<80;if(stickToBottom.current)setNewMessages(false);}}}>
      <ol className="session-timeline">{entries.map(renderItem)}</ol>
      {pageLoading&&<p role="status">{t("loadingData")}</p>}
      {pageError&&<p role="alert">{copy.failed} <button className="ghost" onClick={()=>void load(selected,cursor??0,items.length>0)}>{t("retry")}</button></p>}
    </div>
    {newMessages&&<button className="ghost session-new-messages" onClick={()=>{stickToBottom.current=true;setNewMessages(false);chatWindow.current?.scrollTo({top:chatWindow.current.scrollHeight,behavior:"smooth"});}}>{chat.newMessages} ↓</button>}
    <InstructionComposer project={project} run={run} locale={locale} lifecycle={lifecycle} active={active} csrf={csrf} request={request} t={t} show={lifecycle==="working"&&currentView} canSendNow={Boolean(selectedSession?.live)} onRows={setInstructions} onSent={()=>{stickToBottom.current=true;setNewMessages(false);}}/>
  </section>;
}

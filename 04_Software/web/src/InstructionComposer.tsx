/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {useEffect,useId,useRef,useState} from "react";
import type {Locale,MessageKey} from "./i18n";
import {ApiError} from "./errors";
import {instructionCopy} from "./instructionCopy";
import {readInstructions,readInstructionResponse,validInstructionText,type Instruction} from "./instructionModel";
import {startVisiblePolling} from "./polling";

type Request=<T>(path:string,method?:string,body?:unknown,csrf?:string)=>Promise<T>;

/** Queue literal instructions below the live view, including between-session states. */
export function InstructionComposer({project,run,locale,lifecycle,active,csrf,request,t}:{project:string;run:string;locale:Locale;lifecycle:string;active:boolean;csrf:string;request:Request;t:(key:MessageKey)=>string}) {
  const copy=instructionCopy[locale],id=useId();
  const [text,setText]=useState(""),[rows,setRows]=useState<Instruction[]>([]),[notices,setNotices]=useState<string[]>([]);
  const [error,setError]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true);
  const generation=useRef(0),sending=useRef(false),reading=useRef(false),sequence=useRef(0);
  const refreshQueued=useRef(false),activeView=useRef(active);activeView.current=active;
  const base=`/jobs/${encodeURIComponent(project)}/${encodeURIComponent(run)}/instructions`;
  useEffect(()=>()=>{generation.current++;sending.current=false;reading.current=false;refreshQueued.current=false;},[base]);
  const load=async(fresh=false)=>{
    if(reading.current){if(fresh)refreshQueued.current=true;return;}
    refreshQueued.current=false;reading.current=true;const current=generation.current,version=sequence.current;
    try{
      const data=readInstructions(await request(base),project,run);
      if(current!==generation.current||version!==sequence.current)return;
      setRows(data.instructions);setNotices(data.notices);setLoading(false);setError(previous=>previous==="read"?"":previous);
    }catch{if(current===generation.current){setError("read");setLoading(false);}}
    finally{if(current===generation.current){
      reading.current=false;
      // A lifecycle change or send must get a fresh snapshot after an older read.
      if(refreshQueued.current&&activeView.current)void load(true);
    }}
  };
  useEffect(()=>{
    if(!active)return;
    void load(true);
    if(lifecycle==="working")return startVisiblePolling(()=>void load(),3000);
  },[base,active,lifecycle]);
  const send=async(mode:"now"|"after")=>{
    if(sending.current||lifecycle!=="working"||!validInstructionText(text))return;
    sending.current=true;setBusy(true);setError("");const current=generation.current,captured=text;
    sequence.current++;
    try{
      const row=readInstructionResponse(await request(base,"POST",{text:captured,mode},csrf),project,run);
      if(current!==generation.current)return;
      if(row.text!==captured||row.mode!==mode)throw new ApiError("unexpected_response");
      setRows(previous=>[...previous.filter(item=>item.id!==row.id),row]);setText("");setLoading(false);
    }catch(cause){if(current===generation.current)setError(cause instanceof ApiError?cause.code:"send");}
    finally{if(current===generation.current){sending.current=false;setBusy(false);void load(true);}}
  };
  const message=error==="job_not_working"?copy.notWorking:error==="instruction_limit"?copy.full:error==="instruction_busy"?copy.busy:copy.failed;
  return <section className="instruction-composer" aria-label={copy.title}>
    <h3>{copy.title}</h3>
    <p className="field-hint" id={`${id}-meaning`}>{copy.meaning}</p>
    {loading&&<p role="status">{t("loadingData")}</p>}
    {error&&<p role="alert">{message} <button className="ghost" onClick={()=>{setError("");void load(true);}}>{t("retry")}</button></p>}
    {notices.length>0&&<p role="alert">{copy.notice}</p>}
    <ol className="instruction-list" aria-describedby={`${id}-meaning`}>{rows.map(row=><li key={row.id}>
      <strong>{row.delivery?copy.delivered:copy.queued}</strong> · {row.user.username} · {row.mode==="now"?copy.now:copy.after}
      <pre tabIndex={0}>{row.text}</pre>{row.last_error&&<p>{copy.rejected}</p>}
    </li>)}</ol>
    <label htmlFor={`${id}-text`}>{copy.text}</label>
    <textarea id={`${id}-text`} rows={4} value={text} disabled={busy||lifecycle!=="working"}
      aria-describedby={`${id}-limit ${id}-wait`} onChange={event=>setText(event.target.value)} />
    <p id={`${id}-limit`} className="field-hint">{copy.limit} {Array.from(text).length}/4000</p>
    <div className="button-row"><button disabled={busy||lifecycle!=="working"||!validInstructionText(text)} onClick={()=>void send("now")}>{copy.now}</button>
      <button disabled={busy||lifecycle!=="working"||!validInstructionText(text)} onClick={()=>void send("after")}>{copy.after}</button></div>
    <p id={`${id}-wait`} className="field-hint">{copy.wait}</p>
    {lifecycle!=="working"&&<p>{copy.notWorking}</p>}
  </section>;
}

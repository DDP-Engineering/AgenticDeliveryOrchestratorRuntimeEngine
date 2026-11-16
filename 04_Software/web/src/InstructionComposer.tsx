import {useEffect,useId,useRef,useState} from "react";
import type {Locale,MessageKey} from "./i18n";
import {ApiError} from "./errors";
import {instructionCopy} from "./instructionCopy";
import {conversationCopy} from "./conversationCopy";
import {readInstructions,readInstructionResponse,validInstructionText,type Instruction} from "./instructionModel";
import {startVisiblePolling} from "./polling";

type Request=<T>(path:string,method?:string,body?:unknown,csrf?:string)=>Promise<T>;

/** Own one draft and durable send statuses; the conversation owns message rendering. */
export function InstructionComposer({project,run,locale,lifecycle,active,csrf,request,t,show,canSendNow,onRows,onSent}:{project:string;run:string;locale:Locale;lifecycle:string;active:boolean;csrf:string;request:Request;t:(key:MessageKey)=>string;show:boolean;canSendNow:boolean;onRows:(rows:Instruction[])=>void;onSent:()=>void}) {
  const copy=instructionCopy[locale],chat=conversationCopy[locale],id=useId();
  const [text,setText]=useState(""),[rows,setRows]=useState<Instruction[]>([]),[notices,setNotices]=useState<string[]>([]);
  const [error,setError]=useState(""),[busy,setBusy]=useState(false);
  const generation=useRef(0),sending=useRef(false),reading=useRef(false),sequence=useRef(0);
  const refreshQueued=useRef(false),activeView=useRef(active);activeView.current=active;
  const base=`/jobs/${encodeURIComponent(project)}/${encodeURIComponent(run)}/instructions`;
  useEffect(()=>()=>{generation.current++;sending.current=false;reading.current=false;refreshQueued.current=false;},[base]);
  useEffect(()=>onRows(rows),[rows,onRows]);
  const load=async(fresh=false)=>{
    if(reading.current){refreshQueued.current ||= fresh;return;}
    reading.current=true;refreshQueued.current=false;const current=generation.current,revision=sequence.current;
    try{
      const result=readInstructions(await request(base),project,run);
      if(current===generation.current&&revision===sequence.current){setRows(result.instructions);setNotices(result.notices);setError(previous=>previous==="read"?"":previous);}
    }catch{if(current===generation.current)setError("read");}
    finally{if(current===generation.current){reading.current=false;if(refreshQueued.current&&activeView.current)void load(true);}}
  };
  useEffect(()=>{
    if(!active)return;
    void load(true);
    if(lifecycle==="working")return startVisiblePolling(()=>void load(),3000);
  },[base,active,lifecycle]);
  const send=async(mode:"now"|"after")=>{
    if(sending.current||!show||lifecycle!=="working"||mode==="now"&&!canSendNow)return;
    if(!validInstructionText(text)){setError("invalid");return;}
    sending.current=true;setBusy(true);setError("");const current=generation.current,captured=text;
    sequence.current++;
    try{
      const row=readInstructionResponse(await request(base,"POST",{text:captured,mode},csrf),project,run);
      if(current!==generation.current)return;
      if(row.text!==captured||row.mode!==mode)throw new ApiError("unexpected_response");
      setRows(previous=>[...previous.filter(item=>item.id!==row.id),row]);setText("");onSent();
    }catch(cause){if(current===generation.current)setError(cause instanceof ApiError?cause.code:"send");}
    finally{if(current===generation.current){sending.current=false;setBusy(false);void load(true);}}
  };
  const message=error==="invalid"?chat.invalid:error==="job_not_working"?copy.notWorking:error==="instruction_limit"?copy.full:error==="instruction_busy"?copy.busy:copy.failed;
  return <>{!show&&error&&<p role="alert">{message}</p>}{!show&&notices.length>0&&<p role="alert">{copy.notice}</p>}<section className="instruction-composer" aria-label={chat.message} hidden={!show}>
    {error&&<p role="alert" id={`${id}-error`}>{message}{error!=="invalid"&&<button className="ghost" onClick={()=>{setError("");void load(true);}}>{t("retry")}</button>}</p>}
    {notices.length>0&&<p role="alert">{copy.notice}</p>}
    <div className="instruction-input"><label htmlFor={`${id}-text`}>{chat.message}</label>
    <textarea id={`${id}-text`} rows={2} value={text} disabled={busy} aria-invalid={error==="invalid"} aria-describedby={error?`${id}-error`:undefined} onChange={event=>{setText(event.target.value);if(error==="invalid")setError("");}} />
    </div>
    <div className="instruction-actions"><button className="primary" disabled={busy||!canSendNow||!text.length} onClick={()=>void send("now")}>{copy.now}</button><button className="ghost" disabled={busy||!text.length} onClick={()=>void send("after")}>{chat.queue}</button></div>
  </section></>;
}

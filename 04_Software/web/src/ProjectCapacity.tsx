/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useState } from "react";
import { describeError, ApiError } from "./errors";
import { startVisiblePolling } from "./polling";
import { readCapacity, readWorkers, workerCopy, type Capacity, type Worker } from "./projectStatus";
import type { Locale } from "./i18n";
import { reasonSentence } from "./operationReason";
import { HelpLink } from "./HelpCenter";

type Read = <T>(path:string)=>Promise<T>;

/** Project capacity is independent of heartbeat freshness and observed worker activity. */
export function ProjectCapacity({project,name,locale,request,refresh=0,compact=false}:{project:string;name?:string;locale:Locale;request:Read;refresh?:number;compact?:boolean}) {
  const copy=workerCopy[locale];
  const [state,setState]=useState<{project:string;data?:Capacity;error?:unknown}>({project});
  useEffect(()=>{
    let active=true,sequence=0;
    const load=async()=>{
      const current=++sequence;
      try{const data=readCapacity(await request(`/projects/${encodeURIComponent(project)}/capacity`),project);
        if(active&&current===sequence)setState({project,data});
      }catch(error){if(active&&current===sequence)setState({project,error});}
    };
    void load();const stop=startVisiblePolling(()=>void load(),2000);
    return ()=>{active=false;stop();};
  },[project,refresh,request]);
  const data=state.project===project?state.data:undefined;
  if(compact)return <>{[["limit",copy.limit,data?.limit],["free",copy.free,data?.free],["queued",copy.waiting,data?.waiting_jobs]].map(([key,label,value],index)=><div className="summary-fact" data-capacity-fact={key} key={key}>
    <dt>{label}</dt><dd>{value===undefined?"—":new Intl.NumberFormat(locale).format(Number(value))}</dd>
    {index===0&&state.project===project&&state.error!==undefined&&<small role="alert" className="field-hint">{copy.error}: {describeError(locale,state.error)}</small>}
  </div>)}</>;
  return <section className="panel compact project-capacity" aria-label={`${copy.capacity}${name ? ` · ${name}` : ""}`}>
    <div className="panel-heading"><h2>{copy.capacity}{name && <> · {name}</>}</h2><HelpLink topic="jobs" locale={locale}/></div>
    {state.project===project&&state.error!==undefined?<p className="alert" role="alert">{copy.error}: {describeError(locale,state.error)}</p>:!data?<p>…</p>:<>
      <dl className="capacity-facts">{[[copy.limit,data.limit],[copy.occupied,data.occupied],[copy.free,data.free],[copy.waiting,data.waiting_jobs]].map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
      <p className="muted"><WorkerObservation worker={data.worker} locale={locale}/></p>
      {!data.available&&<p className="field-hint">{data.worker.heartbeat!=="recent"?copy.worker_unavailable:data.free===0?copy.project_limit:copy.unavailable}</p>}
      {data.queue.length>0&&<ul className="capacity-queue">{data.queue.map(item=><li key={item.id}>#{item.id} · {copy[item.action]} · {copy[item.reason]}</li>)}</ul>}
      {data.waiting_runs.length>0&&<ul className="capacity-queue">{data.waiting_runs.map(item=><li key={item.ticket_iid}>#{item.ticket_iid} · {copy[item.reason]}</li>)}</ul>}
      {data.staged_change&&<p className="notice" role="status">{copy.staged}{data.staged_limit!==null&&data.staged_limit<data.active_limit&&<> {copy.stagedLower}</>}{data.staged_limit!==data.active_limit&&<> {copy.limit}: {data.staged_limit}</>}</p>}
      {data.recent_operations.length>0&&<details className="project-operations" open={data.recent_operations.some(op=>["pending","running","failed","uncertain"].includes(op.status))}>
        <summary>{copy.operations}</summary><ul>{data.recent_operations.map(op=><li key={op.id} data-operation-id={op.id}>
          #{op.id} · {copy[op.action]} · <strong>{copy[op.status]}</strong>
          {op.reason&&<p className="field-hint">{reasonSentence(locale,op.reason) ?? describeError(locale,new ApiError(op.reason))}</p>}
        </li>)}</ul>
      </details>}
    </>}
  </section>;
}

function WorkerObservation({worker,locale}:{worker:Worker;locale:Locale}) {
  const copy=workerCopy[locale];
  return <>{copy[worker.role]} · {copy[worker.heartbeat]} · {copy[worker.activity]}</>;
}

/** System roles stay separate; a missing project worker names only that project. */
export function WorkerStatus({locale,projects,request}:{locale:Locale;projects:Array<{id:string;display_name:string}>;request:Read}) {
  const [state,setState]=useState<{workers?:Worker[];error?:unknown}>({});
  const copy=workerCopy[locale];
  useEffect(()=>{
    let active=true,sequence=0;
    const load=async()=>{const current=++sequence;try{
      const data=readWorkers(await request("/system/workers"));if(active&&current===sequence)setState(data);
    }catch(error){if(active&&current===sequence)setState({error});}};
    void load();const stop=startVisiblePolling(()=>void load(),5000);return()=>{active=false;stop();};
  },[]);
  return <div className="worker-roles"><h2>{copy.workers}</h2><p className="muted">{copy.heartbeatHelp}</p>
    {state.error!==undefined?<p className="alert" role="alert">{describeError(locale,state.error)}</p>:!state.workers?<p>…</p>:<ul>{state.workers.map((worker,index)=><li key={`${worker.role}:${worker.project_id}:${worker.run_id}:${index}`}>
      {worker.project_id&&<strong>{projects.find(item=>item.id===worker.project_id)?.display_name||worker.project_id} · </strong>}
      <WorkerObservation worker={worker} locale={locale}/>
    </li>)}</ul>}
  </div>;
}

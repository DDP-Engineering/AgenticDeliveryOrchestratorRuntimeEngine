/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useState, type ReactElement, type ReactNode } from "react";
import { describeError } from "./errors";
import { startVisiblePolling } from "./polling";
import { StatusBadge } from "./Presentation";
import { currentJobStates, readCapacityOverview, capacityCopy, workerCopy, type CapacityOverview } from "./projectStatus";
import { jobCopy } from "./jobCopy";
import type { Locale, MessageKey } from "./i18n";

type Project = {id:string;name:string;display_name:string;archived:boolean};
type Row = {id:string;data?:CapacityOverview;error?:unknown};
const lifecycleKeys:Record<typeof currentJobStates[number],MessageKey> = {
  working:"working",publishing:"publishingStatus","parked-clarification":"parkedClarificationStatus",
  "awaiting-approval":"awaitingApprovalStatus","in-review":"inReviewStatus","handoff-pending":"handoffPendingStatus",
};

/** Show only current capacity, monitoring and unfinished job states for authorized projects. */
export function CapacityTable({projects,locale,request,t,refresh=0,paginate}:{
  projects:Project[];locale:Locale;request:<T>(path:string,method?:string,body?:unknown,csrf?:string,signal?:AbortSignal)=>Promise<T>;t:(key:MessageKey)=>string;
  refresh?:number;paginate:(table:ReactElement<{children?:ReactNode}>)=>ReactNode;
}) {
  const identities=projects.map(project=>project.id).sort().join(",");
  const [state,setState]=useState<{key:string;rows:Row[]}>({key:"",rows:[]});
  useEffect(()=>{
    let active=true;
    const pending=new Map<string,AbortController>();
    const loadProject=async(id:string)=>{
      if(pending.has(id))return;
      const controller=new AbortController();pending.set(id,controller);
      const timeout=window.setTimeout(()=>controller.abort(),15000);
      let row:Row;
      try{row={id,data:readCapacityOverview(await request(`/projects/${encodeURIComponent(id)}/capacity`,"GET",undefined,undefined,controller.signal),id)};}
      catch(error){row={id,error};}
      finally{window.clearTimeout(timeout);pending.delete(id);}
      if(active)setState(previous=>({key:identities,rows:[...(previous.key===identities?previous.rows:[]).filter(item=>item.id!==id),row]}));
    };
    const load=()=>{for(const id of identities.split(",").filter(Boolean))void loadProject(id);};
    load();const stop=startVisiblePolling(load,2000);
    return()=>{active=false;stop();for(const controller of pending.values())controller.abort();};
  },[identities,refresh,request]);
  const copy=capacityCopy[locale],worker=workerCopy[locale],jobs=jobCopy[locale];
  const rows=state.key===identities?state.rows:[];
  const number=(value:number|undefined)=>value===undefined?"—":new Intl.NumberFormat(locale).format(value);
  return <section className="panel capacity-table" aria-label={copy.tab}>
    {paginate(<table><thead><tr><th>{t("project")}</th><th>{worker.limit}</th><th>{worker.free}</th><th>{worker.waiting}</th><th>{jobs.pickup}</th><th>{copy.jobStatus}</th></tr></thead>
      <tbody>{projects.map(project=>{
        const row=rows.find(item=>item.id===project.id),data=row?.data;
        return <tr key={project.id} data-capacity-project={project.id}>
          <th scope="row"><a href={`/projects/${encodeURIComponent(project.id)}`}>{project.display_name||project.name}</a></th>
          <td>{number(data?.limit)}</td><td>{number(data?.free)}</td><td>{number(data?.waiting_jobs)}</td>
          <td>{project.archived?<StatusBadge code="archived">{t("archived")}</StatusBadge>:data?<><StatusBadge code={data.paused?"paused":"working"}>{data.paused?jobs.pickupStopped:jobs.pickupActive}</StatusBadge>{data.worker.heartbeat!=="recent"&&<small className="field-hint">{worker.worker_unavailable}</small>}</>:"—"}</td>
          <td>{row?.error!==undefined?<span role="alert">{describeError(locale,row.error)}</span>:!data?"…":<div className="capacity-job-states">
            {currentJobStates.some(status=>data.job_counts[status]>0)?currentJobStates.filter(status=>data.job_counts[status]>0).map(status=><StatusBadge key={status} code={status}>{number(data.job_counts[status])} · {t(lifecycleKeys[status])}</StatusBadge>):<span className="muted">{copy.noActiveJobs}</span>}
          </div>}</td>
        </tr>;
      })}</tbody></table>)}
  </section>;
}

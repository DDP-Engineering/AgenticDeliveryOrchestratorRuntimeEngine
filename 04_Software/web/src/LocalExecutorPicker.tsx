/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {useEffect,useId,useRef,useState,type ReactNode} from "react";
import type {Locale} from "./i18n";
import {setupCopy} from "./setupCopy";
import {commandForExecutable,discoveryCopy,executableFromCommand,nativePresets,readLocalExecutors,validExecutablePath,type LocalExecutors} from "./localExecutors";

/** Installed launch suggestions with explicit manual authority and stale-read protection. */
export function LocalExecutorPicker({agent,value,onChange,locale,disabled=false,id,label,autoFill=true,onSystem,children}:{
 agent:string;value:string;onChange:(command:string)=>void;locale:Locale;disabled?:boolean;id?:string;label?:string;autoFill?:boolean;onSystem?:(system:string)=>void;children?:ReactNode;
}) {
 const c=discoveryCopy[locale],uid=useId();
 const [listing,setListing]=useState<LocalExecutors|null>(null),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0);
 const [path,setPath]=useState(()=>executableFromCommand(value));
 const pathEdited=useRef(false);
 const manual=useRef(false),lastAutomatic=useRef("");
 const changeRef=useRef(onChange),systemRef=useRef(onSystem);
 changeRef.current=onChange;systemRef.current=onSystem;
 useEffect(()=>{
  let active=true;setLoading(true);
  void readLocalExecutors().then(result=>{if(active){setListing(result);setLoading(false);if(result)systemRef.current?.(result.system);}});
  return ()=>{active=false;};
 },[retry]);
 const installations=listing?.executors.find(item=>item.agent===agent)?.installations ?? [];
 useEffect(()=>{if(!pathEdited.current)setPath(executableFromCommand(value));},[value]);
 useEffect(()=>{
  const first=listing?.executors.find(item=>item.agent===agent)?.installations[0];
  if(listing && !first && !manual.current && value && value===lastAutomatic.current){
   lastAutomatic.current="";changeRef.current("");return;
  }
  if(!manual.current && first && (!value || value===lastAutomatic.current || autoFill && Object.values(nativePresets).includes(value)) && value!==first.command){
   lastAutomatic.current=first.command;changeRef.current(first.command);
  }
 },[listing,agent,value,autoFill]);
 const select=(command:string)=>{manual.current=true;pathEdited.current=false;changeRef.current(command);};
 const pathValid=validExecutablePath(path) && (listing?.system!=="Windows" || /\.exe$/i.test(path));
 return <div className="local-executor-picker">
  <label htmlFor={uid+"-installed"}>{c.installed}</label>
  <select id={uid+"-installed"} disabled={disabled || loading} value={installations.some(item=>item.command===value)?value:""}
   onChange={event=>{if(event.target.value)select(event.target.value);}}>
   <option value="">{c.manual}</option>
   {installations.map(item=><option key={item.command} value={item.command}>{item.executable}{item.entrypoint?" · "+item.entrypoint:""}</option>)}
  </select>
  {loading?<p role="status">{c.loading}</p>:!listing?<p role="status">{c.unavailable}</p>:
   <>{!installations.length && <p role="status">{c.missing}</p>}<p className="field-hint">{setupCopy[locale].runsAs}: <strong>{listing.account}</strong> · {listing.machine} · {listing.system}</p></>}
  <p className="field-hint">{setupCopy[locale].automaticEnvironment}</p>
  <details className="local-executor-advanced">
  <summary>{setupCopy[locale].advanced}</summary>
  <div className="local-executor-fields">
  <button type="button" className="ghost" disabled={disabled || loading} onClick={()=>setRetry(retry+1)}>{c.refresh}</button>
  <label htmlFor={id || uid+"-command"}>{label || c.command}</label>
  <input id={id || uid+"-command"} aria-label={label || c.command} value={value} maxLength={4096} disabled={disabled}
   autoComplete="off" onChange={event=>select(event.target.value)}/>
  <label htmlFor={uid+"-path"}>{c.path}</label>
  <input id={uid+"-path"} value={path} maxLength={2048} disabled={disabled} autoComplete="off" onChange={event=>{pathEdited.current=true;setPath(event.target.value);}}/>
  <button type="button" className="ghost" disabled={disabled || !pathValid} onClick={()=>{
   const matches=(item:{executable:string})=>item.executable.replaceAll("\\","/")===path.replaceAll("\\","/");
   const known=installations.find(item=>item.command===value && matches(item)) ?? installations.find(matches);
   select(known?.command ?? commandForExecutable(agent,path));
  }}>{c.use}</button>
  <p className="field-hint">{c.help}</p>
  {children}
  </div>
  </details>
 </div>;
}

/** Read-only identity in Settings; detection never changes saved configuration. */
export function LocalExecutionIdentity({locale}:{locale:Locale}) {
 const [host,setHost]=useState<LocalExecutors|null>(null);
 useEffect(()=>{let active=true;void readLocalExecutors().then(value=>{if(active)setHost(value);});return()=>{active=false;};},[]);
 return <p className="field-hint">{setupCopy[locale].runsAs}: {host ? <><strong>{host.account}</strong> · {host.machine} · {host.system}</> : setupCopy[locale].processAccount}. {setupCopy[locale].automaticEnvironment}</p>;
}

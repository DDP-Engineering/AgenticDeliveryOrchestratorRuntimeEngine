/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";
import { imageCopy, imageGuidance, IMAGE_COMPILER_EXAMPLE, IMAGE_COMPILER_CHECKS, validImageOperation, validImageView, type ImageOperation, type ImageView } from "./imageBuild";
import { startVisiblePolling } from "./polling";

/** Compact explicit administrator flow inside the existing Environment group. */
export function ProjectImage({project, revision, local, locale, admin, disabled, currentImage, onExisting, call, onStage}: {
  project:string; revision:string; local:boolean; locale:Locale; admin:boolean; disabled:boolean;
  currentImage:string; onExisting:()=>void;
  call:(path:string,method?:string,body?:unknown)=>Promise<unknown>;
  onStage:(image:string,operation:string)=>Promise<boolean>;
}) {
  const copy=imageCopy[locale], guidance=imageGuidance[locale];
  const [view,setView]=useState<ImageView|null>(null);
  const [define,setDefine]=useState(false);
  const [source,setSource]=useState("");
  const [checks,setChecks]=useState("");
  const [network,setNetwork]=useState<"none"|"default">("none");
  const [timeout,setTimeout]=useState(600), [memory,setMemory]=useState(1024);
  const [result,setResult]=useState<ImageOperation|null>(null);
  const [log,setLog]=useState(""),[error,setError]=useState(""),[notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);
  const mounted=useRef(true),pending=useRef(false);
  const root="/projects/"+encodeURIComponent(project)+"/image-build";
  const active=!!result && ["queued","inspecting","building","verifying"].includes(result.phase);
  const dirty=!!view && (source!==(view.draft?.dockerfile ?? view.template) || checks!==(view.draft?.checks.join("\n")??view.template_checks.join("\n")) || network!==(view.draft?.network??"none") || timeout!==(view.draft?.timeout_seconds??600) || memory!==(view.draft?.memory_mib??1024));
  const stale=!!result && (result.config_revision!==revision || result.draft_revision!==view?.draft?.revision || dirty);
  const selectView=(value:unknown)=>{
    if (!validImageView(value,project)) throw new Error("image_response_invalid");
    setView(value); setSource(value.draft?.dockerfile??value.template);setChecks(value.draft?.checks.join("\n")??value.template_checks.join("\n"));
    setNetwork(value.draft?.network??"none");setTimeout(value.draft?.timeout_seconds??600);setMemory(value.draft?.memory_mib??1024);
    const current=value.operations.filter(v=>v.config_revision===revision && v.draft_revision===value.draft?.revision);
    setResult(current.find(v=>["queued","inspecting","building","verifying"].includes(v.phase)) ?? current.find(v=>v.phase==="verified") ?? current.at(-1) ?? value.operations.at(-1) ?? null);
  };
  useEffect(()=>{
    mounted.current=true;
    if (!local) void call(root).then(value=>{if(mounted.current)selectView(value);}).catch(()=>{if(mounted.current)setError(copy.failed);});
    return ()=>{mounted.current=false;};
  },[project,revision,local]);
  const refresh=async ()=>{
    if (!result || pending.current) return;
    try {
      const value=await call(root+"/operations/"+result.id) as {build:unknown;log:unknown};
      if (!mounted.current) return;
      if (!value || Object.keys(value).sort().join()!=="build,log" || !validImageOperation(value.build) || value.build.id!==result.id || value.build.project_id!==project || typeof value.log!=="string" || new TextEncoder().encode(value.log).length>65536) throw new Error("image_response_invalid");
      setResult(value.build);setLog(value.log);setError("");
    } catch {if(mounted.current)setError(copy.failed);}
  };
  useEffect(()=>active?startVisiblePolling(()=>void refresh(),1500):undefined,[result?.id,active]);
  const perform=async (action:()=>Promise<void>)=>{
    if(pending.current)return;pending.current=true;setBusy(true);setError("");setNotice("");
    try{await action();}catch{if(mounted.current)setError(copy.failed);}
    finally{pending.current=false;if(mounted.current)setBusy(false);}
  };
  const save=()=>perform(async ()=>{
    const value=await call(root,"PUT",{dockerfile:source,checks:checks.split("\n").map(v=>v.trim()).filter(Boolean),revision:view?.draft?.revision??"",network,timeout_seconds:timeout,memory_mib:memory});
    if(mounted.current){selectView(value);setNotice(copy.saved);}
  });
  const build=()=>perform(async ()=>{
    if(!view?.draft || dirty)return;
    const value=await call(root+"/operations","POST",{revision:view.draft.revision,config_revision:revision,idempotency_key:crypto.randomUUID().replaceAll("-","")}) as {build:unknown;operation:unknown};
    if(!mounted.current)return;
    if(!value || !validImageOperation(value.build) || value.build.project_id!==project || value.build.config_revision!==revision || value.build.draft_revision!==view.draft.revision)throw new Error("image_response_invalid");
    setResult(value.build);setLog("");void refresh();
  });
  const exportSource=()=>{
    if(!view?.draft)return;
    const blob=new Blob([view.draft.dockerfile],{type:"text/plain;charset=utf-8"}),url=URL.createObjectURL(blob);
    const link=document.createElement("a");link.href=url;link.download="Dockerfile";link.click();URL.revokeObjectURL(url);
  };
  const exportEvidence=()=>{
    if(!view?.draft || !result)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify({draft:view.draft,build:result,log},null,2)],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download="image-build.json";link.click();URL.revokeObjectURL(url);
  };
  const upload=async (file:File|undefined)=>{
    if(!file)return;
    try{if(file.size>65536)throw new Error();const value=new TextDecoder("utf-8",{fatal:true}).decode(await file.arrayBuffer());if(mounted.current)setSource(value);}
    catch{if(mounted.current)setError(copy.failed);}
  };
  if(local)return <div className="project-image"><h3>{copy.title}</h3><p>{copy.local}</p></div>;
  return <div className="project-image">
    <h3>{copy.title}</h3><p>{copy.help}</p>
    {admin && <div className="button-row"><button type="button" className="ghost" aria-pressed={!define} onClick={()=>setDefine(false)}>{copy.existing}</button><button type="button" className="ghost" aria-pressed={define} onClick={()=>setDefine(true)}>{copy.define}</button></div>}
    {!define && <div className="image-existing"><p><strong>{guidance.current}:</strong> <code>{currentImage || guidance.noImage}</code></p><p>{guidance.existing}</p>{admin && <button type="button" className="ghost" disabled={busy||active||disabled} onClick={onExisting}>{guidance.change}</button>}</div>}
    {disabled && admin && <p className="image-prerequisite">{guidance.blocked}</p>}
    {(define || !admin && view?.draft) && <div className="image-definition">
      <ol className="image-steps"><li>{guidance.source}</li><li>{guidance.checks}</li><li>{guidance.finish}</li></ol>
      <details className="image-example"><summary>{guidance.example}</summary><p>{guidance.exampleSource}</p><pre>{IMAGE_COMPILER_EXAMPLE}</pre><p>{guidance.exampleChecks}</p><pre>{IMAGE_COMPILER_CHECKS}</pre><p>{guidance.downloads}</p></details>
      <label>{copy.source}<textarea aria-label={copy.source} rows={16} value={source} readOnly={!admin} disabled={busy||active||disabled} onChange={e=>setSource(e.target.value)}/></label>
      <label>{copy.checks}<textarea aria-label={copy.checks} rows={6} placeholder={IMAGE_COMPILER_CHECKS} value={checks} readOnly={!admin} disabled={busy||active||disabled} onChange={e=>setChecks(e.target.value)}/></label>
      {admin && <label>{copy.upload}<input aria-label={copy.upload} type="file" accept=".txt,.dockerfile,text/plain" disabled={busy||active||disabled} onChange={e=>{void upload(e.target.files?.[0]);e.target.value="";}}/></label>}
      <details><summary>{copy.advanced}</summary><p>{copy.context}</p><fieldset disabled={!admin||busy||active||disabled}>
        <label>{copy.network}<select value={network} onChange={e=>setNetwork(e.target.value as "none"|"default")}><option value="none">{copy.none}</option><option value="default">{copy.downloads}</option></select></label>
        <label>{copy.timeout}<input type="number" min={30} max={1800} step={1} value={timeout} onChange={e=>setTimeout(Number(e.target.value))}/></label>
        <label>{copy.memory}<input type="number" min={512} max={4096} step={1} value={memory} onChange={e=>setMemory(Number(e.target.value))}/></label>
      </fieldset></details>
      <div className="button-row">{admin && <><button className="primary" disabled={busy||active||disabled||!view} onClick={()=>void save()}>{copy.save}</button><button className="primary" disabled={busy||active||disabled||dirty||!view?.draft} onClick={()=>void build()}>{copy.build}</button></>}{admin && <button className="ghost" disabled={!view?.draft} onClick={exportSource}>{copy.export}</button>}</div>
    </div>}
    {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {result && <div className="image-evidence">
      <p role="status">{copy.phases[result.phase as keyof typeof copy.phases]}</p>
      {["uncertain","interrupted"].includes(result.phase) && <p className="alert">{copy.uncertain}</p>}
      {result.phase==="failed" && <p className="alert">{copy.failed}</p>}
      {stale && <p className="alert">{copy.stale}</p>}
      <p>{copy.reviewed}: {result.verified_checks.join(", ") || "—"}</p>
      <div className="button-row">{admin && result.phase==="verified" && <button className="primary" disabled={busy||disabled||stale} onClick={()=>void perform(async ()=>{await onStage(result.image_id,result.id);})}>{copy.use}</button>}
        {admin && active && <button className="ghost" disabled={busy} onClick={()=>void perform(async ()=>{await call(root+"/operations/"+result.id+"/cancel","POST",{});})}>{copy.cancel}</button>}
        <button className="ghost" disabled={busy} onClick={()=>void refresh()}>{copy.refresh}</button>
      </div>
      <details><summary>{copy.advanced}</summary><p>{result.host.machine} · {result.host.account} · {result.host.system}</p><p><code>{result.runtime}</code></p><p><code>{result.tag}</code></p><p><code>{result.image_id}</code></p><p><code>{result.base_id}</code></p><p><code>{result.context_sha256}</code></p>{result.error && <p><code>{result.error}</code></p>}{admin && <button className="ghost" disabled={!view?.draft} onClick={exportEvidence}>{copy.evidence}</button>}</details>
      <details><summary>{copy.logs}</summary><pre>{log||"—"}</pre></details>
    </div>}
  </div>;
}

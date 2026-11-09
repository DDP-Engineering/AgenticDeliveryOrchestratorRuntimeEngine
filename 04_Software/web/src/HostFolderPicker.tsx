/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {useEffect,useId,useRef,useState,type KeyboardEvent} from "react";
import type {Locale} from "./i18n";
import {setupCopy} from "./setupCopy";
import {readHostFolders,type HostFolders} from "./hostFolders";

function FolderIcon() {
 return <svg className="folder-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Z"/></svg>;
}

/** Compact directory chooser; every path refers to the authenticated ADORE host. */
function HostFolderDialog({locale,onSelect,onClose}:{locale:Locale;onSelect:(path:string)=>void;onClose:()=>void}) {
 const c=setupCopy[locale],id=useId(),dialog=useRef<HTMLDialogElement>(null);
 const [listing,setListing]=useState<HostFolders|null>(null),[location,setLocation]=useState("");
 const [selected,setSelected]=useState<string|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState(false);
 const generation=useRef(0),pending=useRef<AbortController|null>(null),history=useRef<string[]>([]);
 const load=async(path:string,back=false)=>{
  pending.current?.abort();const controller=new AbortController();pending.current=controller;
  const token=++generation.current,previous=listing?.path;
  setLoading(true);setError(false);setSelected(null);setLocation(path);
  const result=await readHostFolders(path,controller.signal);
  if(token!==generation.current || controller.signal.aborted)return;
  setLoading(false);setError(!result);
  if(result){
   if(back)history.current.pop();
   else if(previous && previous!==result.path)history.current.push(previous);
   setListing(result);setLocation(result.path);
  }
 };
 useEffect(()=>{
  const trigger=document.activeElement instanceof HTMLElement?document.activeElement:null,node=dialog.current;
  node?.showModal();void load("");
  return()=>{generation.current++;pending.current?.abort();node?.close();if(trigger?.isConnected)trigger.focus();};
 },[]);
 const ready=!!listing && !loading && !error && location===listing.path;
 const back=()=>{const path=history.current.at(-1);if(path)void load(path,true);};
 const rowKey=(event:KeyboardEvent<HTMLLIElement>,index:number)=>{
  if(!ready || !listing)return;
  let next=index;
  if(event.key==="ArrowDown")next=Math.min(index+1,listing.folders.length-1);
  else if(event.key==="ArrowUp")next=Math.max(index-1,0);
  else if(event.key==="Home")next=0;
  else if(event.key==="End")next=listing.folders.length-1;
  else if(event.key==="Enter"){event.preventDefault();void load(listing.folders[index].path);return;}
  else if(event.key!==" ")return;
  event.preventDefault();setSelected(listing.folders[next].path);
  const row=document.getElementById(id+"-folder-"+next);
  row?.focus({preventScroll:true});row?.scrollIntoView({block:"nearest"});
 };
 return <dialog ref={dialog} className="host-folder-dialog" aria-labelledby={id+"-title"}
  onCancel={event=>{event.preventDefault();onClose();}}>
  <header className="folder-dialog-header"><h3 id={id+"-title"}>{c.dialog}</h3><small>{c.hostHelp}</small></header>
  <div className="folder-toolbar">
   <button type="button" className="ghost folder-nav-button" aria-label={c.back} title={c.back} disabled={loading || !history.current.length} onClick={back}>←</button>
   <button type="button" className="ghost folder-nav-button" aria-label={c.up} title={c.up} disabled={loading || !listing?.parent} onClick={()=>{if(listing?.parent)void load(listing.parent);}}>↑</button>
   <label className="visually-hidden" htmlFor={id+"-location"}>{c.location}</label>
   <input id={id+"-location"} value={location} maxLength={4096} autoComplete="off" autoFocus
    onChange={event=>{setLocation(event.target.value);setSelected(null);}}
    onKeyDown={event=>{if(event.key==="Enter"){event.preventDefault();void load(location);}}}/>
   <button type="button" className="ghost folder-nav-button" aria-label={c.go} title={c.go} onClick={()=>void load(location)}>→</button>
  </div>
  <div className="folder-browser">
   <nav aria-label={c.roots} className="folder-places">{listing?.roots.map(root=><button type="button" key={root} title={root}
    aria-current={root===listing.path?"location":undefined} onClick={()=>void load(root)}><FolderIcon/><span>{root}</span></button>)}</nav>
   <div className="folder-panel">
    {loading?<p className="folder-status" role="status">{c.loading}</p>:error?<p className="folder-status alert" role="alert">{c.unavailable}</p>:
     listing && <><ul role="listbox" aria-label={c.folders} className="host-folder-list">{listing.folders.map((folder,index)=><li
      id={id+"-folder-"+index} key={folder.path} role="option" aria-label={folder.name} aria-selected={selected===folder.path}
      tabIndex={selected===folder.path || !selected && index===0?0:-1} title={folder.path}
      onClick={()=>setSelected(folder.path)} onDoubleClick={()=>void load(folder.path)} onKeyDown={event=>rowKey(event,index)}>
      <FolderIcon/><span>{folder.name}</span>
     </li>)}</ul>{!listing.folders.length && <p className="folder-status">{c.empty}</p>}</>}
   </div>
  </div>
  {listing?.truncated && !loading && !error && <p className="folder-limit" role="status">{c.truncated}</p>}
  <footer className="folder-dialog-actions"><button type="button" className="primary" disabled={!ready}
   onClick={()=>{if(ready && listing)onSelect(selected ?? listing.path);}}>{c.use}</button>
   <button type="button" className="ghost" onClick={onClose}>{c.cancel}</button></footer>
 </dialog>;
}

/** Automatic clone destination or an editable path with a host folder chooser. */
export function CloneLocation({value,automatic,label,locale,onChange,invalid}:{value:string;automatic:string;label:string;locale:Locale;onChange:(path:string)=>void;invalid?:boolean}) {
 const c=setupCopy[locale],id=useId();
 const [manual,setManual]=useState(false),[open,setOpen]=useState(false);
 const custom=manual || value!==automatic;
 return <div className="enrollment-field clone-location">
  <label htmlFor="enroll-repo_path">{label}<span aria-hidden="true"> *</span></label>
  <div className="clone-location-mode">
   <label><input type="radio" name={id} checked={!custom} onChange={()=>{setManual(false);onChange(automatic);}}/>{c.automatic}</label>
   <label><input type="radio" name={id} checked={custom} onChange={()=>setManual(true)}/>{c.custom}</label>
  </div>
  <div className="inline-field"><input id="enroll-repo_path" value={value} maxLength={1024} readOnly={!custom} autoComplete="off"
   aria-describedby="enrollment-clone-note" aria-invalid={invalid || undefined} onChange={event=>onChange(event.target.value)}/>
   {custom && <button type="button" className="ghost" onClick={()=>setOpen(true)}>{c.choose}</button>}</div>
  {open && <HostFolderDialog locale={locale} onClose={()=>setOpen(false)} onSelect={path=>{onChange(path);setOpen(false);}}/>}
 </div>;
}

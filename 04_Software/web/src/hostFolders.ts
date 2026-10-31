/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
export type HostFolders = {system:string;path:string;parent:string|null;roots:string[];folders:{name:string;path:string}[];truncated:boolean};

/** A folder name is one portable path segment, never a traversal or device name. */
export function validChildFolder(value:string):boolean {
 return value==="" || value.length<=255 && !/[\p{Cc}\p{Cf}<>:"/\\|?*]/u.test(value)
  && value===value.trim() && !/[. ]$/.test(value) && ![".",".."].includes(value)
  && !/^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(value);
}

/** Join a selected native directory and an optional new child without writing it. */
export function cloneDestination(path:string,child:string):string {
 return child && validChildFolder(child) ? path.replace(/[\\/]$/,"")+(path.includes("\\")?"\\":"/")+child : child?"":path;
}

/** Refuse malformed directory metadata before exposing it as navigation authority. */
export function validHostFolders(value:unknown):value is HostFolders {
 const item=value as HostFolders|null;
 if(!item || !["Windows","Linux"].includes(item.system))return false;
 const path=(s:unknown):s is string=>typeof s==="string" && s.length<=4096 && !/[\p{Cc}\p{Cf}]/u.test(s)
  && (item.system==="Windows"?/^[A-Za-z]:[\\/]/.test(s):/^\/(?!\/)/.test(s))
  && !s.split(/[\\/]/).includes("..");
 return path(item.path) && (item.parent===null || path(item.parent)) && typeof item.truncated==="boolean"
  && Array.isArray(item.roots) && item.roots.length>0 && item.roots.length<=32 && item.roots.every(path)
  && Array.isArray(item.folders) && item.folders.length<=200
  && new Set(item.folders.map(row=>row?.path)).size===item.folders.length
  && item.folders.every(row=>row && typeof row.name==="string" && row.name.length>0
   && row.name.length<=255 && !/[\p{Cc}\p{Cf}/\\]/u.test(row.name) && ![".",".."].includes(row.name)
   && path(row.path) && item.path.replace(/[\\/]$/,"")+(item.path.includes("\\")?"\\":"/")+row.name===row.path);
}

/** Read only the ADORE host; cancelling or superseding a dialog aborts its request. */
export async function readHostFolders(path:string,signal:AbortSignal):Promise<HostFolders|null> {
 try {
  const response=await fetch("/api/v1/host-folders"+(path?"?"+new URLSearchParams({path}):""),
   {credentials:"same-origin",cache:"no-store",signal:AbortSignal.any([signal,AbortSignal.timeout(10000)])});
  const result:unknown=response.ok?await response.json():null;
  return validHostFolders(result)?result:null;
 } catch {return null;}
}

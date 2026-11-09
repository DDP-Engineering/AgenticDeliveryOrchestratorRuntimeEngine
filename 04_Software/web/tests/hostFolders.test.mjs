/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test} from "node:test";
import assert from "node:assert/strict";
import {cloneDestination,validChildFolder,validHostFolders,readHostFolders} from "../src/hostFolders.ts";
import {setupCopy} from "../src/setupCopy.ts";

test("clone destinations preserve Windows/Linux spaces and reject child traversal/devices",()=>{
 assert.equal(cloneDestination("D:\\Projects","my repo"),"D:\\Projects\\my repo");
 assert.equal(cloneDestination("/home/projects/","my repo"),"/home/projects/my repo");
 assert.equal(cloneDestination("/",""),"/");
 for(const child of ["..",".","../escape","C:\\escape","a/b","file\nname","CON","nul.txt","LPT1","end."," space ","a".repeat(256)]) {
  assert.equal(validChildFolder(child),false,child);
  assert.equal(cloneDestination("/tmp",child),"");
 }
 for(const c of Object.values(setupCopy))assert.deepEqual(Object.keys(c).sort(),Object.keys(setupCopy.en).sort());
});

test("host folder metadata validates absolute paths and bounded child navigation",()=>{
 const listing={system:"Linux",path:"/home",parent:"/",roots:["/"],folders:[{name:"user",path:"/home/user"}],truncated:false};
 assert.equal(validHostFolders(listing),true);
 assert.equal(validHostFolders({...listing,system:"Windows",path:"D:\\",parent:null,roots:["D:\\"],folders:[]}),true);
 for(const change of [{path:"relative"},{path:"//server/share"},{parent:4},{roots:[]},{truncated:"false"},
  {folders:[{name:"../outside",path:"/outside"}]},{folders:[{name:"user",path:"/elsewhere"}]},
  {folders:Array(201).fill(listing.folders[0])},{folders:[...listing.folders,...listing.folders]}]) {
  assert.equal(validHostFolders({...listing,...change}),false);
 }
});

test("host folder reads send host paths and fail closed on bad responses or abort",async()=>{
 const old=globalThis.fetch,signal=new AbortController().signal;
 const listing={system:"Linux",path:"/",parent:null,roots:["/"],folders:[],truncated:false};
 try {
  globalThis.fetch=async(url,options)=>{
   assert.equal(new URL("http://localhost"+url).searchParams.get("path"),"/home/my folder");
   assert.equal(options.credentials,"same-origin");assert.equal(options.cache,"no-store");
   return {ok:true,json:async()=>listing};
  };
  assert.deepEqual(await readHostFolders("/home/my folder",signal),listing);
  globalThis.fetch=async()=>({ok:true,json:async()=>({folders:[]})});
  assert.equal(await readHostFolders("",signal),null);
  globalThis.fetch=async()=>{throw new DOMException("cancelled","AbortError");};
  assert.equal(await readHostFolders("",signal),null);
 } finally {globalThis.fetch=old;}
});

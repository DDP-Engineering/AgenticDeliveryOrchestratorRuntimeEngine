/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test} from "node:test";
import assert from "node:assert/strict";
import {commandForExecutable,discoveryCopy,executableFromCommand,validExecutablePath,validLocalExecutors,readLocalExecutors} from "../src/localExecutors.ts";

test("manual native paths preserve spaces and launch placeholders on both operating systems",()=>{
 assert.equal(commandForExecutable("pi","C:\\Program Files\\Pi\\pi.exe"),'"C:/Program Files/Pi/pi.exe" -p --mode json --model {model} {prompt}');
 assert.equal(commandForExecutable("opencode","/opt/installed agents/opencode"),'"/opt/installed agents/opencode" run --dir {worktree} -m {model} --format json {prompt}');
 for(const path of ["opencode","C:relative.exe",'/tmp/bad"path',"/tmp/{prompt}","/tmp/x\nfoo","//network/path"]){
  assert.equal(validExecutablePath(path),false,path);
  assert.equal(commandForExecutable("opencode",path),"");
 }
 assert.equal(commandForExecutable("unknown","/bin/tool"),"");
 assert.equal(executableFromCommand('"C:/Program Files/Pi/pi.exe" -p {prompt}'),"C:/Program Files/Pi/pi.exe");
 assert.equal(executableFromCommand('"/opt/my tools/opencode" run {prompt}'),"/opt/my tools/opencode");
 assert.equal(executableFromCommand("opencode run {prompt}"),"");
 for(const copy of Object.values(discoveryCopy)) assert.deepEqual(Object.keys(copy).sort(),Object.keys(discoveryCopy.en).sort());
});

test("discovery response is bounded and rejects duplicate agents and malformed launch references",()=>{
 const valid={system:"Linux",machine:"host",account:"account",executors:["opencode","pi","codex","qwen"].map(agent=>({agent,installations:[]}))};
 assert.equal(validLocalExecutors(valid),true);
 for(const mutate of [v=>{v.executors[1].agent="opencode";},v=>{v.executors[0].installations=[{executable:"relative",entrypoint:null,source:"PATH",command:"tool {prompt}"}];},v=>{v.system="unknown";},v=>{v.executors[0].installations=Array(13).fill({});}]){
  const invalid=structuredClone(valid);mutate(invalid);assert.equal(validLocalExecutors(invalid),false);
 }
});

test("failed HTTP and malformed JSON discovery fail closed without launch proposals",async()=>{
 const previous=globalThis.fetch;
 try {
  globalThis.fetch=async()=>new Response("{}",{status:503});
  assert.equal(await readLocalExecutors(),null);
  globalThis.fetch=async()=>new Response("{broken",{status:200});
  assert.equal(await readLocalExecutors(),null);
  globalThis.fetch=async()=>{throw Error("offline");};
  assert.equal(await readLocalExecutors(),null);
 } finally {globalThis.fetch=previous;}
});

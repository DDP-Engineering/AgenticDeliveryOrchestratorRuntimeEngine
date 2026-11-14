/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readCapacity, readCapacityOverview, currentJobStates, readWorkers, workerCopy } from "../src/projectStatus.ts";
import { readDraft, writeDraft, clearDraft } from "../src/settingsDrafts.ts";

const id = "a".repeat(32);
const worker = { role: "project", project_id: id, run_id: "", heartbeat: "recent", activity: "busy", updated_at: "2026-11-14T01:00:00+00:00" };
const capacity = { project_id: id, active_limit: 1, limit: 1, occupied: 1, free: 0, waiting_jobs: 1, available: false,
  worker, queue: [{ id: 4, action: "start", reason: "project_limit" }], waiting_runs: [], staged_change: true, staged_limit: 2,
  recent_operations: [{ id: 4, action: "start", status: "pending", result: "", reason: "" }] };

test("scoped capacity and worker evidence validates identity, arithmetic and closed domains", () => {
  assert.deepEqual(readCapacity(capacity, id), capacity);
  assert.equal(readCapacity({...capacity,waiting_runs:[{ticket_iid:7,reason:"staged_change"}]},id).waiting_runs[0].reason,"staged_change");
  for (const patch of [{project_id:"b".repeat(32)}, {limit:0}, {free:2}, {waiting_jobs:-1},
    {worker:{...worker,project_id:"b".repeat(32)}}, {queue:[{id:4,action:"start",reason:"invented"}]},
    {recent_operations:[{id:4,action:"start",status:"finished"}]}, {available:true},
    {waiting_runs:[{ticket_iid:7,reason:"invented"}]}]) {
    assert.throws(()=>readCapacity({...capacity,...patch},id), /unexpected_response/);
  }
  assert.equal(readWorkers({workers:[worker]}).workers.length,1);
  assert.throws(()=>readWorkers({workers:[{...worker,heartbeat:"alive"}]}),/unexpected_response/);
  for (const locale of ["en","fr","de","ro"]) assert.ok(workerCopy[locale].project_limit);
});

test("unsaved values retain account/project/revision scope and invalid input without secrets", () => {
  const data = new Map();
  const storage = {getItem:key=>data.get(key)??null,setItem:(key,value)=>data.set(key,value),removeItem:key=>data.delete(key)};
  const saved = {revision:"b".repeat(64),drafts:{"polling.max_concurrent_runs":"0","container.runtime":"podman"},editing:["polling.max_concurrent_runs"]};
  assert.equal(writeDraft(storage,1,id,saved),true);
  assert.deepEqual(readDraft(storage,1,id),saved);
  assert.equal(readDraft(storage,2,id),null);
  assert.equal(readDraft(storage,1,"b".repeat(32)),null);
  assert.equal(writeDraft(storage,1,id,{...saved,drafts:{"executor.api_key":"secret"}}),false);
  for(const base_url of ["http://user:password@host/v1","https://host/v1?api_key=secret"]){
    const connection=JSON.stringify({provider:"custom",model:"model",thinking:"",api:"openai-completions",base_url});
    assert.equal(writeDraft(storage,1,id,{...saved,drafts:{"executor.connection":connection}}),false);
  }
  assert.deepEqual(readDraft(storage,1,id),saved);
  const key=[...data.keys()][0]; data.set(key,'{"revision": "legacy"}');
  assert.deepEqual(readDraft(storage,1,id),{corrupt:true});
  clearDraft(storage,1,id);assert.equal(readDraft(storage,1,id),null);
  assert.equal(writeDraft({...storage,setItem:()=>{throw Error("quota");}},1,id,saved),false);
});


test("capacity overview accepts only current job counts and an explicit monitoring state",()=>{
  const value={...capacity,paused:true,job_counts:Object.fromEntries(currentJobStates.map(status=>[status,status==="working"?2:0]))};
  assert.equal(readCapacityOverview(value,id).job_counts.working,2);
  for(const patch of [{paused:"yes"},{job_counts:null},{job_counts:{working:1}},
    {job_counts:{...value.job_counts,working:-1}},{job_counts:{...value.job_counts,done:4}}]){
    assert.throws(()=>readCapacityOverview({...value,...patch},id),/unexpected_response/);
  }
});

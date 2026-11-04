/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import test from "node:test";
import assert from "node:assert/strict";
import {validPendingConfig} from "../src/settings.ts";
import {prepareSettingDrafts,recoverSettingDrafts,candidateMatchesEdits,settingImpacts} from "../src/settingsSave.ts";

const candidate = {
 base_revision:"a".repeat(64),candidate_revision:"b".repeat(64),
 key:"settings.batch",value:JSON.stringify({"polling.poll_interval_seconds":75}),
 proposed_value:{"polling.poll_interval_seconds":75},
 created_at:"2026-11-04T10:00:00Z",restart_required:false,
};

test("a bound complete settings batch is accepted as pending evidence",()=>{
 assert.equal(validPendingConfig(candidate),true);
});

test("batch evidence refuses malformed members and mismatched public values",()=>{
 for(const proposed_value of [[],{},{"settings.batch":"nested"},{"polling.poll_interval_seconds":null},
   {"polling.poll_interval_seconds":Infinity},{"recovery.retry_backoff_seconds":[-1]},
   {"executor.connection":{provider:"custom",model:"model",base_url:"bad",api:"bad"}}]){
  assert.equal(validPendingConfig({...candidate,proposed_value,value:JSON.stringify(proposed_value)}),false);
 }
 assert.equal(validPendingConfig({...candidate,value:'{"polling.poll_interval_seconds":90}'}),false);
 assert.equal(validPendingConfig({...candidate,candidate_revision:"unbound"}),false);
});

const row=(key,value,input="number",extra={})=>({
 key,editKey:key,value,input,choices:[],group:"selection",groupIndex:0,
 source:"project",restart:false,common:false,defaultValue:value,step:"1",...extra,
});

test("one settings draft retains multiple edits and omits unchanged values",()=>{
 const rows=[row("polling.poll_interval_seconds",60),row("polling.poll_jitter_seconds",5),row("polling.poll_backoff",true,"boolean")];
 const draft=prepareSettingDrafts({},rows,{
  "polling.poll_interval_seconds":"75","polling.poll_jitter_seconds":"7","polling.poll_backoff":"true",
 });
 assert.deepEqual(draft,{edits:[
  {key:"polling.poll_interval_seconds",value:"75"},{key:"polling.poll_jitter_seconds",value:"7"},
 ],invalid:[]});
 assert.deepEqual(settingImpacts(draft.edits,rows),[]);
});

test("incomplete and forbidden drafts stay invalid instead of silently dropping members",()=>{
 const rows=[row("polling.poll_interval_seconds",60,"number",{minimum:1}),row("metrics.db_path","private","none")];
 for(const value of ["","NaN","-1","9007199254740993"]){
  assert.deepEqual(prepareSettingDrafts({},rows,{"polling.poll_interval_seconds":value}).invalid,["polling.poll_interval_seconds"]);
 }
 assert.deepEqual(prepareSettingDrafts({},rows,{"metrics.db_path":"changed","unknown.key":"x"}).invalid,["metrics.db_path","unknown.key"]);
});

test("equivalent duration and map ordering do not enable Save",()=>{
 const rows=[row("clarification.answer_timeout","24h","duration"),row("workflow.stage_timeout_overrides",{build:12,validate:20},"stage-timeouts")];
 assert.deepEqual(prepareSettingDrafts({},rows,{
  "clarification.answer_timeout":"1440m","workflow.stage_timeout_overrides":'{"validate":20,"build":12}',
 }),{edits:[],invalid:[]});
});

test("recovered values use the right editor domain and exact response meaning",()=>{
 const rows=[row("recovery.retry_backoff_seconds",[1,2],"retry-delays"),row("polling.poll_interval_seconds",60)];
 const saved={...candidate,proposed_value:{"recovery.retry_backoff_seconds":[3,4],"polling.poll_interval_seconds":75}};
 const drafts=recoverSettingDrafts({},rows,saved);
 assert.equal(drafts["recovery.retry_backoff_seconds"],"3\n4");
 const {edits}=prepareSettingDrafts({},rows,drafts);
 assert.equal(candidateMatchesEdits(saved,edits,rows),true);
 assert.equal(candidateMatchesEdits({...saved,proposed_value:{"polling.poll_interval_seconds":75}},edits,rows),false);
 assert.equal(candidateMatchesEdits({...saved,proposed_value:{...saved.proposed_value,"polling.poll_interval_seconds":"75"}},edits,rows),false);
});

test("only important effects request confirmation",()=>{
 const edits=[
  {key:"container.system_packages",value:"true"},{key:"executor.internet",value:"true"},
  {key:"budgets.max_cost_usd",value:"10"},{key:"delivery.draft",value:"false"},
  {key:"platform.repo",value:"group/project"},{key:"executor.connection",value:"{}"},
 ];
 assert.deepEqual(settingImpacts(edits,[row("executor.model","model","connection",{editKey:"executor.connection",restart:true})]),
  ["packages","network","budget","publication","identity","runtime"]);
});

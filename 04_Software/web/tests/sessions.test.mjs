/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test} from "node:test";
import assert from "node:assert/strict";
import {readSessions,readSessionPage} from "../src/sessionModel.ts";
const session={id:"build-attempt-2-attempt1-10",stage:"build",attempt:2,start_at:null,end_at:"2026-11-14T10:00:00Z",outcome:"succeeded",exit_code:0};
const page=()=>({session,items:[{kind:"tool_result",tool:"bash",call_id:"x",text:"API_KEY=fake-exact",is_error:false}],next_cursor:10});
test("literal recorded text and physical archive identity survive transport validation",()=>{
  assert.deepEqual(readSessions({sessions:[session]}),[session]);
  assert.equal(readSessionPage(page(),session.id,0,false).items[0].text,"API_KEY=fake-exact");
});
test("malformed identities, cursors, text bounds and structured costs fail closed",()=>{
  for(const mutate of [p=>p.next_cursor=0,p=>p.session={...session,id:"../outside"},p=>p.items[0].text="🙂".repeat(5000),
    p=>p.items[0].kind="system",p=>p.items[0].is_error="no",p=>p.items=[{kind:"usage",text:"",usage:{input:-1}}],
    p=>p.items=[{kind:"usage",text:"",usage:{cost:{total:1}}}]]){
    const value=page();mutate(value);assert.throws(()=>readSessionPage(value,session.id,0,false));
  }
  assert.throws(()=>readSessions({sessions:[session,session]}));
  assert.throws(()=>readSessions({sessions:[{...session,attempt:3}]}));
  const value=page();value.items=[{kind:"usage",text:"",usage:{input:1,cost:{total:.1}}}];
  assert.equal(readSessionPage(value,session.id,0,true).items[0].usage.cost.total,.1);
  value.items=[{kind:"assistant",text:"",parts:[{kind:"assistant",text:"answer"},{kind:"reasoning",text:"thought"},{kind:"usage",text:"",usage:{input:1}}]}];
  assert.equal(readSessionPage(value,session.id,0,false).items.length,1);
  value.items[0].parts[0].parts=[];
  assert.throws(()=>readSessionPage(value,session.id,0,false));
});

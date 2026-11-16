import {test} from "node:test";
import assert from "node:assert/strict";
import {readSessions,readSessionPage,shouldPollSession,applySessionActivity} from "../src/sessionModel.ts";
const session={id:"build-attempt-2-attempt1-10",stage:"build",attempt:2,start_at:null,end_at:"2026-11-14T10:00:00Z",outcome:"succeeded",exit_code:0};
const page=()=>({session,items:[{kind:"tool_result",tool:"bash",call_id:"x",text:"API_KEY=fake-exact",is_error:false}],next_cursor:10});

test("live polling requires a working visible active view and live selection",()=>{
  assert.equal(shouldPollSession("working",true,true,true),true);
  for(const args of [["done",true,true,true],["working",false,true,true],["working",true,false,true],["working",true,true,false]])
    assert.equal(shouldPollSession(...args),false);
});

test("unfinished tools and thinking survive cursor pages without text deltas",()=>{
  let state={thinking:false,tools:{}};
  state=applySessionActivity(state,{items:[],thinking:true});
  assert.equal(state.thinking,true);
  state=applySessionActivity(state,{items:[{kind:"tool_call",tool:"bash",call_id:"x",text:"args"}],thinking:false});
  assert.equal(state.tools.x,"bash");
  state=applySessionActivity(state,{items:[],thinking:null});
  assert.equal(state.tools.x,"bash");
  state=applySessionActivity(state,{items:[{kind:"tool_result",tool:"bash",call_id:"x",text:"result",is_error:false}],thinking:null});
  assert.deepEqual(Object.entries(state.tools),[]);
  state=applySessionActivity(state,{items:[{kind:"tool_call",tool:"bash",call_id:"__proto__",text:"args"}],thinking:null});
  assert.equal(state.tools.__proto__,"bash");
});

test("live transport permits an unchanged complete-line cursor and validates handoff",()=>{
  const live={...session,id:"live-"+"a".repeat(32),live:true,archive_id:session.id,start_at:session.end_at,end_at:null,outcome:null,exit_code:null};
  assert.equal(readSessions({sessions:[live,session]})[0].live,true);
  const value={session:live,items:[],next_cursor:0,continuity:"b".repeat(64),thinking:null,session_ended:false};
  assert.equal(readSessionPage(value,live.id,0,false).next_cursor,0);
  for(const mutate of [p=>p.continuity="bad",p=>p.thinking="yes",p=>p.next_cursor=-1]){
    const bad={...value};mutate(bad);assert.throws(()=>readSessionPage(bad,live.id,0,false));
  }
  assert.equal(readSessionPage({session_ended:true,archive_id:session.id,items:[],next_cursor:null},live.id,0,false).session_ended,true);
  assert.throws(()=>readSessions({sessions:[{...live,end_at:session.end_at}]}));
});
test("literal recorded text and physical archive identity survive transport validation",()=>{
  assert.deepEqual(readSessions({sessions:[session]}),[session]);
  assert.equal(readSessionPage(page(),session.id,0,false).items[0].text,"API_KEY=fake-exact");
});
test("malformed identities, cursors, text bounds and structured costs fail closed",()=>{
  for(const mutate of [p=>p.next_cursor=0,p=>p.session={...session,id:"../outside"},p=>p.items[0].text="🙂".repeat(4*1024*1024+1),
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

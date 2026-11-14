/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {test} from "node:test";
import assert from "node:assert/strict";
import {existsSync} from "node:fs";

test("instruction transport is literal and bound to the requested composite job",async()=>{
  assert.ok(existsSync(new URL("../src/instructionModel.ts",import.meta.url)),"instruction transport missing");
  const {readInstructions,readInstructionResponse,validInstructionText}=await import("../src/instructionModel.ts");
  const row={schema:1,id:"a".repeat(32),user:{id:7,username:"operator"},created_at:"2026-11-14T10:00:00Z",mode:"now",text:"  password=SYNTHETIC\n<script>🙂</script>",delivery:null,last_error:""};
  const value={project_id:"p",run_id:"r",instructions:[row],notices:[]};
  assert.equal(readInstructions(value,"p","r").instructions[0].text,row.text);
  assert.equal(readInstructionResponse({project_id:"p",run_id:"r",instruction:row},"p","r").id,row.id);
  for(const bad of [{...value,project_id:"other"},{...value,run_id:"other"},{...value,instructions:[row,row]},
    {...value,instructions:[{...row,delivery:{at:"invalid",how:"steer"}}]},
    {...value,instructions:[{...row,text:"a\0b"}]}, {...value,instructions:[{...row,user:{id:7,username:"\ud800"}}]}])
    assert.throws(()=>readInstructions(bad,"p","r"));
  assert.equal(validInstructionText("🙂".repeat(4000)),true);
  for(const text of ["","x".repeat(4001),"a\0b","\ud800"])assert.equal(validInstructionText(text),false);
});

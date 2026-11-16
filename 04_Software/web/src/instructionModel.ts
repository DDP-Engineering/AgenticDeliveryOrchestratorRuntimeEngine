import {ApiError} from "./errors.ts";

export type Instruction = {schema:1;id:string;user:{id:number;username:string};created_at:string;mode:"now"|"after";text:string;delivery:null|{at:string;how:"prompt"|"steer"|"follow_up"};last_error:""|"pi_rejected"};
const invalid=():never=>{throw new ApiError("unexpected_response");};
const object=(value:unknown):Record<string,unknown>=>value!==null&&typeof value==="object"&&!Array.isArray(value)?value as Record<string,unknown>:invalid();
const unicode=(value:string)=>!Array.from(value).some(c=>{const n=c.codePointAt(0)!;return n>=0xd800&&n<=0xdfff;});
const timestamp=(value:unknown)=>typeof value==="string"&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)&&Number.isFinite(Date.parse(value));

/** Count Unicode characters without trimming or replacing the operator's text. */
export function validInstructionText(value:string):boolean {
  return Array.from(value).length>=1&&Array.from(value).length<=4000&&!value.includes("\0")&&unicode(value);
}

function instruction(value:unknown):Instruction {
  const row=object(value),user=object(row.user);
  if(row.schema!==1||typeof row.id!=="string"||! /^[a-f0-9]{32}$/.test(row.id)||
    !Number.isSafeInteger(user.id)||Number(user.id)<1||typeof user.username!=="string"||
    !user.username.length||Array.from(user.username).length>200||/[\x00-\x1f]/.test(user.username)||!unicode(user.username)||
    !timestamp(row.created_at)||(typeof row.mode!=="string"||!["now","after"].includes(row.mode))||typeof row.text!=="string"||!validInstructionText(row.text)||
    (typeof row.last_error!=="string"||!["","pi_rejected"].includes(row.last_error)))invalid();
  if(row.delivery!==null){const receipt=object(row.delivery);if(!timestamp(receipt.at)||(typeof receipt.how!=="string"||!["prompt","steer","follow_up"].includes(receipt.how)))invalid();}
  return row as Instruction;
}

function identity(value:unknown,project:string,run:string):Record<string,unknown> {
  const row=object(value);if(row.project_id!==project||row.run_id!==run)invalid();return row;
}

/** Fence every literal read to the exact job and reject malformed/duplicate rows. */
export function readInstructions(value:unknown,project:string,run:string):{instructions:Instruction[];notices:string[]} {
  const data=identity(value,project,run);
  if(!Array.isArray(data.instructions)||data.instructions.length>256||!Array.isArray(data.notices)||data.notices.length>256||data.notices.some(n=>typeof n!=="string"||n.length>300))invalid();
  const rows=(data.instructions as unknown[]).map(instruction);
  if(new Set(rows.map(row=>row.id)).size!==rows.length)invalid();
  return {instructions:rows,notices:data.notices as string[]};
}

/** A send completion can update only its requested composite job. */
export function readInstructionResponse(value:unknown,project:string,run:string):Instruction {
  return instruction(identity(value,project,run).instruction);
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { validPreparationEvidence, type PreparationEvidence } from "./executionPlan.ts";
export const lifecycles = ["working", "publishing", "parked-clarification", "awaiting-approval", "in-review", "handoff-pending", "handed-off", "done", "failed", "cancelled", "stale"] as const;
export const stages = ["frame", "specify", "design", "build", "validate", "done", "publishing"] as const;
export type Lifecycle = typeof lifecycles[number];
export type Workflow = "aegis" | "direct";
export type DirectEvidence = { attempt: number | null };
export type JobBudget = { launches: number; active_seconds: number } & (
  { availability: "observed"; reason: null; max_launches: number;
    max_active_seconds: number; config_revision: string } |
  { availability: "unavailable"; reason: "config_missing" | "config_corrupt";
    max_launches: null; max_active_seconds: null; config_revision: null }
);
export type Job = {
  workflow: Workflow;
  direct?: DirectEvidence;
  state_revision?: string;
  budget?: JobBudget;
  preparation?: PreparationEvidence | null;
  project_id: string; project_name: string; project_display_name: string; project_archived: boolean;
  run_id: string; ticket_iid: number; ticket_title: string | null; ticket_url: string | null; mr_url: string | null;
  lifecycle: Lifecycle; stage: string; status_group: string; outcome: string;
  stage_failures: number; review_rounds: number; created_at: string | null; updated_at: string | null; last_activity_at: string | null;
  waiting: { availability: "observed" | "unknown"; reason: string | null; next_action: string | null;
    responsible_role: string | null; responsible_person: string | null; evidence_url: string | null; source: string | null };
  evidence_url: string; consumption: { availability: "unknown" };
  coverage: { ticket: string; journal: string; title: string; last_activity: string };
  timeline?: Array<{ ts: string | null; event: string; stage: string | null }>;
};
export type JobPage = { items: Job[]; total: number; counts: Record<string, number>; groups: Record<string, number>;
  limit: number; offset: number; complete: true; snapshot: string; snapshot_semantics: "optimistic-source-revision";
  unreadable_projects?: string[] };
export class IncompleteJobs extends Error { constructor() { super("incomplete"); } }
const lifecycleGroup = (value: string) => ["working", "publishing"].includes(value) ? "active" :
  ["parked-clarification", "awaiting-approval", "handoff-pending"].includes(value) ? "waiting" : value === "in-review" ? "review" : "terminal";
const invalid = (): never => { throw new Error("unexpected_response"); };
const object = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : invalid();
const string = (value: unknown): value is string => typeof value === "string";
const optionalText = (value: unknown) => value === null || string(value);
const count = (value: unknown) => Number.isSafeInteger(value) && Number(value) >= 0;
const stamp = (value: unknown) => value === null || string(value) && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));

/** Validate saved HTTP(S) evidence, including the supported forge comment anchors. */
export function safeEvidenceLink(value: unknown): string | null {
  if (!string(value) || !/^https?:\/\//.test(value)) return null;
  try {
    const decoded = decodeURIComponent(value);
    if (/[\s\x00-\x1f\x7f\\]/.test(decoded)) return null;
    const url = new URL(value);
    if (!url.hostname || url.username || url.password || url.search ||
      url.hash && !/^#(?:issuecomment-\d+|note_\d+)$/.test(url.hash)) return null;
    return value;
  } catch { return null; }
}

/** Fail closed at the transport boundary before exposing an authorized job. */
export function readJob(value: unknown, authorized: string[]): Job {
  const revision = object(value).state_revision;
  if (revision !== undefined && (!string(revision) || !/^[a-f0-9]{64}$/.test(revision))) invalid();
  const row = object(value), waiting = object(row.waiting), coverage = object(row.coverage);
  if (!string(row.project_id) || !/^[a-f0-9]{32}$/.test(row.project_id) || !authorized.includes(row.project_id) ||
    !string(row.run_id) || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$/.test(row.run_id) ||
    !string(row.project_name) || !string(row.project_display_name) || typeof row.project_archived !== "boolean" ||
    !count(row.ticket_iid) || Number(row.ticket_iid) < 1 || !optionalText(row.ticket_title) ||
    (row.workflow !== "aegis" && row.workflow !== "direct") ||
    row.workflow === "direct" && !["build", "validate", "done"].includes(String(row.stage))
      && !(row.stage === "publishing" && row.lifecycle === "failed") ||
    !lifecycles.includes(row.lifecycle as Lifecycle) || !stages.includes(row.stage as typeof stages[number]) ||
    row.status_group !== lifecycleGroup(String(row.lifecycle)) || !string(row.outcome) ||
    !count(row.stage_failures) || !count(row.review_rounds) ||
    ![row.created_at, row.updated_at, row.last_activity_at].every(stamp) ||
    row.evidence_url !== `/api/v1/jobs/${row.project_id}/${row.run_id}` ||
    object(row.consumption).availability !== "unknown") invalid();
  if (row.budget !== undefined) {
    const budget = object(row.budget);
    if (!count(budget.launches) || typeof budget.active_seconds !== "number" ||
      !Number.isFinite(budget.active_seconds) || budget.active_seconds < 0) invalid();
    if (budget.availability === "observed") {
      if (!count(budget.max_launches) || Number(budget.max_launches) < 1 ||
        !count(budget.max_active_seconds) || Number(budget.max_active_seconds) < 1 || budget.reason !== null ||
        !string(budget.config_revision) || !/^[a-f0-9]{64}$/.test(budget.config_revision)) invalid();
    } else if (budget.availability !== "unavailable" ||
      !["config_missing", "config_corrupt"].includes(String(budget.reason)) ||
      budget.max_launches !== null || budget.max_active_seconds !== null || budget.config_revision !== null) invalid();
  }
  if (row.preparation !== undefined && row.preparation !== null && !validPreparationEvidence(row.preparation)) invalid();
  for (const link of [row.ticket_url, row.mr_url, waiting.evidence_url]) if (link !== null && safeEvidenceLink(link) === null) invalid();
  if (!["unknown", "observed"].includes(String(waiting.availability)) ||
    ![waiting.reason, waiting.next_action, waiting.responsible_role, waiting.responsible_person, waiting.source].every(optionalText) ||
    !["missing", "present"].includes(String(coverage.ticket)) || !["missing", "present"].includes(String(coverage.journal)) ||
    !["unknown", "observed"].includes(String(coverage.title)) || !["unknown", "observed"].includes(String(coverage.last_activity))) invalid();
  const actions: Record<string, [string, string]> = {
    answer_question_on_ticket: ["parked-clarification", "human_responder"],
    review_candidate_on_ticket: ["awaiting-approval", "human_approver"],
    review_draft_on_forge: ["in-review", "human_reviewer"],
  };
  if (waiting.next_action !== null) {
    const expected = actions[String(waiting.next_action)];
    if (!expected || expected[0] !== row.lifecycle || expected[1] !== waiting.responsible_role ||
      waiting.availability !== "observed" || !waiting.evidence_url) invalid();
  }
  return row as unknown as Job;
}

/** Validate complete counts, composite identity and optimistic source revision. */
export function readJobPage(value: unknown, authorized: string[], overview = false): JobPage {
  const page = object(value);
  if (page.complete === false) throw new IncompleteJobs();
  if (page.complete !== true || !Array.isArray(page.items) || !count(page.total) || !count(page.limit) || !count(page.offset) ||
    !string(page.snapshot) || !/^[a-f0-9]{64}$/.test(page.snapshot) || page.snapshot_semantics !== "optimistic-source-revision") invalid();
  const counts = object(page.counts);
  for (const [key, value] of Object.entries(counts)) if (!lifecycles.includes(key as Lifecycle) || !count(value)) invalid();
  const groups = object(page.groups);
  for (const key of ["active", "waiting", "review", "terminal"]) {
    if (!count(groups[key]) || groups[key] !== Object.entries(counts).reduce((sum, [lifecycle, value]) =>
      sum + (lifecycleGroup(lifecycle) === key ? Number(value) : 0), 0)) invalid();
  }
  if (Number(page.total) > Object.values(counts).reduce<number>((sum, value) => sum + Number(value), 0)) invalid();
  const items = (page.items as unknown[]).map(row => readJob(row, authorized));
  if (items.length > Number(page.limit) || items.length > Number(page.total) ||
    new Set(items.map(row => `${row.project_id}/${row.run_id}`)).size !== items.length) invalid();
  if (page.unreadable_projects !== undefined) {
    const unreadable = page.unreadable_projects;
    if (!overview || !Array.isArray(unreadable) ||
      unreadable.some(id => !string(id) || !/^[a-f0-9]{32}$/.test(id) || !authorized.includes(id)) ||
      new Set(unreadable).size !== unreadable.length ||
      items.some(row => unreadable.includes(row.project_id)) ||
      (authorized.every(id => unreadable.includes(id)) && Object.values(counts).some(value => Number(value) > 0))) invalid();
  }
  return { ...page, items } as JobPage;
}

/** Validate the closed saved direct evidence before rendering any result. */
function readDirectEvidence(value: unknown): DirectEvidence {
  const direct = object(value);
  if (Object.keys(direct).join() !== "attempt" ||
    direct.attempt !== null && (!count(direct.attempt) || Number(direct.attempt) < 1)) invalid();
  return direct as DirectEvidence;
}

/** Validate strict detail; display observed events rather than inferred stage completion. */
export function readJobDetail(value: unknown, project: string, run: string): Job & { timeline: NonNullable<Job["timeline"]> } {
  const response = object(value);
  if (response.complete === false) throw new IncompleteJobs();
  if (response.complete !== true || !string(response.snapshot) || !/^[a-f0-9]{64}$/.test(response.snapshot)) invalid();
  const job = readJob(response.job, [project]);
  if (job.run_id !== run || !job.budget || !Array.isArray(job.timeline)) invalid();
  if (job.workflow === "direct") readDirectEvidence(job.direct);
  else if ("direct" in job) invalid();
  for (const event of job.timeline!) if (!event || !stamp(event.ts) || !string(event.event) || !event.event ||
    event.stage !== null && (!stages.includes(event.stage as typeof stages[number]) ||
      job.workflow === "direct" && !["build", "validate", "done"].includes(event.stage)
        && !(event.stage === "publishing" && event.event === "reset"))) invalid();
  return job as Job & { timeline: NonNullable<Job["timeline"]> };
}

/** Old recorded activity is evidence age, never a diagnosis of executor health. */
export function activityAge(value: string | null, now = Date.now()): "unknown" | "recent" | "old" {
  return value === null ? "unknown" : now - Date.parse(value) > 15 * 60_000 ? "old" : "recent";
}

/** Mirror conservative existing operator controls; the API/worker rechecks authority. */
export function stableExecutionDrift(job: Job): boolean {
  return job.lifecycle === "failed" && /^(?:INFRASTRUCTURE_EXHAUSTED|RETRY_REVALIDATION_FAILED):/.test(job.outcome) &&
    /execution profile drift|Retry execution settings changed|Retry cannot change the job execution backend|different machine\/account\/state root/.test(job.outcome);
}

/** Mirror conservative existing operator controls; the API/worker rechecks authority. */
export function commandAllowed(job: Job, action: "retry" | "cancel" | "restart"): boolean {
  if (job.project_archived) return false;
  if (action === "restart") return job.lifecycle === "failed" && /^[a-f0-9]{64}$/.test(job.state_revision ?? "");
  return action === "retry" ? job.lifecycle === "failed" && !stableExecutionDrift(job) :
    !["done", "failed", "cancelled", "stale", "handoff-pending", "handed-off"].includes(job.lifecycle);
}


export type ExecutorOutput = {project_id:string;run_id:string;state_revision:string;in_progress:boolean} & (
  {availability:"observed";stdout:string;stderr:string;exit_code:number;timed_out:boolean;
    attempt:number;stage:typeof stages[number] | null;recorded_at:string} |
  {availability:"missing";stdout:null;stderr:null;exit_code:null;timed_out:null;
    attempt:null;stage:null;recorded_at:null}
);
/** Closed operational evidence transport; raw transcript bytes are never displayable. */
export function readExecutorOutput(value: unknown, project: string, run: string): ExecutorOutput {
  const row = object(value);
  if (Object.keys(row).sort().join(",") !== "attempt,availability,exit_code,in_progress,project_id,recorded_at,run_id,stage,state_revision,stderr,stdout,timed_out" ||
    row.project_id !== project || row.run_id !== run || typeof row.in_progress !== "boolean" ||
    !string(row.state_revision) || !/^[a-f0-9]{64}$/.test(row.state_revision)) invalid();
  if (row.availability === "missing") {
    if ([row.stdout,row.stderr,row.exit_code,row.timed_out,row.attempt,row.stage,row.recorded_at].some(value=>value!==null)) invalid();
  } else if (row.availability === "observed") {
    if (!string(row.stdout) || !string(row.stderr) || row.stdout.length>65536 || row.stderr.length>65536 ||
      !Number.isInteger(row.exit_code) || Number(row.exit_code)<-(2**31) || Number(row.exit_code)>=2**31 ||
      typeof row.timed_out!=="boolean" || !count(row.attempt) || Number(row.attempt)<1 ||
      row.stage !== null && !stages.includes(row.stage as typeof stages[number]) ||
      row.recorded_at === null || !stamp(row.recorded_at)) invalid();
    const credential = /(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|[a-fA-F0-9]{32,})/;
    const module = /^ModuleNotFoundError: No module named '[A-Za-z_][A-Za-z0-9_.]{0,79}'$/;
    const counts = /^pytest: [0-9]{1,7} (?:failed|passed|skipped|errors?|deselected|xfailed|xpassed)(?:, [0-9]{1,7} (?:failed|passed|skipped|errors?|deselected|xfailed|xpassed))*$/;
    const status = /^(?:RPC (?:completed|failed|timed-out|cancelled|protocol-error)|diagnostic: (?:not-found|permission|credential|rate-limit|network|model|timeout|protocol)|AssertionError|SyntaxError|TypeError|ImportError)$/;
    const canonical = (text: string) => {
      const lines = text ? text.split("\n") : [];
      return lines.length <= 500 && lines.every(line => line === "[other output withheld]" ||
        !credential.test(line) && (module.test(line) || counts.test(line) || status.test(line)));
    };
    if (!canonical(String(row.stdout)) || !canonical(String(row.stderr))) invalid();
  } else invalid();
  return row as ExecutorOutput;
}

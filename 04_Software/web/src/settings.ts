/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { CONNECTION_KEY, CUSTOM, validConnection } from "./agentConnection.ts";
import { validCredentialNames } from "./executorSettings.ts";
import { validImplementationCollection } from "./implementationSettings.ts";
import type { MessageKey } from "./i18n";
import { validExecutionPlan, type ExecutionPlan } from "./executionPlan.ts";

/** Per-setting metadata returned by GET /projects/{name}/config. */
export type SettingMeta = {
  key: string;
  edit_key: string;
  source: "project" | "default";
  editable: boolean;
  restart: boolean;
  type?: "boolean" | "integer" | "number" | "text" | "list" | "map";
  choices?: Array<string | boolean>;
  minimum?: number | null;
  maximum?: number | null;
  /** ADORE's value when the project's file does not set the key; null when there is none. */
  default?: unknown;
};

/** How a row's value is edited in the browser; `none` means not editable here. */
export type InputKind = "boolean" | "number" | "choice" | "text" | "reviewers" | "duration" | "retry-delays" | "stage-timeouts" | "credential-names" | "connection" | "none";

type CommonKind = "text" | "positive" | "forge" | "runtime";

/** The settings most projects tune, shown first under their own labels. */
export const COMMON_SETTINGS: Array<{ key: string; label: MessageKey; kind: CommonKind }> = [
  { key: "platform.repo", label: "repository", kind: "text" },
  { key: "platform.kind", label: "forge", kind: "forge" },
  { key: "execution.backend", label: "runsIn", kind: "text" },
  { key: "container.runtime", label: "runtime", kind: "runtime" },
  { key: "container.image", label: "image", kind: "text" },
  { key: "polling.poll_interval_seconds", label: "pollInterval", kind: "positive" },
  { key: "polling.max_concurrent_runs", label: "concurrentJobs", kind: "positive" },
  { key: "budgets.max_iterations", label: "maxIterations", kind: "positive" },
  { key: "budgets.max_wall_clock_seconds", label: "maxWallClock", kind: "positive" },
  { key: "budgets.max_files_touched", label: "maxFilesTouched", kind: "positive" },
];

export type SettingRow = {
  key: string;
  group: string;
  /** Position of the row's section in the configuration, for group order. */
  groupIndex: number;
  value: unknown;
  source: "project" | "default";
  editKey: string;
  restart: boolean;
  input: InputKind;
  choices: string[];
  common: boolean;
  label?: MessageKey;
  hint?: "positive" | "runtime";
  /** ADORE's default for the setting; null when there is none. */
  defaultValue: unknown;
  /** Number input step: whole numbers for positive settings, any otherwise. */
  step?: "1" | "any";
  minimum?: number | null;
  maximum?: number | null;
  type?: SettingMeta["type"];
};

export type SettingGroup = { name: string; rows: SettingRow[] };

export const settingValue = (config: Record<string, unknown>, key: string): unknown =>
  key.split(".").reduce<unknown>((current, part) =>
    current && typeof current === "object" ? (current as Record<string, unknown>)[part] : undefined, config);

const inputKind = (item: SettingMeta): InputKind => {
  if (item.editable && item.edit_key === CONNECTION_KEY) return "connection";
  if (item.editable && item.key === "executor.env_keys") return "credential-names";
  if (item.key === "metrics.db_path") return "none";
  if (settingPurpose(item.key) === "technical" || item.key.startsWith("worktree.") && !BRANCH_NAMING_KEYS.has(item.key)) return "none";
  if (item.editable && item.key === "clarification.answer_timeout" && item.type === "text") return "duration";
  if (item.editable && item.key === "recovery.retry_backoff_seconds" && item.type === "list") return "retry-delays";
  if (item.editable && item.key === "workflow.stage_timeout_overrides" && item.type === "map") return "stage-timeouts";
  if (item.editable && item.key === "delivery.reviewers" && item.type === "list") return "reviewers";
  if (!item.editable || !["boolean", "integer", "number", "text"].includes(item.type || "")) return "none";
  if (item.choices?.length) return "choice";
  if (item.type === "boolean") return "boolean";
  if (item.type === "integer" || item.type === "number") return "number";
  return "text";
};

export const PURPOSE_GROUPS = ["repository", "tickets", "implementation", "reviews", "statistics", "executor", "technical", "environment"] as const;

/** The only worktree fields managed through reviewed browser edits. */
export const BRANCH_NAMING_KEYS = new Set(["worktree.branch_template", "worktree.branch_rule"]);

export type BranchPreview = {
  revision: string; template: string; rule: string; slug: string; iid: 1;
  run_id: "sample-run-1"; name: string | null; valid: boolean;
  rule_matches: boolean | null; issues: string[];
};

/** Closed server result; malformed evidence never enables branch candidate preparation. */
export function validBranchPreview(value: unknown): value is BranchPreview {
  if (!value || typeof value !== "object") return false;
  const item = value as BranchPreview;
  const codes = ["missing_identity", "invalid_template", "invalid_branch", "invalid_rule", "rule_mismatch", "rule_timeout", "rule_check_failed", "too_long"];
  return typeof item.revision === "string" && /^[a-f0-9]{64}$/.test(item.revision)
    && [item.template, item.rule].every(text => typeof text === "string" && text.length <= 512)
    && typeof item.slug === "string" && /^[a-z][a-z0-9-]*$/.test(item.slug)
    && item.iid === 1 && item.run_id === "sample-run-1"
    && (item.name === null || typeof item.name === "string")
    && typeof item.valid === "boolean" && [true, false, null].includes(item.rule_matches)
    && Array.isArray(item.issues) && item.issues.every(code => codes.includes(code))
    && new Set(item.issues).size === item.issues.length
    && item.valid === (item.issues.length === 0)
    && (!item.valid || typeof item.name === "string" && item.name.length > 0 && item.name.length <= 255
      && item.rule_matches === (item.rule ? true : null))
    && (item.rule_matches !== false || item.issues.includes("rule_mismatch"));
}

/** CLI-only and technical keys retained by configuration but omitted from operator controls. */
export const HIDDEN_SETTING_KEYS = new Set([
  "readiness.max_scope_hint",
  "labels.selection.type_feature", "review.trigger", "review.review_reminder_after",
  "clarification.reminder_after", "clarification.timeout_state", "metrics.capture_resource",
  "reconcile.on_ticket_closed", "reconcile.on_ticket_deleted", "reconcile.on_trigger_removed",
  "executor.mode", "polling.mode", "metrics.export_jsonl", "metrics.html_out",
]);

/** Ticket state names share one optional disclosure; ready is the pickup action. */
export const STATUS_LABEL_KEYS = new Set([
  "labels.lifecycle.answered",
  "labels.lifecycle.clarify", "labels.lifecycle.done", "labels.lifecycle.failed",
  "labels.lifecycle.review", "labels.lifecycle.working",
]);

/** Purpose ownership of catalog settings, including dynamic entries. */
export function settingPurpose(key: string): string {
  if (["agent.name", "agent.email", "delivery.target_branch", "worktree.branch_template", "worktree.branch_rule"].includes(key) || key.startsWith("platform.")) return "repository";
  if (["polling.max_concurrent_runs", "delivery.publish_checkpoints", "workflow.quick_label"].includes(key) || key.startsWith("workflow.stage_timeout_overrides") || ["budgets", "recovery", "clarification"].includes(key.split(".")[0])) return "implementation";
  if (["labels", "polling", "readiness"].includes(key.split(".")[0]) || key === "workflow.default_kind" || key.startsWith("workflow.kind_labels")) return "tickets";
  if (key.startsWith("delivery.") || key.startsWith("review.")) return "reviews";
  if (key.startsWith("metrics.")) return "statistics";
  if (key.startsWith("executor.") || CHOSEN_ENVIRONMENT_KEYS.has(key)) return "executor";
  if (key.startsWith("container.") || key.startsWith("execution.") || key.startsWith("local.")) return "environment";
  return "technical";
}

/** Environment settings administrators choose in Agent and model; the rest stays external. */
export const CHOSEN_ENVIRONMENT_KEYS = new Set(["execution.backend", "container.runtime", "container.image",
  "container.system_packages",
  "local.path"]);

/** Only known informational worktree fields accompany the external environment. */
export function settingVisible(key: string, executorOnly = false, backend = "container"): boolean {
  if (HIDDEN_SETTING_KEYS.has(key) || backend === "local" && key === "executor.command") return false;
  // Container rows for container projects, local-account rows for local ones.
  if (CHOSEN_ENVIRONMENT_KEYS.has(key)) return key === "execution.backend" || key.startsWith("local.") === (backend === "local");
  if (["container.", "execution.", "local."].some(prefix => key.startsWith(prefix))) return false;
  if (key.startsWith("worktree.") && !["worktree.repo_path", "worktree.root", "worktree.branch_template", "worktree.branch_rule"].includes(key)) return false;
  return !executorOnly || key.startsWith("executor.");
}

/** Endpoint rows matter only for an OpenAI-compatible endpoint. */
export function connectionRowVisible(key: string, provider: unknown): boolean {
  return !key.startsWith("executor.endpoint.") || provider === CUSTOM;
}

/** Optional topic disclosures inside a workflow category; ordinary rows stay direct. */
export function settingSubgroup(key: string): "clarification" | "recovery" | "stageLimits" | "statisticsFiles" | "authentication" | null {
  if (key === "executor.env_keys") return "authentication";
  if (key.startsWith("clarification.")) return "clarification";
  if (key.startsWith("recovery.")) return "recovery";
  if (key.startsWith("workflow.stage_timeout_overrides")) return "stageLimits";
  if (["metrics.db_path", "metrics.export_jsonl", "metrics.html_out"].includes(key)) return "statisticsFiles";
  return null;
}

/**
 * One row per setting the server described, in the server's key order, with
 * the value read from the effective configuration.
 */
export function settingRows(config: Record<string, unknown>, settings: SettingMeta[]): SettingRow[] {
  const sections = Object.keys(config);
  return settings.map(item => {
    const common = COMMON_SETTINGS.find(entry => entry.key === item.key);
    const value = settingValue(config, item.key);
    const group = item.key.split(".")[0];
    return {
      key: item.key,
      group,
      groupIndex: sections.indexOf(group),
      value,
      source: item.source,
      editKey: item.edit_key,
      restart: item.restart,
      input: inputKind(item),
      choices: (item.choices || []).map(String),
      common: !!common,
      label: common?.label,
      defaultValue: item.default ?? null,
      hint: common?.kind === "positive" || common?.kind === "runtime" ? common.kind : undefined,
      step: item.type === "integer" ? "1" : item.type === "number" ? "any" : undefined,
      minimum: item.minimum, maximum: item.maximum, type: item.type,
    };
  });
}

/**
 * Groups rows by delivery flow, followed by technical and executor views. With
 * `projectOnly`, only settings the project's file sets remain, and groups
 * left empty are dropped.
 */
export function settingGroups(rows: SettingRow[], projectOnly: boolean): SettingGroup[] {
  const shown = projectOnly ? rows.filter(row => row.source === "project") : rows;
  const rank = (row: SettingRow) => {
    const position = COMMON_SETTINGS.findIndex(item => item.key === row.key);
    if (BRANCH_NAMING_KEYS.has(row.key)) return COMMON_SETTINGS.length + (row.key.endsWith("template") ? 1 : 2);
    return position < 0 ? COMMON_SETTINGS.length : position;
  };
  return PURPOSE_GROUPS.map(name => ({ name, rows: shown.filter(row => settingPurpose(row.key) === name)
    .sort((left, right) => rank(left) - rank(right)) }))
    .filter(group => group.rows.length > 0);
}

/** The text an editor starts from for a setting's current value. */
export function editValue(value: unknown): string {
  return value === null || value === undefined ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
}

/** Whether a setting's ADORE default is worth showing: missing, empty text, an empty list or an empty map read as none. */
export function hasDefault(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  return typeof value !== "object" || Object.keys(value).length > 0;
}


/** Reject malformed settings transport before a browser can edit it. */
export function validSettingCatalog(settings: unknown): settings is SettingMeta[] {
  if (!Array.isArray(settings)) return false;
  const keys = new Set<string>();
  return settings.every(item => {
    if (!item || typeof item.key !== "string" || keys.has(item.key)) return false;
    keys.add(item.key);
    return typeof item.edit_key === "string" && ["project", "default"].includes(item.source)
      && typeof item.editable === "boolean" && typeof item.restart === "boolean"
      && ["boolean", "integer", "number", "text", "list", "map"].includes(item.type)
      && Array.isArray(item.choices) && item.choices.every((choice: unknown) => typeof choice === "string" || typeof choice === "boolean")
      && [item.minimum, item.maximum].every(bound => bound === null || typeof bound === "number" && Number.isFinite(bound));
  });
}

export type PendingConfig = { base_revision: string; candidate_revision: string; key: string; value: string; proposed_value: string | number | boolean | string[] | number[] | Record<string, number> | Record<string, string>; created_at: string; restart_required: boolean; execution_plan?: ExecutionPlan };

/** A malformed or unbound server candidate never enables Apply. */
export function validPendingConfig(value: unknown): value is PendingConfig | null {
  if (value === null) return true;
  if (!value || typeof value !== "object") return false;
  const item = value as PendingConfig;
  const digest = (part: unknown) => typeof part === "string" && /^[a-f0-9]{64}$/.test(part);
  const reviewerList = item.key === "delivery.reviewers" && Array.isArray(item.proposed_value)
    && item.proposed_value.every(name => typeof name === "string"
      && name.length > 0 && name.length <= 255 && !name.startsWith("-") && !/[\s\u0000-\u001f\u007f]/.test(name));
  const credentials = item.key === "executor.env_keys" && validCredentialNames(item.proposed_value);
  const collection = validImplementationCollection(item.key, item.proposed_value);
  const connection = item.key === CONNECTION_KEY && validConnection(item.proposed_value);
  const json = reviewerList || collection || credentials || connection;
  return digest(item.base_revision) && digest(item.candidate_revision)
    && typeof item.key === "string" && item.key.length > 0 && typeof item.value === "string"
    && item.value === (json ? JSON.stringify(item.proposed_value) : typeof item.proposed_value === "boolean" ? String(item.proposed_value).toLowerCase() : String(item.proposed_value))
    && (json || ![CONNECTION_KEY, "executor.env_keys", "delivery.reviewers", "recovery.retry_backoff_seconds", "workflow.stage_timeout_overrides"].includes(item.key) && ["string", "number", "boolean"].includes(typeof item.proposed_value))
    && (typeof item.proposed_value !== "number" || Number.isFinite(item.proposed_value))
    && typeof item.restart_required === "boolean"
    && (item.execution_plan === undefined || validExecutionPlan(item.execution_plan))
    && (item.key !== "execution.preparation" || !item.proposed_value || !!item.execution_plan && item.execution_plan.selection === item.proposed_value)
    && typeof item.created_at === "string" && /(?:Z|[+-]\d{2}:\d{2})$/.test(item.created_at) && Number.isFinite(Date.parse(item.created_at));
}

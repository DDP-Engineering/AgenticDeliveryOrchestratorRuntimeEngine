/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { validLocalProbe, type LocalProbe } from "./localDiagnostics.ts";
import { ApiError } from "./errors.ts";
import type { Locale } from "./i18n";

export const readinessKeys = ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli"] as const;
export type RepositoryWorkflow = "aegis" | "direct" | "not-inspected";

/** File observation only: no version approval and no readiness gate. */
export function validWorkflow(value: unknown): value is RepositoryWorkflow {
  return value === "aegis" || value === "direct" || value === "not-inspected";
}

export const workflowCopy = {
  en: { label: "Workflow", aegis: "AEGIS, stage by stage", direct: "Direct, no AEGIS found", "not-inspected": "Not inspected: the clone is not yet available" },
  fr: { label: "Workflow", aegis: "AEGIS, étape par étape", direct: "Direct, aucun AEGIS trouvé", "not-inspected": "Non inspecté : le clone n’est pas encore disponible" },
  de: { label: "Workflow", aegis: "AEGIS, Phase für Phase", direct: "Direkt, kein AEGIS gefunden", "not-inspected": "Nicht geprüft: Der Klon ist noch nicht verfügbar" },
  ro: { label: "Workflow", aegis: "AEGIS, etapă cu etapă", direct: "Direct, AEGIS nu a fost găsit", "not-inspected": "Neinspectat: clona nu este încă disponibilă" },
} satisfies Record<Locale, Record<RepositoryWorkflow | "label", string>>;
export type ReadinessKey = typeof readinessKeys[number];
/** Present exactly for a ChatGPT project: the server's ChatGPT sign-in. */
export const signInKey = "executor_sign_in";
/** Present with the internet switch: the proxy image (off) and the web search key (on). */
export const internetKeys = ["egress_proxy", "web_search_key"] as const;
export const optionalReadinessKeys: readonly string[] = [signInKey, ...internetKeys];
export type ProjectReadiness = {
  status: "failed" | "partial" | "verified" | "stale"; project_id: string; revision: string; context: "api-host"; checked_at: string;
  workflow: RepositoryWorkflow; local_probe?: LocalProbe; required_checks: string[]; auth_bound: boolean;
  checks: Record<ReadinessKey, boolean | null> & { executor_sign_in?: boolean; egress_proxy?: boolean; web_search_key?: boolean };
};

/** Whether a check set has the required keys plus, at most, the boolean optional checks. */
export function readinessChecksShape(checks: Record<string, unknown>, required: readonly string[]): boolean {
  const extra = Object.keys(checks).filter(key => !required.includes(key));
  return required.every(key => Object.hasOwn(checks, key))
    && extra.every(key => optionalReadinessKeys.includes(key))
    && Object.entries(checks).every(([key, value]) => typeof value === "boolean" || key === "container_runtime" && value === null);
}
const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

/** Shared measured domain for project, enrollment and transfer response readers. */
export function validReadinessMeasurement(value: unknown, expected: readonly string[] = readinessKeys): boolean {
  if (!object(value) || !validWorkflow(value.workflow) || typeof value.auth_bound !== "boolean"
      || !object(value.checks) || !readinessChecksShape(value.checks, expected)
      || !Array.isArray(value.required_checks) || value.required_checks.some(key => typeof key !== "string")
      || new Set(value.required_checks).size !== value.required_checks.length
      || [...value.required_checks].sort().join() !== Object.keys(value.checks).sort().join()) return false;
  return value.status === "stale" || value.status === readinessVerdict(value as ProjectReadiness);
}

/** Validate scoped host-check evidence before presenting any successful result. */
export function readReadiness(value: unknown, project: string): ProjectReadiness {
  const reject = () => { throw new ApiError("readiness_corrupt"); };
  if (!object(value) || !["failed", "partial", "verified", "stale"].includes(String(value.status)) || value.project_id !== project || value.context !== "api-host"
      || typeof value.revision !== "string" || !/^[a-f0-9]{64}$/.test(value.revision)
      || typeof value.checked_at !== "string" || !/Z$|[+]00:00$/.test(value.checked_at)
      || !Number.isFinite(Date.parse(value.checked_at)) || Date.parse(value.checked_at) > Date.now() + 60000
      || !validReadinessMeasurement(value) || !object(value.checks)
      || Object.keys(value).sort().join() !== ["status", "project_id", "revision", "context", "checked_at", "required_checks", "auth_bound", "checks", "workflow", ...("local_probe" in value ? ["local_probe"] : [])].sort().join()) return reject();
  if ("local_probe" in value && !validLocalProbe(value.local_probe, value.checks.executor_cli === true)) return reject();
  const evidence = value as ProjectReadiness;
  if (evidence.status !== "stale" && evidence.status !== readinessVerdict(evidence)) return reject();
  return evidence;
}

/** Match the backend's measured prerequisite verdict. */
export function readinessVerdict(evidence: ProjectReadiness): "failed" | "partial" | "verified" {
  return Object.values(evidence.checks).some(value => value === false) ? "failed"
    : !evidence.auth_bound || Object.values(evidence.checks).some(value => value !== true) ? "partial" : "verified";
}

/** Validate the project list before displaying any claimed verdict. */
export function validProjectVerification(value: unknown, project: string, required: unknown): boolean {
  if (!object(value) || !Array.isArray(required) || required.some(key => typeof key !== "string")
      || new Set(required).size !== required.length) return false;
  if (value.status === "unverified") return Object.keys(value).sort().join() === "checked_at,revision,status"
    && value.revision === null && value.checked_at === null;
  if (Object.keys(value).sort().join() !== "auth_bound,checked_at,checks,context,project_id,required_checks,revision,status,workflow") return false;
  try {
    const evidence = readReadiness(value, project);
    return evidence.status === "stale" || [...evidence.required_checks].sort().join() === [...required].sort().join();
  } catch { return false; }
}

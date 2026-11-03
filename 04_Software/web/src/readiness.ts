/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { validLocalProbe, type LocalProbe } from "./localDiagnostics.ts";
import { ApiError } from "./errors.ts";

export const readinessKeys = ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "aegis_files"] as const;
export type ReadinessKey = typeof readinessKeys[number];
/** Present exactly for a ChatGPT project: the server's ChatGPT sign-in. */
export const signInKey = "executor_sign_in";
/** Present with the internet switch: the proxy image (off) and the web search key (on). */
export const internetKeys = ["egress_proxy", "web_search_key"] as const;
export const optionalReadinessKeys: readonly string[] = [signInKey, ...internetKeys];
export type ProjectReadiness = {
  status: "failed" | "partial" | "verified" | "stale"; project_id: string; revision: string; context: "api-host"; checked_at: string;
  local_probe?: LocalProbe;
  checks: Record<ReadinessKey, boolean | null> & { executor_sign_in?: boolean; egress_proxy?: boolean; web_search_key?: boolean };
};

/** Whether a check set has the required keys plus, at most, the boolean optional checks. */
export function readinessChecksShape(checks: Record<string, unknown>, required: readonly string[]): boolean {
  const extra = Object.keys(checks).filter(key => !required.includes(key));
  return required.every(key => key in checks)
    && extra.every(key => optionalReadinessKeys.includes(key) && typeof checks[key] === "boolean");
}
const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

/** Validate scoped host-check evidence before presenting any successful result. */
export function readReadiness(value: unknown, project: string): ProjectReadiness {
  const reject = () => { throw new ApiError("readiness_corrupt"); };
  if (!object(value) || !["failed", "partial", "verified", "stale"].includes(String(value.status)) || value.project_id !== project || value.context !== "api-host"
      || typeof value.revision !== "string" || !/^[a-f0-9]{64}$/.test(value.revision)
      || typeof value.checked_at !== "string" || !/Z$|[+]00:00$/.test(value.checked_at)
      || !Number.isFinite(Date.parse(value.checked_at)) || Date.parse(value.checked_at) > Date.now() + 60000
      || !object(value.checks) || !readinessChecksShape(value.checks, readinessKeys)) return reject();
  for (const key of readinessKeys) {
    const result = value.checks[key];
    if (typeof result !== "boolean" && !(key === "container_runtime" && result === null)) return reject();
  }
  if ("local_probe" in value && !validLocalProbe(value.local_probe, value.checks.executor_cli === true)) return reject();
  const evidence = value as ProjectReadiness;
  if (evidence.status !== "stale" && evidence.status !== readinessVerdict(evidence)) return reject();
  return evidence;
}

/** Match the backend's measured prerequisite verdict. */
export function readinessVerdict(evidence: ProjectReadiness): "failed" | "partial" | "verified" {
  return Object.values(evidence.checks).some(value => value === false) ? "failed"
    : evidence.checks.container_runtime === null ? "partial" : "verified";
}

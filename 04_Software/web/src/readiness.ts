/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { ApiError } from "./errors.ts";

export const readinessKeys = ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "aegis_files", "model_endpoint"] as const;
export type ReadinessKey = typeof readinessKeys[number];
export type ProjectReadiness = {
  status: "failed" | "partial" | "verified" | "stale"; project_id: string; revision: string; context: "api-host"; checked_at: string;
  checks: Record<ReadinessKey, boolean | null | "not-checked">;
  model_probe: { context: "executor-container" | "executor-local"; ready: boolean; model: string; reason: string };
};
const reasons = new Set(["ready", "credential-missing", "tool-stream-incompatible", "redirect-rejected", "http-error", "endpoint-unreachable-or-incompatible", "probe-failed", "not-configured", "unsupported-executor", "invalid-endpoint", "invalid-provider-config", "invalid-credential-reference", "image-missing", "timeout", "runtime-error"]);
const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

/** Validate scoped host-check evidence before presenting any successful result. */
export function readReadiness(value: unknown, project: string): ProjectReadiness {
  const reject = () => { throw new ApiError("readiness_corrupt"); };
  if (!object(value) || !["failed", "partial", "verified", "stale"].includes(String(value.status)) || value.project_id !== project || value.context !== "api-host"
      || typeof value.revision !== "string" || !/^[a-f0-9]{64}$/.test(value.revision)
      || typeof value.checked_at !== "string" || !/Z$|[+]00:00$/.test(value.checked_at)
      || !Number.isFinite(Date.parse(value.checked_at)) || Date.parse(value.checked_at) > Date.now() + 60000
      || !object(value.checks) || Object.keys(value.checks).length !== readinessKeys.length) return reject();
  for (const key of readinessKeys) {
    const result = value.checks[key];
    if (typeof result !== "boolean" && !(key === "container_runtime" && result === null)
        && !(key === "model_endpoint" && result === "not-checked")) return reject();
  }
  const probe = value.model_probe;
  if (!object(probe) || !["executor-container", "executor-local"].includes(String(probe.context)) || typeof probe.ready !== "boolean"
      || typeof probe.model !== "string" || (probe.model !== "" && !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$/.test(probe.model))
      || typeof probe.reason !== "string" || !(reasons.has(probe.reason) || /^http-[45]\d\d$/.test(probe.reason))) return reject();
  const skipped = probe.reason === "unsupported-executor" || probe.reason === "not-configured";
  if (value.checks.model_endpoint !== (skipped ? "not-checked" : probe.ready)
      || probe.ready !== (probe.reason === "ready")) return reject();
  const evidence = value as ProjectReadiness;
  if (evidence.status !== "stale" && evidence.status !== readinessVerdict(evidence)) return reject();
  return evidence;
}

/** Match the backend's measured prerequisite verdict; skipped model checks retain a coverage note. */
export function readinessVerdict(evidence: ProjectReadiness): "failed" | "partial" | "verified" {
  return Object.values(evidence.checks).some(value => value === false) ? "failed"
    : evidence.checks.container_runtime === null ? "partial" : "verified";
}

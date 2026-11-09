/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/

export const portableFields = {
  polling: ["mode", "poll_interval_seconds", "poll_jitter_seconds", "poll_backoff", "max_concurrent_runs"],
  readiness: ["require_acceptance_criteria", "require_priority_label"],
  recovery: ["max_stage_failures", "max_transient_retries", "retry_backoff_seconds"],
  budgets: ["max_iterations", "max_wall_clock_seconds", "per_gate_timeout_seconds", "max_cost_usd", "max_files_touched"],
} as const;

export type PortablePackage = { kind: "adore-project-settings"; schema_version: 1; source: { product: "ADORE"; version: string; contract: "portable-rules-v1" }; settings: Record<string, Record<string, unknown>>; checksum: string };

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const keys = (value: unknown, names: readonly string[]): value is Record<string, unknown> => object(value) && Object.keys(value).length === names.length && names.every(name => Object.hasOwn(value, name));
const number = (value: unknown, min: number, integer = true): boolean => typeof value === "number" && Number.isFinite(value) && value >= min && value <= 1_000_000_000 && (!integer || Number.isInteger(value));

/** Validate exact server bytes before preview or download; checksum is not authentication. */
export async function parsePortableResponse(raw: string): Promise<PortablePackage> {
  const fail = () => { throw new Error("unexpected_response"); };
  if (!raw || new TextEncoder().encode(raw).length > 65536) return fail();
  let value: unknown;
  try { value = JSON.parse(raw); } catch { return fail(); }
  if (!keys(value, ["kind", "schema_version", "source", "settings", "checksum"]) || value.kind !== "adore-project-settings" || value.schema_version !== 1) return fail();
  if (!keys(value.source, ["product", "version", "contract"]) || value.source.product !== "ADORE" || value.source.contract !== "portable-rules-v1" || typeof value.source.version !== "string" || !/^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$/.test(value.source.version)) return fail();
  if (!keys(value.settings, Object.keys(portableFields)) || typeof value.checksum !== "string" || !/^[0-9a-f]{64}$/.test(value.checksum)) return fail();
  if (!raw.includes('"schema_version":1,')) return fail();
  for (const [section, fields] of Object.entries(portableFields)) {
    const settings = value.settings[section];
    if (!keys(settings, fields)) return fail();
    for (const name of fields) {
      const item = settings[name];
      if (name === "mode") {
        if (item !== "loop" && item !== "once") return fail();
      } else if (name === "poll_backoff" || section === "readiness") {
        if (typeof item !== "boolean") return fail();
      } else if (name === "retry_backoff_seconds") {
        if (!Array.isArray(item) || item.length < 1 || item.length > 100 || !item.every(seconds => number(seconds, 0))) return fail();
      } else {
        const minimum = ["max_cost_usd", "poll_jitter_seconds"].includes(name) ? 0 : 1;
        if (!number(item, minimum, name !== "max_cost_usd")) return fail();
      }
      // JavaScript folds 1.0/1e0 into integers. The server's strict integer
      // contract also requires an integer JSON token, including list entries.
      if (name === "retry_backoff_seconds") {
        if (!new RegExp(`"${name}":\\[\\d+(?:,\\d+)*\\]`).test(raw)) return fail();
      } else if (typeof item === "number" && name !== "max_cost_usd") {
        const token = raw.match(new RegExp(`"${name}":([^,}]+)`))?.[1];
        if (!token || !/^\d+$/.test(token)) return fail();
      }
    }
  }
  // This closed format has unique property names throughout. Count lexical keys,
  // including escaped spellings, so JSON.parse cannot hide a duplicate key.
  const seen = new Set<string>();
  for (const match of raw.matchAll(/("(?:[^"\\]|\\.)*")\s*:/g)) {
    const key = JSON.parse(match[1]) as string;
    if (seen.has(key)) return fail();
    seen.add(key);
  }
  const prefix = `{"checksum":"${value.checksum}",`;
  if (!raw.startsWith(prefix) || !raw.endsWith("}\n")) return fail();
  const unsigned = "{" + raw.slice(prefix.length, -1);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(unsigned));
  const checksum = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  if (checksum !== value.checksum) return fail();
  return value as PortablePackage;
}

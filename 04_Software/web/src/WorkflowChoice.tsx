/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useState } from "react";
import { ApiError, describeError } from "./errors";
import { workflowCopy } from "./workflowCopy";
import type { Locale } from "./i18n";

export type Workflow = "aegis" | "direct";
type Request = <T>(path: string, method?: string, body?: unknown, csrf?: string) => Promise<T>;

/** Validate the authorized new-job defaults and observed AEGIS presence. */
export function readWorkflowSelection(value: unknown): { default: Workflow; aegis_available: boolean } {
  const data = value as { default: Workflow; aegis_available: boolean };
  if (!data || !["aegis", "direct"].includes(data.default) || typeof data.aegis_available !== "boolean" || data.default === "aegis" && !data.aegis_available) throw new ApiError("unexpected_response");
  return data;
}

/** Shared Start/Restart choice; never submits before the operator can review the default. */
export function WorkflowChoice({ project, locale, request, value, onChange, showHelp = true }: {
  project: string; locale: Locale; request: Request; value: Workflow | null;
  onChange: (value: Workflow | null) => void;
  showHelp?: boolean;
}) {
  const copy = workflowCopy[locale];
  const [available, setAvailable] = useState<boolean | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    let active = true;
    onChange(null); setAvailable(null); setError(null);
    void request<unknown>(`/projects/${encodeURIComponent(project)}/workflow-selection`).then(readWorkflowSelection).then(data => {
      if (active) { setAvailable(data.aegis_available); onChange(data.default); }
    }).catch(cause => { if (active) setError(cause); });
    return () => { active = false; };
  }, [project, request, onChange]);
  if (error) return <p role="alert">{describeError(locale, error)}</p>;
  if (available === null) return <p role="status">{copy.loading}</p>;
  return <div className="workflow-choice"><label>{copy.label}<select aria-label={copy.label} value={value ?? ""} onChange={event => onChange(event.target.value as Workflow)}>
    <option value="aegis" disabled={!available}>{copy.aegis}</option><option value="direct">{copy.direct}</option>
  </select></label>{showHelp && <p className="field-hint">{available ? copy.help : copy.unavailable}</p>}</div>;
}

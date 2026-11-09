/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { ReactNode } from "react";
import type { MessageKey } from "./i18n";

export type DataState = "loading" | "ready" | "error";
export type ScopedState = { key: string; state: DataState };

/** Distinct request feedback, with no synthetic numeric values or operational promises. */
export function DataFeedback({ state, t }: { state: DataState; t: (key: MessageKey) => string }) {
  return <section className={`panel data-feedback data-${state}`} role={state === "error" ? "alert" : "status"}
    aria-busy={state === "loading"}><span className="feedback-icon" aria-hidden="true">{state === "error" ? "!" : "…"}</span>
    <div><h2>{t(state === "error" ? "dataFailed" : "loadingData")}</h2>
      {state === "error" && <p>{t("dataRetryHelp")}</p>}</div>
  </section>;
}

/** Successful empty project access has a role-specific next step and remains separate from errors. */
export function ProjectEmpty({ isAdmin, t, onEnroll }: { isAdmin: boolean; t: (key: MessageKey) => string; onEnroll?: () => void }) {
  return <section className="panel data-feedback" role="status"><span className="feedback-icon" aria-hidden="true">◇</span>
    <div className="project-empty-content">
      <h2>{t(isAdmin ? "noProjects" : "noProjectAccess")}</h2>
      <p>{t(isAdmin ? "noEnrolledProjectsHelp" : "noProjectAccessHelp")}</p>
      {isAdmin && onEnroll && <button className="primary" onClick={onEnroll}>{t("createProject")}</button>}
    </div>
  </section>;
}

/** Labels remain readable without color; unknown codes retain their literal evidence. */
export function StatusBadge({ code, children }: { code: string; children: ReactNode }) {
  const symbol = /failed|invalid|needs-config/.test(code) ? "!" : /approval|clarification|paused|handoff-pending/.test(code) ? "◷" : /done|configured/.test(code) ? "✓" : "◇";
  return <span className={`status status-${code}`}><span aria-hidden="true">{symbol} </span>{children}</span>;
}

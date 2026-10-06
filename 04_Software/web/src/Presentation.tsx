/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, type ReactNode } from "react";
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
export function ProjectEmpty({ isAdmin, t }: { isAdmin: boolean; t: (key: MessageKey) => string }) {
  return <section className="panel data-feedback" role="status"><span className="feedback-icon" aria-hidden="true">◇</span>
    <div><h2>{t(isAdmin ? "noProjects" : "noProjectAccess")}</h2><p>{t(isAdmin ? "noEnrolledProjectsHelp" : "noProjectAccessHelp")}</p><p className="muted">{t("accountStillAvailable")}</p></div>
  </section>;
}

/** Labels remain readable without color; unknown codes retain their literal evidence. */
export function StatusBadge({ code, children }: { code: string; children: ReactNode }) {
  const symbol = /failed|invalid|needs-config/.test(code) ? "!" : /approval|clarification|paused|handoff-pending/.test(code) ? "◷" : /done|configured/.test(code) ? "✓" : "◇";
  return <span className={`status status-${code}`}><span aria-hidden="true">{symbol} </span>{children}</span>;
}

/** Delivery concepts are available on demand in each supported language. */
export function DeliveryGlossary({ t }: { t: (key: MessageKey) => string }) {
  const disclosure = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const closeOutside = (event: PointerEvent) => {
      if (disclosure.current && !disclosure.current.contains(event.target as Node)) disclosure.current.open = false;
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, []);
  const entries: [MessageKey, MessageKey][] = [["jobTerm", "jobDefinition"], ["enrolledProjectTerm", "enrolledProjectDefinition"],
    ["paused", "pickupStoppedDefinition"], ["parkedClarificationStatus", "clarificationDefinition"],
    ["awaitingApprovalStatus", "approvalDefinition"], ["inReviewStatus", "draftReviewDefinition"]];
  return <details ref={disclosure} className="delivery-glossary" onKeyDown={event => {
    if (event.key === "Escape" && disclosure.current?.open) {
      disclosure.current.open = false; disclosure.current.querySelector("summary")?.focus(); event.stopPropagation();
    }
  }}><summary className="ghost">{t("glossary")}</summary>
    <dl>{entries.map(([term, definition]) => <div key={term}><dt>{t(term)}</dt><dd>{t(definition)}</dd></div>)}</dl>
  </details>;
}

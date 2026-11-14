/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { isHelpTopic, type HelpTopic } from "./help/topics.ts";

export type JobsView = "tickets" | "jobs" | "capacity";
export type ProjectTab = "overview" | "configuration" | "executor" | "prices" | "access" | "jobs" | "statistics" | "history";
export type MetricsTabRoute = "summary" | "usage" | "quality" | "trends" | "projects";
type PlainView = "projects" | "createProject" | "administration" | "adminUsers" | "adminAudit" | "settings";
export type ReportingRoute = { from: string; through: string; timezone: string; granularity: string };
export type Route =
  | { view: "overview"; project?: string }
  | { view: PlainView }
  | { view: "projectDetails"; project: string; tab: ProjectTab; run?: string; jobsView?: Exclude<JobsView,"tickets">; metricsTab?: MetricsTabRoute; reporting?: ReportingRoute }
  | { view: "jobs"; project?: string; run?: string; jobsView?: Exclude<JobsView,"tickets">; reporting?: ReportingRoute }
  | { view: "metrics"; project?: string; tab?: MetricsTabRoute; reporting?: ReportingRoute }
  | { view: "help"; topic?: HelpTopic };

const PLAIN: Record<string, PlainView> = {
  "/projects": "projects", "/projects/new": "createProject",
  "/admin/status": "administration", "/admin/users": "adminUsers", "/admin/audit": "adminAudit",
  "/account": "settings",
};
const PLAIN_PATHS = Object.fromEntries(Object.entries(PLAIN).map(([path, view]) => [view, path])) as Record<PlainView, string>;
const ADMIN_ONLY = new Set<string>(["createProject", "administration", "adminUsers", "adminAudit"]);
const PROJECT_TABS: ProjectTab[] = ["overview", "configuration", "executor", "prices", "access", "jobs", "statistics", "history"];
const ADMIN_PROJECT_TABS = new Set<ProjectTab>(["access"]);
/** Retired tab paths whose content now lives in Settings; links to them open Settings. */
const SETTINGS_ALIASES = new Set<ProjectTab>(["executor", "prices"]);
const METRICS_TABS: MetricsTabRoute[] = ["summary", "usage", "quality", "trends", "projects"];
/** The cross-project comparison belongs to the global Statistics page only. */
const PROJECT_METRICS_TABS: MetricsTabRoute[] = METRICS_TABS.filter(tab => tab !== "projects");
const IDENTIFIER = /^[A-Za-z0-9._-]{1,160}$/;

const identifier = (value: string | null): string | undefined =>
  value !== null && IDENTIFIER.test(value) ? value : undefined;

/** Read the view named by a location; null for an unknown or malformed path. */
export function parseRoute(pathname: string, search = ""): Route | null {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const query = new URLSearchParams(search);
  const project = identifier(query.get("project"));
  let reporting: ReportingRoute | undefined;
  if (["from", "through", "timezone", "granularity"].some(key => query.has(key))) {
    reporting = { from: query.get("from") || "", through: query.get("through") || "", timezone: query.get("timezone") || "UTC", granularity: query.get("granularity") || "day" };
    if ([reporting.from, reporting.through].some(value => value && !/^\d{4}-\d{2}-\d{2}$/.test(value)) ||
      !["day", "week", "month"].includes(reporting.granularity) || reporting.timezone.length > 64) return null;
    try { new Intl.DateTimeFormat("en", { timeZone: reporting.timezone }); } catch { return null; }
  }
  if (path === "/" || path === "") return project ? { view: "overview", project } : { view: "overview" };
  if (path === "/projects/import" || path === "/projects/clone") return { view: "projects" };
  if (path in PLAIN) return { view: PLAIN[path] };
  if (path === "/help") return { view: "help" };
  const help = /^\/help\/([^/]+)$/.exec(path);
  if (help) return isHelpTopic(help[1]) ? { view: "help", topic: help[1] } : null;
  if (path === "/jobs") {
    const run = identifier(query.get("run"));
    return { view: "jobs", ...(reporting ? { reporting } : {}), ...(project ? { project } : {}), ...(project && run ? { run } : ["jobs","capacity"].includes(query.get("view") || "") ? { jobsView: query.get("view") as Exclude<JobsView,"tickets"> } : {}) };
  }
  if (path === "/metrics") {
    const tab = query.get("tab") as MetricsTabRoute | null;
    return { view: "metrics", ...(reporting ? { reporting } : {}), ...(project ? { project } : {}), ...(tab && METRICS_TABS.includes(tab) ? { tab } : {}) };
  }
  const match = /^\/projects\/([^/]+)(?:\/([^/]+))?$/.exec(path);
  if (match) {
    let id: string;
    try { id = decodeURIComponent(match[1]); } catch { return null; }
    const tab = (match[2] ?? "overview") as ProjectTab;
    if (!IDENTIFIER.test(id) || !PROJECT_TABS.includes(tab) || match[2] === "overview") return null;
    // Only the Jobs tab carries a selected run, and only Statistics carries its sub-tab and reporting period.
    if (tab === "jobs") {
      // A selected run always shows the Jobs sub-tab; otherwise `view=jobs` selects it over Tickets.
      const run = identifier(query.get("run"));
      return { view: "projectDetails", project: id, tab, ...(run ? { run } : ["jobs","capacity"].includes(query.get("view") || "") ? { jobsView: query.get("view") as Exclude<JobsView,"tickets"> } : {}) };
    }
    if (tab === "statistics") {
      const metricsTab = query.get("tab") as MetricsTabRoute | null;
      return { view: "projectDetails", project: id, tab, ...(reporting ? { reporting } : {}), ...(metricsTab && PROJECT_METRICS_TABS.includes(metricsTab) ? { metricsTab } : {}) };
    }
    return { view: "projectDetails", project: id, tab };
  }
  return null;
}

/** Build the URL (path and query) that names a view. */
export function formatRoute(route: Route): string {
  const withQuery = (path: string, params: Record<string, string | undefined>) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) if (value) query.set(key, value);
    const text = query.toString();
    return text ? `${path}?${text}` : path;
  };
  const reportingParams = "reporting" in route && route.reporting ? {
    from: route.reporting.from, through: route.reporting.through,
    timezone: route.reporting.timezone === "UTC" ? undefined : route.reporting.timezone,
    granularity: route.reporting.granularity === "day" ? undefined : route.reporting.granularity,
  } : {};
  switch (route.view) {
    case "overview": return withQuery("/", { project: route.project });
    case "projectDetails": {
      const path = `/projects/${encodeURIComponent(route.project)}${route.tab === "overview" ? "" : `/${route.tab}`}`;
      if (route.tab === "jobs") return withQuery(path, route.run ? { run: route.run } : { view: route.jobsView });
      if (route.tab === "statistics") return withQuery(path, { tab: route.metricsTab, ...reportingParams });
      return path;
    }
    case "jobs": return withQuery("/jobs", { project: route.project, run: route.project ? route.run : undefined, view: route.project && route.run ? undefined : route.jobsView, ...reportingParams });
    case "metrics": return withQuery("/metrics", { project: route.project, tab: route.tab, ...reportingParams });
    case "help": return route.topic ? `/help/${route.topic}` : "/help";
    default: return PLAIN_PATHS[route.view];
  }
}

/** Apply role rules; `replaced` means the browser entry must be replaced, not added. */
export function normalizeRoute(route: Route | null, context: { isAdmin: boolean }): { route: Route; replaced: boolean } {
  if (route === null) return { route: { view: "overview" }, replaced: true };
  if (route.view === "projectDetails" && SETTINGS_ALIASES.has(route.tab)) return { route: { ...route, tab: "configuration" }, replaced: true };
  // The global Projects tab is gone; old links land on Summary for every role.
  if (route.view === "metrics" && route.tab === "projects") return { route: { ...route, tab: "summary" }, replaced: true };
  if (context.isAdmin) return { route, replaced: false };
  if (ADMIN_ONLY.has(route.view)) return { route: { view: "overview" }, replaced: true };
  if (route.view === "projectDetails" && ADMIN_PROJECT_TABS.has(route.tab)) return { route: { ...route, tab: "overview" }, replaced: true };
  return { route, replaced: false };
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
export type ProjectTab = "overview" | "configuration" | "prices";
export type MetricsTabRoute = "summary" | "usage" | "quality" | "trends" | "projects";
type PlainView = "projects" | "createProject" | "importProject" | "administration" | "adminUsers" | "adminAudit" | "settings";
export type Route =
  | { view: "overview"; project?: string }
  | { view: PlainView }
  | { view: "projectDetails"; project: string; tab: ProjectTab }
  | { view: "jobs"; project?: string; run?: string }
  | { view: "metrics"; project?: string; tab?: MetricsTabRoute };

const PLAIN: Record<string, PlainView> = {
  "/projects": "projects", "/projects/new": "createProject", "/projects/import": "importProject",
  "/admin/status": "administration", "/admin/users": "adminUsers", "/admin/audit": "adminAudit",
  "/account": "settings",
};
const PLAIN_PATHS = Object.fromEntries(Object.entries(PLAIN).map(([path, view]) => [view, path])) as Record<PlainView, string>;
const ADMIN_ONLY = new Set<string>(["createProject", "importProject", "administration", "adminUsers", "adminAudit"]);
const PROJECT_TABS: ProjectTab[] = ["overview", "configuration", "prices"];
const METRICS_TABS: MetricsTabRoute[] = ["summary", "usage", "quality", "trends", "projects"];
const IDENTIFIER = /^[A-Za-z0-9._-]{1,160}$/;

const identifier = (value: string | null): string | undefined =>
  value !== null && IDENTIFIER.test(value) ? value : undefined;

/** Read the view named by a location; null for an unknown or malformed path. */
export function parseRoute(pathname: string, search = ""): Route | null {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const query = new URLSearchParams(search);
  const project = identifier(query.get("project"));
  if (path === "/" || path === "") return project ? { view: "overview", project } : { view: "overview" };
  if (path in PLAIN) return { view: PLAIN[path] };
  if (path === "/jobs") {
    const run = identifier(query.get("run"));
    return { view: "jobs", ...(project ? { project } : {}), ...(project && run ? { run } : {}) };
  }
  if (path === "/metrics") {
    const tab = query.get("tab") as MetricsTabRoute | null;
    return { view: "metrics", ...(project ? { project } : {}), ...(tab && METRICS_TABS.includes(tab) ? { tab } : {}) };
  }
  const match = /^\/projects\/([^/]+)(?:\/([^/]+))?$/.exec(path);
  if (match) {
    let id: string;
    try { id = decodeURIComponent(match[1]); } catch { return null; }
    const tab = (match[2] ?? "overview") as ProjectTab;
    if (!IDENTIFIER.test(id) || !PROJECT_TABS.includes(tab) || match[2] === "overview") return null;
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
  switch (route.view) {
    case "overview": return withQuery("/", { project: route.project });
    case "projectDetails":
      return `/projects/${encodeURIComponent(route.project)}${route.tab === "overview" ? "" : `/${route.tab}`}`;
    case "jobs": return withQuery("/jobs", { project: route.project, run: route.project ? route.run : undefined });
    case "metrics": return withQuery("/metrics", { project: route.project, tab: route.tab });
    default: return PLAIN_PATHS[route.view];
  }
}

/** Apply role rules; `replaced` means the browser entry must be replaced, not added. */
export function normalizeRoute(route: Route | null, context: { isAdmin: boolean }): { route: Route; replaced: boolean } {
  if (route === null) return { route: { view: "overview" }, replaced: true };
  if (context.isAdmin) return { route, replaced: false };
  if (ADMIN_ONLY.has(route.view)) return { route: { view: "overview" }, replaced: true };
  if (route.view === "projectDetails" && route.tab === "prices") return { route: { ...route, tab: "overview" }, replaced: true };
  if (route.view === "metrics" && route.tab === "projects") return { route: { ...route, tab: "summary" }, replaced: true };
  return { route, replaced: false };
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { Children, cloneElement, isValidElement, useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactElement, type ReactNode } from "react";
import { aggregateMetrics, aggregateUsage, type Metrics, type Usage } from "./metrics";
import { messages, type Locale, type MessageKey } from "./i18n";

type User = { id: number; username: string; role: "admin" | "developer"; disabled: boolean; projects?: string[] };
type Session = { user: User; csrf: string };
type Preferences = { language: Locale | null; theme: "light" | "dark" | "system" | null };
type Project = { id: string; name: string; description: string; platform: string; repo: string; runtime: string; executor: string; readiness: string; last_activity: string | null; paused: boolean; archived: boolean; runs: number; invalid_runs: string[] };
type ImportPreview = { name: string; revision: string; issues: string[]; platform?: string; repo?: string; runtime?: string; store_root?: string; unchanged?: boolean; paused_on_import?: boolean };
type PendingConfig = { base_revision: string; candidate_revision: string; key: string; value: string; created_at: string; restart_required: boolean; endpoint?: { protocol: string; model: string; auth_env: string | null; timeout_seconds: number | null; ca_file: string | null } };
type Run = { run_id: string; ticket_iid: number; stage: string; lifecycle: string; outcome: string; stage_failures: number; review_rounds: number; mr_url: string; updated_at: string };
type RunPage = { items: Run[]; total: number; counts: Record<string, number>; limit: number; offset: number };
type Config = { config: Record<string, unknown>; revision: string; issues: string[]; local_endpoint_timeout_seconds?: number | null };
type Operation = { id: number; status: string; result?: string };
type AuditRow = { id: number; actor: string | null; action: string; project: string; detail: string; created_at: string };
type Price = { id: number; executor: string; model: string; effective_from: string; input_usd_per_million: string; output_usd_per_million: string };
type Page = "overview" | "projects" | "createProject" | "importProject" | "projectDetails" | "jobs" | "metrics" | "administration" | "adminUsers" | "adminAudit" | "settings";
type MetricsTab = "summary" | "usage" | "quality" | "trends" | "projects";
type OverviewSection = "projects" | "active" | "review" | "failed" | null;
type ProjectSortKey = "name" | "repo" | "readiness" | "runs" | "last_activity";
const metricsTabLabels: Record<MetricsTab, MessageKey> = {
  summary: "metricsTabSummary", usage: "metricsTabUsage", quality: "metricsTabQuality",
  trends: "metricsTabTrends", projects: "metricsTabProjects",
};
type WorkerStatus = "checking" | "ready" | "unavailable" | "error";
type StorageStatus = { threshold_bytes: number; low: boolean; volumes: Array<{ scope: "home" | "project"; project: string | null; free_bytes: number; total_bytes: number; low: boolean }> };
type AuditPolicy = { retention_days: number | null; max_bytes: number | null };
type ProjectReadiness = { context: string; checked_at: string; checks: Record<string, boolean | null | string>; model_probe?: { context: string; ready: boolean; model: string; reason: string } };

const commonSettings: Array<{ key: string; label: MessageKey; help: MessageKey; kind: "text" | "positive" | "forge" | "runtime" | "executor" }> = [
  { key: "platform.repo", label: "repository", help: "settingHelpRepository", kind: "text" },
  { key: "platform.kind", label: "forge", help: "settingHelpForge", kind: "forge" },
  { key: "container.runtime", label: "runtime", help: "settingHelpRuntime", kind: "runtime" },
  { key: "container.image", label: "image", help: "settingHelpImage", kind: "text" },
  { key: "executor.default", label: "executor", help: "settingHelpExecutor", kind: "executor" },
  { key: "polling.poll_interval_seconds", label: "pollInterval", help: "settingHelpPollInterval", kind: "positive" },
  { key: "polling.max_concurrent_runs", label: "concurrentJobs", help: "settingHelpConcurrent", kind: "positive" },
  { key: "budgets.max_iterations", label: "maxIterations", help: "settingHelpIterations", kind: "positive" },
  { key: "budgets.max_wall_clock_seconds", label: "maxWallClock", help: "settingHelpWallClock", kind: "positive" },
  { key: "budgets.max_files_touched", label: "maxFilesTouched", help: "settingHelpFiles", kind: "positive" },
];

const localeNames: Record<Locale, string> = { en: "English", fr: "Français", de: "Deutsch", ro: "Română" };
const initialLocale = (): Locale => {
  const saved = localStorage.getItem("adore-language") as Locale | null;
  if (saved && saved in messages) return saved;
  const browser = navigator.language.slice(0, 2) as Locale;
  return browser in messages ? browser : "en";
};

async function request<T>(path: string, method = "GET", body?: unknown, csrf?: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method, credentials: "same-origin", cache: "no-store",
    headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload?.detail?.code || payload?.detail || `HTTP ${response.status}`);
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error(`${path}: unexpected response (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const lifecycleLabels: Record<string, MessageKey> = {
  working: "working", publishing: "publishingStatus", "awaiting-approval": "awaitingApprovalStatus",
  "parked-clarification": "parkedClarificationStatus", "in-review": "inReviewStatus",
  "handoff-pending": "handoffPendingStatus", "handed-off": "handedOffStatus",
  done: "done", failed: "failed", cancelled: "cancelled",
};
const stageLabels: Record<string, MessageKey> = {
  frame: "frameStage", specify: "specifyStage", design: "designStage",
  build: "buildStage", validate: "validateStage", deliver: "deliverStage",
};
const displayCode = (value: string, labels: Record<string, MessageKey>, t: (key: MessageKey) => string) =>
  labels[value] ? t(labels[value]) : value;

export default function App() {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [theme, setTheme] = useState(localStorage.getItem("adore-theme") || "system");
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<Page>("overview");
  const [overviewSection, setOverviewSection] = useState<OverviewSection>(null);
  const [overviewRuns, setOverviewRuns] = useState<Run[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectSortKey, setProjectSortKey] = useState<ProjectSortKey>("name");
  const [projectSortDescending, setProjectSortDescending] = useState(false);
  const [selected, setSelected] = useState("");
  const [runs, setRuns] = useState<Run[]>([]);
  const [runCounts, setRunCounts] = useState<Record<string, number>>({});
  const [jobPage, setJobPage] = useState<RunPage>({ items: [], total: 0, counts: {}, limit: 25, offset: 0 });
  const [jobOffset, setJobOffset] = useState(0);
  const [jobPageSize, setJobPageSize] = useState<10 | 25 | 50 | "all">(10);
  const [jobLifecycle, setJobLifecycle] = useState("");
  const [jobStage, setJobStage] = useState("");
  const [jobExecutor, setJobExecutor] = useState("");
  const [jobUpdatedFrom, setJobUpdatedFrom] = useState("");
  const [jobUpdatedTo, setJobUpdatedTo] = useState("");
  const [jobOutcome, setJobOutcome] = useState("");
  const [selectedMetrics, setMetrics] = useState<Metrics | null>(null);
  const [allMetrics, setAllMetrics] = useState<Record<string, Metrics> | null>(null);
  const [metricFrom, setMetricFrom] = useState("");
  const [metricTo, setMetricTo] = useState("");
  const [metricTimezone, setMetricTimezone] = useState("UTC");
  const [metricGranularity, setMetricGranularity] = useState<"day" | "week" | "month">("day");
  const [metricAllProjects, setMetricAllProjects] = useState(true);
  const [metricsScope, setMetricsScope] = useState("");
  const [metricsTab, setMetricsTab] = useState<MetricsTab>("summary");
  const [usageExecutor, setUsageExecutor] = useState("");
  const [usageModel, setUsageModel] = useState("");
  const [selectedUsage, setUsage] = useState<Usage | null>(null);
  const [usageScope, setUsageScope] = useState("");
  const [allUsage, setAllUsage] = useState<Record<string, Usage> | null>(null);
  const [usageRefresh, setUsageRefresh] = useState(0);
  const [config, setConfig] = useState<Config | null>(null);
  const [configScope, setConfigScope] = useState("");
  const [pendingConfig, setPendingConfig] = useState<PendingConfig | null>(null);
  const [pendingConfigScope, setPendingConfigScope] = useState("");
  const [prices, setPrices] = useState<Price[]>([]);
  const [pricesScope, setPricesScope] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);
  const [auditPolicy, setAuditPolicy] = useState<AuditPolicy | null>(null);
  const [adminMenuOpen, setAdminMenuOpen] = useState(true);
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus>("checking");
  const [storageStatus, setStorageStatus] = useState<StorageStatus | null>(null);
  const [storageError, setStorageError] = useState(false);
  const [projectReadiness, setProjectReadiness] = useState<ProjectReadiness | null>(null);
  const [details, setDetails] = useState<{ run: Run; events: Array<Record<string, unknown>> } | null>(null);
  const [about, setAbout] = useState<{ name: string; version: string; license: string; license_text: string; third_party_notices: string } | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [ticket, setTicket] = useState("");
  const [operation, setOperation] = useState<Operation | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [projectExecutor, setProjectExecutor] = useState("opencode");
  const [importName, setImportName] = useState("");
  const [importDescription, setImportDescription] = useState("");
  const [importText, setImportText] = useState("");
  const [importFileName, setImportFileName] = useState("");
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [resetTarget, setResetTarget] = useState<number | null>(null);
  const aboutTrigger = useRef<HTMLButtonElement>(null);
  const aboutClose = useRef<HTMLButtonElement>(null);
  const jobRequest = useRef(0);
  const selectedMetricsRequest = useRef(0);
  const globalMetricsRequest = useRef(0);
  const usageRequest = useRef(0);
  const configRequest = useRef(0);
  const readinessRequest = useRef(0);
  const preferenceRequest = useRef({ language: 0, theme: 0 });
  const importFileRead = useRef(0);
  const importPreviewRequest = useRef(0);
  const viewGeneration = useRef(0);

  const closeAbout = () => {
    setAbout(null);
    window.requestAnimationFrame(() => aboutTrigger.current?.focus());
  };

  const t = (key: MessageKey) => messages[locale][key];
  const applyPreferences = (saved: Preferences) => {
    if (saved.language) setLocale(saved.language);
    if (saved.theme) setTheme(saved.theme);
  };
  const isAdmin = session?.user.role === "admin";
  const metricsTabs: MetricsTab[] = isAdmin ? ["summary", "usage", "quality", "trends", "projects"] : ["summary", "usage", "quality", "trends"];
  const onMetricsTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, tab: MetricsTab) => {
    const current = metricsTabs.indexOf(tab);
    const next = event.key === "ArrowRight" ? (current + 1) % metricsTabs.length :
      event.key === "ArrowLeft" ? (current + metricsTabs.length - 1) % metricsTabs.length :
      event.key === "Home" ? 0 : event.key === "End" ? metricsTabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault();
    setMetricsTab(metricsTabs[next]);
    document.getElementById(`metrics-tab-${metricsTabs[next]}`)?.focus();
  };
  const projectStatusLabel = (item: Project) => t(item.readiness === "configured" ? "configured" : item.readiness === "needs-config" ? "needsConfig" : item.readiness === "invalid-state" ? "invalidState" : item.readiness === "archived" ? "archived" : "paused");
  const sortedProjects = [...projects].sort((left, right) => {
    const a = projectSortKey === "readiness" ? projectStatusLabel(left) : left[projectSortKey];
    const b = projectSortKey === "readiness" ? projectStatusLabel(right) : right[projectSortKey];
    if (a === null || a === "") return b === null || b === "" ? left.name.localeCompare(right.name, locale) : 1;
    if (b === null || b === "") return -1;
    const comparison = typeof a === "number" && typeof b === "number" ? a - b :
      String(a).localeCompare(String(b), locale, { numeric: true, sensitivity: "base" });
    return (projectSortDescending ? -comparison : comparison) || left.name.localeCompare(right.name, locale);
  });
  const changeProjectSort = (key: ProjectSortKey) => {
    if (key === projectSortKey) setProjectSortDescending(value => !value);
    else { setProjectSortKey(key); setProjectSortDescending(false); }
  };
  const selectedProject = projects.find(item => item.id === selected);
  const projectConfig = configScope === selected ? config : null;
  const projectPendingConfig = pendingConfigScope === selected ? pendingConfig : null;
  const projectPrices = pricesScope === selected ? prices : [];
  const modelReason = (reason: string): string => {
    const keys: Record<string, MessageKey> = {
      ready: "checkPassed", "not-configured": "modelNotConfigured",
      "unsupported-executor": "modelUnsupported", "invalid-endpoint": "modelInvalidConfig",
      "invalid-provider-config": "modelInvalidConfig",
      "invalid-credential-reference": "modelInvalidConfig",
      "image-missing": "modelImageMissing", "credential-missing": "modelCredentialMissing",
      "tool-stream-incompatible": "modelIncompatible",
      "endpoint-unreachable-or-incompatible": "modelUnreachable",
      "redirect-rejected": "modelRedirectRejected", timeout: "modelRuntimeError",
      "runtime-error": "modelRuntimeError", "probe-failed": "modelRuntimeError",
    };
    return reason.startsWith("http-") ? reason.toUpperCase() : t(keys[reason] || "modelRuntimeError");
  };
  const metricParams = new URLSearchParams();
  if (metricFrom) metricParams.set("day_from", metricFrom);
  if (metricTo) metricParams.set("day_to", metricTo);
  metricParams.set("timezone", metricTimezone);
  metricParams.set("granularity", metricGranularity);
  const metricSuffix = metricParams.toString() ? `?${metricParams}` : "";
  const trendTitle = t(metricGranularity === "day" ? "dailyTrends" : metricGranularity === "week" ? "weeklyTrends" : "monthlyTrends");
  const usageParams = new URLSearchParams(metricParams);
  if (usageExecutor.trim()) usageParams.set("executor", usageExecutor.trim());
  if (usageModel.trim()) usageParams.set("model", usageModel.trim());
  const usageSuffix = usageParams.toString() ? `?${usageParams}` : "";
  const allProjectScope = isAdmin && metricAllProjects;
  const scopeLabel = allProjectScope ? t("metricsAllProjects") : selectedProject?.name || "";
  const scopeProjects = allProjectScope ? projects : projects.filter(project => project.id === selected);
  const globalRows = allProjectScope ? Object.entries(allMetrics || {}) :
    selectedMetrics && metricsScope === selected && selectedProject ? [[selectedProject.name, selectedMetrics] as [string, Metrics]] : [];
  const metrics = allProjectScope ? (allMetrics ? aggregateMetrics(Object.values(allMetrics), metricTimezone, metricFrom, metricTo) : null) :
    metricsScope === selected ? selectedMetrics : null;
  const usage = allProjectScope ? (allUsage ? aggregateUsage(Object.values(allUsage)) : null) : usageScope === selected ? selectedUsage : null;
  const scopedUsageRows = allProjectScope ? Object.entries(allUsage || {}) : selectedUsage && selectedProject ? [[selectedProject.name, selectedUsage] as [string, Usage]] : [];
  const globalTokensIn = globalRows.reduce((sum, [, item]) => sum + (item.totals.tokens_in || 0), 0);
  const globalTokensOut = globalRows.reduce((sum, [, item]) => sum + (item.totals.tokens_out || 0), 0);
  const globalReportedCost = globalRows.reduce((sum, [, item]) => sum + (item.totals.cost_usd || 0), 0);
  const globalReviewRounds = globalRows.reduce((sum, [, item]) => sum + item.runs.reduce((runSum, run) => runSum + Number(run.review_rounds || 0), 0), 0);
  const repositoryRows = Object.entries(scopeProjects.reduce<Record<string, {
    projects: number; jobs: number; tokensIn: number; tokensOut: number; mrRevisions: number; pipelineRepairs: number;
    reported: number; estimated: number; hasReported: boolean; hasEstimated: boolean;
  }>>((acc, project) => {
    if (!project.repo.trim()) return acc;
    const row = acc[project.repo] || (acc[project.repo] = {
      projects: 0, jobs: 0, tokensIn: 0, tokensOut: 0, mrRevisions: 0, pipelineRepairs: 0,
      reported: 0, estimated: 0, hasReported: false, hasEstimated: false,
    });
    const item = globalRows.find(([name]) => name === project.name)?.[1];
    row.projects += 1;
    row.jobs += project.runs;
    row.tokensIn += item?.totals.tokens_in || 0;
    row.tokensOut += item?.totals.tokens_out || 0;
    row.mrRevisions += item?.totals.mr_revisions || 0;
    row.pipelineRepairs += item?.totals.pipeline_repairs || 0;
    if (item?.totals.cost_usd != null) {
      row.reported += item.totals.cost_usd;
      row.hasReported = true;
    }
    if (item?.totals.estimated_cost_usd != null) {
      row.estimated += item.totals.estimated_cost_usd;
      row.hasEstimated = true;
    }
    return acc;
  }, {})).sort(([a], [b]) => a.localeCompare(b));
  const formatNumber = (value: number) => new Intl.NumberFormat(locale).format(value || 0);
  const formatPercent = (value: number | null | undefined) => value == null ? "—" : new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 1 }).format(value);
  const formatMoney = (value: number | null | undefined) => value == null ? "—" : new Intl.NumberFormat(locale, { style: "currency", currency: "USD" }).format(value);
  const formatDate = (value: string) => value ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";

  useEffect(() => {
    document.documentElement.lang = locale;
    localStorage.setItem("adore-language", locale);
  }, [locale]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("adore-theme", theme);
  }, [theme]);

  useEffect(() => {
    request<Session>("/me").then(async current => {
      try { applyPreferences(await request<Preferences>("/me/preferences")); }
      catch (cause) { setError((cause as Error).message); }
      setSession(current);
    }).catch(() => setSession(null)).finally(() => setLoading(false));
  }, []);

  const updatePreference = (key: "language" | "theme", value: string) => {
    const previous = key === "language" ? locale : theme;
    if (key === "language") setLocale(value as Locale);
    else setTheme(value);
    if (!session) return;
    const generation = viewGeneration.current;
    const revision = ++preferenceRequest.current[key];
    void request<Preferences>("/me/preferences", "PATCH", { [key]: value }, session.csrf)
      .catch(cause => {
        if (generation !== viewGeneration.current || revision !== preferenceRequest.current[key]) return;
        if (key === "language") setLocale(previous as Locale);
        else setTheme(previous);
        setError((cause as Error).message);
      });
  };

  const refreshProjects = useCallback(async () => {
    const generation = viewGeneration.current;
    const items = await request<Project[]>("/projects");
    if (generation !== viewGeneration.current) return;
    setProjects(items);
    setSelected(current => items.some(item => item.id === current) ? current : (items[0]?.id || ""));
    setLastRefresh(new Date());
  }, []);

  useEffect(() => {
    if (!session) return;
    refreshProjects().catch(cause => setError(String(cause.message)));
    const timer = window.setInterval(() => refreshProjects().catch(() => {}), 15000);
    return () => window.clearInterval(timer);
  }, [session, refreshProjects]);

  useEffect(() => { setMetrics(null); setAllMetrics(null); }, [metricSuffix]);

  useEffect(() => { setUsage(null); setAllUsage(null); }, [usageSuffix, selected]);

  useEffect(() => { readinessRequest.current += 1; setProjectReadiness(null); }, [selected, session?.user.id]);

  useEffect(() => {
    if (!session || !selected || page !== "metrics") return;
    const revision = ++usageRequest.current;
    const generation = viewGeneration.current;
    const refresh = async () => {
      try {
        const scoped = await request<Usage>(`/projects/${encodeURIComponent(selected)}/usage${usageSuffix}`);
        if (generation === viewGeneration.current && revision === usageRequest.current) { setUsage(scoped); setUsageScope(selected); }
        if (isAdmin) {
          const global = await request<Record<string, Usage>>(`/usage${usageSuffix}`);
          if (generation === viewGeneration.current && revision === usageRequest.current) setAllUsage(global);
        }
      } catch (cause) {
        if (generation === viewGeneration.current && revision === usageRequest.current) setError((cause as Error).message);
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30000);
    return () => { usageRequest.current += 1; window.clearInterval(timer); };
  }, [session, selected, page, usageSuffix, isAdmin, usageRefresh]);

  const refreshSelected = useCallback(async () => {
    const revision = ++selectedMetricsRequest.current;
    if (!selected || !session) { setRuns([]); setRunCounts({}); setMetrics(null); return; }
    const generation = viewGeneration.current;
    try {
      const [runData, metricData] = await Promise.all([
        request<RunPage>(`/projects/${encodeURIComponent(selected)}/runs-page?limit=7`),
        request<Metrics>(`/projects/${encodeURIComponent(selected)}/metrics${metricSuffix}`),
      ]);
      if (generation !== viewGeneration.current || revision !== selectedMetricsRequest.current) return;
      setRuns(runData.items);
      setRunCounts(runData.counts);
      setMetrics(metricData); setMetricsScope(selected);
      setLastRefresh(new Date());
    } catch (cause) {
      if (generation === viewGeneration.current && revision === selectedMetricsRequest.current) setError((cause as Error).message);
    }
  }, [selected, session, metricSuffix]);

  useEffect(() => {
    void refreshSelected();
    const timer = window.setInterval(() => void refreshSelected(), 15000);
    return () => window.clearInterval(timer);
  }, [refreshSelected]);

  useEffect(() => {
    if (page !== "overview" || !selected || !session || !overviewSection || overviewSection === "projects") {
      setOverviewRuns([]);
      return;
    }
    const generation = viewGeneration.current;
    let active = true;
    setOverviewRuns([]);
    const refresh = async () => {
      try {
        const result = await request<RunPage>(`/projects/${encodeURIComponent(selected)}/runs-page?limit=all`);
        if (active && generation === viewGeneration.current) setOverviewRuns(result.items);
      } catch (cause) {
        if (active && generation === viewGeneration.current) setError((cause as Error).message);
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, [page, selected, session, overviewSection]);

  const refreshJobPage = useCallback(async () => {
    if (!selected || !session || page !== "jobs") return;
    const revision = ++jobRequest.current;
    const generation = viewGeneration.current;
    const query = new URLSearchParams({ limit: String(jobPageSize), offset: String(jobOffset) });
    if (jobLifecycle) query.set("lifecycle", jobLifecycle);
    if (jobStage) query.set("stage", jobStage);
    if (jobExecutor.trim()) query.set("executor", jobExecutor.trim());
    if (jobUpdatedFrom) query.set("updated_from", jobUpdatedFrom);
    if (jobUpdatedTo) query.set("updated_to", jobUpdatedTo);
    if (jobOutcome.trim()) query.set("outcome", jobOutcome.trim());
    try {
      const result = await request<RunPage>(`/projects/${encodeURIComponent(selected)}/runs-page?${query}`);
      if (revision === jobRequest.current && generation === viewGeneration.current) setJobPage(result);
    } catch (cause) {
      if (revision === jobRequest.current && generation === viewGeneration.current) setError((cause as Error).message);
    }
  }, [selected, session, page, jobOffset, jobPageSize, jobLifecycle, jobStage, jobExecutor, jobUpdatedFrom, jobUpdatedTo, jobOutcome]);

  useEffect(() => { setJobOffset(0); }, [selected, jobPageSize, jobLifecycle, jobStage, jobExecutor, jobUpdatedFrom, jobUpdatedTo, jobOutcome]);

  useEffect(() => {
    void refreshJobPage();
    if (page !== "jobs") return;
    const timer = window.setInterval(() => void refreshJobPage(), 15000);
    return () => window.clearInterval(timer);
  }, [page, refreshJobPage]);

  useEffect(() => {
    if (page === "adminUsers" && isAdmin) {
      const generation = viewGeneration.current;
      request<User[]>("/users").then(value => { if (generation === viewGeneration.current) setUsers(value); }).catch(cause => setError(cause.message));
    }
    if (page === "adminAudit" && isAdmin) {
      const generation = viewGeneration.current;
      request<AuditRow[]>("/audit?limit=all").then(value => { if (generation === viewGeneration.current) setAuditRows(value); }).catch(cause => setError(cause.message));
      request<AuditPolicy>("/audit-policy").then(value => { if (generation === viewGeneration.current) setAuditPolicy(value); }).catch(cause => setError(cause.message));
    }
    if (page === "projectDetails" && selected) {
      const generation = viewGeneration.current;
      const revision = ++configRequest.current;
      setConfig(null); setConfigScope(""); setPendingConfig(null); setPendingConfigScope(""); setPrices([]); setPricesScope("");
      request<Config>(`/projects/${encodeURIComponent(selected)}/config`).then(value => { if (generation === viewGeneration.current && revision === configRequest.current) { setConfig(value); setConfigScope(selected); } }).catch(cause => { if (generation === viewGeneration.current && revision === configRequest.current) setError(cause.message); });
      if (isAdmin) {
        request<PendingConfig | null>(`/projects/${encodeURIComponent(selected)}/config/pending`).then(value => { if (generation === viewGeneration.current && revision === configRequest.current) { setPendingConfig(value); setPendingConfigScope(selected); } }).catch(cause => { if (generation === viewGeneration.current && revision === configRequest.current) setError(cause.message); });
        request<Price[]>(`/projects/${encodeURIComponent(selected)}/prices`).then(value => { if (generation === viewGeneration.current && revision === configRequest.current) { setPrices(value); setPricesScope(selected); } }).catch(cause => { if (generation === viewGeneration.current && revision === configRequest.current) setError(cause.message); });
      }
    }
  }, [page, isAdmin, selected]);

  useEffect(() => {
    if (page !== "administration" || !isAdmin) return;
    let active = true;
    const check = async () => {
      try {
        const response = await fetch("/api/v1/ready", { cache: "no-store" });
        const code = response.ok ? "" : (await response.json().catch(() => ({})))?.detail?.code;
        if (active) setWorkerStatus(response.ok ? "ready" : code === "worker_unavailable" ? "unavailable" : "error");
      } catch {
        if (active) setWorkerStatus("error");
      }
    };
    setWorkerStatus("checking");
    void check();
    const timer = window.setInterval(() => void check(), 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, [page, isAdmin]);

  useEffect(() => {
    if (page !== "administration" || !isAdmin) return;
    let active = true;
    const check = async () => {
      try {
        const value = await request<StorageStatus>("/system/storage");
        if (active) { setStorageStatus(value); setStorageError(false); }
      } catch {
        if (active) { setStorageStatus(null); setStorageError(true); }
      }
    };
    setStorageStatus(null); setStorageError(false);
    void check();
    const timer = window.setInterval(() => void check(), 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, [page, isAdmin]);

  useEffect(() => {
    if (page !== "metrics" || !isAdmin) return;
    const refresh = () => {
      const revision = ++globalMetricsRequest.current;
      const generation = viewGeneration.current;
      return request<Record<string, Metrics>>(`/metrics${metricSuffix}`).then(value => {
        if (generation === viewGeneration.current && revision === globalMetricsRequest.current) setAllMetrics(value);
      }).catch(cause => { if (generation === viewGeneration.current && revision === globalMetricsRequest.current) setError(cause.message); });
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30000);
    return () => window.clearInterval(timer);
  }, [page, isAdmin, metricSuffix, usageRefresh]);

  useEffect(() => {
    if (!operation || !["pending", "running"].includes(operation.status)) return;
    const timer = window.setInterval(async () => {
      const generation = viewGeneration.current;
      try {
        const current = await request<Operation>(`/operations/${operation.id}`);
        if (generation !== viewGeneration.current) return;
        setOperation(current);
        if (!["pending", "running"].includes(current.status)) {
          await refreshSelected();
          await refreshProjects();
          await refreshJobPage();
        }
      } catch (cause) {
        if (generation === viewGeneration.current) setError((cause as Error).message);
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [operation?.id, operation?.status, refreshSelected, refreshProjects, refreshJobPage]);

  const clearImportDraft = () => {
    importFileRead.current += 1;
    importPreviewRequest.current += 1;
    setImportName(""); setImportDescription(""); setImportText("");
    setImportFileName(""); setImportPreview(null);
  };

  useEffect(() => {
    if (page !== "importProject") clearImportDraft();
  }, [page]);

  const clearPrivateView = () => {
    viewGeneration.current += 1;
    setPage("overview"); setMenuOpen(false);
    jobRequest.current += 1;
    selectedMetricsRequest.current += 1;
    globalMetricsRequest.current += 1;
    usageRequest.current += 1;
    configRequest.current += 1;
    preferenceRequest.current.language += 1;
    preferenceRequest.current.theme += 1;
    setProjects([]); setSelected(""); setRuns([]); setRunCounts({});
    setProjectSortKey("name"); setProjectSortDescending(false);
    setJobPage({ items: [], total: 0, counts: {}, limit: 25, offset: 0 });
    setJobOffset(0); setJobLifecycle(""); setJobStage("");
    setJobUpdatedFrom(""); setJobUpdatedTo(""); setJobOutcome("");
    setMetrics(null); setAllMetrics(null); setMetricFrom(""); setMetricTo("");
    setMetricAllProjects(true); setMetricsScope(""); setMetricTimezone("UTC"); setMetricGranularity("day"); setMetricsTab("summary");
    setUsage(null); setUsageScope(""); setAllUsage(null); setUsageExecutor(""); setUsageModel("");
    setConfig(null); setPendingConfig(null); setPrices([]);
    setUsers([]); setAuditRows([]); setAuditPolicy(null); setDetails(null); setOperation(null);
    clearImportDraft();
    setWorkerStatus("checking");
    setNotice(""); setLastRefresh(null);
  };

  const signIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const fields = new FormData(event.currentTarget);
    try {
      const authenticated = await request<Session>("/session", "POST", Object.fromEntries(fields));
      let saved: Preferences | null = null;
      try { saved = await request<Preferences>("/me/preferences"); }
      catch (cause) { setError((cause as Error).message); }
      clearPrivateView();
      if (saved) applyPreferences(saved);
      setSession(authenticated);
    }
    catch (cause) { setError((cause as Error).message); }
  };

  const signOut = async () => {
    try { await request("/session", "DELETE", undefined, session?.csrf); }
    finally { setSession(null); clearPrivateView(); }
  };

  const operate = async (action: "start" | "retry" | "cancel" | "pause" | "resume", target = "", projectId = selected) => {
    if (!session || !projectId) return;
    setError(""); setNotice("");
    const body = action === "start" ? { ticket_iid: Number(target) } :
      action === "retry" || action === "cancel" ? { run_id: target } : {};
    try {
      const op = await request<{ id: number; status: string }>(
        `/projects/${encodeURIComponent(projectId)}/operations/${action}`, "POST",
        { ...body, idempotency_key: crypto.randomUUID() }, session.csrf,
      );
      setOperation(op);
      setNotice(`${t("operationQueued")} · #${op.id}`);
      setTicket("");
      await refreshSelected();
    } catch (cause) { setError((cause as Error).message); }
  };

  const openRun = async (runId: string) => {
    const generation = viewGeneration.current;
    try {
      const result = await request<{ run: Run; events: Array<Record<string, unknown>> }>(
        `/projects/${encodeURIComponent(selected)}/runs/${encodeURIComponent(runId)}`,
      );
      if (generation === viewGeneration.current) setDetails(result);
    } catch (cause) {
      if (generation === viewGeneration.current) setError((cause as Error).message);
    }
  };

  const createProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const created = await request<Project>("/projects", "POST", Object.fromEntries(new FormData(event.currentTarget)), session?.csrf);
      await refreshProjects(); setSelected(created.id); setPage("projectDetails");
    } catch (cause) { setError((cause as Error).message); }
  };

  const previewProjectImport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(""); setImportPreview(null);
    const generation = viewGeneration.current;
    const currentRequest = ++importPreviewRequest.current;
    try {
      const preview = await request<ImportPreview>("/projects/import-preview", "POST",
        { name: importName, description: importDescription, config_text: importText }, session?.csrf);
      if (generation === viewGeneration.current && currentRequest === importPreviewRequest.current) setImportPreview(preview);
    } catch (cause) { if (generation === viewGeneration.current && currentRequest === importPreviewRequest.current) setError((cause as Error).message); }
  };

  const importProject = async () => {
    if (!importPreview || importPreview.issues.length) return;
    setError("");
    const generation = viewGeneration.current;
    try {
      const created = await request<Project>("/projects/import", "POST", {
        name: importName, description: importDescription, config_text: importText,
        revision: importPreview.revision,
      }, session?.csrf);
      if (generation !== viewGeneration.current) return;
      clearImportDraft();
      await refreshProjects(); setSelected(created.id); setPage("projectDetails");
      setNotice(t("projectImported"));
    } catch (cause) { if (generation === viewGeneration.current) setError((cause as Error).message); }
  };

  const setProjectArchive = async (archive: boolean, projectId = selected) => {
    if (!projectId || !session || !isAdmin) return;
    setError(""); setNotice("");
    try {
      await request(`/projects/${encodeURIComponent(projectId)}/${archive ? "archive" : "restore"}`,
        "POST", undefined, session.csrf);
      await refreshProjects();
      setNotice(t(archive ? "projectArchived" : "projectRestored"));
    } catch (cause) { setError((cause as Error).message); }
  };

  const createUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    try {
      await request("/users", "POST", Object.fromEntries(new FormData(form)), session?.csrf);
      setUsers(await request<User[]>("/users")); form.reset();
    } catch (cause) { setError((cause as Error).message); }
  };

  const saveAuditPolicy = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const days = String(values.get("retention_days") || "").trim();
    const mebibytes = String(values.get("max_mib") || "").trim();
    try {
      const policy = await request<AuditPolicy>("/audit-policy", "PUT", {
        retention_days: days ? Number(days) : null,
        max_bytes: mebibytes ? Number(mebibytes) * 1024 * 1024 : null,
      }, session?.csrf);
      setAuditPolicy(policy);
      setAuditRows(await request<AuditRow[]>("/audit?limit=all"));
      setNotice(t("auditPolicySaved"));
    } catch (cause) { setError((cause as Error).message); }
  };

  const assignProjects = async (event: FormEvent<HTMLFormElement>, userId: number) => {
    event.preventDefault();
    try {
      const projects = new FormData(event.currentTarget).getAll("projects").map(String);
      await request(`/users/${userId}/projects`, "PUT", { projects }, session?.csrf);
      setUsers(await request<User[]>("/users")); setNotice(t("assign"));
    } catch (cause) { setError((cause as Error).message); }
  };

  const setAccountEnabled = async (userId: number, enabled: boolean) => {
    try {
      await request(`/users/${userId}/${enabled ? "enable" : "disable"}`, "POST", {}, session?.csrf);
      setUsers(await request<User[]>("/users"));
    } catch (cause) { setError((cause as Error).message); }
  };

  const resetUserPassword = async (event: FormEvent<HTMLFormElement>, userId: number) => {
    event.preventDefault();
    const form = event.currentTarget;
    const replacement = String(new FormData(form).get("replacement") || "");
    try {
      await request(`/users/${userId}/reset-password`, "POST", { replacement }, session?.csrf);
      form.reset(); setResetTarget(null); setNotice(t("passwordResetDone"));
    } catch (cause) { setError((cause as Error).message); }
  };

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await request("/me/password", "POST", Object.fromEntries(new FormData(event.currentTarget)), session?.csrf);
      setNotice(t("changePassword")); setSession(null);
    } catch (cause) { setError((cause as Error).message); }
  };

  const editConfig = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config || !selected) return;
    const form = event.currentTarget;
    const fields = Object.fromEntries(new FormData(form));
    try {
      const staged = await request<PendingConfig>(`/projects/${encodeURIComponent(selected)}/config/pending`, "POST", { ...fields, revision: config.revision }, session?.csrf);
      setPendingConfig(staged); setPendingConfigScope(selected); setNotice(t("changeStaged")); form.reset();
    } catch (cause) { setError((cause as Error).message); }
  };

  const rebuildUsage = async () => {
    try {
      const result = await request<{ projects: number; runs: number; usage_events: number }>(
        "/usage/rebuild", "POST", {}, session?.csrf);
      setNotice(`${t("usageRebuilt")}: ${formatNumber(result.usage_events)}`);
      setUsageRefresh(current => current + 1);
    } catch (cause) { setError((cause as Error).message); }
  };

  const saveEndpoint = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config || !selected) return;
    const fields = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const staged = await request<PendingConfig>(`/projects/${encodeURIComponent(selected)}/config/pending`, "POST", {
        key: "container.runtime_env.OPENAI_BASE_URL", value: fields.endpoint,
        model: fields.model, auth_env: fields.auth_env || undefined,
        protocol: fields.protocol, timeout_seconds: Number(fields.timeout_seconds),
        ca_file: fields.ca_file,
        revision: config.revision,
      }, session?.csrf);
      setPendingConfig(staged); setPendingConfigScope(selected); setNotice(t("changeStaged"));
    } catch (cause) { setError((cause as Error).message); }
  };

  const applyPendingConfig = async () => {
    if (!selected || !pendingConfig) return;
    try {
      await request(`/projects/${encodeURIComponent(selected)}/config/apply`, "POST", {
        candidate_revision: pendingConfig.candidate_revision,
      }, session?.csrf);
      setConfig(await request<Config>(`/projects/${encodeURIComponent(selected)}/config`)); setConfigScope(selected);
      setPendingConfig(null); setNotice(t("changeApplied"));
      await refreshProjects();
    } catch (cause) { setError((cause as Error).message); }
  };

  const discardPendingConfig = async () => {
    if (!selected || !pendingConfig) return;
    try {
      await request(`/projects/${encodeURIComponent(selected)}/config/pending`, "DELETE", undefined, session?.csrf);
      setPendingConfig(null); setNotice(t("changeDiscarded"));
    } catch (cause) { setError((cause as Error).message); }
  };

  const checkProjectReadiness = async () => {
    if (!selected || !isAdmin) return;
    const revision = ++readinessRequest.current;
    const generation = viewGeneration.current;
    setProjectReadiness(null);
    try {
      const result = await request<ProjectReadiness>(`/projects/${encodeURIComponent(selected)}/readiness-check`, "POST", {}, session?.csrf);
      if (generation === viewGeneration.current && revision === readinessRequest.current) setProjectReadiness(result);
    } catch (cause) {
      if (generation === viewGeneration.current && revision === readinessRequest.current) setError((cause as Error).message);
    }
  };

  const savePrice = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    const form = event.currentTarget;
    try {
      await request(`/projects/${encodeURIComponent(selected)}/prices`, "POST",
        Object.fromEntries(new FormData(form)), session?.csrf);
      setPrices(await request<Price[]>(`/projects/${encodeURIComponent(selected)}/prices`)); setPricesScope(selected);
      setNotice(t("priceSaved")); form.reset();
    } catch (cause) { setError((cause as Error).message); }
  };

  if (loading) return <main className="splash" aria-busy="true">ADORE</main>;

  if (!session) return <main className="login-page">
    <section className="login-card">
      <div className="brand-mark">A</div><p className="eyebrow">ADORE</p><h1>{t("login")}</h1><p className="muted">{t("subtitle")}</p>
      {error && <p className="alert" role="alert">{error}</p>}
      <form onSubmit={signIn} className="form-stack">
        <label>{t("username")}<input name="username" autoComplete="username" required autoFocus /></label>
        <label>{t("password")}<input name="password" type="password" autoComplete="current-password" required /></label>
        <button className="primary" type="submit">{t("login")}</button>
      </form>
      <div className="login-preferences"><label>{t("language")}<select value={locale} onChange={event => updatePreference("language", event.target.value)}>{Object.entries(localeNames).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>{t("theme")}<select value={theme} onChange={event => updatePreference("theme", event.target.value)}><option value="system">{t("system")}</option><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option></select></label></div>
    </section>
  </main>;

  const activeJobs = runCounts.working || 0;
  const reviewJobs = (runCounts["awaiting-approval"] || 0) + (runCounts["in-review"] || 0);
  const failedJobs = runCounts.failed || 0;
  const nav: Page[] = ["overview", "projects", "jobs", "metrics"];
  const adminPages: Page[] = ["administration", "adminUsers", "adminAudit", "settings"];

  return <div className="shell">
    <aside className="sidebar" inert={!!about}>
      <div className="brand"><span className="brand-mark">A</span><div><strong>ADORE</strong><small>{t("subtitle")}</small></div></div>
      <button className="mobile-menu ghost" type="button" aria-controls="primary-navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(open => !open)}>☰ {t("menu")}</button>
      <nav id="primary-navigation" aria-label="Primary" className={menuOpen ? "nav-open" : ""}>
        {nav.map(item => <button key={item} className={page === item || (item === "projects" && (page === "createProject" || page === "importProject")) ? "nav-item active" : "nav-item"} onClick={() => { setPage(item); setDetails(null); setMenuOpen(false); }}>{t(item)}</button>)}
        {isAdmin ? <><button className={`nav-item nav-parent${adminPages.includes(page) ? " admin-active" : ""}`} aria-expanded={adminMenuOpen} aria-controls="admin-navigation" onClick={() => setAdminMenuOpen(open => !open)}>{t("administration")} <span aria-hidden="true">{adminMenuOpen ? "⌄" : "›"}</span></button>
          {adminMenuOpen && <div id="admin-navigation" className="nav-submenu">{adminPages.map(item => <button key={item} className={page === item ? "nav-item active" : "nav-item"} onClick={() => { setPage(item); setDetails(null); setMenuOpen(false); }}>{t(item === "administration" ? "systemStatus" : item)}</button>)}</div>}</>
          : <button className={page === "settings" ? "nav-item active" : "nav-item"} onClick={() => { setPage("settings"); setDetails(null); setMenuOpen(false); }}>{t("myAccount")}</button>}
      </nav>
      <div className="sidebar-bottom"><span className="user-avatar">{session.user.username.charAt(0).toUpperCase()}</span><div><strong>{session.user.username}</strong><small>{t(session.user.role)}</small></div><button className="icon-button" onClick={signOut} title={t("logout")}>↗</button></div>
    </aside>

    <div className="workspace" inert={!!about}>
      <header className="topbar"><h1 className="topbar-title" aria-label={isAdmin && adminPages.includes(page) ? `${t("administration")} / ${t(page === "administration" ? "systemStatus" : page)}` : t(page === "settings" ? "myAccount" : page)}><span className="topbar-brand">ADORE</span><span aria-hidden="true">/</span>{isAdmin && adminPages.includes(page) ? `${t("administration")} / ${t(page === "administration" ? "systemStatus" : page)}` : t(page === "settings" ? "myAccount" : page)}</h1>
        {page === "projectDetails" && projects.length > 0 && <label className="project-picker">{t("project")}<select value={selected} onChange={event => setSelected(event.target.value)}>{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}
        <div className="top-actions">
        <span className="refresh-stamp">{lastRefresh && `${t("lastRefresh")}: ${formatDate(lastRefresh.toISOString())}`}</span>
        <button className="ghost" onClick={() => { void refreshProjects(); void refreshSelected(); void refreshJobPage(); setUsageRefresh(value => value + 1); }}>{t("refresh")}</button>
        <button className="ghost" ref={aboutTrigger} onClick={() => request<typeof about>("/about").then(setAbout).catch(cause => setError(cause.message))}>{t("about")}</button>
        <button className="ghost mobile-signout" onClick={signOut}>{t("logout")}</button>
      </div></header>

      <main className="content">
        {error && <div className="alert" role="alert">{error}<button onClick={() => setError("")} aria-label={t("close")}>×</button></div>}
        {notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice("")} aria-label={t("close")}>×</button></div>}
        {operation && <div className="notice" role="status">{t("operationStatus")}: #{operation.id} · {operation.status}{operation.result ? ` · ${operation.result}` : ""}</div>}
        {page === "overview" && <>
          <div className="stats-grid">
            <OverviewCard label={t("allProjects")} value={formatNumber(projects.length)} hint={t("projects")} selected={overviewSection === "projects"} onClick={() => setOverviewSection(section => section === "projects" ? null : "projects")} />
            <OverviewCard label={t("activeJobs")} value={formatNumber(activeJobs)} hint={selectedProject?.name || "—"} selected={overviewSection === "active"} onClick={() => setOverviewSection(section => section === "active" ? null : "active")} />
            <OverviewCard label={t("needsReview")} value={formatNumber(reviewJobs)} hint={selectedProject?.name || "—"} selected={overviewSection === "review"} onClick={() => setOverviewSection(section => section === "review" ? null : "review")} />
            <OverviewCard label={t("failedJobs")} value={formatNumber(failedJobs)} hint={selectedProject?.name || "—"} selected={overviewSection === "failed"} onClick={() => setOverviewSection(section => section === "failed" ? null : "failed")} />
          </div>
          <section className="panel" id="overview-detail"><div className="panel-heading"><h2>{t(overviewSection === "projects" ? "allProjects" : overviewSection === "active" ? "activeJobs" : overviewSection === "review" ? "needsReview" : overviewSection === "failed" ? "failedJobs" : "recentJobs")}{overviewSection && overviewSection !== "projects" && selectedProject ? ` · ${selectedProject.name}` : ""}</h2>{overviewSection !== "projects" && <button className="text-button" onClick={() => setPage("jobs")}>{t("view")} →</button>}</div>
            {overviewSection === "projects" ? projects.length ? <PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("repository")}</th><th>{t("status")}</th><th>{t("jobs")}</th><th>{t("actions")}</th></tr></thead><tbody>{projects.map(item => <tr key={item.id} className={item.id === selected ? "overview-project-selected" : ""}><td className="strong"><button className="text-button" aria-current={item.id === selected ? "true" : undefined} onClick={() => setSelected(item.id)}>{item.name}</button></td><td>{item.repo}</td><td>{t(item.readiness === "configured" ? "configured" : item.readiness === "needs-config" ? "needsConfig" : item.readiness === "invalid-state" ? "invalidState" : item.readiness === "archived" ? "archived" : "paused")}</td><td>{item.runs}</td><td><button className="text-button" onClick={() => { setSelected(item.id); setPage("projectDetails"); }}>{t("view")} →</button></td></tr>)}</tbody></table></PagedTable> : <Empty label={t("noProjects")} /> : <RunTable runs={overviewSection ? overviewRuns.filter(run => overviewSection === "active" ? run.lifecycle === "working" : overviewSection === "review" ? ["awaiting-approval", "in-review"].includes(run.lifecycle) : run.lifecycle === "failed") : runs.slice(0, 7)} t={t} formatDate={formatDate} onOpen={runId => { void openRun(runId); setPage("jobs"); }} paged={!!overviewSection} />}
          </section>
        </>}

        {page === "projects" && <>
          <div className="section-actions">{isAdmin && <><button className="primary" onClick={() => { setError(""); setPage("createProject"); }}>{t("createProject")}</button><button className="ghost" onClick={() => { setError(""); setPage("importProject"); }}>{t("importProject")}</button></>}</div>
          <section className="panel">
            {projects.length ? <PagedTable key={`${projectSortKey}-${projectSortDescending}`} t={t}><table className="projects-table"><thead><tr>
              <SortHeader label={t("project")} sortKey="name" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <SortHeader label={t("repository")} sortKey="repo" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <SortHeader label={t("status")} sortKey="readiness" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <SortHeader label={t("jobs")} sortKey="runs" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <SortHeader label={t("lastActivity")} sortKey="last_activity" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <th>{t("actions")}</th>
            </tr></thead><tbody>{sortedProjects.map(item => <tr key={item.id}>
              <td className="strong">{item.name}</td><td>{item.repo}</td>
              <td><span className={`status status-${item.readiness}`}>{projectStatusLabel(item)}</span></td>
              <td>{item.runs}</td><td>{item.last_activity ? formatDate(item.last_activity) : "\u2014"}</td>
              <td><div className="project-row-actions"><button className="text-button" onClick={() => { setSelected(item.id); setPage("projectDetails"); }}>{t("view")}</button>
                {isAdmin && <>{!item.archived && <button className="text-button" onClick={() => void operate(item.paused ? "resume" : "pause", "", item.id)}>{t(item.paused ? "resume" : "pause")}</button>}
                  <button className="text-button" onClick={() => void setProjectArchive(!item.archived, item.id)}>{t(item.archived ? "restoreProject" : "archiveProject")}</button></>}
              </div></td>
            </tr>)}</tbody></table></PagedTable> : <Empty label={t("noProjects")} />}
          </section>
        </>}

        {page === "createProject" && isAdmin && <>
          <div className="section-actions"><button className="ghost" type="button" onClick={() => { setError(""); setPage("projects"); }}>{t("backToProjects")}</button></div>
          <section className="panel"><form className="form-grid project-create-form" onSubmit={createProject}>
            <GuidedField id="new-project-name" label={t("name")} help={t("createHelpName")} helpLabel={t("settingHelp")}><input id="new-project-name" name="name" pattern="[a-z0-9][a-z0-9._-]{0,63}" maxLength={64} required /></GuidedField>
            <GuidedField id="new-project-description" label={t("description")} help={t("createHelpDescription")} helpLabel={t("settingHelp")}><input id="new-project-description" name="description" /></GuidedField>
            <GuidedField id="new-project-forge" label={t("forge")} help={t("settingHelpForge")} helpLabel={t("settingHelp")}><select id="new-project-forge" name="kind"><option value="gitlab">GitLab</option><option value="github">GitHub</option><option value="gitea">Gitea</option></select></GuidedField>
            <GuidedField id="new-project-repo" label={t("repository")} help={t("settingHelpRepository")} helpLabel={t("settingHelp")}><input id="new-project-repo" name="repo" placeholder="owner/repository" required /></GuidedField>
            <GuidedField id="new-project-path" label={t("clonePath")} help={t("createHelpClonePath")} helpLabel={t("settingHelp")}><input id="new-project-path" name="repo_path" placeholder="/home/adore/projects/example" required /><small className="field-hint">{t("createCloneHint")}</small></GuidedField>
            <GuidedField id="new-project-reviewers" label={t("reviewers")} help={t("createHelpReviewers")} helpLabel={t("settingHelp")}><input id="new-project-reviewers" name="reviewers" placeholder="reviewer.one, reviewer.two" required /></GuidedField>
            <GuidedField id="new-project-executor" label={t("executor")} help={t("settingHelpExecutor")} helpLabel={t("settingHelp")}><select id="new-project-executor" name="executor_cli" value={projectExecutor} onChange={event => setProjectExecutor(event.target.value)}><option>opencode</option><option>codex</option><option>pi</option><option>qwen</option></select></GuidedField>
            <GuidedField id="new-project-model" label={t("model")} help={t("createHelpModel")} helpLabel={t("settingHelp")}><input id="new-project-model" name="model" placeholder="provider/model" required /></GuidedField>
            <GuidedField id="new-project-runtime" label={t("runtime")} help={t("createHelpRuntime")} helpLabel={t("settingHelp")}><input id="new-project-runtime" name="runtime" list="container-runtime-suggestions" defaultValue="docker" required /><datalist id="container-runtime-suggestions"><option value="docker" /><option value="podman" /></datalist></GuidedField>
            <GuidedField id="new-project-image" label={t("image")} help={t("createHelpImage")} helpLabel={t("settingHelp")}><input id="new-project-image" name="image" list="executor-image-suggestions" defaultValue="adore-executor-base:1.0.0" required /><datalist id="executor-image-suggestions"><option value="adore-executor-base:1.0.0" /><option value="adore-executor-project:latest" /></datalist><small className="field-hint">{t("createImageHint")}</small></GuidedField>
            <GuidedField id="new-project-branch" label={t("targetBranch")} help={t("createHelpBranch")} helpLabel={t("settingHelp")}><input id="new-project-branch" name="target_branch" defaultValue="main" required /></GuidedField>
            <GuidedField id="new-project-auth" label={t("authMode")} help={t("createHelpAuthMode")} helpLabel={t("settingHelp")}><select id="new-project-auth" name="auth_mode" key={projectExecutor}>{["opencode", "codex"].includes(projectExecutor) && <option value="host-auth">host-auth</option>}<option value="api-key">api-key</option></select></GuidedField>
            <div className="project-create-actions"><button className="primary" type="submit">{t("save")}</button><button className="ghost" type="button" onClick={() => { setError(""); setPage("projects"); }}>{t("cancel")}</button></div>
          </form></section>
        </>}

        {page === "importProject" && isAdmin && <>
          <div className="section-actions"><button className="ghost" type="button" onClick={() => { setError(""); setPage("projects"); }}>{t("backToProjects")}</button></div>
          <section className="panel"><p className="muted">{t("importHelp")}</p><form className="form-grid project-create-form" onSubmit={previewProjectImport}>
            <GuidedField id="import-project-name" label={t("name")} help={t("createHelpName")} helpLabel={t("settingHelp")}><input id="import-project-name" value={importName} onChange={event => { importPreviewRequest.current += 1; setImportName(event.target.value); setImportPreview(null); }} pattern="[a-z0-9][a-z0-9._-]{0,63}" maxLength={64} required /></GuidedField>
            <GuidedField id="import-project-description" label={t("description")} help={t("createHelpDescription")} helpLabel={t("settingHelp")}><input id="import-project-description" value={importDescription} onChange={event => { importPreviewRequest.current += 1; setImportDescription(event.target.value); setImportPreview(null); }} /></GuidedField>
            <GuidedField id="import-project-file" label={t("configFile")} help={t("importConfigHelp")} helpLabel={t("settingHelp")}><input id="import-project-file" type="file" accept=".toml,.txt" onChange={event => { const file = event.target.files?.[0]; const read = ++importFileRead.current; importPreviewRequest.current += 1; setImportPreview(null); setImportText(""); setImportFileName(file?.name || ""); if (file) void file.text().then(value => { if (read === importFileRead.current) setImportText(value); }).catch(cause => { if (read === importFileRead.current) setError(String(cause)); }); }} required /></GuidedField>
            <div className="project-create-actions"><button className="primary" type="submit" disabled={!importText}>{t("previewImport")}</button><button className="ghost" type="button" onClick={() => { setError(""); setPage("projects"); }}>{t("cancel")}</button></div>
          </form></section>
          {importPreview && <section className="panel import-preview"><h2>{t("importPreview")}</h2><p>{importFileName} · {importPreview.platform || "—"} · {importPreview.repo || "—"} · {importPreview.runtime || "—"}</p>{importPreview.store_root && <p className="muted">{t("stateRoot")}: {importPreview.store_root}</p>}<p className="muted">{t("importUnchanged")}</p>{importPreview.issues.length ? <ul>{importPreview.issues.map((issue, index) => <li key={`${issue}-${index}`}>{issue}</li>)}</ul> : <button className="primary" onClick={() => void importProject()}>{t("importProject")}</button>}</section>}
        </>}

        {page === "projectDetails" && selectedProject && <>
          <section className="panel"><div className="panel-heading"><h2>{selectedProject.name}</h2><span className={`status status-${selectedProject.readiness}`}>{t(selectedProject.readiness === "configured" ? "configured" : selectedProject.readiness === "needs-config" ? "needsConfig" : selectedProject.readiness === "invalid-state" ? "invalidState" : selectedProject.readiness === "archived" ? "archived" : "paused")}</span></div><p>{selectedProject.description || selectedProject.repo}</p><div className="project-meta">{t("forge")}: {selectedProject.platform} · {t("repository")}: {selectedProject.repo}</div><div className="project-meta">{t("runtime")}: {selectedProject.runtime} · {t("executor")}: {selectedProject.executor || "—"}</div><div className="project-meta">{t("lastActivity")}: {selectedProject.last_activity ? formatDate(selectedProject.last_activity) : "—"}</div><div className="button-row"><button className="primary" onClick={() => setPage("jobs")}>{t("jobs")}</button><button className="ghost" onClick={() => { setMetricAllProjects(false); setPage("metrics"); }}>{t("metrics")}</button><button className="ghost" disabled={!projectConfig} onClick={() => document.getElementById("project-settings")?.scrollIntoView()}>{t("settings")}</button>{isAdmin && <button className="ghost" onClick={() => setPage("adminUsers")}>{t("assignedProjects")}</button>}</div></section>
          {isAdmin && <section className="panel"><div className="panel-heading"><h2>{t("hostReadiness")}</h2><button className="ghost" onClick={() => void checkProjectReadiness()}>{t("runReadinessCheck")}</button></div><p className="muted">{t("hostReadinessHelp")}</p>{projectReadiness && <><p className="muted">{t("checkedAt")}: {formatDate(projectReadiness.checked_at)}</p><div className="detail-grid">{Object.entries(projectReadiness.checks).map(([key, value]) => <span key={key}>{t(({ git: "gitTool", forge_cli: "forgeCli", forge_auth: "forgeAuth", container_runtime: "containerRuntime", executor_cli: "executorCli", aegis_files: "aegisPayload", model_endpoint: "modelEndpoint" } as Record<string, MessageKey>)[key])}: <strong>{value === true ? t("checkPassed") : value === false ? t("checkMissing") : t("checkUnverified")}</strong></span>)}</div>{projectReadiness.model_probe && <p className="muted">{t("modelEndpoint")}: {modelReason(projectReadiness.model_probe.reason)}{projectReadiness.model_probe.model ? ` (${projectReadiness.model_probe.model})` : ""}</p>}</>}</section>}
          <section className="panel"><div className="panel-heading"><h2>{t("recentJobs")}</h2><button className="text-button" onClick={() => setPage("jobs")}>{t("view")} →</button></div><RunTable runs={runs} t={t} formatDate={formatDate} onOpen={openRun} /></section>
          {projectConfig && <ProjectConfigReadOnly config={projectConfig.config} t={t} />}
          {isAdmin && selected && projectConfig && (projectConfig.config.executor as { default?: string } | undefined)?.default === "opencode" && <section className="panel wide-panel"><h2>{t("localEndpoint")}</h2><p className="muted">{t("localEndpointHelp")}</p><p className="muted">{t("localProviderHelp")}</p>{(projectConfig.config.executor as { default?: string } | undefined)?.default === "opencode" && <form key={`${selected}-${projectConfig.revision}`} className="inline-form config-form" onSubmit={saveEndpoint}><Field name="model" label={t("model")} defaultValue={(projectConfig.config.executor as { commands?: { opencode?: { model?: string } } }).commands?.opencode?.model || ""} required /><Field name="endpoint" label={t("localEndpoint")} type="url" defaultValue={(projectConfig.config.container as { runtime_env?: { OPENAI_BASE_URL?: string } } | undefined)?.runtime_env?.OPENAI_BASE_URL || ""} required /><label>{t("endpointAuth")}<select name="auth_env"><option value="">{t("none")}</option><option value="OPENAI_API_KEY">OPENAI_API_KEY</option></select></label><label>{t("endpointProtocol")}<select name="protocol"><option value="openai-chat-completions">OpenAI chat completions</option></select></label><Field name="timeout_seconds" label={t("endpointTimeout")} type="number" defaultValue={String(projectConfig.local_endpoint_timeout_seconds || 300)} required /><Field name="ca_file" label={t("endpointCa")} defaultValue={(projectConfig.config.container as { runtime_env?: { NODE_EXTRA_CA_CERTS?: string } } | undefined)?.runtime_env?.NODE_EXTRA_CA_CERTS || ""} /><button className="primary" disabled={!!projectPendingConfig}>{t("stageChange")}</button></form>}</section>}
          {isAdmin && selected && <section className="panel wide-panel"><h2>{t("estimatedPrices")}</h2><p className="muted">{t("priceHelp")}</p>
            <form className="form-grid" onSubmit={savePrice}><label>{t("executor")}<select name="executor"><option value="codex">codex</option><option value="opencode">opencode</option><option value="pi">pi</option><option value="qwen">qwen</option></select></label><Field name="model" label={t("model")} required /><label>{t("effectiveFrom")}<input name="effective_from" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label>{t("inputRate")}<input name="input_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><label>{t("outputRate")}<input name="output_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><button className="primary form-submit" type="submit">{t("save")}</button></form>
            {projectPrices.length > 0 && <PagedTable t={t}><table><thead><tr><th>{t("executor")}</th><th>{t("model")}</th><th>{t("effectiveFrom")}</th><th>{t("inputRate")}</th><th>{t("outputRate")}</th></tr></thead><tbody>{projectPrices.map(price => <tr key={price.id}><td>{price.executor}</td><td>{price.model}</td><td>{price.effective_from}</td><td>{price.input_usd_per_million}</td><td>{price.output_usd_per_million}</td></tr>)}</tbody></table></PagedTable>}
          </section>}
          {isAdmin && selected && <section className="panel wide-panel"><h2>{t("config")}</h2>{projectConfig ? <><p className="muted">{t("revision")}: {projectConfig.revision.slice(0, 12)}</p>{projectConfig.issues.length > 0 && <div className="alert">{projectConfig.issues.join(" · ")}</div>}<GuidedConfigForm key={`${selected}-${projectConfig.revision}`} config={projectConfig.config} t={t} onSubmit={editConfig} disabled={!!projectPendingConfig} /><details><summary>{t("advancedConfig")}</summary><form className="inline-form config-form" onSubmit={editConfig}><Field name="key" label={t("configKey")} required /><Field name="value" label={t("configValue")} required /><button className="primary" disabled={!!projectPendingConfig}>{t("stageChange")}</button></form></details>{projectPendingConfig && <div className="import-preview" role="status"><h3>{t("pendingChange")}</h3><p>{projectPendingConfig.key}: {projectPendingConfig.value}</p>{projectPendingConfig.endpoint && <div className="detail-grid"><span>{t("endpointProtocol")}: {projectPendingConfig.endpoint.protocol}</span><span>{t("model")}: {projectPendingConfig.endpoint.model}</span><span>{t("endpointTimeout")}: {projectPendingConfig.endpoint.timeout_seconds ?? "—"}</span><span>{t("endpointAuth")}: {projectPendingConfig.endpoint.auth_env || "—"}</span><span>{t("endpointCa")}: {projectPendingConfig.endpoint.ca_file || "—"}</span></div>}<p className="muted">{t("revision")}: {projectPendingConfig.candidate_revision.slice(0, 12)}</p><p className="muted">{projectPendingConfig.restart_required ? t("pendingRestartHelp") : t("pendingApplyHelp")}</p><div className="button-row"><button className="primary" onClick={() => void applyPendingConfig()}>{t("apply")}</button><button className="ghost" onClick={() => void discardPendingConfig()}>{t("discardChange")}</button></div></div>}<details><summary>{t("rawConfig")}</summary><pre className="config-preview">{JSON.stringify(projectConfig.config, null, 2)}</pre></details></> : <Empty label={t("empty")} />}</section>}
        </>}

        {page === "jobs" && <>
          {projects.length > 0 && <section className="panel compact"><form className="inline-form job-start-form" onSubmit={event => { event.preventDefault(); if (selectedProject && !selectedProject.archived) void operate("start", ticket); }}>
            <label htmlFor="jobs-project">{t("project")}<select id="jobs-project" value={selected} onChange={event => { setTicket(""); setDetails(null); setSelected(event.target.value); }}>{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            {selectedProject && !selectedProject.archived && <><GuidedField id="job-ticket-number" label={t("ticketNumber")} help={t("ticketNumberHelp")} helpLabel={t("settingHelp")}><input id="job-ticket-number" type="number" min="1" step="1" placeholder="42" value={ticket} onChange={event => setTicket(event.target.value)} required /></GuidedField><button className="primary" type="submit">{t("start")}</button></>}
          </form></section>}
          <section className="panel">
            <div className="job-filters job-basic-filters"><label>{t("status")}<select value={jobLifecycle} onChange={event => setJobLifecycle(event.target.value)}><option value="">{t("all")}</option>{Object.keys(lifecycleLabels).map(value => <option key={value} value={value}>{displayCode(value, lifecycleLabels, t)}</option>)}</select></label><label>{t("stage")}<select value={jobStage} onChange={event => setJobStage(event.target.value)}><option value="">{t("all")}</option>{Object.keys(stageLabels).map(value => <option key={value} value={value}>{displayCode(value, stageLabels, t)}</option>)}</select></label><label>{t("updatedFrom")}<input type="date" value={jobUpdatedFrom} max={jobUpdatedTo || undefined} onChange={event => setJobUpdatedFrom(event.target.value)} /></label><label>{t("updatedTo")}<input type="date" value={jobUpdatedTo} min={jobUpdatedFrom || undefined} onChange={event => setJobUpdatedTo(event.target.value)} /></label></div>
            <div className="job-filters job-text-filters">
              <GuidedField id="jobs-executor-filter" label={t("observedExecutor")} help={t("observedExecutorHelp")} helpLabel={t("settingHelp")}><input id="jobs-executor-filter" type="search" maxLength={200} placeholder="pi" value={jobExecutor} onChange={event => setJobExecutor(event.target.value)} /></GuidedField>
              <GuidedField id="jobs-outcome-filter" label={t("outcomeContains")} help={t("outcomeContainsHelp")} helpLabel={t("settingHelp")}><input id="jobs-outcome-filter" type="search" maxLength={80} placeholder="EXECUTOR_TIMEOUT" value={jobOutcome} onChange={event => setJobOutcome(event.target.value)} /></GuidedField>
            </div>
            <RunTable runs={jobPage.items} t={t} formatDate={formatDate} onOpen={openRun} emptyLabel={jobLifecycle || jobStage || jobExecutor.trim() || jobUpdatedFrom || jobUpdatedTo || jobOutcome.trim() ? t("noMatchingJobs") : t("noJobs")} />
            {jobPage.total > 10 && <div className="page-controls"><label>{t("rowsPerPage")}<select value={jobPageSize} onChange={event => setJobPageSize(event.target.value === "all" ? "all" : Number(event.target.value) as 10 | 25 | 50)}><option value="10">10</option><option value="25">25</option><option value="50">50</option><option value="all">{t("all")}</option></select></label>{jobPageSize !== "all" && <><button className="ghost" disabled={jobOffset === 0} onClick={() => setJobOffset(Math.max(0, jobOffset - jobPageSize))}>{t("previous")}</button><span>{jobOffset + 1}–{Math.min(jobOffset + jobPageSize, jobPage.total)} / {jobPage.total}</span><button className="ghost" disabled={jobOffset + jobPageSize >= jobPage.total} onClick={() => setJobOffset(jobOffset + jobPageSize)}>{t("next")}</button></>}</div>}
          </section>
          {details && <section className="panel detail-panel"><div className="panel-heading"><h2>{t("ticket")} #{details.run.ticket_iid}</h2><button className="ghost" onClick={() => setDetails(null)}>{t("close")}</button></div>
            <div className="detail-grid"><span>{t("status")}: <strong>{displayCode(details.run.lifecycle, lifecycleLabels, t)}</strong></span><span>{t("stage")}: <strong>{displayCode(details.run.stage, stageLabels, t)}</strong></span><span>{t("reviewRounds")}: <strong>{details.run.review_rounds}</strong></span><span>{t("attempts")}: <strong>{details.run.stage_failures}</strong></span></div>
            <div className="button-row">{!projects.find(project => project.id === selected)?.archived && details.run.lifecycle === "failed" && <button className="ghost" onClick={() => operate("retry", details.run.run_id)}>{t("retry")}</button>}{!projects.find(project => project.id === selected)?.archived && !["done", "failed", "cancelled", "handoff-pending", "handed-off"].includes(details.run.lifecycle) && <button className="danger" onClick={() => operate("cancel", details.run.run_id)}>{t("cancel")}</button>}{details.run.mr_url && <a className="ghost link-button" href={details.run.mr_url} target="_blank" rel="noreferrer">{t("draft")} ↗</a>}</div>
            <h3>{t("timeline")}</h3><ol className="timeline">{details.events.map((event, index) => <li key={index}><time>{formatDate(String(event.ts || ""))}</time><strong>{String(event.event || "")}</strong>{Boolean(event.stage) && <span>{String(event.stage)}</span>}</li>)}</ol>
          </section>}
        </>}

        {page === "metrics" && <>
        <section className="panel compact metrics-period"><div className="panel-heading"><h2>{t("reportingPeriod")}</h2>{(selected || isAdmin) && <details className="metrics-export"><summary className="ghost metrics-export-trigger">{t("exportCsv")}</summary><div className="metrics-export-links">{!allProjectScope && selected && <><a href={`/api/v1/projects/${encodeURIComponent(selected)}/metrics.csv${metricSuffix}`}>{t("projectMetricsExport")}</a><a href={`/api/v1/projects/${encodeURIComponent(selected)}/usage.csv${usageSuffix}`}>{t("projectUsageExport")}</a></>}{allProjectScope && <><a href={`/api/v1/metrics.csv${metricSuffix}`}>{t("allMetricsExport")}</a><a href={`/api/v1/usage.csv${usageSuffix}`}>{t("allUsageExport")}</a></>}</div></details>}</div><div className="job-filters">{projects.length > 0 && <label className="metrics-project-filter" htmlFor="metrics-project">{t("project")}<select id="metrics-project" value={allProjectScope ? "" : selected} onChange={event => { setMetricAllProjects(event.target.value === ""); if (event.target.value) setSelected(event.target.value); }}>{isAdmin && <option value="">{t("metricsAllProjects")}</option>}{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label>{t("dateFromLocal")}<input type="date" value={metricFrom} max={metricTo || undefined} onChange={event => setMetricFrom(event.target.value)} /></label><label>{t("dateToLocal")}<input type="date" value={metricTo} min={metricFrom || undefined} onChange={event => setMetricTo(event.target.value)} /></label><label>{t("reportingTimezone")}<select value={metricTimezone} onChange={event => setMetricTimezone(event.target.value)}><option value="UTC">UTC</option><option value="Europe/Bucharest">Europe/Bucharest</option><option value="Europe/Paris">Europe/Paris</option><option value="Europe/Berlin">Europe/Berlin</option><option value="America/New_York">America/New_York</option></select></label><label>{t("trendGranularity")}<select value={metricGranularity} onChange={event => setMetricGranularity(event.target.value as "day" | "week" | "month")}><option value="day">{t("byDay")}</option><option value="week">{t("byWeek")}</option><option value="month">{t("byMonth")}</option></select></label></div><p className="muted">{t("metricsScopeHelp")} {t("reportingScopeHelp")}</p></section>
        <div className="metrics-tabs" role="tablist" aria-label={t("metrics")}>
          {metricsTabs.map(tab => <button key={tab} id={`metrics-tab-${tab}`} type="button" role="tab" aria-controls="metrics-tab-panel" aria-selected={metricsTab === tab} tabIndex={metricsTab === tab ? 0 : -1} onClick={() => setMetricsTab(tab)} onKeyDown={event => onMetricsTabKeyDown(event, tab)}>{t(metricsTabLabels[tab])}</button>)}
        </div>
        <div id="metrics-tab-panel" role="tabpanel" aria-labelledby={`metrics-tab-${metricsTab}`} tabIndex={0}>
        {metricsTab === "usage" && <>
        <section className="panel"><div className="panel-heading usage-heading"><h2>{t("attributedUsage")}</h2>{isAdmin && <button className="ghost" onClick={() => void rebuildUsage()}>{t("rebuildUsage")}</button>}</div>
          <div className="job-filters"><label>{t("executor")}<input type="search" maxLength={200} value={usageExecutor} onChange={event => setUsageExecutor(event.target.value)} /></label><label>{t("model")}<input type="search" maxLength={200} value={usageModel} onChange={event => setUsageModel(event.target.value)} /></label></div>
          <p className="muted">{t("attributedUsageHelp")}</p>
          {usage && <p className="muted">{t("usageEvents")}: {formatNumber(usage.totals.events)} · {t("tokensIn")}: {formatNumber(usage.totals.tokens_in)} · {t("tokensOut")}: {formatNumber(usage.totals.tokens_out)} / {t("cacheRead")}: {usage.totals.cache_read_tokens == null ? "\u2014" : formatNumber(usage.totals.cache_read_tokens)} / {t("cacheWrite")}: {usage.totals.cache_write_tokens == null ? "\u2014" : formatNumber(usage.totals.cache_write_tokens)}{isAdmin && <> · {t("cost")}: {formatMoney(usage.totals.reported_cost_usd)} · {t("estimatedCost")}: {formatMoney(usage.totals.estimated_cost_usd)}</>}</p>}
          {usage?.daily.length ? <PagedTable t={t}><table><thead><tr><th>{t("date")}</th><th>{t("executor")}</th><th>{t("model")}</th><th>{t("usageEvents")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cacheRead")}</th><th>{t("cacheWrite")}</th>{isAdmin && <th>{t("cost")}</th>}{isAdmin && <th>{t("estimatedCost")}</th>}</tr></thead><tbody>{usage.daily.map((row, index) => <tr key={`${row.date}-${row.executor}-${row.model}-${index}`}><td>{row.date}</td><td>{row.executor || "—"}</td><td>{row.model || "—"}</td><td>{formatNumber(row.events)}</td><td>{formatNumber(row.tokens_in)}</td><td>{formatNumber(row.tokens_out)}</td><td>{row.cache_read_tokens == null ? "\u2014" : formatNumber(row.cache_read_tokens)}</td><td>{row.cache_write_tokens == null ? "\u2014" : formatNumber(row.cache_write_tokens)}</td>{isAdmin && <td>{formatMoney(row.reported_cost_usd)}</td>}{isAdmin && <td>{formatMoney(row.estimated_cost_usd)}</td>}</tr>)}</tbody></table></PagedTable> : <Empty label={t("noMatchingMetrics")} />}
          {allProjectScope && allUsage && <><h3>{t("allProjects")}</h3><PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("usageEvents")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>{scopedUsageRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{formatNumber(item.totals.events)}</td><td>{formatNumber(item.totals.tokens_in)}</td><td>{formatNumber(item.totals.tokens_out)}</td><td>{formatMoney(item.totals.reported_cost_usd)}</td><td>{formatMoney(item.totals.estimated_cost_usd)}</td></tr>)}</tbody></table></PagedTable></>}
        </section></>}
        {metricsTab === "summary" && <>
        <p className="muted">{scopeLabel} · {t("allTimeTotals")}</p><div className="stats-grid">
          <Stat label={t("runs")} value={formatNumber(metrics?.totals.runs || 0)} hint={scopeLabel} />
          <Stat label={t("tokensIn")} value={formatNumber(metrics?.totals.tokens_in || 0)} hint={t("coverage")} />
          <Stat label={t("tokensOut")} value={formatNumber(metrics?.totals.tokens_out || 0)} hint={t("coverage")} />
          <Stat label={t("reviewRounds")} value={formatNumber(metrics?.runs.reduce((sum, row) => sum + Number(row.review_rounds || 0), 0) || 0)} hint={scopeLabel} />
          <Stat label={t("mrRevisions")} value={formatNumber(metrics?.totals.mr_revisions || 0)} hint={scopeLabel} />
          <Stat label={t("pipelineRepairs")} value={formatNumber(metrics?.totals.pipeline_repairs || 0)} hint={scopeLabel} />
          {isAdmin && <Stat label={t("cost")} value={metrics?.totals.cost_usd == null ? "—" : new Intl.NumberFormat(locale, { style: "currency", currency: "USD" }).format(metrics.totals.cost_usd)} hint={scopeLabel} />}
          {isAdmin && <Stat label={t("estimatedCost")} value={formatMoney(metrics?.totals.estimated_cost_usd)} hint={scopeLabel} />}
        </div>
        {allProjectScope && allMetrics && <section className="panel"><div className="panel-heading"><h2>{t("projectComparison")}</h2><span className="muted">{t("allTimeTotals")}</span></div>
          <PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("jobs")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("reviewRounds")}</th><th>{t("mrRevisions")}</th><th>{t("pipelineRepairs")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>
            {globalRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{formatNumber(item.totals.runs || 0)}</td><td>{formatNumber(item.totals.tokens_in || 0)}</td><td>{formatNumber(item.totals.tokens_out || 0)}</td><td>{formatNumber(item.runs.reduce((total, row) => total + Number(row.review_rounds || 0), 0))}</td><td>{formatNumber(item.totals.mr_revisions || 0)}</td><td>{formatNumber(item.totals.pipeline_repairs || 0)}</td><td>{formatMoney(item.totals.cost_usd)}</td><td>{formatMoney(item.totals.estimated_cost_usd)}</td></tr>)}
          </tbody></table></PagedTable>
        </section>}
        <section className="panel"><div className="panel-heading"><h2>{t("coverage")}</h2><span className="muted">{t("allTimeTotals")}</span></div>
          <p className="muted">{t("launchCoverageHelp")}</p><div className="stats-grid">
            <Stat label={t("reportedTokenLaunches")} value={formatNumber(metrics?.coverage.launches_with_reported_tokens || 0)} hint={scopeLabel} />
            <Stat label={t("unavailableTokenLaunches")} value={formatNumber(metrics?.coverage.launches_with_unavailable_tokens || 0)} hint={scopeLabel} />
            <Stat label={t("disabledCaptureLaunches")} value={formatNumber(metrics?.coverage.launches_capture_disabled || 0)} hint={scopeLabel} />
            {isAdmin && <Stat label={t("reportedCostLaunches")} value={formatNumber(metrics?.coverage.launches_with_reported_cost || 0)} hint={scopeLabel} />}
            {isAdmin && <Stat label={t("unavailableCostLaunches")} value={formatNumber(metrics?.coverage.launches_with_unavailable_cost || 0)} hint={scopeLabel} />}
          </div>
        </section>
        <section className="panel"><div className="panel-heading"><h2>{t("jobDuration")}</h2><span className="muted">{t("allTimeTotals")}</span></div>
          <p className="muted">{t("durationHelp")}</p><div className="stats-grid">
            <Stat label={t("measuredJobs")} value={formatNumber(metrics?.duration.sampled_runs || 0)} hint={scopeLabel} />
            <Stat label={t("averageSpan")} value={metrics?.duration.avg_span_seconds == null ? "—" : `${formatNumber(metrics.duration.avg_span_seconds)} s`} hint={t("jobDuration")} />
            <Stat label={t("medianSpan")} value={metrics?.duration.median_span_seconds == null ? "—" : `${formatNumber(metrics.duration.median_span_seconds)} s`} hint={t("jobDuration")} />
          </div>
        </section>
        {(metricFrom || metricTo) && metrics?.period && <section className="panel"><div className="panel-heading"><h2>{t("periodTotals")}</h2><span className="muted">{metricTimezone}</span></div><p className="muted">{t("datedEventsHelp")}</p><PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("jobsStarted")}</th><th>{t("completed")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("mrRevisions")}</th><th>{t("pipelineRepairs")}</th>{isAdmin && <th>{t("cost")}</th>}{isAdmin && <th>{t("estimatedCost")}</th>}</tr></thead><tbody><tr><td>{scopeLabel}</td><td>{formatNumber(metrics.period.started)}</td><td>{formatNumber(metrics.period.completed)}</td><td>{formatNumber(metrics.period.tokens_in)}</td><td>{formatNumber(metrics.period.tokens_out)}</td><td>{formatNumber(metrics.period.mr_revisions)}</td><td>{formatNumber(metrics.period.pipeline_repairs)}</td>{isAdmin && <td>{formatMoney(metrics.period.cost_usd)}</td>}{isAdmin && <td>{formatMoney(metrics.period.estimated_cost_usd)}</td>}</tr></tbody></table></PagedTable></section>}
        {(metricFrom || metricTo) && metrics?.period && <section className="panel"><div className="panel-heading"><h2>{t("jobDuration")} · {t("periodTotals")}</h2><span className="muted">{metricTimezone}</span></div>
          <p className="muted">{t("durationPeriodHelp")}</p><div className="stats-grid">
            <Stat label={t("measuredJobs")} value={formatNumber(metrics.period.duration.sampled_runs)} hint={scopeLabel} />
            <Stat label={t("averageSpan")} value={metrics.period.duration.avg_span_seconds == null ? "—" : `${formatNumber(metrics.period.duration.avg_span_seconds)} s`} hint={scopeLabel} />
            <Stat label={t("medianSpan")} value={metrics.period.duration.median_span_seconds == null ? "—" : `${formatNumber(metrics.period.duration.median_span_seconds)} s`} hint={scopeLabel} />
          </div>
        </section>}
        </>}
        {metricsTab === "quality" && <>
        <section className="panel"><div className="panel-heading"><h2>{t("deliveryQuality")}</h2><span className="muted">{t("allTimeTotals")}</span></div>
          <p className="muted">{t("qualityHelp")}</p><div className="stats-grid">
            <Stat label={t("reviewReworkRate")} value={formatPercent(metrics?.quality.review_rework_rate)} hint={`${formatNumber(metrics?.quality.reworked_jobs || 0)} / ${formatNumber(metrics?.quality.reviewed_jobs || 0)} ${t("reviewedJobs")}`} />
            <Stat label={t("firstValidationRate")} value={formatPercent(metrics?.quality.first_validation_rate)} hint={`${formatNumber(metrics?.quality.first_pass_validations || 0)} / ${formatNumber(metrics?.quality.validated_jobs || 0)} ${t("validatedJobs")}`} />
            <Stat label={t("firstPassMergeRate")} value={formatPercent(metrics?.quality.first_pass_merge_rate)} hint={`${formatNumber(metrics?.quality.first_pass_merges || 0)} / ${formatNumber(metrics?.quality.human_merged_jobs || 0)} ${t("humanMergedJobs")}`} />
            <Stat label={t("openReviews")} value={formatNumber(metrics?.quality.open_review_jobs || 0)} hint={t("reviewedJobs")} />
            <Stat label={t("attempts")} value={formatNumber(metrics?.quality.stage_failures || 0)} hint={t("jobs")} />
            <Stat label={t("operatorRetries")} value={formatNumber(metrics?.quality.operator_retries || 0)} hint={t("jobs")} />
          </div>
        </section>
        {isAdmin && <section className="panel"><div className="panel-heading"><h2>{t("qualityEfficiency")}</h2><span className="muted">USD</span></div>
          <p className="muted">{t("costEvidenceHelp")}</p><div className="stats-grid">
            {([ ["reported_per_completed", "reportedCompleted"], ["estimated_per_completed", "estimatedCompleted"], ["reported_per_human_merged", "reportedMerged"], ["estimated_per_human_merged", "estimatedMerged"] ] as const).map(([key, label]) => <Stat key={key} label={t(label)} value={formatMoney(metrics?.quality.cost_efficiency?.[key]?.usd_per_job)} hint={`${formatNumber(metrics?.quality.cost_efficiency?.[key]?.jobs_with_evidence || 0)} ${t("jobsWithEvidence")}`} />)}
          </div>
        </section>}
        <section className="panel"><div className="panel-heading"><h2>{t("mrRevisions")} / {t("pipelineRepairs")}</h2><span className="muted">{metricTimezone}</span></div>
          <PagedTable t={t}><table><thead><tr><th>{t("date")}</th><th>{t("mrRevisions")}</th><th>{t("pipelineRepairs")}</th></tr></thead><tbody>
            {metrics?.daily.map(day => <tr key={day.date}><td>{day.date}</td><td>{formatNumber(day.mr_revisions)}</td><td>{formatNumber(day.pipeline_repairs)}</td></tr>)}
          </tbody></table></PagedTable>
          <p className="muted coverage-note">{t("unclassifiedRevisions")}: {formatNumber(metrics?.coverage.revision_events_unclassified || 0)}</p>
        </section>
        {allProjectScope && <section className="panel"><div className="panel-heading"><h2>{t("metricsAllProjects")} · {t("mrRevisions")} / {t("pipelineRepairs")}</h2></div>
          <PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("mrRevisions")}</th><th>{t("pipelineRepairs")}</th></tr></thead><tbody>
            {globalRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{formatNumber(item.totals.mr_revisions || 0)}</td><td>{formatNumber(item.totals.pipeline_repairs || 0)}</td></tr>)}
          </tbody></table></PagedTable>
        </section>}
        {isAdmin && !allProjectScope && selected && (metrics?.revisions?.length || 0) > 0 && <section className="panel"><div className="panel-heading"><h2>{t("revisionCosts")}</h2><span className="muted">{scopeLabel}</span></div>
          <PagedTable t={t}><table><thead><tr><th>{t("jobs")}</th><th>{t("revision")}</th><th>{t("date")}</th><th>{t("status")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>
            {metrics?.revisions?.map(row => <tr key={`${row.run_id}-${row.revision}`}><td>{row.run_id}</td><td>{row.revision}</td><td>{row.date || "—"}</td><td>{row.trigger === "revise-label" ? t("mrRevisions") : row.trigger === "pipeline-failed" ? t("pipelineRepairs") : t("unclassifiedRevisions")}</td><td>{formatNumber(row.tokens_in)}</td><td>{formatNumber(row.tokens_out)}</td><td>{formatMoney(row.reported_cost_usd)}</td><td>{formatMoney(row.estimated_cost_usd)}</td></tr>)}
          </tbody></table></PagedTable>
        </section>}
        </>}
        {metricsTab === "projects" && isAdmin && <>
        <section className="panel"><div className="panel-heading metrics-project-heading"><h2>{t("projectComparison")}</h2><span className="muted">{scopeProjects.length} {t("projects")} · {repositoryRows.length} {t("repository")}</span></div>
          <PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("repository")}</th><th>{t("jobs")}</th><th>{t("measuredJobs")}</th><th>{t("averageSpan")}</th><th>{t("reviewReworkRate")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("reviewRounds")}</th><th>{t("cost")}</th></tr></thead><tbody>
            {globalRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{projects.find(project => project.name === name)?.repo || "—"}</td><td>{formatNumber(projects.find(project => project.name === name)?.runs || 0)}</td><td>{formatNumber(item.duration.sampled_runs)}</td><td>{item.duration.avg_span_seconds == null ? "—" : `${formatNumber(item.duration.avg_span_seconds)} s`}</td><td>{formatPercent(item.quality.review_rework_rate)} ({formatNumber(item.quality.reworked_jobs)}/{formatNumber(item.quality.reviewed_jobs)})</td><td>{formatNumber(item.totals.tokens_in || 0)}</td><td>{formatNumber(item.totals.tokens_out || 0)}</td><td>{formatNumber(item.runs.reduce((sum, run) => sum + Number(run.review_rounds || 0), 0))}</td><td>{item.totals.cost_usd == null ? "—" : new Intl.NumberFormat(locale, { style: "currency", currency: "USD" }).format(item.totals.cost_usd)}</td></tr>)}
            {allProjectScope && <tr><th>{t("metricsAllProjects")}</th><th>{repositoryRows.length}</th><th>{formatNumber(scopeProjects.reduce((sum, project) => sum + project.runs, 0))}</th><th>{formatNumber(globalRows.reduce((sum, [, item]) => sum + item.duration.sampled_runs, 0))}</th><th>—</th><th>—</th><th>{formatNumber(globalTokensIn)}</th><th>{formatNumber(globalTokensOut)}</th><th>{formatNumber(globalReviewRounds)}</th><th>{globalRows.some(([, item]) => item.totals.cost_usd != null) ? new Intl.NumberFormat(locale, { style: "currency", currency: "USD" }).format(globalReportedCost) : "—"}</th></tr>}
          </tbody></table></PagedTable></section>
        {isAdmin && repositoryRows.length > 0 && <section className="panel"><div className="panel-heading"><h2>{t("repository")}</h2><span className="muted">{repositoryRows.length}</span></div>
          <PagedTable t={t}><table><thead><tr><th>{t("repository")}</th><th>{t("projects")}</th><th>{t("jobs")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>
            {repositoryRows.map(([repo, row]) => <tr key={repo}><td>{repo}</td><td>{formatNumber(row.projects)}</td><td>{formatNumber(row.jobs)}</td><td>{formatNumber(row.tokensIn)}</td><td>{formatNumber(row.tokensOut)}</td><td>{formatMoney(row.hasReported ? row.reported : null)}</td><td>{formatMoney(row.hasEstimated ? row.estimated : null)}</td></tr>)}
          </tbody></table></PagedTable></section>}
        </>}
        {metricsTab === "trends" && <>
        <section className="panel"><div className="panel-heading"><h2>{trendTitle}</h2><span className="muted">{metricTimezone}</span></div>
          {metrics?.daily.length ? <PagedTable t={t}><table><thead><tr><th>{t("date")}</th><th>{t("jobsStarted")}</th><th>{t("completed")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th>{isAdmin && <th>{t("cost")}</th>}</tr></thead><tbody>{metrics.daily.map(day => <tr key={day.date}><td>{day.date}</td><td>{formatNumber(day.started)}</td><td>{formatNumber(day.completed)}</td><td>{formatNumber(day.tokens_in)}</td><td>{formatNumber(day.tokens_out)}</td>{isAdmin && <td>{day.cost_usd == null ? "—" : new Intl.NumberFormat(locale, { style: "currency", currency: "USD" }).format(day.cost_usd)}</td>}</tr>)}</tbody></table></PagedTable> : <Empty label={metricFrom || metricTo ? t("noMatchingMetrics") : t("noMetrics")} />}
          <p className="muted coverage-note">{t("coverage")}: {formatNumber(metrics?.coverage.runs_with_usage || 0)} / {formatNumber(metrics?.totals.runs || 0)} {t("jobs")}</p>
        </section>
        {isAdmin && <section className="panel"><div className="panel-heading"><h2>{t("estimatedCost")}</h2><strong>{formatMoney(metrics?.totals.estimated_cost_usd)} {scopeLabel}</strong></div>
          <p className="muted">{t("priceHelp")}</p>
          <PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("estimatedCost")}</th><th>{t("unpricedEvents")}</th></tr></thead><tbody>{globalRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{formatMoney(item.totals.estimated_cost_usd)}</td><td>{formatNumber(item.coverage.usage_events_unpriced || 0)}</td></tr>)}</tbody></table></PagedTable>
          <h3>{scopeLabel} {trendTitle}</h3>
          <PagedTable t={t}><table><thead><tr><th>{t("date")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>{metrics?.daily.map(day => <tr key={day.date}><td>{day.date}</td><td>{formatMoney(day.estimated_cost_usd)}</td></tr>)}</tbody></table></PagedTable>
        </section>}</>}
        </div></>}

        {page === "administration" && isAdmin && <div className="two-column">
          <section className="panel wide-panel" role="status" aria-live="polite"><div className="panel-heading"><h2>{t("workerReadiness")}</h2><strong className={`readiness readiness-${workerStatus}`}>{t(workerStatus === "ready" ? "workerReady" : workerStatus === "unavailable" ? "workerUnavailable" : workerStatus === "error" ? "workerCheckFailed" : "workerChecking")}</strong></div><p className="muted">{t("workerReadinessHelp")}</p></section>
          <section className="panel wide-panel" role="status" aria-live="polite"><div className="panel-heading"><h2>{t("storageStatus")}</h2><strong className={`readiness readiness-${storageError ? "error" : storageStatus?.low ? "unavailable" : storageStatus ? "ready" : "checking"}`}>{t(storageError ? "storageCheckFailed" : storageStatus?.low ? "storageLow" : storageStatus ? "storageHealthy" : "workerChecking")}</strong></div><p className="muted">{t("storageHelp")}</p>{storageStatus && <PagedTable t={t}><table><thead><tr><th>{t("storageVolume")}</th><th>{t("storageFree")}</th><th>{t("status")}</th></tr></thead><tbody>{storageStatus.volumes.map((volume, index) => <tr key={`${volume.scope}-${volume.project || index}`}><td>{volume.scope === "home" ? t("storageHome") : volume.project}</td><td>{new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(volume.free_bytes / 1024**3)} GiB</td><td>{t(volume.low ? "storageLow" : "storageHealthy")}</td></tr>)}</tbody></table></PagedTable>}</section>
        </div>}

        {page === "adminUsers" && isAdmin && <div className="two-column">
          <section className="panel"><h2>{t("createUser")}</h2><form className="form-stack" onSubmit={createUser}><Field name="username" label={t("username")} required /><Field name="password" label={t("password")} type="password" required /><label>{t("role")}<select name="role"><option value="developer">{t("developer")}</option><option value="admin">{t("admin")}</option></select></label><button className="primary">{t("createUser")}</button></form></section>
          <section className="panel"><h2>{t("userAccounts")}</h2><div className="user-list">{users.map(item =>
            <div className="user-row" key={item.id}>
              <span className="user-avatar">{item.username.charAt(0).toUpperCase()}</span>
              <div><strong>{item.username}</strong><small>{t(item.role)}{item.disabled ? ` · ${t("disable")}` : ""}</small></div>
              {item.role === "developer" && <details className="membership-editor"><summary>{t("assignedProjects")}</summary>
                <form onSubmit={event => assignProjects(event, item.id)}>
                  {projects.map(project => <label key={project.name}><input type="checkbox" name="projects" value={project.name} defaultChecked={item.projects?.includes(project.name)} />{project.name}</label>)}
                  <button className="ghost">{t("save")}</button>
                </form>
              </details>}
              {item.id !== session.user.id && <button type="button" className="ghost" onClick={() => setAccountEnabled(item.id, item.disabled)}>{t(item.disabled ? "enable" : "disable")}</button>}
              <button type="button" className="ghost" onClick={() => setResetTarget(resetTarget === item.id ? null : item.id)}>{t("resetPassword")}</button>
              {resetTarget === item.id && <form className="inline-form" onSubmit={event => resetUserPassword(event, item.id)}><Field name="replacement" label={t("newPassword")} type="password" required /><button className="primary">{t("save")}</button></form>}
            </div>
          )}</div></section>
        </div>}

        {page === "adminAudit" && isAdmin && <div className="two-column">
          <section className="panel wide-panel"><h2>{t("auditRetention")}</h2><p className="muted">{t("auditRetentionHelp")}</p>{auditPolicy && <form key={`${auditPolicy.retention_days}-${auditPolicy.max_bytes}`} className="inline-form audit-policy-form" onSubmit={saveAuditPolicy}><label>{t("auditDays")}<input name="retention_days" type="number" min="1" max="36500" step="1" defaultValue={auditPolicy.retention_days ?? ""} /></label><label>{t("auditMib")}<input name="max_mib" type="number" min="1" max="1024" step="1" defaultValue={auditPolicy.max_bytes == null ? "" : auditPolicy.max_bytes / 1024**2} /></label><button className="primary" type="submit">{t("save")}</button></form>}</section>
          <section className="panel wide-panel"><div className="panel-heading"><h2>{t("auditTrail")}</h2><button className="ghost" onClick={() => request<AuditRow[]>("/audit?limit=all").then(setAuditRows).catch(cause => setError(cause.message))}>{t("refresh")}</button></div>
            {auditRows.length ? <PagedTable t={t}><table><thead><tr><th>{t("date")}</th><th>{t("actor")}</th><th>{t("action")}</th><th>{t("project")}</th><th>{t("detail")}</th></tr></thead><tbody>{auditRows.map(row => <tr key={row.id}><td>{formatDate(row.created_at)}</td><td>{row.actor || "—"}</td><td>{row.action}</td><td>{row.project || "—"}</td><td>{row.detail || "—"}</td></tr>)}</tbody></table></PagedTable> : <Empty label={t("empty")} />}
          </section>
        </div>}

        {page === "settings" && <div className="two-column"><section className="panel"><h2>{t("appearance")}</h2><div className="form-stack"><label>{t("language")}<select value={locale} onChange={event => updatePreference("language", event.target.value)}>{Object.entries(localeNames).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>{t("theme")}<select value={theme} onChange={event => updatePreference("theme", event.target.value)}><option value="system">{t("system")}</option><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option></select></label></div></section><section className="panel"><h2>{t("changePassword")}</h2><form className="form-stack" onSubmit={changePassword}><Field name="current" label={t("currentPassword")} type="password" required /><Field name="replacement" label={t("newPassword")} type="password" required /><button className="primary">{t("save")}</button></form></section>
        </div>}
      </main>
    </div>

    {about && <div className="modal-backdrop" onClick={closeAbout}><section role="dialog" aria-modal="true" aria-labelledby="adore-about-heading" className="modal" onClick={event => event.stopPropagation()} onKeyDown={event => { if (event.key === "Escape") closeAbout(); if (event.key === "Tab") { event.preventDefault(); aboutClose.current?.focus(); } }}><button className="ghost modal-close" ref={aboutClose} autoFocus onClick={closeAbout}>{t("close")}</button><div className="brand-mark">A</div><h2 id="adore-about-heading">{t("about")} ADORE</h2><p>{t("version")}: {about.version}</p><p>{t("license")}: {about.license}</p><pre className="license-text">{about.license_text}</pre><h3>{t("thirdPartyNotices")}</h3><pre className="license-text">{about.third_party_notices}</pre></section></div>}
  </div>;
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return <div className="stat-card"><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>;
}

function OverviewCard({ label, value, hint, selected, onClick }: { label: string; value: string; hint: string; selected: boolean; onClick: () => void }) {
  return <button type="button" className={`stat-card overview-card${selected ? " selected" : ""}`} aria-expanded={selected} aria-controls="overview-detail" onClick={onClick}><span>{label}</span><strong>{value}</strong><small>{hint}</small><span className="overview-chevron" aria-hidden="true">{selected ? "⌃" : "⌄"}</span></button>;
}

function SortHeader({ label, sortKey, activeKey, descending, onSort }: { label: string; sortKey: ProjectSortKey; activeKey: ProjectSortKey; descending: boolean; onSort: (key: ProjectSortKey) => void }) {
  const active = sortKey === activeKey;
  return <th aria-sort={active ? descending ? "descending" : "ascending" : undefined}><button type="button" className="sort-heading" onClick={() => onSort(sortKey)}>{label}<span aria-hidden="true">{active ? descending ? "↓" : "↑" : "↕"}</span></button></th>;
}

function Empty({ label }: { label: string }) { return <p className="empty">{label}</p>; }

function PagedTable({ t, children }: { t: (key: MessageKey) => string; children: ReactElement<{ children?: ReactNode }> }) {
  const [size, setSize] = useState<10 | 25 | 50 | "all">(10);
  const [requestedPage, setRequestedPage] = useState(0);
  const sections = Children.toArray(children.props.children);
  const body = sections.find(section => isValidElement<{ children?: ReactNode }>(section) && section.type === "tbody") as ReactElement<{ children?: ReactNode }> | undefined;
  const rows = body ? Children.toArray(body.props.children) : [];
  const pageCount = size === "all" ? 1 : Math.max(1, Math.ceil(rows.length / size));
  const page = Math.min(requestedPage, pageCount - 1);
  const visible = size === "all" ? rows : rows.slice(page * size, (page + 1) * size);
  const table = body ? cloneElement(children, undefined, ...sections.map(section => section === body ? cloneElement(body, undefined, ...visible) : section)) : children;
  return <><div className="table-scroll">{table}</div>{rows.length > 10 && <div className="page-controls"><label>{t("rowsPerPage")}<select value={size} onChange={event => { setSize(event.target.value === "all" ? "all" : Number(event.target.value) as 10 | 25 | 50); setRequestedPage(0); }}><option value="10">10</option><option value="25">25</option><option value="50">50</option><option value="all">{t("all")}</option></select></label>{size !== "all" && <><button className="ghost" disabled={page === 0} onClick={() => setRequestedPage(page - 1)}>{t("previous")}</button><span>{page * size + 1}–{Math.min((page + 1) * size, rows.length)} / {rows.length}</span><button className="ghost" disabled={page + 1 >= pageCount} onClick={() => setRequestedPage(page + 1)}>{t("next")}</button></>}</div>}</>;
}

function Field({ name, label, type = "text", required = false, defaultValue }: { name: string; label: string; type?: string; required?: boolean; defaultValue?: string }) {
  return <label>{label}<input name={name} type={type} required={required} defaultValue={defaultValue} /></label>;
}

function GuidedField({ id, label, help, helpLabel, children }: { id: string; label: string; help: string; helpLabel: string; children: ReactNode }) {
  return <div className="guided-field"><div className="guided-label"><label htmlFor={id}>{label}</label><details className="guided-help"><summary>{helpLabel}</summary><p>{help}</p></details></div>{children}</div>;
}

function ProjectConfigReadOnly({ config, t }: { config: Record<string, unknown>; t: (key: MessageKey) => string }) {
  const flatten = (value: unknown, prefix: string): Array<[string, unknown]> => {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) => flatten(child, prefix ? `${prefix}.${key}` : key));
    }
    return [[prefix, value]];
  };
  const sections = Object.entries(config).map(([section, value]) => [section, flatten(value, section)] as const);
  const typeOf = (key: string, value: unknown) => {
    if (commonSettings.some(item => item.key === key && (item.kind === "forge" || item.kind === "executor"))) return t("settingEnum");
    if (Array.isArray(value)) return t("settingList");
    if (typeof value === "boolean") return t("settingBoolean");
    if (typeof value === "number") return Number.isInteger(value) ? t("settingInteger") : t("settingNumber");
    if (/(?:^|\.)(?:repo_path|root|store_root|db_path|export_jsonl|html_out|ca_file)$/.test(key)) return t("settingPath");
    return t("settingText");
  };
  const shown = (value: unknown) => value == null || value === "" ? "—" :
    Array.isArray(value) || typeof value === "object" ? JSON.stringify(value) : String(value);
  return <section className="panel" id="project-settings">
    <h2>{t("projectSettings")}</h2><p className="muted">{t("projectSettingsHelp")}</p>
    <div className="setting-groups">{sections.map(([section, rows]) => <details key={section}>
      <summary>{section} <span className="muted">({rows.length})</span></summary>
      <div className="setting-list">{rows.map(([key, value]) => {
        const known = commonSettings.find(item => item.key === key);
        return <div className="setting-row" key={key}>
          <div><strong>{known ? t(known.label) : key.slice(section.length + 1).replaceAll("_", " ")}</strong><small>{key}</small></div>
          <code>{shown(value)}</code>
          <details><summary aria-label={`${t("settingHelp")} ${key}`}>{t("settingHelp")}</summary>
            <p>{typeOf(key, value)}{known?.kind === "positive" ? ` · ${t("settingPositive")}` : known?.kind === "forge" ? " · gitlab, github, gitea" : known?.kind === "executor" ? " · opencode, pi, codex, qwen" : known?.kind === "runtime" ? ` · ${t("settingRuntimeDomain")}` : ""}</p>
            <p>{known ? t(known.help) : t("settingGeneralHelp")}</p>
          </details>
        </div>;
      })}</div>
    </details>)}</div>
  </section>;
}

function GuidedConfigForm({ config, t, onSubmit, disabled }: { config: Record<string, unknown>; t: (key: MessageKey) => string; onSubmit: (event: FormEvent<HTMLFormElement>) => void; disabled: boolean }) {
  const read = (key: string) => {
    const value = key.split(".").reduce<unknown>((current, part) =>
      current && typeof current === "object" ? (current as Record<string, unknown>)[part] : undefined, config);
    return value === undefined || value === null ? "" : String(value);
  };
  const [key, setKey] = useState(commonSettings[0].key);
  const [value, setValue] = useState(read(commonSettings[0].key));
  const chosen = commonSettings.find(item => item.key === key) || commonSettings[0];
  return <form className="inline-form config-form" onSubmit={onSubmit}>
    <label>{t("commonSetting")}<select name="key" value={key} onChange={event => { setKey(event.target.value); setValue(read(event.target.value)); }}>{commonSettings.map(item => <option key={item.key} value={item.key}>{t(item.label)}</option>)}</select></label>
    <label>{t("configValue")}{chosen.kind === "forge" || chosen.kind === "executor" ? <select name="value" value={value} onChange={event => setValue(event.target.value)}>{(chosen.kind === "forge" ? ["gitlab", "github", "gitea"] : ["opencode", "pi", "codex", "qwen"]).map(item => <option key={item} value={item}>{item}</option>)}</select> : <input name="value" type={chosen.kind === "positive" ? "number" : "text"} min={chosen.kind === "positive" ? "1" : undefined} step={chosen.kind === "positive" ? "1" : undefined} value={value} onChange={event => setValue(event.target.value)} required />}</label>
    <p className="setting-editor-help">{t(chosen.help)} <span className="muted">{chosen.kind === "positive" ? t("settingPositive") : chosen.kind === "runtime" ? t("settingRuntimeDomain") : ""}</span></p>
    <button className="primary" disabled={disabled}>{t("stageChange")}</button>
  </form>;
}

function RunTable({ runs, t, formatDate, onOpen, emptyLabel, paged = false }: { runs: Run[]; t: (key: MessageKey) => string; formatDate: (value: string) => string; onOpen: (id: string) => void; emptyLabel?: string; paged?: boolean }) {
  if (!runs.length) return <Empty label={emptyLabel || t("noJobs")} />;
  const table = <table><thead><tr><th>{t("ticket")}</th><th>{t("status")}</th><th>{t("stage")}</th><th>{t("updated")}</th><th>{t("actions")}</th></tr></thead><tbody>{runs.map(run => <tr key={run.run_id}><td className="strong">#{run.ticket_iid}</td><td><span className={`status status-${run.lifecycle}`}>{displayCode(run.lifecycle, lifecycleLabels, t)}</span></td><td>{displayCode(run.stage, stageLabels, t)}</td><td>{formatDate(run.updated_at)}</td><td><button className="text-button" onClick={() => onOpen(run.run_id)}>{t("view")} →</button></td></tr>)}</tbody></table>;
  return paged ? <PagedTable t={t}>{table}</PagedTable> : <div className="table-scroll">{table}</div>;
}

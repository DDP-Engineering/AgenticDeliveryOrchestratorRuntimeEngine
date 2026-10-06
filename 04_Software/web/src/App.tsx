/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { Children, cloneElement, isValidElement, useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactElement, type ReactNode } from "react";
import { aggregateMetrics, aggregateUsage, type Metrics, type Usage } from "./metrics";
import { messages, type Locale, type MessageKey } from "./i18n";
import { ModelConnection } from "./ModelConnection";
import { RepositoryConnection } from "./RepositoryConnection";
import { ReadinessEvidence } from "./ReadinessEvidence";
import { readReadiness, type ProjectReadiness } from "./readiness";
import { AuditHistory } from "./AuditHistory";
import { auditCopy } from "./auditCopy";
import { auditPolicyPayload } from "./auditPolicy";
import { ApiError, describeError } from "./errors";
import { startVisiblePolling } from "./polling";
import { formatRoute, normalizeRoute, parseRoute, type ProjectTab, type Route } from "./routes";
import { editValue, hasDefault, settingGroups, settingRows, type SettingMeta, type SettingRow, settingValue, validSettingCatalog, validPendingConfig, type PendingConfig } from "./settings";
import { settingHelp } from "./settingHelp";
import { settingsCopy, settingLabel } from "./settingsCopy";
import { ImportWizard } from "./ImportWizard";
import { PortableSettings } from "./PortableSettings";
import { TransferWizard } from "./TransferWizard";
import { readStatistics, readConsumption } from "./statistics";
import { StatisticsEvidence, TrendEvidence } from "./StatisticsEvidence";
import { statisticsCopy } from "./statisticsCopy";
import { JobWorkspace } from "./JobWorkspace";
import { jobCopy } from "./jobCopy";
import { UserCreation, AccountAccessEditor, AccessReview, validAccount, type Account } from "./UserCreation";
import { userCopy } from "./userCopy";
import { DashboardShell, NavigationLink, type ShellLink } from "./DashboardShell";
import { DataFeedback, ProjectEmpty, StatusBadge, DeliveryGlossary, type DataState, type ScopedState } from "./Presentation";

type User = { id: number; username: string; role: "admin" | "developer"; disabled: boolean; password_change_required?: boolean; projects?: string[] };
type AccountUser = User & Account;
type Session = { user: User; csrf: string };
type Preferences = { language: Locale | null; theme: "light" | "dark" | "system" | null };
type Project = { display_name: string; pickup_state: string; verification: { status: string; checked_at?: string | null; revision?: string | null }; validation: { structural_valid: boolean }; id: string; name: string; description: string; platform: string; repo: string; runtime: string; executor: string; readiness: string; last_activity: string | null; paused: boolean; archived: boolean; runs: number; invalid_runs: string[] };
type Config = { config: Record<string, unknown>; revision: string; issues: string[]; local_endpoint_timeout_seconds?: number | null; local_endpoint?: { protocol: string; auth_env: string | null } | null; settings?: SettingMeta[] };
type Operation = { id: number; status: string; result?: string; action?: string };
type Price = { id: number; executor: string; model: string; effective_from: string; input_usd_per_million: string; output_usd_per_million: string };
type Page = "overview" | "projects" | "createProject" | "importProject" | "projectDetails" | "jobs" | "metrics" | "administration" | "adminUsers" | "adminAudit" | "settings";
type MetricsTab = "summary" | "usage" | "quality" | "trends" | "projects";
type ProjectSortKey = "name" | "repo" | "readiness" | "runs" | "last_activity";
const metricsTabLabels: Record<MetricsTab, MessageKey> = {
  summary: "metricsTabSummary", usage: "metricsTabUsage", quality: "metricsTabQuality",
  trends: "metricsTabTrends", projects: "metricsTabProjects",
};
type WorkerStatus = "checking" | "ready" | "unavailable" | "error";
type StorageStatus = { threshold_bytes: number; low: boolean; volumes: Array<{ scope: "home" | "project"; project: string | null; free_bytes: number; total_bytes: number; low: boolean }> };
type AuditPolicy = { retention_days: number | null; max_bytes: number | null };

const localeNames: Record<Locale, string> = { en: "English", fr: "Français", de: "Deutsch", ro: "Română" };
const initialLocale = (): Locale => {
  const saved = localStorage.getItem("adore-language") as Locale | null;
  if (saved && saved in messages) return saved;
  const browser = navigator.language.slice(0, 2) as Locale;
  return browser in messages ? browser : "en";
};

async function request<T>(path: string, method = "GET", body?: unknown, csrf?: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method, credentials: "same-origin", cache: "no-store",
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiError("network_error", String((cause as Error)?.message ?? cause));
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload?.detail;
    if (typeof detail?.code === "string") throw new ApiError(detail.code, typeof detail.message === "string" ? detail.message : "");
    throw new ApiError("request_failed", `HTTP ${response.status}`);
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new ApiError("unexpected_response", `${path} (HTTP ${response.status})`);
  }
  return response.json() as Promise<T>;
}


export default function App() {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [theme, setTheme] = useState(localStorage.getItem("adore-theme") || "system");
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<Page>("overview");
  const [viewRefresh, setViewRefresh] = useState(0);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectSortKey, setProjectSortKey] = useState<ProjectSortKey>("name");
  const [projectSortDescending, setProjectSortDescending] = useState(false);
  const [selected, setSelected] = useState("");
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
  const [users, setUsers] = useState<AccountUser[]>([]);
  const [auditPolicy, setAuditPolicy] = useState<AuditPolicy | null>(null);
  const [adminMenuOpen, setAdminMenuOpen] = useState(true);
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus>("checking");
  const [storageStatus, setStorageStatus] = useState<StorageStatus | null>(null);
  const [storageError, setStorageError] = useState(false);
  const [projectReadiness, setProjectReadiness] = useState<ProjectReadiness | null>(null);
  const [about, setAbout] = useState<{ name: string; version: string; license: string; license_text: string; third_party_notices: string } | null>(null);
  const [error, setError] = useState<unknown>("");
  const [passwordSession, setPasswordSession] = useState<Session | null>(null);
  const [projectTab, setProjectTab] = useState<ProjectTab>("overview");
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [deleteName, setDeleteName] = useState("");
  const [projectsLoaded, setProjectsLoaded] = useState(false);
  const [configState, setConfigState] = useState<ScopedState>({ key: "", state: "loading" });
  const [usersState, setUsersState] = useState<DataState>("loading");
  const [jobScope, setJobScope] = useState("");
  const [requestedRun, setRequestedRun] = useState("");
  const [projectsState, setProjectsState] = useState<DataState>("loading");
  const [selectedState, setSelectedState] = useState<ScopedState>({ key: "", state: "loading" });
  const [globalState, setGlobalState] = useState<ScopedState>({ key: "", state: "loading" });
  const [usageState, setUsageState] = useState<ScopedState>({ key: "", state: "loading" });
  const [globalUsageState, setGlobalUsageState] = useState<ScopedState>({ key: "", state: "loading" });
  const [routeReady, setRouteReady] = useState(false);
  const routedProject = useRef<string | null>(null);
  const preserveError = useRef(false);
  const [notice, setNotice] = useState("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const enrollmentGuard = useRef<(() => boolean) | null>(null);
  const [resetTarget, setResetTarget] = useState<number | null>(null);
  const aboutTrigger = useRef<HTMLButtonElement>(null);
  const aboutClose = useRef<HTMLButtonElement>(null);
  const selectedMetricsRequest = useRef(0);
  const projectsRequest = useRef(0);
  const globalMetricsRequest = useRef(0);
  const usageRequest = useRef(0);
  const configRequest = useRef(0);
  const configMutation = useRef(false);
  const configView = useRef("");
  configView.current = `${page}:${selected}`;
  const [configBusy, setConfigBusy] = useState(false);
  const configDiscardFocus = useRef<(() => void) | null>(null);
  useEffect(() => {
    if (!configBusy) { configDiscardFocus.current?.(); configDiscardFocus.current = null; }
  }, [configBusy]);
  const [pendingReady, setPendingReady] = useState(false);
  const [pendingReadFailed, setPendingReadFailed] = useState(false);
  const readinessRequest = useRef(0);
  const preferenceRequest = useRef({ language: 0, theme: 0 });
  const viewGeneration = useRef(0);

  const closeAbout = () => {
    setAbout(null);
    window.requestAnimationFrame(() => aboutTrigger.current?.focus());
  };

  const t = (key: MessageKey) => messages[locale][key];
  const jc = jobCopy[locale];
  const verificationLabel = (item: Project) => !item.validation.structural_valid ? jc.invalid : ({ verified: jc.passed, partial: jc.partial, failed: jc.checkFailed, stale: jc.stale, invalid: jc.invalid, unverified: jc.unverified }[item.verification.status] || jc.unverified);
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
  const projectTabs: ProjectTab[] = isAdmin ? ["overview", "configuration", "prices", "access", "history"] : ["overview", "configuration", "history"];
  const onProjectTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, tab: ProjectTab) => {
    const current = projectTabs.indexOf(tab);
    const next = event.key === "ArrowRight" ? (current + 1) % projectTabs.length :
      event.key === "ArrowLeft" ? (current + projectTabs.length - 1) % projectTabs.length :
      event.key === "Home" ? 0 : event.key === "End" ? projectTabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault();
    setProjectTab(projectTabs[next]);
    document.getElementById(`project-tab-${projectTabs[next]}`)?.focus();
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
  useEffect(() => {
    if (selectedProject?.verification.status === "stale") setProjectReadiness(null);
  }, [selectedProject?.verification.status]);
  const projectConfig = configScope === selected ? config : null;
  const configDataState = configState.key === selected ? configState.state : "loading";
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
  const statisticsText = statisticsCopy[locale];
  const authorizedMetricsKey = JSON.stringify(projects.map(project => [project.id, project.name]).sort());
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
  const selectedKey = JSON.stringify([selected, metricSuffix, authorizedMetricsKey]);
  const globalMetricKey = JSON.stringify([metricSuffix, authorizedMetricsKey]);
  const globalUsageKey = JSON.stringify([usageSuffix, authorizedMetricsKey]);
  const scopedUsageKey = JSON.stringify([selected, usageSuffix, authorizedMetricsKey]);
  const selectedDataState = selectedState.key === selectedKey ? selectedState.state : "loading";
  const metricDataState = allProjectScope ? globalState.key === globalMetricKey ? globalState.state : "loading" : selectedDataState;
  const usageDataState = allProjectScope ? globalUsageState.key === globalUsageKey ? globalUsageState.state : "loading" : usageState.key === scopedUsageKey ? usageState.state : "loading";
  const canonicalScopes = (items: Array<Metrics | Usage>) => items.map(item => JSON.stringify([item.scope?.project_ids, item.scope?.mode, item.scope?.interval, item.scope?.from, item.scope?.to, item.scope?.timezone, item.scope?.granularity, item.scope?.interval_seconds])).sort().join("\0");
  const metricScopeItems = allProjectScope ? Object.values(allMetrics ?? {}) : selectedMetrics ? [selectedMetrics] : [];
  const usageScopeItems = allProjectScope ? Object.values(allUsage ?? {}) : selectedUsage ? [selectedUsage] : [];
  const reportingDataState: DataState = metricDataState === "error" || usageDataState === "error" ? "error" :
    metricDataState !== "ready" || usageDataState !== "ready" ? "loading" :
    canonicalScopes(metricScopeItems) === canonicalScopes(usageScopeItems) ? "ready" : "error";
  const metrics = reportingDataState !== "ready" ? null : allProjectScope ? (allMetrics ? aggregateMetrics(Object.values(allMetrics), metricTimezone, metricFrom, metricTo) : null) :
    metricsScope === selected ? selectedMetrics : null;
  const metricsEmpty = metrics !== null && !((metrics.totals.runs || 0) > 0);
  const usage = reportingDataState !== "ready" ? null : allProjectScope ? (allUsage ? aggregateUsage(Object.values(allUsage)) : null) : usageScope === selected ? selectedUsage : null;
  const scopedUsageRows = allProjectScope ? Object.entries(allUsage || {}) : selectedUsage && selectedProject ? [[selectedProject.name, selectedUsage] as [string, Usage]] : [];
  const globalTokensIn = metrics?.totals.tokens_in;
  const globalTokensOut = metrics?.totals.tokens_out;
  const globalReportedCost = globalRows.reduce((sum, [, item]) => sum + (item.totals.cost_usd || 0), 0);
  const globalReviewRounds = globalRows.reduce((sum, [, item]) => sum + item.runs.reduce((runSum, run) => runSum + Number(run.review_rounds || 0), 0), 0);
  const repositoryRows = Object.entries(scopeProjects.reduce<Record<string, {
    projects: number; jobs: number; tokensIn: number | null; tokensOut: number | null; mrRevisions: number; pipelineRepairs: number;
    reported: number; estimated: number; hasReported: boolean; hasEstimated: boolean;
  }>>((acc, project) => {
    if (!project.repo.trim()) return acc;
    const row = acc[project.repo] || (acc[project.repo] = {
      projects: 0, jobs: 0, tokensIn: null, tokensOut: null, mrRevisions: 0, pipelineRepairs: 0,
      reported: 0, estimated: 0, hasReported: false, hasEstimated: false,
    });
    const item = globalRows.find(([name]) => name === project.name)?.[1];
    row.projects += 1;
    row.jobs += item?.totals.runs || 0;
    if (item?.totals.tokens_in != null) row.tokensIn = (row.tokensIn || 0) + item.totals.tokens_in;
    if (item?.totals.tokens_out != null) row.tokensOut = (row.tokensOut || 0) + item.totals.tokens_out;
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
  const formatNumber = (value: number | null | undefined) => value == null ? "—" : new Intl.NumberFormat(locale).format(value);
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
      catch (cause) { setError(cause); }
      if (current.user.password_change_required) setPasswordSession(current);
      else setSession(current);
    }).catch(() => setSession(null)).finally(() => setLoading(false));
  }, []);

  const updatePreference = (key: "language" | "theme", value: string) => {
    const previous = key === "language" ? locale : theme;
    if (key === "language") setLocale(value as Locale);
    else setTheme(value);
    const account = session ?? passwordSession;
    if (!account) return;
    const generation = viewGeneration.current;
    const revision = ++preferenceRequest.current[key];
    void request<Preferences>("/me/preferences", "PATCH", { [key]: value }, account.csrf)
      .catch(cause => {
        if (generation !== viewGeneration.current || revision !== preferenceRequest.current[key]) return;
        if (key === "language") setLocale(previous as Locale);
        else setTheme(previous);
        setError(cause);
      });
  };

  const refreshProjects = useCallback(async () => {
    const generation = viewGeneration.current;
    const revision = ++projectsRequest.current;
    if (!projectsLoaded) setProjectsState("loading");
    try {
      const items = await request<Project[]>("/projects");
      if (generation !== viewGeneration.current || revision !== projectsRequest.current) return;
      if (!Array.isArray(items) || items.some(item => !item || typeof item.id !== "string" || typeof item.name !== "string" ||
        typeof item.repo !== "string" || typeof item.display_name !== "string" || !/^[a-f0-9]{32}$/.test(item.id) ||
        typeof item.readiness !== "string" || typeof item.paused !== "boolean" || typeof item.archived !== "boolean" ||
        !item.verification || !["unverified", "stale", "failed", "partial", "verified"].includes(item.verification.status) ||
        !item.validation || typeof item.validation.structural_valid !== "boolean" ||
        item.verification.checked_at != null && (typeof item.verification.checked_at !== "string" || !Number.isFinite(Date.parse(item.verification.checked_at))) ||
        item.verification.revision != null && (typeof item.verification.revision !== "string" || !/^[a-f0-9]{64}$/.test(item.verification.revision)) ||
        item.last_activity !== null && (typeof item.last_activity !== "string" || !Number.isFinite(Date.parse(item.last_activity))) ||
        !Number.isSafeInteger(item.runs) || item.runs < 0) || new Set(items.map(item => item.id)).size !== items.length) throw new ApiError("unexpected_response");
      setProjects(items);
      setSelected(current => items.some(item => item.id === current) || routedProject.current ? current : (items[0]?.id || ""));
      setProjectsLoaded(true); setProjectsState("ready"); setLastRefresh(new Date());
    } catch (cause) {
      if (generation === viewGeneration.current && revision === projectsRequest.current) {
        setProjectsState("error"); setError(cause);
      }
    }
  }, [projectsLoaded]);

  useEffect(() => {
    if (!session) return;
    void refreshProjects();
    const stopPolling = startVisiblePolling(() => refreshProjects(), 15000);
    return () => stopPolling();
  }, [session, refreshProjects]);

  useEffect(() => { setMetrics(null); setAllMetrics(null); }, [metricSuffix]);

  useEffect(() => { setUsage(null); setAllUsage(null); }, [usageSuffix, selected]);

  useEffect(() => { readinessRequest.current += 1; setProjectReadiness(null); }, [selected, session?.user.id]);

  useEffect(() => {
    if (!session || !selected || page !== "metrics" || projectsState !== "ready" || !projects.some(item => item.id === selected)) return;
    let revision = ++usageRequest.current;
    const generation = viewGeneration.current;
    const key = JSON.stringify([selected, usageSuffix, authorizedMetricsKey]);
    const current = () => generation === viewGeneration.current && revision === usageRequest.current;
    const refresh = async () => {
      revision = ++usageRequest.current;
      const sequence = revision;
      const live = () => current() && sequence === usageRequest.current;
      setUsageState({ key, state: "loading" });
      if (isAdmin) setGlobalUsageState({ key: globalUsageKey, state: "loading" });
      const scoped = async () => {
        try {
          const value = await request<Usage>("/projects/" + encodeURIComponent(selected) + "/usage" + usageSuffix);
          readConsumption(value, selected, { from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }, isAdmin);
          if (live()) { setUsage(value); setUsageScope(selected); setUsageState({ key, state: "ready" }); }
        } catch (cause) { if (live()) { setUsage(null); setUsageState({ key, state: "error" }); setError(cause); } }
      };
      const global = async () => {
        try {
          const value = await request<Record<string, Usage>>("/usage" + usageSuffix);
          if (!value || Array.isArray(value)) throw new ApiError("unexpected_response");
          if (Object.keys(value).sort().join("\0") !== projects.map(item => item.name).sort().join("\0")) throw new ApiError("unexpected_response");
          for (const project of projects) readConsumption(value[project.name], project.id, { from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }, true);
          if (live()) { setAllUsage(value); setGlobalUsageState({ key: globalUsageKey, state: "ready" }); }
        } catch (cause) { if (live()) { setAllUsage(null); setGlobalUsageState({ key: globalUsageKey, state: "error" }); setError(cause); } }
      };
      await Promise.all([scoped(), ...(isAdmin ? [global()] : [])]);
    };
    void refresh();
    const stopPolling = startVisiblePolling(() => void refresh(), 30000);
    return () => { usageRequest.current += 1; stopPolling(); };
  }, [session, selected, page, usageSuffix, isAdmin, usageRefresh, authorizedMetricsKey, projectsState]);

  const refreshSelected = useCallback(async () => {
    const revision = ++selectedMetricsRequest.current;
    if (!selected || !session || page !== "metrics" || projectsState !== "ready" || !projects.some(item => item.id === selected)) { setMetrics(null); return; }
    const generation = viewGeneration.current;
    const key = JSON.stringify([selected, metricSuffix, authorizedMetricsKey]);
    setSelectedState({ key, state: "loading" });
    try {
      const metricData = await request<Metrics>(`/projects/${encodeURIComponent(selected)}/metrics${metricSuffix}`);
      if (generation !== viewGeneration.current || revision !== selectedMetricsRequest.current) return;
      readStatistics(metricData, selected, { from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }, isAdmin);
      setSelectedState({ key, state: "ready" });
      setMetrics(metricData); setMetricsScope(selected);
      setLastRefresh(new Date());
    } catch (cause) {
      if (generation === viewGeneration.current && revision === selectedMetricsRequest.current) {
        setSelectedState({ key, state: "error" }); setMetrics(null); setError(cause);
      }
    }
  }, [selected, session, metricSuffix, page, authorizedMetricsKey, projectsState]);

  useEffect(() => {
    void refreshSelected();
    const stopPolling = startVisiblePolling(() => void refreshSelected(), 15000);
    return () => { selectedMetricsRequest.current += 1; stopPolling(); };
  }, [refreshSelected]);

  useEffect(() => {
    if (page === "adminUsers" && isAdmin) {
      const generation = viewGeneration.current;
      let active = true;
      setUsersState("loading");
      request<AccountUser[]>("/users").then(value => {
        if (!Array.isArray(value) || value.some(item => !validAccount(item) || typeof item.disabled !== "boolean") || new Set(value.map(item => item.id)).size !== value.length) throw new ApiError("unexpected_response");
        if (active && generation === viewGeneration.current) { setUsers(value); setUsersState("ready"); }
      }).catch(cause => { if (active && generation === viewGeneration.current) { setUsersState("error"); setError(cause); } });
      return () => { active = false; };
    }
    if (page === "administration" && isAdmin) {
      const generation = viewGeneration.current;
      request<AuditPolicy>("/audit-policy").then(value => { if (generation === viewGeneration.current) setAuditPolicy(value); }).catch(cause => setError(cause));
    }
    if (page === "projectDetails" && selected) {
      const generation = viewGeneration.current;
      const revision = ++configRequest.current;
      setConfigState({ key: selected, state: "loading" });
      setPendingReadFailed(false); setPendingReady(false);
      setConfig(null); setConfigScope(""); setPendingConfig(null); setPendingConfigScope(""); setPrices([]); setPricesScope("");
      request<Config>("/projects/" + encodeURIComponent(selected) + "/config").then(value => {
        if (!value || !value.config || typeof value.revision !== "string" || !Array.isArray(value.issues) || !validSettingCatalog(value.settings)) throw new ApiError("unexpected_response");
        if (generation === viewGeneration.current && revision === configRequest.current) { setConfig(value); setConfigScope(selected); setConfigState({ key: selected, state: "ready" }); }
      }).catch(cause => { if (generation === viewGeneration.current && revision === configRequest.current) { setConfigState({ key: selected, state: "error" }); setError(cause); } });
      if (isAdmin) {
        request<PendingConfig | null>(`/projects/${encodeURIComponent(selected)}/config/pending`).then(value => { if (!validPendingConfig(value)) throw new ApiError("unexpected_response"); if (generation === viewGeneration.current && revision === configRequest.current) { setPendingConfig(value); setPendingConfigScope(selected); setPendingReady(true); } }).catch(cause => { if (generation === viewGeneration.current && revision === configRequest.current) { setPendingConfig(null); setPendingReadFailed(true); setError(cause); } });
        request<Price[]>(`/projects/${encodeURIComponent(selected)}/prices`).then(value => { if (generation === viewGeneration.current && revision === configRequest.current) { setPrices(value); setPricesScope(selected); } }).catch(cause => { if (generation === viewGeneration.current && revision === configRequest.current) setError(cause); });
      }
    }
  }, [page, isAdmin, selected, viewRefresh]);

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
    const stopPolling = startVisiblePolling(() => void check(), 5000);
    return () => { active = false; stopPolling(); };
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
    const stopPolling = startVisiblePolling(() => void check(), 30000);
    return () => { active = false; stopPolling(); };
  }, [page, isAdmin]);

  useEffect(() => {
    if (page !== "metrics" || !isAdmin || projectsState !== "ready") return;
    const refresh = () => {
      const revision = ++globalMetricsRequest.current;
      const generation = viewGeneration.current;
      setGlobalState({ key: globalMetricKey, state: "loading" });
      return request<Record<string, Metrics>>(`/metrics${metricSuffix}`).then(value => {
        if (!value || Array.isArray(value)) throw new ApiError("unexpected_response");
        if (Object.keys(value).sort().join("\0") !== projects.map(item => item.name).sort().join("\0")) throw new ApiError("unexpected_response");
        for (const project of projects) readStatistics(value[project.name], project.id, { from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }, true);
        if (generation === viewGeneration.current && revision === globalMetricsRequest.current) { setAllMetrics(value); setGlobalState({ key: globalMetricKey, state: "ready" }); }
      }).catch(cause => { if (generation === viewGeneration.current && revision === globalMetricsRequest.current) { setAllMetrics(null); setGlobalState({ key: globalMetricKey, state: "error" }); setError(cause); } });
    };
    void refresh();
    const stopPolling = startVisiblePolling(() => void refresh(), 30000);
    return () => { globalMetricsRequest.current += 1; stopPolling(); };
  }, [page, isAdmin, metricSuffix, usageRefresh, authorizedMetricsKey, projectsState]);

  useEffect(() => {
    if (!operation || !["pending", "running"].includes(operation.status)) return;
    const stopPolling = startVisiblePolling(async () => {
      const generation = viewGeneration.current;
      try {
        const current = await request<Operation>(`/operations/${operation.id}`);
        if (generation !== viewGeneration.current) return;
        setOperation(current);
        if (!["pending", "running"].includes(current.status)) {
          if (current.action === "delete") await refreshProjects();
          else { await refreshSelected(); await refreshProjects(); setViewRefresh(value => value + 1); }
        }
      } catch (cause) {
        if (generation === viewGeneration.current) setError(cause);
      }
    }, 2000);
    return () => stopPolling();
  }, [operation?.id, operation?.status, refreshSelected, refreshProjects]);

  useEffect(() => {
    if (preserveError.current) { preserveError.current = false; return; }
    setError("");
  }, [page]);


  const openProject = (id: string) => {
    setRequestedRun("");
    setSelected(id); setProjectTab("overview"); setPage("projectDetails");
  };

  const reportingRoute = metricFrom || metricTo || metricTimezone !== "UTC" || metricGranularity !== "day" ? { reporting: { from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity } } : {};
  const currentRoute = (): Route => {
    switch (page) {
      case "overview": return jobScope ? { view: "overview", project: jobScope } : { view: "overview" };
      case "projectDetails": return selected ? { view: "projectDetails", project: selected, tab: projectTab } : { view: "projects" };
      case "jobs": return { view: "jobs", ...reportingRoute, ...(jobScope ? { project: jobScope } : {}), ...(jobScope && requestedRun ? { run: requestedRun } : {}) };
      case "metrics": return { view: "metrics", ...reportingRoute, ...(selected && !(isAdmin && metricAllProjects) ? { project: selected } : {}), ...(metricsTab !== "summary" ? { tab: metricsTab } : {}) };
      default: return { view: page };
    }
  };

  const applyRoute = (route: Route) => {
    setRequestedRun(route.view === "jobs" ? route.run || "" : "");
    setPage(route.view); setMenuOpen(false);
    if (route.view === "jobs" || route.view === "overview") setJobScope(route.project || "");
    if ("project" in route && route.project) { routedProject.current = route.project; setSelected(route.project); }
    if (route.view === "projectDetails") setProjectTab(route.tab);
    if (route.view === "metrics" || route.view === "jobs") {
      setMetricFrom(route.reporting?.from ?? ""); setMetricTo(route.reporting?.through ?? "");
      setMetricTimezone(route.reporting?.timezone ?? "UTC"); setMetricGranularity((route.reporting?.granularity ?? "day") as "day" | "week" | "month");
    }
    if (route.view === "metrics") { setMetricsTab(route.tab ?? "summary"); setMetricAllProjects(!route.project); }
  };

  const applyLocation = () => {
    const { route, replaced } = normalizeRoute(parseRoute(window.location.pathname, window.location.search), { isAdmin });
    if (replaced) window.history.replaceState(null, "", formatRoute(route));
    applyRoute(route);
  };

  useEffect(() => {
    if (!session) { setRouteReady(false); return; }
    applyLocation();
    setRouteReady(true);
    const onPop = () => {
      if (enrollmentGuard.current && !enrollmentGuard.current()) {
        window.history.pushState(null, "", formatRoute({ view: "createProject" }));
        return;
      }
      applyLocation();
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [session?.user.id]);

  useEffect(() => {
    if (!session || !routeReady) return;
    const target = formatRoute(currentRoute());
    const here = window.location.pathname + window.location.search;
    if (target === here) return;
    if (target.split("?")[0] === window.location.pathname) window.history.replaceState(null, "", target);
    else window.history.pushState(null, "", target);
  }, [session, routeReady, page, selected, projectTab, metricsTab, metricAllProjects, requestedRun, jobScope, isAdmin, metricFrom, metricTo, metricTimezone, metricGranularity]);

  useEffect(() => {
    const wanted = routedProject.current;
    if (!wanted || !projectsLoaded) return;
    routedProject.current = null;
    const match = projects.find(item => item.id === wanted || item.name === wanted);
    if (match) { setSelected(match.id); if (page === "jobs" || page === "overview") setJobScope(match.id); return; }
    preserveError.current = ["projectDetails", "jobs", "overview"].includes(page);
    setRequestedRun(""); setJobScope("");
    setSelected(projects[0]?.id || "");
    if (page === "projectDetails") { setPage("projects"); window.history.replaceState(null, "", "/projects"); }
    setError(new ApiError("project_not_found"));
  }, [projects, projectsLoaded]);

  const clearPrivateView = () => {
    viewGeneration.current += 1;
    setPage("overview"); setJobScope(""); setMenuOpen(false);
    selectedMetricsRequest.current += 1;
    globalMetricsRequest.current += 1;
    usageRequest.current += 1;
    configRequest.current += 1;
    preferenceRequest.current.language += 1;
    preferenceRequest.current.theme += 1;
    setProjects([]); setSelected(""); setRequestedRun(""); setUsersState("loading"); setConfigState({ key: "", state: "loading" });
    projectsRequest.current += 1;
    setProjectsState("loading"); setSelectedState({ key: "", state: "loading" }); setGlobalState({ key: "", state: "loading" });
    setUsageState({ key: "", state: "loading" }); setGlobalUsageState({ key: "", state: "loading" });
    setProjectsLoaded(false); setProjectTab("overview"); routedProject.current = null;
    setProjectSortKey("name"); setProjectSortDescending(false);
    setMetrics(null); setAllMetrics(null); setMetricFrom(""); setMetricTo("");
    setMetricAllProjects(true); setMetricsScope(""); setMetricTimezone("UTC"); setMetricGranularity("day"); setMetricsTab("summary");
    setUsage(null); setUsageScope(""); setAllUsage(null); setUsageExecutor(""); setUsageModel("");
    setConfig(null); setPendingConfig(null); setPrices([]);
    setUsers([]); setAuditPolicy(null); setOperation(null);
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
      catch (cause) { setError(cause); }
      clearPrivateView();
      if (saved) applyPreferences(saved);
      if (authenticated.user.password_change_required) setPasswordSession(authenticated);
      else setSession(authenticated);
    }
    catch (cause) { setError(cause); }
  };

  const signOut = async () => {
    if (enrollmentGuard.current && !enrollmentGuard.current()) return;
    try { await request("/session", "DELETE", undefined, (session ?? passwordSession)?.csrf); }
    finally { setSession(null); setPasswordSession(null); clearPrivateView(); window.history.pushState(null, "", "/"); }
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
      await refreshSelected();
    } catch (cause) { setError(cause); }
  };

  const deleteProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setNotice("");
    if (!deleteTarget || !session || !isAdmin || page !== "projectDetails" || deleteTarget.id !== selected || deleteName !== deleteTarget.name || !deleteTarget.archived || !selectedProject?.archived) return;
    try {
      const op = await request<Operation>(`/projects/${encodeURIComponent(deleteTarget.id)}/delete`, "POST",
        { confirm_name: deleteName, idempotency_key: crypto.randomUUID() }, session.csrf);
      setOperation(op);
      setNotice(`${t("projectDeletionQueued")} · #${op.id}`);
      setDeleteTarget(null); setDeleteName("");
    } catch (cause) { setError(cause); }
  };

  useEffect(() => { setDeleteTarget(null); setDeleteName(""); }, [page, selected, projectTab]);

  const setProjectArchive = async (archive: boolean, projectId = selected) => {
    if (!projectId || !session || !isAdmin) return;
    setError(""); setNotice("");
    try {
      await request(`/projects/${encodeURIComponent(projectId)}/${archive ? "archive" : "restore"}`,
        "POST", undefined, session.csrf);
      await refreshProjects();
      setNotice(t(archive ? "projectArchived" : "projectRestored"));
    } catch (cause) { setError(cause); }
  };

  const saveAuditPolicy = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const form = event.currentTarget;
    const values = new FormData(form);
    const days = String(values.get("retention_days") || "").trim();
    const mebibytes = String(values.get("max_mib") || "").trim();
    try {
      const policy = await request<AuditPolicy>("/audit-policy", "PUT", auditPolicyPayload(days, mebibytes), session?.csrf);
      setAuditPolicy(policy);
      form.reset();
      setNotice(`${t("auditPolicySaved")} · ${"deleted_events" in policy ? String(policy.deleted_events) : "0"} ${locale === "ro" ? "evenimente șterse" : locale === "fr" ? "événements supprimés" : locale === "de" ? "Ereignisse gelöscht" : "events deleted"}`);
    } catch (cause) { setError(cause instanceof RangeError ? t("auditInvalidLimit") : cause); }
  };

  const setAccountEnabled = async (userId: number, enabled: boolean) => {
    setError("");
    try {
      await request(`/users/${userId}/${enabled ? "enable" : "disable"}`, "POST", {}, session?.csrf);
      setViewRefresh(value => value + 1);
    } catch (cause) { setError(cause); }
  };

  const resetUserPassword = async (event: FormEvent<HTMLFormElement>, userId: number) => {
    event.preventDefault(); setError("");
    const form = event.currentTarget;
    const replacement = String(new FormData(form).get("replacement") || "");
    try {
      await request(`/users/${userId}/reset-password`, "POST", { replacement }, session?.csrf);
      form.reset(); setResetTarget(null); setNotice(t("passwordResetDone"));
    } catch (cause) { setError(cause); }
  };

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    try {
      await request("/me/password", "POST", Object.fromEntries(new FormData(event.currentTarget)), (session ?? passwordSession)?.csrf);
      clearPrivateView(); setSession(null); setPasswordSession(null); setNotice(t("passwordChanged"));
    } catch (cause) { setError(cause); }
  };

  const stageSetting = async (key: string, value: string): Promise<boolean> => {
    if (!projectConfig || !selected || configMutation.current || projectPendingConfig || pendingReadFailed || !pendingReady) return false;
    const target = selected, generation = viewGeneration.current, revision = configRequest.current, scope = configView.current;
    const current = () => generation === viewGeneration.current && revision === configRequest.current && scope === configView.current;
    configMutation.current = true; setConfigBusy(true); setError("");
    try {
      const staged = await request<PendingConfig>(`/projects/${encodeURIComponent(target)}/config/pending`, "POST", { key, value, revision: projectConfig.revision }, session?.csrf);
      if (!validPendingConfig(staged) || !staged || staged.base_revision !== projectConfig.revision || staged.key !== key) throw new ApiError("unexpected_response");
      if (!current()) return false;
      setPendingConfig(staged); setPendingConfigScope(target); setNotice(t("changeStaged"));
      return true;
    } catch (cause) { if (current()) { setError(cause); if (cause instanceof ApiError && ["unexpected_response", "network_error", "pending_config_exists"].includes(cause.code)) setPendingReadFailed(true); } return false; }
    finally { configMutation.current = false; setConfigBusy(false); }
  };

  const rebuildUsage = async () => {
    setError("");
    try {
      const result = await request<{ projects: number; runs: number; usage_events: number }>(
        "/usage/rebuild", "POST", {}, session?.csrf);
      setNotice(`${t("usageRebuilt")}: ${formatNumber(result.usage_events)}`);
      setUsageRefresh(current => current + 1);
    } catch (cause) { setError(cause); }
  };

  const saveEndpoint = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!projectConfig || !selected || configMutation.current || projectPendingConfig || pendingReadFailed || !pendingReady) return;
    const fields = Object.fromEntries(new FormData(event.currentTarget));
    const target = selected, generation = viewGeneration.current, revision = configRequest.current, scope = configView.current;
    const current = () => generation === viewGeneration.current && revision === configRequest.current && scope === configView.current;
    configMutation.current = true; setConfigBusy(true); setError("");
    try {
      const staged = await request<PendingConfig>(`/projects/${encodeURIComponent(target)}/config/pending`, "POST", {
        key: "container.runtime_env.OPENAI_BASE_URL", value: fields.endpoint,
        model: fields.model, auth_env: fields.auth_env || undefined,
        protocol: fields.protocol, timeout_seconds: Number(fields.timeout_seconds), ca_file: fields.ca_file,
        revision: projectConfig.revision,
      }, session?.csrf);
      if (!validPendingConfig(staged) || !staged || !staged.endpoint || staged.base_revision !== projectConfig.revision || staged.key !== "container.runtime_env.OPENAI_BASE_URL") throw new ApiError("unexpected_response");
      if (current()) { setPendingConfig(staged); setPendingConfigScope(target); setNotice(t("changeStaged")); }
    } catch (cause) { if (current()) { setError(cause); if (cause instanceof ApiError && ["unexpected_response", "network_error", "pending_config_exists"].includes(cause.code)) setPendingReadFailed(true); } }
    finally { configMutation.current = false; setConfigBusy(false); }
  };

  const applyPendingConfig = async () => {
    if (!selected || !projectPendingConfig || !projectConfig || configMutation.current || pendingReadFailed || projectPendingConfig.base_revision !== projectConfig.revision) return;
    const target = selected, candidate = projectPendingConfig, generation = viewGeneration.current, revision = configRequest.current, scope = configView.current;
    const current = () => generation === viewGeneration.current && revision === configRequest.current && scope === configView.current;
    configMutation.current = true; setConfigBusy(true); setError("");
    try {
      await request(`/projects/${encodeURIComponent(target)}/config/apply`, "POST", { candidate_revision: candidate.candidate_revision, base_revision: candidate.base_revision }, session?.csrf);
      if (!current()) return;
      setPendingConfig(null); setNotice(t("changeApplied")); setViewRefresh(value => value + 1);
      await refreshProjects();
    } catch (cause) { if (current()) setError(cause); }
    finally { configMutation.current = false; setConfigBusy(false); }
  };

  const discardPendingConfig = async () => {
    if (!selected || (!projectPendingConfig && !pendingReadFailed) || configMutation.current) return;
    const target = selected, key = projectPendingConfig?.key, generation = viewGeneration.current, revision = configRequest.current, scope = configView.current;
    const current = () => generation === viewGeneration.current && revision === configRequest.current && scope === configView.current;
    configMutation.current = true; setConfigBusy(true); setError("");
    try {
      await request(`/projects/${encodeURIComponent(target)}/config/pending`, "DELETE", undefined, session?.csrf);
      if (current()) { setPendingConfig(null); setPendingReadFailed(false); setPendingReady(true); setNotice(t("changeDiscarded"));
        configDiscardFocus.current = () => {
          if (!current()) return;
          const button = Array.from(document.querySelectorAll<HTMLButtonElement>("button[data-edit-key]")).find(item => item.dataset.editKey === key);
          (button || document.querySelector<HTMLInputElement>(".config-form [name='endpoint']"))?.focus();
        };
      }
    } catch (cause) { if (current()) setError(cause); }
    finally { configMutation.current = false; setConfigBusy(false); }
  };

  const checkProjectReadiness = async () => {
    setError("");
    if (!selected || !isAdmin) return;
    const revision = ++readinessRequest.current;
    const generation = viewGeneration.current;
    setProjectReadiness(null);
    try {
      const result = readReadiness(await request<unknown>(`/projects/${encodeURIComponent(selected)}/readiness-check`, "POST", {}, session?.csrf), selected);
      if (generation === viewGeneration.current && revision === readinessRequest.current) {
        setProjectReadiness(result);
        setProjects(items => items.map(item => item.id === selected ? { ...item, verification: { status: result.status, checked_at: result.checked_at, revision: result.revision } } : item));
      }
    } catch (cause) {
      if (generation === viewGeneration.current && revision === readinessRequest.current) setError(cause);
    }
  };

  const savePrice = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    if (!selected) return;
    const form = event.currentTarget;
    try {
      await request(`/projects/${encodeURIComponent(selected)}/prices`, "POST",
        Object.fromEntries(new FormData(form)), session?.csrf);
      setPrices(await request<Price[]>(`/projects/${encodeURIComponent(selected)}/prices`)); setPricesScope(selected);
      setNotice(t("priceSaved")); form.reset();
    } catch (cause) { setError(cause); }
  };

  if (loading) return <main className="splash" aria-busy="true">ADORE</main>;

  const loginPreferences = <div className="login-preferences"><label>{t("language")}<select aria-label={t("language")} value={locale} onChange={event => updatePreference("language", event.target.value)}>{Object.entries(localeNames).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>{t("theme")}<select aria-label={t("theme")} value={theme} onChange={event => updatePreference("theme", event.target.value)}><option value="system">{t("system")}</option><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option></select></label></div>;

  if (passwordSession) return <main className="login-page">
    <section className="login-card">
      <div className="brand-mark">A</div><p className="eyebrow">ADORE</p><h1>{t("passwordRequiredTitle")}</h1><p className="muted">{t("passwordRequiredReason")}</p>
      {error ? <p className="alert" role="alert">{describeError(locale, error)}</p> : null}
      <form onSubmit={changePassword} className="form-stack"><FormLegend t={t} />
        <label><span>{t("currentPassword")}<RequiredMark /></span><input name="current" type="password" autoComplete="current-password" required autoFocus /></label>
        <label><span>{t("newPassword")}<RequiredMark /></span><input name="replacement" type="password" autoComplete="new-password" minLength={8} required /><small className="field-hint">{t("passwordRule")}</small></label>
        <button className="primary" type="submit">{t("changePassword")}</button>
        <button className="ghost" type="button" onClick={signOut}>{t("logout")}</button>
      </form>
      {loginPreferences}
    </section>
  </main>;

  if (!session) return <main className="login-page">
    <section className="login-card">
      <div className="brand-mark">A</div><p className="eyebrow">ADORE</p><h1>{t("login")}</h1><p className="muted">{t("subtitle")}</p>
      {notice ? <p className="notice" role="status">{notice}</p> : null}
      {error ? <p className="alert" role="alert">{describeError(locale, error)}</p> : null}
      <form onSubmit={signIn} className="form-stack"><FormLegend t={t} />
        <label><span>{t("username")}<RequiredMark /></span><input name="username" autoComplete="username" required autoFocus /></label>
        <label><span>{t("password")}<RequiredMark /></span><input name="password" type="password" autoComplete="current-password" required /></label>
        <button className="primary" type="submit">{t("login")}</button>
      </form>
      {loginPreferences}
    </section>
  </main>;

  const workspaceProps = { locale, projects, scope: jobScope, csrf: session.csrf, request, t, refresh: viewRefresh,
    onScope: (id: string) => { setJobScope(id); if (id) setSelected(id); setRequestedRun(""); },
    onOpen: (id: string, runId: string) => { setSelected(id); setJobScope(id); setRequestedRun(runId); setPage("jobs"); },
    onClose: () => setRequestedRun("") };
  const nav: Page[] = ["overview", "projects", "jobs", "metrics"];
  const adminPages: Page[] = ["administration", "adminUsers", "adminAudit"];


  const navigatePage = (target: Page) => {
    if (target !== page && enrollmentGuard.current && !enrollmentGuard.current()) return;
    setRequestedRun("");
    if (target === "overview") { routedProject.current = null; setJobScope(""); }
    if (target === "jobs" && ["projectDetails", "metrics"].includes(page)) setJobScope(selected);
    setPage(target); setMenuOpen(false);
    if (target === "metrics") setMetricAllProjects(false);
  };
  const shellLink = (target: Page): ShellLink => ({
    id: target, label: t(target === "settings" ? "myAccount" : target === "administration" ? "systemStatus" : target),
    href: target === "overview" ? formatRoute({ view: "overview" }) : formatRoute(target === "jobs" || target === "metrics" ?
      { view: target, ...(target === "jobs" ? (jobScope ? { project: jobScope } : ["projectDetails", "metrics"].includes(page) && selectedProject ? { project: selectedProject.id } : {}) : selectedProject ? { project: selectedProject.id } : {}) } : { view: target as Exclude<Page, "overview" | "jobs" | "metrics" | "projectDetails"> }),
    active: target === page || (target === "projects" && ["createProject", "importProject", "projectDetails"].includes(page)),
    onNavigate: () => navigatePage(target),
  });
  const pageTitle = isAdmin && adminPages.includes(page) ? t(page === "administration" ? "systemStatus" : page) : t(page === "settings" ? "myAccount" : page);
  const contextual = ["projectDetails", "metrics"].includes(page) || ["jobs", "overview"].includes(page) && !!jobScope;
  const projectContext = projectsState === "ready" && contextual && selectedProject && !(page === "metrics" && allProjectScope) ?
    <section className={`project-context${page === "projectDetails" ? " project-hub" : ""}`} aria-label={t("projectContext")}>
      <div>{page !== "projectDetails" && <span className="eyebrow">{t("projectContext")}</span>}<strong>{selectedProject.display_name}</strong><small>{selectedProject.repo}</small></div>
      {page === "projectDetails" ? <div className="metrics-tabs project-tabs" role="tablist" aria-label={t("projectSections")}>
        {projectTabs.map(tab => <span className="project-tab-group" key={tab}>
          {tab === "history" && <><RouteLink to={formatRoute({ view: "jobs", project: selectedProject.id })} onNavigate={() => { setJobScope(selectedProject.id); setRequestedRun(""); setPage("jobs"); }}>{t("jobs")}</RouteLink><RouteLink to={formatRoute({ view: "metrics", project: selectedProject.id })} onNavigate={() => { setMetricAllProjects(false); setPage("metrics"); }}>{t("metrics")}</RouteLink></>}
          <button id={`project-tab-${tab}`} type="button" role="tab" aria-controls="project-tab-panel" aria-selected={projectTab === tab} tabIndex={projectTab === tab ? 0 : -1} onClick={() => setProjectTab(tab)} onKeyDown={event => onProjectTabKeyDown(event, tab)}>{tab === "overview" ? jc.summary : tab === "configuration" ? jc.settings : tab === "history" ? jc.history : t(tab === "prices" ? "prices" : "projectAccessTab")}</button>
        </span>)}
      </div> : <nav aria-label={t("projectLinks")}>
        <NavigationLink item={{ id: "project", label: t("projectDetails"), href: formatRoute({ view: "projectDetails", project: selectedProject.id, tab: "overview" }), active: false, onNavigate: () => openProject(selectedProject.id) }} />
        <NavigationLink item={shellLink("jobs")} /><NavigationLink item={shellLink("metrics")} />
      </nav>}
    </section> : page === "metrics" && allProjectScope ? <p className="scope-note">{t("metricsAllProjects")} · {t("globalScopeHelp")}</p> : null;

  return <DashboardShell t={t} title={pageTitle} links={nav.map(shellLink)} adminLinks={isAdmin ? adminPages.map(shellLink) : []}
    account={shellLink("settings")} username={session.user.username} role={t(session.user.role)}
    menuOpen={menuOpen} onMenu={() => setMenuOpen(open => !open)} adminOpen={adminMenuOpen} onAdmin={() => setAdminMenuOpen(open => !open)}
    onSignOut={signOut} context={projectContext}
    controls={page === "overview" && projectsState === "ready" && projects.length > 0 && <label className="overview-header-scope" htmlFor="overview-project">{t("project")}<select id="overview-project" aria-label={t("project")} value={jobScope} onChange={event => workspaceProps.onScope(event.target.value)}><option value="">{jc.allProjects}</option>{projects.map(item => <option key={item.id} value={item.id}>{item.display_name || item.name}</option>)}</select></label>}
    actions={<>{page !== "overview" && <span className="refresh-stamp">{lastRefresh && t("lastRefresh") + ": " + formatDate(lastRefresh.toISOString())}</span>}
      <button className="ghost" onClick={() => { void refreshProjects().catch(setError); void refreshSelected();  setUsageRefresh(value => value + 1); setViewRefresh(value => value + 1); }}>{t("refresh")}</button>
      <button className="ghost" ref={aboutTrigger} onClick={() => request<typeof about>("/about").then(setAbout).catch(cause => setError(cause))}>{t("about")}</button><DeliveryGlossary t={t} /></>}
    modal={about && <div className="modal-backdrop" onClick={closeAbout}><section role="dialog" aria-modal="true" aria-labelledby="adore-about-heading" className="modal" onClick={event => event.stopPropagation()} onKeyDown={event => { if (event.key === "Escape") closeAbout(); if (event.key === "Tab") { event.preventDefault(); aboutClose.current?.focus(); } }}><button className="ghost modal-close" ref={aboutClose} autoFocus onClick={closeAbout}>{t("close")}</button><div className="brand-mark">A</div><h2 id="adore-about-heading">{t("about")} ADORE</h2><p>{t("version")}: {about.version}</p><p>{t("license")}: {about.license}</p><pre className="license-text">{about.license_text}</pre><h3>{t("thirdPartyNotices")}</h3><pre className="license-text">{about.third_party_notices}</pre></section></div>}>

        {error ? <div className="alert" role="alert">{describeError(locale, error)}<button onClick={() => setError("")} aria-label={t("close")}>×</button></div> : null}
        {notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice("")} aria-label={t("close")}>×</button></div>}
        {operation && <div className="notice" role="status">{t("operationStatus")}: #{operation.id} · {operation.status}{operation.result ? ` · ${operation.result}` : ""}</div>}
        {["overview", "projects", "projectDetails", "jobs", "metrics"].includes(page) && projectsState !== "ready" && <DataFeedback state={projectsState} t={t} />}
        {["overview", "projects", "projectDetails", "jobs", "metrics"].includes(page) && projectsState === "ready" && projects.length === 0 && <ProjectEmpty isAdmin={isAdmin} t={t} />}
        {page === "overview" && projectsState === "ready" && projects.length > 0 && <JobWorkspace reporting={{ from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }} reportingQuery={metricSuffix} admin={isAdmin} {...workspaceProps} mode="overview" />}

        {page === "projects" && projectsState === "ready" && <>
          <div className="section-actions">{isAdmin && <><button className="primary" onClick={() => { setError(""); setPage("createProject"); }}>{t("createProject")}</button><button className="ghost" onClick={() => { setError(""); setPage("importProject"); }}>{t("importProject")}</button></>}</div>
          <section className="panel">
            {projects.length ? <PagedTable key={`${projectSortKey}-${projectSortDescending}`} t={t}><table className="projects-table"><thead><tr>
              <SortHeader label={t("project")} sortKey="name" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <SortHeader label={t("repository")} sortKey="repo" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <th>Repo</th><th>{jc.pickup}</th>
              <SortHeader label={t("jobs")} sortKey="runs" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
              <SortHeader label={t("lastActivity")} sortKey="last_activity" activeKey={projectSortKey} descending={projectSortDescending} onSort={changeProjectSort} />
            </tr></thead><tbody>{sortedProjects.map(item => <tr key={item.id}>
              <td className="strong"><RouteLink to={formatRoute({ view: "projectDetails", project: item.id, tab: "overview" })} onNavigate={() => openProject(item.id)}>{item.display_name}</RouteLink></td><td>{item.repo}</td>
              <td>{({ gitea: "Gitea", github: "GitHub", gitlab: "GitLab" } as Record<string, string>)[item.platform] || item.platform}</td>
              <td><StatusBadge code={item.archived ? "archived" : item.paused ? "paused" : "working"}>{item.archived ? t("archived") : item.paused ? jc.pickupStopped : jc.pickupActive}</StatusBadge></td>
              <td>{item.runs}</td><td>{item.last_activity ? formatDate(item.last_activity) : "\u2014"}</td>
            </tr>)}</tbody></table></PagedTable> : null}
          </section>
        </>}

        {page === "createProject" && isAdmin && <TransferWizard locale={locale} csrf={session.csrf} t={t}
          projects={projects} onExact={() => setPage("importProject")}
          registerGuard={guard => { enrollmentGuard.current = guard; }}
          onCancel={() => { setError(""); setPage("projects"); }}
          onCreated={() => { void refreshProjects(); }} onOpen={id => openProject(id)} />}

        {page === "importProject" && isAdmin && <ImportWizard locale={locale} csrf={session.csrf} t={t}
          registerGuard={guard => { enrollmentGuard.current = guard; }}
          onCancel={() => { setError(""); setPage("projects"); }}
          onCreated={() => { void refreshProjects(); }} onOpen={id => openProject(id)} />}

        {page === "projectDetails" && projectsState === "ready" && selectedProject && <>
          <div id="project-tab-panel" role="tabpanel" aria-labelledby={`project-tab-${projectTab}`}>
          {projectTab === "overview" && <>
          <JobWorkspace reporting={{ from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }} reportingQuery={metricSuffix} admin={isAdmin} {...workspaceProps} mode="overview" scope={selected} fixedScope summaryHeader={evidence => <section className="panel project-summary">
            <dl className="summary-facts">
              <div className="summary-fact"><dt>{t("containerType")}</dt><dd>{({ docker: "Docker", podman: "Podman" } as Record<string, string>)[selectedProject.runtime] || selectedProject.runtime}</dd></div>
              <div className="summary-fact"><dt>{t("executor")}</dt><dd>{({ pi: "Pi", codex: "Codex", opencode: "OpenCode", qwen: "Qwen Code" } as Record<string, string>)[selectedProject.executor] || selectedProject.executor || "—"}</dd></div>
              <div className="summary-fact"><dt>{jc.pickup}</dt><dd><StatusBadge code={selectedProject.archived ? "archived" : selectedProject.paused ? "paused" : "working"}>{selectedProject.archived ? t("archived") : selectedProject.paused ? jc.pickupStopped : jc.pickupActive}</StatusBadge></dd></div>
              <div className="summary-fact"><dt>{jc.verification}</dt><dd>{verificationLabel(selectedProject)}</dd></div>
              {[{ label: t("activeJobs"), value: evidence?.groups.active }, { label: jc.waiting, value: evidence?.groups.waiting }, { label: t("inReviewStatus"), value: evidence ? evidence.counts["in-review"] || 0 : undefined }, { label: t("failedJobs"), value: evidence ? evidence.counts.failed || 0 : undefined }].map(fact => <div className="summary-fact" key={fact.label}><dt>{fact.label}</dt><dd>{fact.value === undefined ? "—" : new Intl.NumberFormat(locale).format(fact.value)}</dd></div>)}
            </dl>
            {isAdmin && <div className="summary-actions button-row">{!selectedProject.archived && <button className="ghost" onClick={() => void operate(selectedProject.paused ? "resume" : "pause", "", selectedProject.id)}>{selectedProject.paused ? jc.startPickup : jc.stopPickup}</button>}
              <button className="ghost" onClick={() => void setProjectArchive(!selectedProject.archived, selectedProject.id)}>{t(selectedProject.archived ? "restoreProject" : "archiveProject")}</button>
              {selectedProject.archived && <button className="danger" onClick={() => { setError(""); setDeleteName(""); setDeleteTarget(selectedProject); }}>{t("deleteProject")}</button>}
              <button className="ghost" onClick={() => void checkProjectReadiness()}>{t("checkHostPrerequisites")}</button>
              {!selectedProject.archived && projectConfig && <ModelConnection key={`${session.user.id}:${selectedProject.id}:${projectConfig.revision}`} project={selectedProject.id} revision={projectConfig.revision} executor={selectedProject.executor} model={String(settingValue(projectConfig.config, `executor.commands.${selectedProject.executor}.model`))} locale={locale} test={() => request(`/projects/${encodeURIComponent(selectedProject.id)}/model-connection-test`, "POST", {}, session.csrf)} />}
            {!selectedProject.archived && <RepositoryConnection key={`${session.user.id}:${selectedProject.id}`} project={selectedProject.id} provider={selectedProject.platform} repository={selectedProject.repo} locale={locale}
              connect={body => request(`/projects/${encodeURIComponent(selectedProject.id)}/repository-connection`, "POST", body, session.csrf)}
              onConnected={() => { setProjectReadiness(null); setProjects(items => items.map(item => item.id === selectedProject.id ? { ...item, verification: { status: "unverified" } } : item)); }} />}
            </div>}
            {projectReadiness && <ReadinessEvidence evidence={projectReadiness} locale={locale} modelReason={modelReason(projectReadiness.model_probe.reason)} />}
          </section>} />
          {isAdmin && deleteTarget?.id === selectedProject.id && <ProjectDeleteDialog onClose={() => setDeleteTarget(null)}><section className="delete-confirm">
            <h2 id="delete-project-title">{t("deleteProjectTitle").replace("{project}", deleteTarget.name)}</h2>
            <p>{t("deleteProjectRemoves")}</p>
            <p className="muted">{t("deleteProjectKeeps")}</p>
            <form className="form-stack" onSubmit={deleteProject}><FormLegend t={t} />
              <label><span>{t("deleteProjectConfirm").replace("{project}", deleteTarget.name)}<RequiredMark /></span><input value={deleteName} onChange={event => setDeleteName(event.target.value)} autoComplete="off" spellCheck={false} required /></label>
              <div className="button-row"><button className="danger" type="submit" disabled={deleteName !== deleteTarget.name}>{t("deleteProject")}</button><button className="ghost" type="button" onClick={() => setDeleteTarget(null)}>{t("cancel")}</button></div>
            </form>
          </section></ProjectDeleteDialog>}
          </>}
          {projectTab === "history" && selectedProject?.id && <AuditHistory key={`${session.user.id}:${selected}`} locale={locale} projects={projects} fixedProject={selectedProject?.id} read={path => request(path)} />}
          {projectTab === "history" && <JobWorkspace reporting={{ from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }} reportingQuery={metricSuffix} admin={isAdmin} {...workspaceProps} mode="history" scope={selected} fixedScope />}
          {projectTab === "configuration" && <>
          {isAdmin && selected && <PortableSettings key={`${session?.user.id}-${selected}-${projectConfig?.revision || "unread"}`} project={selected} locale={locale} />}
          {configDataState !== "ready" && <DataFeedback state={configDataState} t={t} />}
          {projectConfig && <SettingsList key={`${selected}-${projectConfig.revision}`} config={projectConfig.config} settings={projectConfig.settings || []} t={t} locale={locale} canEdit={isAdmin} disabled={!!projectPendingConfig || configBusy || pendingReadFailed || isAdmin && !pendingReady} onStage={stageSetting} />}
          {isAdmin && selected && projectConfig && (projectConfig.config.executor as { default?: string } | undefined)?.default === "opencode" && <section className="panel wide-panel"><h2>{t("localEndpoint")}</h2><p className="muted">{t("localEndpointHelp")}</p><p className="muted">{t("localProviderHelp")}</p>{(projectConfig.config.executor as { default?: string } | undefined)?.default === "opencode" && <form key={`${selected}-${projectConfig.revision}`} className="inline-form config-form" onSubmit={saveEndpoint}><fieldset className="endpoint-fields" disabled={!!projectPendingConfig || configBusy || pendingReadFailed || isAdmin && !pendingReady}><FormLegend t={t} /><Field name="model" label={t("model")} defaultValue={(projectConfig.config.executor as { commands?: { opencode?: { model?: string } } }).commands?.opencode?.model || ""} required /><Field name="endpoint" label={t("localEndpoint")} type="url" defaultValue={(projectConfig.config.container as { runtime_env?: { OPENAI_BASE_URL?: string } } | undefined)?.runtime_env?.OPENAI_BASE_URL || ""} required /><label>{t("endpointAuth")}<select name="auth_env"><option value="">{t("none")}</option><option value="OPENAI_API_KEY">OPENAI_API_KEY</option></select></label><label>{t("endpointProtocol")}<select name="protocol"><option value="openai-chat-completions">OpenAI chat completions</option></select></label><Field name="timeout_seconds" label={t("endpointTimeout")} type="number" defaultValue={String(projectConfig.local_endpoint_timeout_seconds || 300)} required /><Field name="ca_file" label={t("endpointCa")} defaultValue={(projectConfig.config.container as { runtime_env?: { NODE_EXTRA_CA_CERTS?: string } } | undefined)?.runtime_env?.NODE_EXTRA_CA_CERTS || ""} /><button className="primary" disabled={!!projectPendingConfig || configBusy || pendingReadFailed || isAdmin && !pendingReady}>{settingsCopy[locale].prepare}</button></fieldset></form>}</section>}
          {isAdmin && selected && <section className="panel wide-panel" id="project-config-editor"><h2>{t("config")}</h2>{projectConfig && <>
            <p className="muted">{settingsCopy[locale].single}</p>
            {projectConfig.issues.length > 0 && <div className="alert">{projectConfig.issues.join(" · ")}</div>}
            {projectPendingConfig && <PendingReview config={projectConfig} candidate={projectPendingConfig} project={selectedProject?.display_name || selected} paused={selectedProject?.paused === true} busy={configBusy} locale={locale} t={t} onApply={applyPendingConfig} onDiscard={discardPendingConfig} />}
            {pendingReadFailed && <div className="alert"><p>{settingsCopy[locale].readFailed}</p><p>{settingsCopy[locale].discard}</p><button className="ghost" disabled={configBusy} onClick={() => void discardPendingConfig()}>{t("discardChange")}</button></div>}
            <details><summary>{t("rawConfig")}</summary><pre className="config-preview">{JSON.stringify(projectConfig.config, null, 2)}</pre></details>
          </>}</section>}
          </>}
          {projectTab === "access" && isAdmin && selected && <ProjectAccess key={selected + ":" + viewRefresh} project={selected} csrf={session?.csrf} locale={locale} t={t} onError={setError} onNotice={setNotice} />}
          {projectTab === "prices" && isAdmin && <>
          {isAdmin && selected && <section className="panel wide-panel"><h2>{t("estimatedPrices")}</h2><p className="muted">{t("priceHelp")}</p>
            <form key={selected} className="form-grid" onSubmit={savePrice}><FormLegend t={t} /><label>{t("executor")}<select name="executor" defaultValue={["codex", "opencode", "pi", "qwen"].includes(selectedProject?.executor || "") ? selectedProject?.executor : "codex"}><option value="codex">codex</option><option value="opencode">opencode</option><option value="pi">pi</option><option value="qwen">qwen</option></select></label><Field name="model" label={t("model")} required /><label><span>{t("effectiveFrom")}<RequiredMark /></span><input name="effective_from" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label><span>{t("inputRate")}<RequiredMark /></span><input name="input_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><label><span>{t("outputRate")}<RequiredMark /></span><input name="output_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><button className="primary form-submit" type="submit">{t("save")}</button></form>
            {projectPrices.length > 0 && <PagedTable t={t}><table><thead><tr><th>{t("executor")}</th><th>{t("model")}</th><th>{t("effectiveFrom")}</th><th>{t("inputRate")}</th><th>{t("outputRate")}</th></tr></thead><tbody>{projectPrices.map(price => <tr key={price.id}><td>{price.executor}</td><td>{price.model}</td><td>{price.effective_from}</td><td>{price.input_usd_per_million}</td><td>{price.output_usd_per_million}</td></tr>)}</tbody></table></PagedTable>}
          </section>}
          </>}
          </div>
        </>}

        {page === "jobs" && projectsState === "ready" && projects.length > 0 && <JobWorkspace reporting={{ from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }} reportingQuery={metricSuffix} admin={isAdmin} {...workspaceProps} mode="jobs" run={requestedRun} />}

        {page === "metrics" && projectsState === "ready" && projects.length > 0 && <>
        <section className="panel compact metrics-period"><div className="panel-heading"><h2>{t("reportingPeriod")}</h2>{(selected || isAdmin) && reportingDataState === "ready" && <details className="metrics-export"><summary className="ghost metrics-export-trigger">{t("exportCsv")}</summary><div className="metrics-export-links">{!allProjectScope && selected && <><a href={`/api/v1/projects/${encodeURIComponent(selected)}/metrics.csv${metricSuffix}`}>{t("projectMetricsExport")}</a><a href={`/api/v1/projects/${encodeURIComponent(selected)}/usage.csv${usageSuffix}`}>{t("projectUsageExport")}</a><a href={`/api/v1/projects/${encodeURIComponent(selected)}/jobs-usage.csv${metricSuffix}`}>{statisticsText.jobs}</a></>}{allProjectScope && <><a href={`/api/v1/metrics.csv${metricSuffix}`}>{t("allMetricsExport")}</a><a href={`/api/v1/usage.csv${usageSuffix}`}>{t("allUsageExport")}</a><a href={`/api/v1/jobs-usage.csv${metricSuffix}`}>{statisticsText.jobs}</a></>}</div></details>}</div><button className="ghost" type="button" onClick={() => { setMetricFrom(""); setMetricTo(""); }}>{statisticsText.allTime}</button><div className="job-filters">{projects.length > 0 && <label className="metrics-project-filter" htmlFor="metrics-project">{t("project")}<select id="metrics-project" value={allProjectScope ? "" : selected} onChange={event => { setMetricAllProjects(event.target.value === ""); if (event.target.value) setSelected(event.target.value); }}>{isAdmin && <option value="">{t("metricsAllProjects")}</option>}{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label>{t("dateFromLocal")}<input type="date" value={metricFrom} max={metricTo || undefined} onChange={event => setMetricFrom(event.target.value)} /></label><label>{t("dateToLocal")}<input type="date" value={metricTo} min={metricFrom || undefined} onChange={event => setMetricTo(event.target.value)} /></label><label>{t("reportingTimezone")}<select value={metricTimezone} onChange={event => setMetricTimezone(event.target.value)}><option value="UTC">UTC</option><option value="Europe/Bucharest">Europe/Bucharest</option><option value="Europe/Paris">Europe/Paris</option><option value="Europe/Berlin">Europe/Berlin</option><option value="America/New_York">America/New_York</option></select></label><label>{t("trendGranularity")}<select value={metricGranularity} onChange={event => setMetricGranularity(event.target.value as "day" | "week" | "month")}><option value="day">{t("byDay")}</option><option value="week">{t("byWeek")}</option><option value="month">{t("byMonth")}</option></select></label></div><p className="muted">{t("metricsScopeHelp")} {statisticsText.boundaries}</p><p className="field-hint">{statisticsText.legend}</p></section>
        <div className="metrics-tabs" role="tablist" aria-label={t("metrics")}>
          {metricsTabs.map(tab => <button key={tab} id={`metrics-tab-${tab}`} type="button" role="tab" aria-controls="metrics-tab-panel" aria-selected={metricsTab === tab} tabIndex={metricsTab === tab ? 0 : -1} onClick={() => setMetricsTab(tab)} onKeyDown={event => onMetricsTabKeyDown(event, tab)}>{t(metricsTabLabels[tab])}</button>)}
        </div>
        <div id="metrics-tab-panel" role="tabpanel" aria-labelledby={`metrics-tab-${metricsTab}`} tabIndex={0}>
        {reportingDataState !== "ready" ? <DataFeedback state={reportingDataState} t={t} /> : <>
        {metricsTab === "usage" && <>
        <section className="panel"><div className="panel-heading usage-heading"><h2>{t("attributedUsage")}</h2>{isAdmin && <button className="ghost" onClick={() => void rebuildUsage()}>{t("rebuildUsage")}</button>}</div>
          <div className="job-filters"><label>{t("executor")}<input type="search" maxLength={200} value={usageExecutor} onChange={event => setUsageExecutor(event.target.value)} /></label><label>{t("model")}<input type="search" maxLength={200} value={usageModel} onChange={event => setUsageModel(event.target.value)} /></label></div>
          <p className="muted">{t("attributedUsageHelp")}</p>
          {usage && <p className="muted">{t("usageEvents")}: {formatNumber(usage.totals.events)} · {t("tokensIn")}: {formatNumber(usage.totals.tokens_in)} · {t("tokensOut")}: {formatNumber(usage.totals.tokens_out)} / {t("cacheRead")}: {usage.totals.cache_read_tokens == null ? "\u2014" : formatNumber(usage.totals.cache_read_tokens)} / {t("cacheWrite")}: {usage.totals.cache_write_tokens == null ? "\u2014" : formatNumber(usage.totals.cache_write_tokens)}{isAdmin && <> · {t("cost")}: {formatMoney(usage.totals.reported_cost_usd)} · {t("estimatedCost")}: {formatMoney(usage.totals.estimated_cost_usd)}</>}</p>}
          {usage?.daily.length ? <PagedTable t={t}><table><thead><tr><th>{t("date")}</th><th>{t("executor")}</th><th>{t("model")}</th><th>{t("usageEvents")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cacheRead")}</th><th>{t("cacheWrite")}</th>{isAdmin && <th>{t("cost")}</th>}{isAdmin && <th>{t("estimatedCost")}</th>}</tr></thead><tbody>{usage.daily.map((row, index) => <tr key={`${row.date}-${row.executor}-${row.model}-${index}`}><td>{row.date}</td><td>{row.executor || "—"}</td><td>{row.model || "—"}</td><td>{formatNumber(row.events)}</td><td>{formatNumber(row.tokens_in)}</td><td>{formatNumber(row.tokens_out)}</td><td>{row.cache_read_tokens == null ? "\u2014" : formatNumber(row.cache_read_tokens)}</td><td>{row.cache_write_tokens == null ? "\u2014" : formatNumber(row.cache_write_tokens)}</td>{isAdmin && <td>{formatMoney(row.reported_cost_usd)}</td>}{isAdmin && <td>{formatMoney(row.estimated_cost_usd)}</td>}</tr>)}</tbody></table></PagedTable> : <Empty label={t("noMatchingMetrics")} />}
          {allProjectScope && allUsage && <><h3>{t("allProjects")}</h3><PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("usageEvents")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>{scopedUsageRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{formatNumber(item.totals.events)}</td><td>{formatNumber(item.totals.tokens_in)}</td><td>{formatNumber(item.totals.tokens_out)}</td><td>{formatMoney(item.totals.reported_cost_usd)}</td><td>{formatMoney(item.totals.estimated_cost_usd)}</td></tr>)}</tbody></table></PagedTable></>}
        </section></>}
        {metricsTab === "summary" && metrics && <>
          <StatisticsEvidence reporting={{ from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }} metrics={metrics} locale={locale} admin={isAdmin} t={t} />
          <section className="panel"><h2>{t("jobDuration")}</h2><div className="stats-grid">
            <Stat label={t("measuredJobs")} value={formatNumber(metrics.duration.sampled_runs)} hint={statisticsText.interval} />
            <Stat label={t("averageSpan")} value={metrics.duration.avg_span_seconds == null ? statisticsText.unavailable : `${formatNumber(metrics.duration.avg_span_seconds)} s`} hint={statisticsText.interval} />
            <Stat label={t("medianSpan")} value={metrics.duration.median_span_seconds == null ? statisticsText.unavailable : `${formatNumber(metrics.duration.median_span_seconds)} s`} hint={statisticsText.interval} />
          </div></section>
          {allProjectScope && <section className="panel"><h2>{t("projectComparison")}</h2><PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{statisticsText.started}</th><th>{statisticsText.completed}</th><th>{statisticsText.failed}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th></tr></thead><tbody>{globalRows.map(([name, item]) => <tr key={name}><td>{name}<small>{item.scope?.project_ids[0]}</small></td><td>{item.period.started}</td><td>{item.period.completed}</td><td>{item.period.failed}</td><td>{formatNumber(item.period.tokens_in)}</td><td>{formatNumber(item.period.tokens_out)}</td></tr>)}</tbody></table></PagedTable></section>}
        </>}
        {metricsTab === "quality" && metricsEmpty && <section className="panel"><Empty label={t("metricsNoJobs")} /></section>}{metricsTab === "quality" && !metricsEmpty && <>
        <section className="panel"><div className="panel-heading"><h2>{t("deliveryQuality")}</h2><span className="muted">{t(metricFrom || metricTo ? "periodTotals" : "allTimeTotals")}</span></div>
          <p className="muted">{t("qualityHelp")}</p><div className="stats-grid">
            <Stat label={t("reviewReworkRate")} value={formatPercent(metrics?.quality.review_rework_rate)} hint={`${formatNumber(metrics?.quality.reworked_jobs || 0)} / ${formatNumber(metrics?.quality.reviewed_jobs || 0)} ${t("reviewedJobs")}`} />
            <Stat label={t("firstValidationRate")} value={formatPercent(metrics?.quality.first_validation_rate)} hint={`${formatNumber(metrics?.quality.first_pass_validations || 0)} / ${formatNumber(metrics?.quality.validated_jobs || 0)} ${t("validatedJobs")}`} />
            <Stat label={t("firstPassMergeRate")} value={formatPercent(metrics?.quality.first_pass_merge_rate)} hint={`${formatNumber(metrics?.quality.first_pass_merges || 0)} / ${formatNumber(metrics?.quality.human_merged_jobs || 0)} ${t("humanMergedJobs")}`} />
            <Stat label={t("openReviews")} value={formatNumber(metrics?.quality.open_review_jobs || 0)} hint={t("currentState")} />
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
            {globalRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{projects.find(project => project.name === name)?.repo || "—"}</td><td>{formatNumber(item.totals.runs || 0)}</td><td>{formatNumber(item.duration.sampled_runs)}</td><td>{item.duration.avg_span_seconds == null ? "—" : `${formatNumber(item.duration.avg_span_seconds)} s`}</td><td>{formatPercent(item.quality.review_rework_rate)} ({formatNumber(item.quality.reworked_jobs)}/{formatNumber(item.quality.reviewed_jobs)})</td><td>{formatNumber(item.totals.tokens_in)}</td><td>{formatNumber(item.totals.tokens_out)}</td><td>{formatNumber(item.runs.reduce((sum, run) => sum + Number(run.review_rounds || 0), 0))}</td><td>{item.totals.cost_usd == null ? "—" : new Intl.NumberFormat(locale, { style: "currency", currency: "USD" }).format(item.totals.cost_usd)}</td></tr>)}
            {allProjectScope && <tr><th>{t("metricsAllProjects")}</th><th>{repositoryRows.length}</th><th>{formatNumber(metrics?.totals.runs || 0)}</th><th>{formatNumber(globalRows.reduce((sum, [, item]) => sum + item.duration.sampled_runs, 0))}</th><th>—</th><th>—</th><th>{formatNumber(globalTokensIn)}</th><th>{formatNumber(globalTokensOut)}</th><th>{formatNumber(globalReviewRounds)}</th><th>{globalRows.some(([, item]) => item.totals.cost_usd != null) ? new Intl.NumberFormat(locale, { style: "currency", currency: "USD" }).format(globalReportedCost) : "—"}</th></tr>}
          </tbody></table></PagedTable></section>
        {isAdmin && repositoryRows.length > 0 && <section className="panel"><div className="panel-heading"><h2>{t("repository")}</h2><span className="muted">{repositoryRows.length}</span></div>
          <PagedTable t={t}><table><thead><tr><th>{t("repository")}</th><th>{t("projects")}</th><th>{t("jobs")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>
            {repositoryRows.map(([repo, row]) => <tr key={repo}><td>{repo}</td><td>{formatNumber(row.projects)}</td><td>{formatNumber(row.jobs)}</td><td>{formatNumber(row.tokensIn)}</td><td>{formatNumber(row.tokensOut)}</td><td>{formatMoney(row.hasReported ? row.reported : null)}</td><td>{formatMoney(row.hasEstimated ? row.estimated : null)}</td></tr>)}
          </tbody></table></PagedTable></section>}
        </>}
        {metricsTab === "trends" && metricsEmpty && <section className="panel"><Empty label={t("metricsNoJobs")} /></section>}{metricsTab === "trends" && !metricsEmpty && <>
        <section className="panel"><div className="panel-heading"><h2>{trendTitle}</h2><span className="muted">{metricTimezone}</span></div>
          {metrics && <TrendEvidence metrics={metrics} locale={locale} admin={isAdmin} t={t} />}
          <p className="muted coverage-note">{t("unallocatedUsage")}: {formatNumber(metrics?.coverage.usage_events_unallocated || 0)} · {t("coverage")}: {formatNumber(metrics?.coverage.runs_with_usage || 0)} / {formatNumber(metrics?.totals.runs || 0)} {t("jobs")}</p>
        </section>
        {isAdmin && <section className="panel"><div className="panel-heading"><h2>{t("estimatedCost")}</h2><strong>{formatMoney(metrics?.totals.estimated_cost_usd)} {scopeLabel}</strong></div>
          <p className="muted">{t("priceHelp")}</p>
          <PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("estimatedCost")}</th><th>{t("unpricedEvents")}</th></tr></thead><tbody>{globalRows.map(([name, item]) => <tr key={name}><td>{name}</td><td>{formatMoney(item.totals.estimated_cost_usd)}</td><td>{formatNumber(item.coverage.usage_events_unpriced || 0)}</td></tr>)}</tbody></table></PagedTable>
          <h3>{scopeLabel} {trendTitle}</h3>
          <PagedTable t={t}><table><thead><tr><th>{t("date")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>{metrics?.daily.map(day => <tr key={day.date}><td>{day.date}</td><td>{formatMoney(day.estimated_cost_usd)}</td></tr>)}</tbody></table></PagedTable>
        </section>}</>}
        </>}
        </div></>}

        {page === "administration" && isAdmin && <div className="two-column">
          <section className="panel wide-panel"><h2>{t("auditRetention")}</h2><p className="muted">{t("auditRetentionHelp")}</p><p>{auditCopy[locale].impact}</p>{auditPolicy && <form key={`${auditPolicy.retention_days}-${auditPolicy.max_bytes}`} className="inline-form audit-policy-form" onSubmit={saveAuditPolicy}><label>{t("auditDays")}<input name="retention_days" type="number" min="0" max="36500" step="1" defaultValue={auditPolicy.retention_days ?? 0} /></label><label>{t("auditMib")}<input name="max_mib" type="number" min="0" max="1024" step="any" defaultValue={auditPolicy.max_bytes == null ? 0 : auditPolicy.max_bytes / 1024**2} /></label><button className="primary" type="submit">{t("save")}</button></form>}</section>

          <section className="panel wide-panel" role="status" aria-live="polite"><div className="panel-heading"><h2>{t("workerReadiness")}</h2><strong className={`readiness readiness-${workerStatus}`}>{t(workerStatus === "ready" ? "workerReady" : workerStatus === "unavailable" ? "workerUnavailable" : workerStatus === "error" ? "workerCheckFailed" : "workerChecking")}</strong></div><p className="muted">{t("workerReadinessHelp")}</p></section>
          <section className="panel wide-panel" role="status" aria-live="polite"><div className="panel-heading"><h2>{t("storageStatus")}</h2><strong className={`readiness readiness-${storageError ? "error" : storageStatus?.low ? "unavailable" : storageStatus ? "ready" : "checking"}`}>{t(storageError ? "storageCheckFailed" : storageStatus?.low ? "storageLow" : storageStatus ? "storageHealthy" : "workerChecking")}</strong></div><p className="muted">{t("storageHelp")}</p>{storageStatus && <PagedTable t={t}><table><thead><tr><th>{t("storageVolume")}</th><th>{t("storageFree")}</th><th>{t("status")}</th></tr></thead><tbody>{storageStatus.volumes.map((volume, index) => <tr key={`${volume.scope}-${volume.project || index}`}><td>{volume.scope === "home" ? t("storageHome") : volume.project}</td><td>{new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(volume.free_bytes / 1024**3)} GiB</td><td>{t(volume.low ? "storageLow" : "storageHealthy")}</td></tr>)}</tbody></table></PagedTable>}</section>
        </div>}

        {page === "adminUsers" && isAdmin && <div className="two-column">
          <UserCreation key={session.user.id} projects={projects} ready={projectsState === "ready"} locale={locale} usernameLabel={t("username")} passwordLabel={t("password")} roleLabel={t("role")} createLabel={t("createUser")} requiredLegend={t("requiredLegend")} send={(path, method, body) => request(path, method, body, session.csrf)} onCreated={() => setViewRefresh(value => value + 1)} />
          <section className="panel"><h2>{t("userAccounts")}</h2>{usersState !== "ready" ? <DataFeedback state={usersState} t={t} /> : users.length === 0 ? <Empty label={t("empty")} /> : <div className="user-list">{users.map(item =>
            <div className="user-row" key={item.id}>
              <span className="user-avatar">{item.username.charAt(0).toUpperCase()}</span>
              <div><strong>{item.username}</strong><small>{t(item.role)}{item.disabled ? ` · ${t("disable")}` : ""}</small></div>
              {item.role === "developer" && <details className="membership-editor"><summary>{t("assignedProjects")}</summary>
                <AccountAccessEditor key={item.id + ":" + item.project_ids.join()} account={item} projects={projects} ready={projectsState === "ready"} locale={locale} saveLabel={t("save")} send={(path, method, body) => request(path, method, body, session.csrf)} onError={setError} onApplied={result => { setNotice(result); setViewRefresh(value => value + 1); }} />
              </details>}
              {item.id !== session.user.id && <button type="button" className="ghost" onClick={() => setAccountEnabled(item.id, item.disabled)}>{t(item.disabled ? "enable" : "disable")}</button>}
              <button type="button" className="ghost" onClick={() => setResetTarget(resetTarget === item.id ? null : item.id)}>{t("resetPassword")}</button>
              {resetTarget === item.id && <form className="inline-form" onSubmit={event => resetUserPassword(event, item.id)}><FormLegend t={t} /><Field name="replacement" label={t("newPassword")} type="password" required minLength={8} hint={t("passwordRule")} /><button className="primary">{t("save")}</button></form>}
            </div>
          )}</div>}</section>
        </div>}

        {page === "adminAudit" && isAdmin && <AuditHistory key={`${session.user.id}:${viewRefresh}`} locale={locale} projects={projects} read={path => request(path)} />}

        {page === "settings" && <div className="two-column"><section className="panel"><h2>{t("appearance")}</h2><div className="form-stack"><label>{t("language")}<select aria-label={t("language")} value={locale} onChange={event => updatePreference("language", event.target.value)}>{Object.entries(localeNames).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>{t("theme")}<select aria-label={t("theme")} value={theme} onChange={event => updatePreference("theme", event.target.value)}><option value="system">{t("system")}</option><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option></select></label></div></section><section className="panel"><h2>{t("changePassword")}</h2><form className="form-stack" onSubmit={changePassword}><FormLegend t={t} /><Field name="current" label={t("currentPassword")} type="password" required /><Field name="replacement" label={t("newPassword")} type="password" required minLength={8} hint={t("passwordRule")} /><button className="primary">{t("save")}</button></form></section>
        </div>}
  </DashboardShell>;
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return <div className="stat-card"><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>;
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


function RouteLink({ to, onNavigate, children }: { to: string; onNavigate: () => void; children: ReactNode }) {
  return <a className="text-button" href={to} onClick={event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onNavigate();
  }}>{children}</a>;
}

function RequiredMark() {
  return <span className="required-mark" aria-hidden="true"> *</span>;
}

function FormLegend({ t }: { t: (key: MessageKey) => string }) {
  return <p className="form-legend"><span className="required-mark" aria-hidden="true">*</span> {t("requiredLegend")}</p>;
}

function Field({ name, label, type = "text", required = false, defaultValue, hint, minLength }: { name: string; label: string; type?: string; required?: boolean; defaultValue?: string; hint?: string; minLength?: number }) {
  return <label><span>{label}{required && <RequiredMark />}</span><input name={name} type={type} required={required} defaultValue={defaultValue} minLength={minLength} />{hint && <small className="field-hint">{hint}</small>}</label>;
}


type ProjectDeveloper = { id: number; username: string; disabled: boolean; granted: boolean };
const validDevelopers = (value: unknown): value is { developers: ProjectDeveloper[] } => !!value && typeof value === "object" && "developers" in value && Array.isArray(value.developers) && value.developers.every(row => row && Number.isSafeInteger(row.id) && row.id > 0 && typeof row.username === "string" && typeof row.disabled === "boolean" && typeof row.granted === "boolean") && new Set(value.developers.map(row => row.id)).size === value.developers.length;

/** Administrator view of one project’s developers, granting or removing access one at a time. */
function ProjectAccess({ project, csrf, locale, t, onError, onNotice }: { project: string; csrf?: string; locale: Locale; t: (key: MessageKey) => string; onError: (cause: unknown) => void; onNotice: (text: string) => void }) {
  const [developers, setDevelopers] = useState<ProjectDeveloper[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const mounted = useRef(true);
  const changing = useRef(false);
  const [review, setReview] = useState<ProjectDeveloper | null>(null);
  const copy = userCopy[locale];
  const path = `/projects/${encodeURIComponent(project)}/access`;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    let live = true;
    setDevelopers(null); setFailed(false);
    request<{ developers: ProjectDeveloper[] }>(path).then(value => { if (!validDevelopers(value)) throw new ApiError("unexpected_response"); if (live) setDevelopers(value.developers); }).catch(cause => { if (live) { setFailed(true); onError(cause); } });
    return () => { live = false; };
  }, [path]);
  const change = async (developer: ProjectDeveloper) => {
    if (changing.current) return;
    changing.current = true; setBusy(true); onError("");
    try {
      const result = await request<{ id: number; granted: boolean }>(`${path}/${developer.id}`, "PUT", { granted: !developer.granted }, csrf);
      if (result.id !== developer.id || result.granted !== !developer.granted) throw new ApiError("unexpected_response");
      if (!mounted.current) return;  // another project is shown now; say nothing about this one
      setDevelopers(current => current && current.map(row => row.id === developer.id ? { ...row, granted: !developer.granted } : row));
      setReview(null);
      onNotice(`${copy.applied}: ${developer.username} · ${t(result.granted ? "hasAccess" : "noAccess")}`);
      const value = await request<{ developers: ProjectDeveloper[] }>(path);
      if (!validDevelopers(value)) throw new ApiError("unexpected_response");
      if (mounted.current) setDevelopers(value.developers);
    } catch (cause) { if (mounted.current) onError(cause); } finally { if (mounted.current) { changing.current = false; setBusy(false); } }
  };
  return <section className="panel wide-panel"><h2>{t("projectAccessTab")}</h2><p className="muted">{t("projectAccessHelp")}</p>
    {developers === null ? <DataFeedback state={failed ? "error" : "loading"} t={t} /> : (developers.length === 0 ? <p className="empty">{t("noDevelopers")}</p> : <div className="user-list">{developers.map(developer =>
      <div className="user-row" key={developer.id}>
        <span className="user-avatar">{developer.username.charAt(0).toUpperCase()}</span>
        <div><strong>{developer.username}</strong><small>{t("developer")}{developer.disabled ? ` · ${t("accountDisabled")}` : ""}</small></div>
        <span className={developer.granted ? "status status-working" : "status"}>{t(developer.granted ? "hasAccess" : "noAccess")}</span>
        <button type="button" className="ghost" disabled={busy || review !== null} aria-label={`${t(developer.granted ? "removeAccess" : "grantAccess")}: ${developer.username}`} onClick={() => setReview(developer)}>{t(developer.granted ? "removeAccess" : "grantAccess")}</button>
      </div>)}</div>)}
    {review && <AccessReview subject={`${review.username} · ${project}`} before={t(review.granted ? "hasAccess" : "noAccess")} after={t(review.granted ? "noAccess" : "hasAccess")} copy={copy} busy={busy} correct={() => setReview(null)} apply={() => void change(review)} />}
  </section>;
}

function PendingReview({ config, candidate, project, paused, busy, locale, t, onApply, onDiscard }: { config: Config; candidate: PendingConfig; project: string; paused: boolean; busy: boolean; locale: Locale; t: (key: MessageKey) => string; onApply: () => Promise<void>; onDiscard: () => Promise<void> }) {
  const copy = settingsCopy[locale];
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, [candidate.candidate_revision]);
  const [copied, setCopied] = useState(false);
  const meta = config.settings?.find(item => item.edit_key === candidate.key);
  const active = settingValue(config.config, meta?.key || candidate.key);
  const show = (value: unknown) => value == null ? copy.unknown : value === "" ? t("settingNoDefault") : typeof value === "object" ? JSON.stringify(value) : String(value);
  const rows: Array<{ label: string; active: unknown; proposed: unknown }> = [{ label: locale === "en" ? settingLabel(meta?.key || candidate.key) : t("config"), active, proposed: candidate.proposed_value }];
  if (candidate.endpoint) {
    rows.push({ label: t("model"), active: settingValue(config.config, "executor.commands.opencode.model"), proposed: candidate.endpoint.model });
    rows.push({ label: t("endpointProtocol"), active: config.local_endpoint?.protocol, proposed: candidate.endpoint.protocol });
    rows.push({ label: t("endpointAuth"), active: config.local_endpoint ? config.local_endpoint.auth_env ?? t("settingNoDefault") : undefined, proposed: candidate.endpoint.auth_env ?? t("settingNoDefault") });
    rows.push({ label: t("endpointTimeout"), active: config.local_endpoint_timeout_seconds, proposed: candidate.endpoint.timeout_seconds });
    rows.push({ label: t("endpointCa"), active: settingValue(config.config, "container.runtime_env.NODE_EXTRA_CA_CERTS"), proposed: candidate.endpoint.ca_file ?? t("settingNoDefault") });
  }
  const stale = candidate.base_revision !== config.revision;
  const blocked = stale || candidate.restart_required && !paused;
  const reviewText = [copy.project + ": " + project, ...rows.map(row => `${row.label}: ${copy.active}: ${show(row.active)} → ${copy.proposed}: ${show(row.proposed)}`), copy.base + ": " + candidate.base_revision, copy.candidate + ": " + candidate.candidate_revision].join("\n");
  return <div className="import-preview candidate-review"><h3 ref={heading} tabIndex={-1}>{t("pendingChange")}</h3>
    <p><strong>{copy.project}:</strong> {project}</p><p>{copy.single}</p>
    <div className="candidate-values">{rows.map(row => <section key={row.label}><h4>{row.label}</h4><dl><div><dt>{copy.active}</dt><dd>{show(row.active)}</dd></div><div><dt>{copy.proposed}</dt><dd>{show(row.proposed)}</dd></div></dl></section>)}</div>
    <h4>{copy.effect}</h4><p>{candidate.endpoint ? copy.endpoint : settingHelp(meta?.key || candidate.key, locale)}</p><p>{copy.future}</p>
    <p>{copy.prepared}: <time dateTime={candidate.created_at}>{new Date(candidate.created_at).toLocaleString(locale)}</time></p><p>{copy.actor}</p>
    <p>{copy.idle}</p>{candidate.restart_required && <p className={!paused ? "alert" : "muted"}>{copy.pause}</p>}{stale && <p className="alert">{copy.stale}</p>}
    <details><summary>{copy.details}</summary><p><code>{candidate.key}</code></p><p>{copy.base}: <code>{candidate.base_revision}</code></p><p>{copy.candidate}: <code>{candidate.candidate_revision}</code></p></details>
    <p>{copy.discard}</p><div className="button-row"><button className="primary" disabled={busy || blocked} onClick={() => void onApply()}>{t("apply")}</button><button className="ghost" disabled={busy} onClick={() => void onDiscard()}>{t("discardChange")}</button><button className="ghost" onClick={() => void navigator.clipboard.writeText(reviewText).then(() => setCopied(true)).catch(() => setCopied(false))}>{copy.copy}</button>{copied && <span role="status">{copy.copied}</span>}</div>
  </div>;
}

function SettingsList({ config, settings, t, locale, canEdit, disabled, onStage }: { config: Record<string, unknown>; settings: SettingMeta[]; t: (key: MessageKey) => string; locale: Locale; canEdit: boolean; disabled: boolean; onStage: (key: string, value: string) => Promise<boolean> }) {
  const [projectOnly, setProjectOnly] = useState(false);
  const [editing, setEditing] = useState("");
  const [draft, setDraft] = useState("");
  const groups = settingGroups(settingRows(config, settings), projectOnly);
  const copy = settingsCopy[locale];
  const typeOf = (row: SettingRow) => {
    if (row.input === "choice") return t("settingEnum");
    if (Array.isArray(row.value)) return t("settingList");
    if (typeof row.value === "boolean") return t("settingBoolean");
    if (typeof row.value === "number") return Number.isInteger(row.value) ? t("settingInteger") : t("settingNumber");
    if (/(?:^|\.)(?:repo_path|root|store_root|db_path|export_jsonl|html_out|ca_file)$/.test(row.key)) return t("settingPath");
    return t("settingText");
  };
  const shown = (value: unknown) => value == null || value === "" ? "—" :
    Array.isArray(value) || typeof value === "object" ? JSON.stringify(value) : String(value);
  const label = (row: SettingRow) => locale === "en" ? settingLabel(row.key) : row.label ? t(row.label) : (settingHelp(row.key, locale)?.split(". ")[0] || settingLabel(row.key));
  const submit = async (event: FormEvent<HTMLFormElement>, row: SettingRow) => {
    event.preventDefault();
    if (await onStage(row.editKey, draft)) setEditing("");
  };
  return <section className="panel" id="project-settings">
    <div className="panel-heading"><h2>{t("projectSettings")}</h2><label className="check-inline"><input type="checkbox" checked={projectOnly} onChange={event => setProjectOnly(event.target.checked)} />{t("settingsProjectOnly")}</label></div>
    <p className="muted">{canEdit ? copy.single : copy.readOnly}</p>
    {groups.length === 0 ? <Empty label={t("settingsNoneSet")} /> : <div className="setting-groups">{groups.map(group => <details key={group.name} open={true}>
      <summary>{copy[group.name as keyof typeof copy]} <span className="muted">({group.rows.length})</span></summary>
      <div className="setting-list">{group.rows.map(row => <div className="setting-row" key={row.key}>
        <div>
          <strong>{label(row)}</strong><p className="setting-essential" id={`help-${row.key}`}>{settingHelp(row.key, locale) ?? t("settingGeneralHelp")}</p>
          <span className={row.source === "project" ? "setting-badge set" : "setting-badge"}>{t(row.source === "project" ? "settingSetForProject" : "settingDefault")}</span>
          {canEdit && row.input !== "none" && row.restart && <small className="setting-note">{t("settingRestartShort")}</small>}
          {canEdit && row.input === "none" && <small className="setting-note">{t("settingNotEditableShort")}</small>}
        </div>
        {editing === row.key ? <form className="setting-editor" onSubmit={event => void submit(event, row)}>
          {row.input === "boolean" || row.input === "choice"
            ? <select aria-label={label(row)} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)}>{(row.input === "boolean" ? ["true", "false"] : row.choices).map(option => <option key={option} value={option}>{option}</option>)}</select>
            : <input aria-label={label(row)} type={row.input === "number" ? "number" : "text"} step={row.step} min={row.minimum ?? undefined} max={row.maximum ?? undefined} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} required={row.input === "number"} />}
          <div className="button-row"><button className="primary" disabled={disabled}>{copy.prepare}</button><button type="button" className="ghost" onClick={() => setEditing("")}>{t("cancel")}</button></div>
        </form> : <div><small>{copy.active}</small><code>{shown(row.value)}</code><small>{t("settingDefaultValue")}: {hasDefault(row.defaultValue) ? shown(row.defaultValue) : t("settingNoDefault")}</small></div>}
        <div className="setting-actions">
          {canEdit && row.input !== "none" && editing !== row.key && <button type="button" className="text-button" disabled={disabled} aria-label={`${t("editSetting")} ${label(row)}`} data-edit-key={row.editKey} onClick={() => { setEditing(row.key); setDraft(editValue(row.value)); }}>{t("editSetting")}</button>}
          <details><summary aria-label={`${t("settingHelp")} ${row.key}`}>{t("settingHelp")}</summary>
            <code>{row.key}</code><p>{typeOf(row)}{row.choices.length ? ` · ${row.choices.join(", ")}` : ""}{row.minimum != null ? ` · ${copy.minimum}: ${row.minimum}` : ""}{row.maximum != null ? ` · ${copy.maximum}: ${row.maximum}` : ""}</p>
            <p className="muted">{t("settingDefaultValue")}: {hasDefault(row.defaultValue) ? shown(row.defaultValue) : t("settingNoDefault")}</p>
            {canEdit && row.input === "none" && <p>{t("settingNotEditableNote")}</p>}
          </details>
        </div>
      </div>)}</div>
    </details>)}</div>}
  </section>;
}

/** Native modal owns focus containment; restore the initiating action after dismissal. */
function ProjectDeleteDialog({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const node = dialog.current;
    node?.showModal();
    return () => { node?.close(); if (trigger?.isConnected) trigger.focus(); };
  }, []);
  return <dialog ref={dialog} className="project-delete-dialog" aria-labelledby="delete-project-title" onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>{children}</dialog>;
}

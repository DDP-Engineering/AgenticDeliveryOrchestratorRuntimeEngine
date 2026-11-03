/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { Children, Fragment, cloneElement, isValidElement, useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactElement, type ReactNode } from "react";
import { aggregateMetrics, aggregateUsage, type Metrics, type Usage } from "./metrics";
import { sortUsageRows, type UsageSortKey } from "./usageSort";
import { messages, type Locale, type MessageKey } from "./i18n";
import { ModelConnection, validModelEvidence, type ModelEvidence } from "./ModelConnection";
import { agentSettingsCopy, executorSettingLabel, executorSelectionDraft, validExecutorSelection, validCredentialNames, credentialEditorCopy, systemPackageCopy } from "./executorSettings";
import { CredentialNamesEditor } from "./CredentialNamesEditor";
import { ExecutorSelectionEditor } from "./ExecutorSelectionEditor";
import { LocalExecutorPicker, LocalExecutionIdentity } from "./LocalExecutorPicker";
import { setupCopy } from "./setupCopy";
import { ExecutorCredentials, executorCopy } from "./ExecutorCredentials";
import { RepositoryConnection } from "./RepositoryConnection";
import { ReadinessEvidence, readinessDetailsLabel, readinessCloseLabel } from "./ReadinessEvidence";
import { readReadiness, type ProjectReadiness } from "./readiness";
import { AuditHistory } from "./AuditHistory";
import { groupRelease, type Release } from "./releaseNotes";
import { auditPolicyPayload } from "./auditPolicy";
import { ApiError, describeError } from "./errors";
import { startVisiblePolling } from "./polling";
import { formatRoute, normalizeRoute, parseRoute, type ProjectTab, type Route } from "./routes";
import { editValue, hasDefault, settingGroups, settingRows, type SettingMeta, type SettingRow, settingValue, validSettingCatalog, validPendingConfig, type PendingConfig, settingVisible, settingSubgroup, STATUS_LABEL_KEYS, BRANCH_NAMING_KEYS, CHOSEN_ENVIRONMENT_KEYS, validBranchPreview, type BranchPreview } from "./settings";
import { ExecutorEnvironment, externalEnvironmentCopy, type ExecutorEnvironmentInfo } from "./ExecutorEnvironment";
import { ExecutionPlanReview } from "./ExecutionPlanReview";
import { type ExecutionPlan } from "./executionPlan";
import { settingHelp } from "./settingHelp";
import { durationParts, executionStages, implementationDraft, implementationEditorCopy } from "./implementationSettings";
import { compactReviewCopy, settingsCopy, technicalSettingsHelp, settingLabel, publicationCopy, publicationValue, pipelineFailureCopy, pipelineFailureValue, reviewerCopy, targetBranchCopy, excludeLabelCopy, lifecycleCopy, branchNamingCopy, branchSettingLabel, implementationSettingLabel, localizedSettingLabel } from "./settingsCopy";
import { ImportWizard } from "./ImportWizard";
import { RawConfiguration } from "./RawConfiguration";
import { TransferWizard } from "./TransferWizard";
import { readStatistics, readConsumption } from "./statistics";
import { StatisticsEvidence, TrendEvidence } from "./StatisticsEvidence";
import { statisticsCopy } from "./statisticsCopy";
import { JobWorkspace } from "./JobWorkspace";
import { SortHeader } from "./SortHeader";
import { jobCopy } from "./jobCopy";
import { outcomeText } from "./operationReason";
import { UserCreation, AccountAccessEditor, AccessReview, validAccount, type Account } from "./UserCreation";
import { userCopy } from "./userCopy";
import { companyLogo, DashboardShell, type ShellLink } from "./DashboardShell";
import { TicketWorkspace } from "./TicketWorkspace";
import { ticketCopy, operationResultText } from "./ticketCopy";
import { DataFeedback, ProjectEmpty, StatusBadge, type DataState, type ScopedState } from "./Presentation";
import { HelpCenter, HelpLink } from "./HelpCenter";
import { readServerImages, type ServerImages } from "./serverImages";
import { ForgeLabelsAction } from "./ForgeLabels";
import { settingDisplayLabel } from "./settingLabels";
import { enrollmentCopy } from "./enrollmentCopy";
import { DeleteCloneOption } from "./DeleteCloneOption";
import { CONTEXT_TOPICS, type HelpTopic } from "./help/topics.ts";

type User = { id: number; username: string; role: "admin" | "developer"; disabled: boolean; password_change_required?: boolean; projects?: string[] };
type AccountUser = User & Account;
type Session = { user: User; csrf: string };
type Preferences = { language: Locale | null; theme: "light" | "dark" | "system" | null };
type Project = { display_name: string; pickup_state: string; verification: { status: string; checked_at?: string | null; revision?: string | null }; validation: { structural_valid: boolean }; id: string; name: string; description: string; platform: string; repo: string; runtime: string; executor: string; readiness: string; last_activity: string | null; paused: boolean; archived: boolean; runs: number; invalid_runs: string[] };
type Config = { executor_environment?: ExecutorEnvironmentInfo; local_execution?: { machine: string; account: string; system: string } | null; execution_plan?: ExecutionPlan | null; model_connection?: ModelEvidence | null; config: Record<string, unknown>; revision: string; issues: string[]; local_endpoint_timeout_seconds?: number | null; local_endpoint?: { protocol: string; auth_env: string | null } | null; settings?: SettingMeta[] };
type Operation = { id: number; status: string; result?: string; reason?: string; detail?: string; action?: string };
type Price = { id: number; executor: string; model: string; effective_from: string; input_usd_per_million: string; output_usd_per_million: string };
type Page = "overview" | "projects" | "createProject" | "importProject" | "cloneProject" | "projectDetails" | "jobs" | "metrics" | "administration" | "adminUsers" | "adminAudit" | "settings" | "help";
type MetricsTab = "summary" | "usage" | "quality" | "trends" | "projects";
type ProjectSortKey = "name" | "repo" | "readiness" | "runs" | "last_activity";
const metricsTabLabels: Record<MetricsTab, MessageKey> = {
  summary: "metricsTabSummary", usage: "metricsTabUsage", quality: "metricsTabQuality",
  trends: "metricsTabTrends", projects: "metricsTabProjects",
};
type WorkerStatus = "checking" | "ready" | "unavailable" | "error";
type StorageStatus = { threshold_bytes: number; low: boolean; volumes: Array<{ scope: "home" | "project"; project: string | null; free_bytes: number; total_bytes: number; low: boolean; volume_id: string }> };
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
  const [usageSortKey, setUsageSortKey] = useState<UsageSortKey>("date");
  const [usageSortDescending, setUsageSortDescending] = useState(false);
  const [selectedUsage, setUsage] = useState<Usage | null>(null);
  const [usageScope, setUsageScope] = useState("");
  const [allUsage, setAllUsage] = useState<Record<string, Usage> | null>(null);
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
  const [readinessExpanded, setReadinessExpanded] = useState(false);
  const [readinessBusy, setReadinessBusy] = useState(false);
  const [readinessError, setReadinessError] = useState<unknown>(null);
  const readinessPending = useRef(false);
  const readinessTrigger = useRef<HTMLButtonElement>(null);
  const [about, setAbout] = useState<{ name: string; version: string; license: string; license_text: string; third_party_notices: string; release_notes?: Release[] } | null>(null);
  const [aboutView, setAboutView] = useState<"about" | "whatsNew">("about");
  const [helpTopic, setHelpTopic] = useState<HelpTopic | undefined>();
  const [aboutOpen, setAboutOpen] = useState({ license: false, notices: false });
  const [error, setError] = useState<unknown>("");
  const [passwordSession, setPasswordSession] = useState<Session | null>(null);
  const [projectTab, setProjectTab] = useState<ProjectTab>("overview");
  const [jobsView, setJobsView] = useState<"tickets" | "jobs">("tickets");
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [deleteName, setDeleteName] = useState("");
  const [deleteClone, setDeleteClone] = useState(false);
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
  const [operationVisible, setOperationVisible] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const enrollmentGuard = useRef<(() => boolean) | null>(null);
  // The address of the page shown now, restored when a guarded wizard refuses browser Back.
  const shownUrl = useRef("");
  const [resetTarget, setResetTarget] = useState<number | null>(null);
  const aboutTrigger = useRef<HTMLButtonElement>(null);
  // Switching About views removes the pressed button; focus its counterpart so Escape and Tab keep working.
  const aboutSwitch = useRef<HTMLButtonElement>(null);
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

  useEffect(() => { aboutSwitch.current?.focus(); }, [aboutView]);
  const closeAbout = () => {
    setAbout(null); setAboutView("about"); setAboutOpen({ license: false, notices: false });
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
  const metricsTabs: MetricsTab[] = ["summary", "usage", "quality", "trends"];
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
  const projectTabs: ProjectTab[] = isAdmin ? ["overview", "configuration", "jobs", "statistics", "history", "access"] : ["overview", "configuration", "jobs", "statistics", "history"];
  // Leaving a tab closes any job detail opened in the Jobs tab.
  const selectProjectTab = (tab: ProjectTab) => {
    setRequestedRun("");
    if (tab === "statistics" && tab !== projectTab) setMetricsTab("summary");
    // The Jobs tab opens on Tickets; job detail links select the Jobs sub-tab explicitly.
    if (tab === "jobs" && tab !== projectTab) setJobsView("tickets");
    setProjectTab(tab);
  };
  const selectJobsView = (view: "tickets" | "jobs") => { setRequestedRun(""); setJobsView(view); };
  const onJobsViewKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? "tickets" : event.key === "End" ? "jobs" : jobsView === "tickets" ? "jobs" : "tickets";
    selectJobsView(next);
    document.getElementById(`jobs-subtab-${next}`)?.focus();
  };
  const onProjectTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, tab: ProjectTab) => {
    const current = projectTabs.indexOf(tab);
    const next = event.key === "ArrowRight" ? (current + 1) % projectTabs.length :
      event.key === "ArrowLeft" ? (current + projectTabs.length - 1) % projectTabs.length :
      event.key === "Home" ? 0 : event.key === "End" ? projectTabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault();
    selectProjectTab(projectTabs[next]);
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
  const changeUsageSort = (key: UsageSortKey) => {
    if (key === usageSortKey) setUsageSortDescending(value => !value);
    else { setUsageSortKey(key); setUsageSortDescending(false); }
  };
  const selectedProject = projects.find(item => item.id === selected);
  useEffect(() => {
    if (selectedProject?.verification.status === "stale") setProjectReadiness(null);
  }, [selectedProject?.verification.status]);
  const projectConfig = configScope === selected ? config : null;
  const configDataState = configState.key === selected ? configState.state : "loading";
  const projectPendingConfig = pendingConfigScope === selected ? pendingConfig : null;
  const projectPrices = pricesScope === selected ? prices : [];
  // Prices are recorded only for the applied coding agent and the model configured for it in Agent and model.
  const appliedAgent = projectConfig ? settingValue(projectConfig.config, "executor.default") : undefined;
  const priceExecutor = typeof appliedAgent === "string" && appliedAgent ? appliedAgent : selectedProject?.executor || "";
  const configuredPriceModel = projectConfig && priceExecutor ? settingValue(projectConfig.config, `executor.commands.${priceExecutor}.model`) : undefined;
  const priceModel = typeof configuredPriceModel === "string" && configuredPriceModel.trim() ? configuredPriceModel : "";
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
  const usageSuffix = metricSuffix;
  const allProjectScope = isAdmin && metricAllProjects && page === "metrics";
  const statisticsVisible = page === "metrics" || page === "projectDetails" && projectTab === "statistics";
  // The cross-project comparison tab exists only on the global Statistics page.
  useEffect(() => { if (metricsTab === "projects") setMetricsTab("summary"); }, [metricsTab]);
  // Per-project rows name the project and hint its repository instead of its identifier.
  const projectCell = (name: string) => { const repo = projects.find(item => item.name === name)?.repo; return <td>{name}{repo && <small className="field-hint">{repo}</small>}</td>; };
  const scopeLabel = allProjectScope ? t("metricsAllProjects") : selectedProject?.name || "";
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
      setProjectsLoaded(true); setProjectsState("ready");
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

  useEffect(() => { readinessRequest.current += 1; readinessPending.current = false; setReadinessBusy(false); setReadinessError(null); setProjectReadiness(null); setReadinessExpanded(false); }, [selected, page, session?.user.id]);

  useEffect(() => {
    if (!session || !selected || !statisticsVisible || projectsState !== "ready" || !projects.some(item => item.id === selected)) return;
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
  }, [session, selected, statisticsVisible, usageSuffix, isAdmin, authorizedMetricsKey, projectsState]);

  const refreshSelected = useCallback(async () => {
    const revision = ++selectedMetricsRequest.current;
    if (!selected || !session || !statisticsVisible || projectsState !== "ready" || !projects.some(item => item.id === selected)) { setMetrics(null); return; }
    const generation = viewGeneration.current;
    const key = JSON.stringify([selected, metricSuffix, authorizedMetricsKey]);
    setSelectedState({ key, state: "loading" });
    try {
      const metricData = await request<Metrics>(`/projects/${encodeURIComponent(selected)}/metrics${metricSuffix}`);
      if (generation !== viewGeneration.current || revision !== selectedMetricsRequest.current) return;
      readStatistics(metricData, selected, { from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity }, isAdmin);
      setSelectedState({ key, state: "ready" });
      setMetrics(metricData); setMetricsScope(selected);
    } catch (cause) {
      if (generation === viewGeneration.current && revision === selectedMetricsRequest.current) {
        setSelectedState({ key, state: "error" }); setMetrics(null); setError(cause);
      }
    }
  }, [selected, session, metricSuffix, statisticsVisible, authorizedMetricsKey, projectsState]);

  useEffect(() => {
    void refreshSelected();
    const stopPolling = startVisiblePolling(() => void refreshSelected(), 15000);
    return () => { selectedMetricsRequest.current += 1; stopPolling(); };
  }, [refreshSelected]);

  useEffect(() => {
    setLastRefresh(new Date());
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
        const kind=String(settingValue(value.config,"executor.default")), model=String(settingValue(value.config,`executor.commands.${kind}.model`));
        if(value.model_connection && !validModelEvidence(value.model_connection,selected,value.revision,kind,model)) throw new ApiError("unexpected_response");
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
  }, [page, isAdmin, metricSuffix, authorizedMetricsKey, projectsState]);

  // Presentation expires independently of worker polling and persisted outcomes.
  useEffect(() => {
    if (!notice) return;
    setOperationVisible(false);
    const timer = window.setTimeout(() => setNotice(""), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    // A failure with engine lines stays until it is closed; other outcomes fade after 5 s.
    if (!operationVisible || !operation || ["pending", "running"].includes(operation.status) ||
      ["failed", "uncertain"].includes(operation.status) && operation.detail) return;
    const timer = window.setTimeout(() => setOperationVisible(false), 5000);
    return () => window.clearTimeout(timer);
  }, [operationVisible, operation?.id, operation?.status]);

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
      case "projectDetails": return selected ? { view: "projectDetails", project: selected, tab: projectTab,
        ...(projectTab === "jobs" ? requestedRun ? { run: requestedRun } : jobsView === "jobs" ? { jobsView: "jobs" as const } : {} : {}),
        ...(projectTab === "statistics" ? { ...reportingRoute, ...(metricsTab !== "summary" && metricsTab !== "projects" ? { metricsTab } : {}) } : {}) } : { view: "projects" };
      case "jobs": return { view: "jobs", ...reportingRoute, ...(jobScope ? { project: jobScope } : {}), ...(jobScope && requestedRun ? { run: requestedRun } : jobsView === "jobs" ? { jobsView: "jobs" as const } : {}) };
      case "metrics": return { view: "metrics", ...reportingRoute, ...(selected && !(isAdmin && metricAllProjects) ? { project: selected } : {}), ...(metricsTab !== "summary" ? { tab: metricsTab } : {}) };
      case "help": return helpTopic ? { view: "help", topic: helpTopic } : { view: "help" };
      default: return { view: page };
    }
  };

  const applyRoute = (route: Route) => {
    setRequestedRun(route.view === "jobs" || route.view === "projectDetails" && route.tab === "jobs" ? route.run || "" : "");
    setPage(route.view); setMenuOpen(false);
    if (route.view === "jobs" || route.view === "overview") setJobScope(route.project || "");
    if ("project" in route && route.project) { routedProject.current = route.project; setSelected(route.project); }
    if (route.view === "projectDetails") setProjectTab(route.tab);
    if (route.view === "help") setHelpTopic(route.topic);
    if (route.view === "jobs" || route.view === "projectDetails" && route.tab === "jobs") setJobsView(route.run || route.jobsView === "jobs" ? "jobs" : "tickets");
    if (route.view === "metrics" || route.view === "jobs" || route.view === "projectDetails" && route.tab === "statistics") {
      setMetricFrom(route.reporting?.from ?? ""); setMetricTo(route.reporting?.through ?? "");
      setMetricTimezone(route.reporting?.timezone ?? "UTC"); setMetricGranularity((route.reporting?.granularity ?? "day") as "day" | "week" | "month");
    }
    if (route.view === "metrics") { setMetricsTab(route.tab ?? "summary"); setMetricAllProjects(!route.project); }
    if (route.view === "projectDetails" && route.tab === "statistics") setMetricsTab(route.metricsTab ?? "summary");
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
        window.history.pushState(null, "", shownUrl.current || formatRoute({ view: "createProject" }));
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
    shownUrl.current = target;
    const here = window.location.pathname + window.location.search;
    if (target === here) return;
    if (target.split("?")[0] === window.location.pathname) window.history.replaceState(null, "", target);
    else window.history.pushState(null, "", target);
  }, [session, routeReady, page, selected, projectTab, jobsView, metricsTab, metricAllProjects, requestedRun, jobScope, isAdmin, metricFrom, metricTo, metricTimezone, metricGranularity, helpTopic]);

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
    setUsage(null); setUsageScope(""); setAllUsage(null); setUsageSortKey("date"); setUsageSortDescending(false);
    setConfig(null); setPendingConfig(null); setPrices([]);
    setUsers([]); setAuditPolicy(null); setOperation(null); setOperationVisible(false);
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
      setOperationVisible(true);
      await refreshSelected();
    } catch (cause) { setError(cause); }
  };

  const deleteProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setNotice("");
    if (!deleteTarget || !session || !isAdmin || page !== "projectDetails" || deleteTarget.id !== selected || deleteName !== deleteTarget.name || !deleteTarget.archived || !selectedProject?.archived) return;
    try {
      const op = await request<Operation>(`/projects/${encodeURIComponent(deleteTarget.id)}/delete`, "POST",
        { confirm_name: deleteName, idempotency_key: crypto.randomUUID(), remove_clone: deleteClone }, session.csrf);
      setOperation(op);
      setOperationVisible(true);
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
    if (!selected || !isAdmin || readinessPending.current) return;
    readinessPending.current = true;
    const revision = ++readinessRequest.current;
    const generation = viewGeneration.current;
    setProjectReadiness(null); setReadinessExpanded(true); setReadinessBusy(true); setReadinessError(null);
    try {
      const result = readReadiness(await request<unknown>(`/projects/${encodeURIComponent(selected)}/readiness-check`, "POST", {}, session?.csrf), selected);
      if (generation === viewGeneration.current && revision === readinessRequest.current) {
        setProjectReadiness(result);
        setProjects(items => items.map(item => item.id === selected ? { ...item, verification: { status: result.status, checked_at: result.checked_at, revision: result.revision } } : item));
      }
    } catch (cause) {
      if (generation === viewGeneration.current && revision === readinessRequest.current) setReadinessError(cause);
    } finally {
      if (revision === readinessRequest.current) { readinessPending.current = false; setReadinessBusy(false); }
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
    onOpen: (id: string, runId: string) => { setSelected(id); setJobScope(id); setRequestedRun(runId); setJobsView("jobs"); setPage("jobs"); },
    onClose: () => setRequestedRun("") };
  const hubWorkspaceProps = { ...workspaceProps, scope: selected,
    onOpen: (id: string, runId: string) => { setSelected(id); setRequestedRun(runId); setJobsView("jobs"); setProjectTab("jobs"); } };
  // Pages that poll while visible need no manual Refresh; these load only on open or on Refresh.
  const manualRefresh = page === "adminUsers" || page === "adminAudit" || page === "projectDetails" && ["configuration", "access", "history"].includes(projectTab);
  const nav: Page[] = ["overview", "projects", "jobs", "metrics"];
  const adminPages: Page[] = ["administration", "adminUsers", "adminAudit"];


  // Help links name an address; route it like the browser would, inside the app.
  const navigateHref = (href: string) => {
    const url = new URL(href, window.location.origin);
    if (enrollmentGuard.current && !enrollmentGuard.current()) return;
    applyRoute(normalizeRoute(parseRoute(url.pathname, url.search), { isAdmin }).route);
  };
  const navigatePage = (target: Page) => {
    if (target !== page && enrollmentGuard.current && !enrollmentGuard.current()) return;
    setRequestedRun("");
    if (target !== page) setMetricsTab("summary");
    if (target === "overview") { routedProject.current = null; setJobScope(""); }
    if (target === "jobs" && ["projectDetails", "metrics"].includes(page)) setJobScope(selected);
    if (target === "jobs" && page !== "jobs") setJobsView("tickets");
    setPage(target); setMenuOpen(false);
    if (target === "metrics") setMetricAllProjects(false);
  };
  const shellLink = (target: Page): ShellLink => ({
    id: target, label: t(target === "settings" ? "myAccount" : target === "administration" ? "systemStatus" : target),
    href: target === "overview" ? formatRoute({ view: "overview" }) : formatRoute(target === "jobs" || target === "metrics" ?
      { view: target, ...(target === "jobs" ? (jobScope ? { project: jobScope } : ["projectDetails", "metrics"].includes(page) && selectedProject ? { project: selectedProject.id } : {}) : selectedProject ? { project: selectedProject.id } : {}) } : { view: target as Exclude<Page, "overview" | "jobs" | "metrics" | "projectDetails"> }),
    active: target === page || (target === "projects" && ["createProject", "importProject", "cloneProject", "projectDetails"].includes(page)),
    onNavigate: () => navigatePage(target),
  });
  const pageTitle = isAdmin && adminPages.includes(page) ? t(page === "administration" ? "systemStatus" : page) : t(page === "settings" ? "myAccount" : page);
  const projectContext = projectsState === "ready" && page === "projectDetails" && selectedProject ?
    <section className="project-context project-hub" aria-label={t("projectContext")}>
      <div><strong>{selectedProject.display_name}</strong><small>{selectedProject.repo}</small></div>
      <div className="metrics-tabs project-tabs" role="tablist" aria-label={t("projectSections")}>
        {projectTabs.map(tab => <button key={tab} id={`project-tab-${tab}`} type="button" role="tab" aria-controls="project-tab-panel" aria-selected={projectTab === tab} tabIndex={projectTab === tab ? 0 : -1} onClick={() => selectProjectTab(tab)} onKeyDown={event => onProjectTabKeyDown(event, tab)}>{tab === "overview" ? jc.summary : tab === "configuration" ? jc.settings : tab === "jobs" ? t("jobs") : tab === "statistics" ? t("metrics") : tab === "history" ? jc.history : t("projectAccessTab")}</button>)}
      </div>
    </section> : null;

  const elapsed = (value: number | null) => value == null ? statisticsText.unavailable : `${formatNumber(value)} s`;
  const usageTotals: Chip[] = usage ? [[t("usageEvents"), formatNumber(usage.totals.events)], [t("tokensIn"), formatNumber(usage.totals.tokens_in)],
    [t("tokensOut"), formatNumber(usage.totals.tokens_out)], [t("cacheRead"), formatNumber(usage.totals.cache_read_tokens)], [t("cacheWrite"), formatNumber(usage.totals.cache_write_tokens)],
    ...(isAdmin ? [[t("cost"), formatMoney(usage.totals.reported_cost_usd)], [t("estimatedCost"), formatMoney(usage.totals.estimated_cost_usd)], [t("unpricedEvents"), formatNumber(usage.totals.unpriced_events)]] as Chip[] : []),
    ...(metrics ? [[t("measuredJobs"), formatNumber(metrics.duration.sampled_runs)], [t("averageSpan"), elapsed(metrics.duration.avg_span_seconds)],
      [t("medianSpan"), elapsed(metrics.duration.median_span_seconds)]] as Chip[] : [])] : [];
  const ratio = (numerator: number | undefined, denominator: number | undefined) => `${formatNumber(numerator || 0)}/${formatNumber(denominator || 0)}`;
  const qualityChips: Chip[] = metrics ? [[t("reviewReworkRate"), formatPercent(metrics.quality.review_rework_rate), `${ratio(metrics.quality.reworked_jobs, metrics.quality.reviewed_jobs)} ${t("reviewedJobs")}`],
    [t("firstValidationRate"), formatPercent(metrics.quality.first_validation_rate), `${ratio(metrics.quality.first_pass_validations, metrics.quality.validated_jobs)} ${t("validatedJobs")}`],
    [t("firstPassMergeRate"), formatPercent(metrics.quality.first_pass_merge_rate), `${ratio(metrics.quality.first_pass_merges, metrics.quality.human_merged_jobs)} ${t("humanMergedJobs")}`],
    [t("openReviews"), formatNumber(metrics.quality.open_review_jobs || 0)], [t("attempts"), formatNumber(metrics.quality.stage_failures || 0)],
    [t("operatorRetries"), formatNumber(metrics.quality.operator_retries || 0)]] : [];
  const costChips: Chip[] = metrics ? ([["reported_per_completed", "reportedCompleted"], ["estimated_per_completed", "estimatedCompleted"], ["reported_per_human_merged", "reportedMerged"], ["estimated_per_human_merged", "estimatedMerged"]] as const)
    .map(([key, label]) => [t(label), formatMoney(metrics.quality.cost_efficiency?.[key]?.usd_per_job), `${formatNumber(metrics.quality.cost_efficiency?.[key]?.jobs_with_evidence || 0)} ${t("jobsWithEvidence")}`]) : [];
  const revisionChips: Chip[] = metrics ? [[t("mrRevisions"), formatNumber(metrics.totals.mr_revisions || 0)], [t("pipelineRepairs"), formatNumber(metrics.totals.pipeline_repairs || 0)],
    [t("unclassifiedRevisions"), formatNumber(metrics.coverage.revision_events_unclassified || 0)]] : [];
  const revisionDays = metrics?.daily.filter(day => day.mr_revisions || day.pipeline_repairs) || [];
  const trendChips: Chip[] = metrics ? [[t("coverage"), `${formatNumber(metrics.coverage.runs_with_usage || 0)}/${formatNumber(metrics.totals.runs || 0)}`, t("jobs")]] : [];
  const usageColumns: Array<[UsageSortKey, MessageKey]> = [["date", "date"], ["executor", "executor"], ["model", "model"], ["events", "usageEvents"], ["tokens_in", "tokensIn"],
    ["tokens_out", "tokensOut"], ["cache_read_tokens", "cacheRead"], ["cache_write_tokens", "cacheWrite"], ...(isAdmin ? [["reported_cost_usd", "cost"], ["estimated_cost_usd", "estimatedCost"]] as Array<[UsageSortKey, MessageKey]> : [])];

  /** Tickets/Jobs sub-tabs shared by the project hub and the global Jobs page. */
  const jobsSubtabs = <div className="metrics-tabs jobs-subtabs" role="tablist" aria-label={ticketCopy[locale].sections}>
    {(["tickets", "jobs"] as const).map(view => <button key={view} id={`jobs-subtab-${view}`} type="button" role="tab" aria-controls="jobs-subtab-panel" aria-selected={jobsView === view} tabIndex={jobsView === view ? 0 : -1} onClick={() => selectJobsView(view)} onKeyDown={onJobsViewKeyDown}>{ticketCopy[locale][view]}</button>)}
  </div>;
  const jobScopeProject = projects.find(item => item.id === jobScope);

  // Storage measurements share a row per physical volume, so one disk is described once.
  const gib = (bytes: number) => new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(bytes / 1024**3);
  // A Map keeps the server order (home first); numeric-looking ids would reorder a plain object.
  const storageGroups = [...(storageStatus?.volumes ?? []).reduce((groups, volume) => {
    const group = groups.get(volume.volume_id) ?? { id: volume.volume_id, names: [] as string[], free: volume.free_bytes, total: volume.total_bytes, low: false };
    group.names.push(volume.scope === "home" ? t("storageHome") : volume.project || "");
    group.free = Math.min(group.free, volume.free_bytes);
    group.low ||= volume.low;
    return groups.set(volume.volume_id, group);
  }, new Map<string, { id: string; names: string[]; free: number; total: number; low: boolean }>()).values()];

  /** Statistics content; `fixed` keeps the project chosen by the project hub instead of offering a selector. */
  const statisticsView = (fixed: boolean) => <>
        <section className="panel compact metrics-period"><div className="metrics-period-row"><h2>{t("reportingPeriod")}</h2>{!fixed && projects.length > 0 && <label className="metrics-project-filter" htmlFor="metrics-project">{t("project")}<select id="metrics-project" value={allProjectScope ? "" : selected} onChange={event => { setMetricAllProjects(event.target.value === ""); if (event.target.value) setSelected(event.target.value); }}>{isAdmin && <option value="">{t("metricsAllProjects")}</option>}{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label>{t("dateFromLocal")}<input type="date" value={metricFrom} max={metricTo || undefined} onChange={event => setMetricFrom(event.target.value)} /></label><label>{t("dateToLocal")}<input type="date" value={metricTo} min={metricFrom || undefined} onChange={event => setMetricTo(event.target.value)} /></label><label>{t("trendGranularity")}<select value={metricGranularity} onChange={event => setMetricGranularity(event.target.value as "day" | "week" | "month")}><option value="day">{t("byDay")}</option><option value="week">{t("byWeek")}</option><option value="month">{t("byMonth")}</option></select></label><button className="ghost" type="button" onClick={() => { setMetricFrom(""); setMetricTo(""); }}>{statisticsText.allTime}</button>{(selected || isAdmin) && reportingDataState === "ready" && <details className="metrics-export"><summary className="ghost metrics-export-trigger">{t("exportCsv")}</summary><div className="metrics-export-links">{!allProjectScope && selected && <><a href={`/api/v1/projects/${encodeURIComponent(selected)}/metrics.csv${metricSuffix}`}>{t("projectMetricsExport")}</a><a href={`/api/v1/projects/${encodeURIComponent(selected)}/usage.csv${usageSuffix}`}>{t("projectUsageExport")}</a><a href={`/api/v1/projects/${encodeURIComponent(selected)}/jobs-usage.csv${metricSuffix}`}>{statisticsText.jobs}</a></>}{allProjectScope && <><a href={`/api/v1/metrics.csv${metricSuffix}`}>{t("allMetricsExport")}</a><a href={`/api/v1/usage.csv${usageSuffix}`}>{t("allUsageExport")}</a><a href={`/api/v1/jobs-usage.csv${metricSuffix}`}>{statisticsText.jobs}</a></>}</div></details>}</div></section>
        <div className="metrics-tabs" role="tablist" aria-label={t("metrics")}>
          {metricsTabs.map(tab => <button key={tab} id={`metrics-tab-${tab}`} type="button" role="tab" aria-controls="metrics-tab-panel" aria-selected={metricsTab === tab} tabIndex={metricsTab === tab ? 0 : -1} onClick={() => setMetricsTab(tab)} onKeyDown={event => onMetricsTabKeyDown(event, tab)}>{t(metricsTabLabels[tab])}</button>)}
        </div>
        <div id="metrics-tab-panel" role="tabpanel" aria-labelledby={`metrics-tab-${metricsTab}`} tabIndex={0}>
        {reportingDataState !== "ready" ? <DataFeedback state={reportingDataState} t={t} /> : <>
        {metricsTab === "usage" && <>
        <section className="panel"><h2>{t("attributedUsage")}</h2>
          {usage && <Chips items={usageTotals} className="usage-totals" />}
          {usage?.daily.length ? <PagedTable key={`${usageSortKey}-${usageSortDescending}`} t={t}><table className="usage-table"><thead><tr>{usageColumns.map(([key, label]) => <SortHeader key={key} label={t(label)} sortKey={key} activeKey={usageSortKey} descending={usageSortDescending} onSort={changeUsageSort} />)}</tr></thead><tbody>{sortUsageRows(usage.daily, usageSortKey, usageSortDescending, locale).map((row, index) => <tr key={`${row.date}-${row.executor}-${row.model}-${index}`}><td>{row.date}</td><td>{row.executor || "—"}</td><td>{row.model || "—"}</td><td>{formatNumber(row.events)}</td><td>{formatNumber(row.tokens_in)}</td><td>{formatNumber(row.tokens_out)}</td><td>{row.cache_read_tokens == null ? "\u2014" : formatNumber(row.cache_read_tokens)}</td><td>{row.cache_write_tokens == null ? "\u2014" : formatNumber(row.cache_write_tokens)}</td>{isAdmin && <td>{formatMoney(row.reported_cost_usd)}</td>}{isAdmin && <td>{formatMoney(row.estimated_cost_usd)}</td>}</tr>)}</tbody></table></PagedTable> : <Empty label={t("noMatchingMetrics")} />}
          {allProjectScope && allUsage && <><h3>{t("allProjects")}</h3><PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("usageEvents")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th><th>{t("unpricedEvents")}</th></tr></thead><tbody>{scopedUsageRows.map(([name, item]) => <tr key={name}>{projectCell(name)}<td>{formatNumber(item.totals.events)}</td><td>{formatNumber(item.totals.tokens_in)}</td><td>{formatNumber(item.totals.tokens_out)}</td><td>{formatMoney(item.totals.reported_cost_usd)}</td><td>{formatMoney(item.totals.estimated_cost_usd)}</td><td>{formatNumber(item.totals.unpriced_events)}</td></tr>)}</tbody></table></PagedTable></>}
        </section>
        </>}
        {metricsTab === "summary" && metrics && <>
          <StatisticsEvidence metrics={metrics} locale={locale} admin={isAdmin} t={t} />
          {allProjectScope && <section className="panel"><h2>{t("projectComparison")}</h2><PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{statisticsText.started}</th><th>{statisticsText.completed}</th><th>{statisticsText.failed}</th><th>{t("averageSpan")}</th></tr></thead><tbody>{globalRows.map(([name, item]) => <tr key={name}>{projectCell(name)}<td>{item.period.started}</td><td>{item.period.completed}</td><td>{item.period.failed}</td><td>{elapsed(item.duration.avg_span_seconds)}</td></tr>)}</tbody></table></PagedTable></section>}
        </>}
        {metricsTab === "quality" && metricsEmpty && <section className="panel"><Empty label={t("metricsNoJobs")} /></section>}{metricsTab === "quality" && !metricsEmpty && <>
        <section className="panel"><h2>{t("deliveryQuality")}</h2><Chips items={qualityChips} /></section>
        {isAdmin && <section className="panel"><h2>{t("qualityEfficiency")}</h2><Chips items={costChips} /></section>}
        <section className="panel"><h2>{t("mrRevisions")} / {t("pipelineRepairs")}</h2><Chips items={revisionChips} />
          {revisionDays.length > 0 && <PagedTable t={t}><table className="revision-days"><thead><tr><th>{t("date")}</th><th>{t("mrRevisions")}</th><th>{t("pipelineRepairs")}</th></tr></thead><tbody>
            {revisionDays.map(day => <tr key={day.date}><td>{day.date}</td><td>{formatNumber(day.mr_revisions)}</td><td>{formatNumber(day.pipeline_repairs)}</td></tr>)}
          </tbody></table></PagedTable>}
        </section>
        {allProjectScope && <section className="panel"><h2>{t("projectComparison")}</h2>
          <PagedTable t={t}><table><thead><tr><th>{t("project")}</th><th>{t("reviewReworkRate")}</th><th>{t("mrRevisions")}</th><th>{t("pipelineRepairs")}</th><th>{t("reviewRounds")}</th></tr></thead><tbody>
            {globalRows.map(([name, item]) => <tr key={name}>{projectCell(name)}<td>{formatPercent(item.quality.review_rework_rate)} <small className="field-hint">{ratio(item.quality.reworked_jobs, item.quality.reviewed_jobs)}</small></td><td>{formatNumber(item.totals.mr_revisions || 0)}</td><td>{formatNumber(item.totals.pipeline_repairs || 0)}</td><td>{formatNumber(item.runs.reduce((sum, run) => sum + Number(run.review_rounds || 0), 0))}</td></tr>)}
          </tbody></table></PagedTable>
        </section>}
        {isAdmin && !allProjectScope && selected && (metrics?.revisions?.length || 0) > 0 && <section className="panel"><div className="panel-heading"><h2>{t("revisionCosts")}</h2><span className="muted">{scopeLabel}</span></div>
          <PagedTable t={t}><table><thead><tr><th>{t("jobs")}</th><th>{t("revision")}</th><th>{t("date")}</th><th>{t("status")}</th><th>{t("tokensIn")}</th><th>{t("tokensOut")}</th><th>{t("cost")}</th><th>{t("estimatedCost")}</th></tr></thead><tbody>
            {metrics?.revisions?.map(row => <tr key={`${row.run_id}-${row.revision}`}><td>{row.run_id}</td><td>{row.revision}</td><td>{row.date || "—"}</td><td>{row.trigger === "revise-label" ? t("mrRevisions") : row.trigger === "pipeline-failed" ? t("pipelineRepairs") : t("unclassifiedRevisions")}</td><td>{formatNumber(row.tokens_in)}</td><td>{formatNumber(row.tokens_out)}</td><td>{formatMoney(row.reported_cost_usd)}</td><td>{formatMoney(row.estimated_cost_usd)}</td></tr>)}
          </tbody></table></PagedTable>
        </section>}
        </>}
        {metricsTab === "trends" && metricsEmpty && <section className="panel"><Empty label={t("metricsNoJobs")} /></section>}{metricsTab === "trends" && !metricsEmpty && <>
        <section className="panel"><h2>{trendTitle}</h2><Chips items={trendChips} />
          {metrics && <TrendEvidence metrics={metrics} locale={locale} admin={isAdmin} t={t} />}
        </section></>}
        </>}
        </div></>;

  return <DashboardShell t={t} title={pageTitle} links={nav.map(shellLink)} adminLinks={isAdmin ? adminPages.map(shellLink) : []}
    account={shellLink("settings")} username={session.user.username} role={t(session.user.role)}
    menuOpen={menuOpen} onMenu={() => setMenuOpen(open => !open)} adminOpen={adminMenuOpen} onAdmin={() => setAdminMenuOpen(open => !open)}
    onSignOut={signOut} context={projectContext}
    controls={page === "overview" && projectsState === "ready" && projects.length > 0 && <label className="overview-header-scope" htmlFor="overview-project">{t("project")}<select id="overview-project" aria-label={t("project")} value={jobScope} onChange={event => workspaceProps.onScope(event.target.value)}><option value="">{jc.allProjects}</option>{projects.map(item => <option key={item.id} value={item.id}>{item.display_name || item.name}</option>)}</select></label>}
    actions={<>{manualRefresh && <><span className="refresh-stamp">{lastRefresh && t("lastRefresh") + ": " + formatDate(lastRefresh.toISOString())}</span>
      <button className="ghost" onClick={() => { void refreshProjects().catch(setError); setViewRefresh(value => value + 1); }}>{t("refresh")}</button></>}
      <button className="ghost" ref={aboutTrigger} onClick={() => request<typeof about>("/about").then(setAbout).catch(cause => setError(cause))}>{t("about")}</button><a className="ghost link-button" href="/help" onClick={event => { if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return; event.preventDefault(); navigateHref("/help"); }}>{t("glossary")}</a></>}
    modal={about && <div className="modal-backdrop" onClick={closeAbout}><section role="dialog" aria-modal="true" aria-labelledby="adore-about-heading" className={"modal about-modal" + (aboutView === "whatsNew" ? " about-wide" : "")} onClick={event => event.stopPropagation()} onKeyDown={event => {
      if (event.key === "Escape") closeAbout();
      if (event.key !== "Tab") return;
      // Keep keyboard focus cycling inside the dialog.
      const items = [...event.currentTarget.querySelectorAll<HTMLElement>("button, [tabindex='0']")];
      const index = items.indexOf(document.activeElement as HTMLElement);
      const next = event.shiftKey ? (index <= 0 ? items.length - 1 : index - 1) : (index + 1) % items.length;
      event.preventDefault(); items[next]?.focus();
    }}>
      <div className="about-banner"><img src={companyLogo} alt="DDP Engineering" width="630" height="300" /><button className="ghost modal-close" autoFocus onClick={closeAbout}>{t("close")}</button></div>
      {aboutView === "about" ? <div className="about-body">
        <h2 id="adore-about-heading" className="about-name">ADORE</h2>
        <p className="about-version">{t("version")} {about.version}</p>
        <p className="about-license-name">{about.license}</p>
        <div className="about-actions">
          <button type="button" className="primary" ref={aboutSwitch} onClick={() => setAboutView("whatsNew")}>{t("whatsNew")}</button>
          <button type="button" className="ghost" aria-expanded={aboutOpen.license} aria-controls="about-license" onClick={() => setAboutOpen(value => ({ ...value, license: !value.license }))}>{t("license")}</button>
          <button type="button" className="ghost" aria-expanded={aboutOpen.notices} aria-controls="about-notices" onClick={() => setAboutOpen(value => ({ ...value, notices: !value.notices }))}>{t("thirdPartyNotices")}</button>
        </div>
        {aboutOpen.license && <pre id="about-license" className="license-text" tabIndex={0} aria-label={t("license")}>{about.license_text}</pre>}
        {aboutOpen.notices && <pre id="about-notices" className="license-text" tabIndex={0} aria-label={t("thirdPartyNotices")}>{about.third_party_notices}</pre>}
      </div> : <div className="about-body">
        <div className="about-heading-row"><h2 id="adore-about-heading">{t("whatsNew")}</h2><button type="button" className="ghost" ref={aboutSwitch} onClick={() => setAboutView("about")}>{t("back")}</button></div>
        {about.release_notes?.some(release => release.entries.length) ? <div className="release-notes">{about.release_notes.filter(release => release.entries.length).map(release => <section key={release.version}>
          <h3>{release.version === "Unreleased" ? t("inDevelopment") : `${t("version")} ${release.version}`}{release.date && <small>{release.date}</small>}</h3>
          {groupRelease(release, locale).map(group => <div key={group.category} className="release-category">
            <h4>{t(({ new: "releaseNew", improved: "releaseImproved", fixed: "releaseFixed" } as const)[group.category])}</h4>
            {group.topics.map(topic => <div key={topic.topic}><h5>{topic.topic}</h5><ul>{topic.texts.map(text => <li key={text}>{text}</li>)}</ul></div>)}
          </div>)}
        </section>)}</div> : <p className="muted">{t("noReleaseNotes")}</p>}
      </div>}
    </section></div>}>

        {error ? <div className="alert" role="alert">{describeError(locale, error)}<button onClick={() => setError("")} aria-label={t("close")}>×</button></div> : null}
        {(notice || (operationVisible && operation)) && <div className="notice" role="status">
          {notice || (operation && <>{t("operationStatus")}: #{operation.id} · {operation.status}{(operation.reason ? outcomeText(locale, operation) : operationResultText(operation.result || "", locale)) && operation.result !== "completed" ? ` · ${(operation.reason ? outcomeText(locale, operation) : operationResultText(operation.result || "", locale))}` : ""}{operation.status !== "succeeded" && operation.detail && <pre className="operation-detail" tabIndex={0}>{operation.detail}</pre>}</>)}
          <button onClick={() => { setNotice(""); setOperationVisible(false); }} aria-label={t("close")}>×</button>
        </div>}
        {["overview", "projects", "projectDetails", "jobs", "metrics"].includes(page) && projectsState !== "ready" && <DataFeedback state={projectsState} t={t} />}
        {["overview", "projects", "projectDetails", "jobs", "metrics"].includes(page) && projectsState === "ready" && projects.length === 0 && <ProjectEmpty isAdmin={isAdmin} t={t} />}
        {page === "overview" && projectsState === "ready" && projects.length > 0 && <JobWorkspace admin={isAdmin} {...workspaceProps} mode="overview" />}

        {page === "projects" && projectsState === "ready" && <>
          <div className="section-actions">{isAdmin && <><button className="primary" onClick={() => { setError(""); setPage("createProject"); }}>{t("createProject")}</button><button className="ghost" onClick={() => { setError(""); setPage("importProject"); }}>{t("importProject")}</button><button className="ghost" onClick={() => { setError(""); setPage("cloneProject"); }}>{t("cloneProject")}</button></>}</div>
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

        {(page === "createProject" || page === "cloneProject") && isAdmin && <TransferWizard key={page} mode={page === "createProject" ? "enroll" : "clone"} locale={locale} csrf={session.csrf} t={t}
          projects={projects}
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
          <JobWorkspace admin={isAdmin} {...hubWorkspaceProps} mode="overview" fixedScope summaryHeader={evidence => <section className="panel project-summary">
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
              <button ref={readinessTrigger} type="button" className="ghost" aria-disabled={readinessBusy} aria-controls="host-check-details" aria-expanded={readinessExpanded} onClick={() => void checkProjectReadiness()}>{t("checkHostPrerequisites")}</button>

            {!selectedProject.archived && <RepositoryConnection key={`${session.user.id}:${selectedProject.id}`} project={selectedProject.id} provider={selectedProject.platform} repository={selectedProject.repo} locale={locale}
              connect={body => request(`/projects/${encodeURIComponent(selectedProject.id)}/repository-connection`, "POST", body, session.csrf)}
              onConnected={() => { setProjectReadiness(null); setProjects(items => items.map(item => item.id === selectedProject.id ? { ...item, verification: { status: "unverified" } } : item)); }} />}
            </div>}
            <section id="host-check-details" hidden={!readinessExpanded} aria-busy={readinessBusy} aria-labelledby="host-check-title">
              <div className="panel-heading"><h3 id="host-check-title">{readinessDetailsLabel(locale)}</h3><button type="button" className="ghost" onClick={() => { setReadinessExpanded(false); readinessTrigger.current?.focus(); }}>{readinessCloseLabel(locale)}</button></div>
              {readinessBusy && <p role="status">{t("workerChecking")}</p>}
              {readinessError !== null && <p role="alert" className="alert">{describeError(locale, readinessError)}</p>}
              {projectReadiness && <ReadinessEvidence modelEvidence={projectConfig?.model_connection} evidence={projectReadiness} locale={locale} modelReason={modelReason(projectReadiness.model_probe.reason)} />}
            </section>
          </section>} />
          {isAdmin && deleteTarget?.id === selectedProject.id && <ProjectDeleteDialog onClose={() => setDeleteTarget(null)}><section className="delete-confirm">
            <h2 id="delete-project-title">{t("deleteProjectTitle").replace("{project}", deleteTarget.name)}</h2>
            <p>{t("deleteProjectRemoves")}</p>
            <p className="muted">{t("deleteProjectKeeps")}</p>
            <form className="form-stack" onSubmit={deleteProject}><FormLegend t={t} />
              <DeleteCloneOption locale={locale} project={deleteTarget.id} read={path => request(path)} checked={deleteClone} onChange={setDeleteClone} />
              <label><span className="delete-confirm-label">{t("deleteProjectConfirm").split("{project}").map((part, index) => <Fragment key={index}>{index > 0 && <strong className="delete-confirm-name">{deleteTarget.name}</strong>}{part}</Fragment>)}<RequiredMark /></span><input value={deleteName} onChange={event => setDeleteName(event.target.value)} autoComplete="off" spellCheck={false} required /></label>
              <div className="button-row"><button className="danger" type="submit" disabled={deleteName !== deleteTarget.name}>{t("deleteProject")}</button><button className="ghost" type="button" onClick={() => setDeleteTarget(null)}>{t("cancel")}</button></div>
            </form>
          </section></ProjectDeleteDialog>}
          </>}
          {projectTab === "history" && selectedProject?.id && <AuditHistory key={`${session.user.id}:${selected}:${viewRefresh}`} locale={locale} projects={projects} fixedProject={selectedProject?.id} read={path => request(path)} />}
          {projectTab === "jobs" && selectedProject && <>
            {jobsSubtabs}
            <div id="jobs-subtab-panel" role="tabpanel" aria-labelledby={`jobs-subtab-${jobsView}`}>
              {jobsView === "tickets" ? <TicketWorkspace key={`${session.user.id}:${selectedProject.id}`} projects={[selectedProject]} locale={locale} csrf={session.csrf} request={request} />
                : <JobWorkspace admin={isAdmin} {...hubWorkspaceProps} mode="jobs" run={requestedRun} fixedScope />}
            </div>
          </>}
          {projectTab === "statistics" && statisticsView(true)}
          {projectTab === "history" && <JobWorkspace admin={isAdmin} {...hubWorkspaceProps} mode="history" fixedScope />}
          {projectTab === "configuration" && <>
          {configDataState !== "ready" && <DataFeedback state={configDataState} t={t} />}
          {projectConfig && <SettingsList key={`${selected}-${projectConfig.revision}`} project={selected} revision={projectConfig.revision} csrf={session.csrf} branchCandidate={projectPendingConfig} config={projectConfig.config} settings={projectConfig.settings || []} t={t} locale={locale} canEdit={isAdmin} disabled={!!projectPendingConfig || configBusy || pendingReadFailed || isAdmin && !pendingReady} onStage={stageSetting} executorBefore={selectedProject && <><ModelConnection local={projectConfig.executor_environment?.backend === "local"} heading={agentSettingsCopy[locale].connection} key={`${session.user.id}:${selected}:${projectConfig.revision}:${projectConfig.model_connection?.checked_at || "untested"}`} project={selectedProject.id} revision={projectConfig.revision} executor={selectedProject.executor} model={String(settingValue(projectConfig.config,`executor.commands.${selectedProject.executor}.model`))} locale={locale} saved={projectConfig.model_connection} readOnly={!isAdmin || selectedProject.archived} onResult={value=>setConfig(current=>current?{...current,model_connection:value}:current)} test={()=>request(`/projects/${encodeURIComponent(selected)}/model-connection-test`,"POST",{},session.csrf)} />
                  <p className="muted">{executorCopy[locale].modelHelp}</p></>} executorAuthentication={selectedProject && <>{isAdmin && !selectedProject.archived && <ExecutorCredentials embedded key={`${session.user.id}:${selected}:${projectConfig.revision}`} project={selectedProject.id} revision={projectConfig.revision} executor={selectedProject.executor} locale={locale} disabled={!!projectPendingConfig || configBusy || pendingReadFailed || !pendingReady || !selectedProject.paused} read={() => request(`/projects/${encodeURIComponent(selected)}/executor-credentials`)} write={(method,body)=>request(`/projects/${encodeURIComponent(selected)}/executor-credentials`,method,body,session.csrf)} onChanged={()=>setConfig(current=>current?{...current,model_connection:null}:current)} />}</>} executorAfter={selectedProject && <><ExecutorEnvironment environment={projectConfig.executor_environment} executor={selectedProject.executor} locale={locale} />{isAdmin && selected && projectConfig && !projectConfig.local_execution && (projectConfig.config.executor as { default?: string } | undefined)?.default === "opencode" && <section className="executor-endpoint"><h3>{t("localEndpoint")}</h3><p className="muted">{t("localEndpointHelp")}</p><p className="muted">{t("localProviderHelp")}</p>{(projectConfig.config.executor as { default?: string } | undefined)?.default === "opencode" && <form key={`${selected}-${projectConfig.revision}`} className="form-grid config-form endpoint-form" onSubmit={saveEndpoint}><fieldset className="endpoint-fields" disabled={!!projectPendingConfig || configBusy || pendingReadFailed || isAdmin && !pendingReady}><FormLegend t={t} /><input type="hidden" name="model" value={(projectConfig.config.executor as { commands?: { opencode?: { model?: string } } }).commands?.opencode?.model || ""} /><Field name="endpoint" label={t("localEndpoint")} type="url" defaultValue={(projectConfig.config.container as { runtime_env?: { OPENAI_BASE_URL?: string } } | undefined)?.runtime_env?.OPENAI_BASE_URL || ""} required /><label>{t("endpointAuth")}<select name="auth_env"><option value="">{t("none")}</option><option value="OPENAI_API_KEY">OPENAI_API_KEY</option></select></label><label>{t("endpointProtocol")}<select name="protocol"><option value="openai-chat-completions">OpenAI chat completions</option></select></label><Field name="timeout_seconds" label={t("endpointTimeout")} type="number" defaultValue={String(projectConfig.local_endpoint_timeout_seconds || 300)} required /><Field name="ca_file" label={t("endpointCa")} defaultValue={(projectConfig.config.container as { runtime_env?: { NODE_EXTRA_CA_CERTS?: string } } | undefined)?.runtime_env?.NODE_EXTRA_CA_CERTS || ""} /><button className="primary form-submit" disabled={!!projectPendingConfig || configBusy || pendingReadFailed || isAdmin && !pendingReady}>{settingsCopy[locale].prepare}</button></fieldset></form>}</section>}
                  {isAdmin && selected && <section className="executor-prices"><h3>{t("estimatedPrices")}</h3><p className="muted">{t("priceHelp")}</p>
                    {priceModel ? <form key={selected} className="form-grid" onSubmit={savePrice}><FormLegend t={t} /><input type="hidden" name="executor" value={priceExecutor} /><input type="hidden" name="model" value={priceModel} /><label><span>{t("effectiveFrom")}<RequiredMark /></span><input name="effective_from" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label><span>{t("inputRate")}<RequiredMark /></span><input name="input_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><label><span>{t("outputRate")}<RequiredMark /></span><input name="output_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><button className="primary form-submit" type="submit">{t("save")}</button></form> : <p className="muted">{t("priceNeedsModel")}</p>}
                    {projectPrices.length > 0 && <PagedTable t={t}><table><thead><tr><th>{t("executor")}</th><th>{t("model")}</th><th>{t("effectiveFrom")}</th><th>{t("inputRate")}</th><th>{t("outputRate")}</th></tr></thead><tbody>{projectPrices.map(price => <tr key={price.id}><td>{price.executor}</td><td>{price.model}</td><td>{price.effective_from}</td><td>{price.input_usd_per_million}</td><td>{price.output_usd_per_million}</td></tr>)}</tbody></table></PagedTable>}
                  </section>}</>} actions={isAdmin && <RawConfiguration key={`${session.user.id}:${selected}:${projectConfig.revision}`} project={selected} locale={locale} />}>
            {isAdmin && <>
            {projectConfig.issues.length > 0 && <div className="alert">{projectConfig.issues.join(" · ")}</div>}
            {projectPendingConfig && <PendingReview config={projectConfig} candidate={projectPendingConfig} project={selectedProject?.display_name || selected} paused={selectedProject?.paused === true} busy={configBusy} locale={locale} t={t} onApply={applyPendingConfig} onDiscard={discardPendingConfig} />}
            {pendingReadFailed && <div className="alert"><p>{settingsCopy[locale].readFailed}</p><p>{settingsCopy[locale].discard}</p><button className="ghost" disabled={configBusy} onClick={() => void discardPendingConfig()}>{t("discardChange")}</button></div>}
            </>}
          </SettingsList>}
          </>}
          {projectTab === "access" && isAdmin && selected && <ProjectAccess key={selected + ":" + viewRefresh} project={selected} csrf={session?.csrf} locale={locale} t={t} onError={setError} onNotice={setNotice} />}
          </div>
        </>}

        {page === "jobs" && projectsState === "ready" && projects.length > 0 && <>
          <section className="panel compact"><div className="workspace-controls"><label htmlFor="jobs-project">{jc.scope}<select id="jobs-project" aria-label={jc.scope} value={jobScope} onChange={event => workspaceProps.onScope(event.target.value)}><option value="">{jc.all}</option>{projects.map(item => <option key={item.id} value={item.id}>{item.display_name || item.name}</option>)}</select></label></div></section>
          {jobsSubtabs}
            <div id="jobs-subtab-panel" role="tabpanel" aria-labelledby={`jobs-subtab-${jobsView}`}>
              {jobsView === "tickets" ? <TicketWorkspace key={`${session.user.id}:${jobScopeProject?.id ?? ""}`} projects={jobScopeProject ? [jobScopeProject] : projects.filter(item => !item.archived)} showProject={!jobScopeProject} locale={locale} csrf={session.csrf} request={request} />
                : <JobWorkspace admin={isAdmin} {...workspaceProps} mode="jobs" run={requestedRun} />}
            </div>
        </>}

        {page === "metrics" && projectsState === "ready" && projects.length > 0 && statisticsView(false)}

        {page === "administration" && isAdmin && <div className="two-column">
          <section className="panel wide-panel"><h2>{t("auditRetention")}</h2><p className="muted">{t("auditRetentionShort")}</p>{auditPolicy && <>
            <Chips className="audit-limits" items={[[t("auditDays"), auditPolicy.retention_days == null ? t("unlimitedValue") : formatNumber(auditPolicy.retention_days)], [t("auditMib"), auditPolicy.max_bytes == null ? t("unlimitedValue") : formatNumber(auditPolicy.max_bytes / 1024**2)]]} />
            <form key={`${auditPolicy.retention_days}-${auditPolicy.max_bytes}`} className="inline-form audit-policy-form" onSubmit={saveAuditPolicy}><label>{t("auditDays")}<input name="retention_days" type="number" min="0" max="36500" step="1" defaultValue={auditPolicy.retention_days ?? 0} /></label><label>{t("auditMib")}<input name="max_mib" type="number" min="0" max="1024" step="any" defaultValue={auditPolicy.max_bytes == null ? 0 : auditPolicy.max_bytes / 1024**2} /></label><button className="primary" type="submit">{t("save")}</button></form></>}</section>
          <section className="panel wide-panel" role="status" aria-live="polite">
            <div className="system-status-row">
              <span className="system-indicator"><span>{t("workerReadiness")}</span><strong className={`readiness readiness-${workerStatus}`}>{t(workerStatus === "ready" ? "workerReady" : workerStatus === "unavailable" ? "workerUnavailable" : workerStatus === "error" ? "workerCheckFailed" : "workerChecking")}</strong></span>
              <span className="system-indicator"><span>{t("storageStatus")}</span><strong className={`readiness readiness-${storageError ? "error" : storageStatus?.low ? "unavailable" : storageStatus ? "ready" : "checking"}`}>{t(storageError ? "storageCheckFailed" : storageStatus?.low ? "storageLow" : storageStatus ? "storageHealthy" : "workerChecking")}</strong></span>
            </div>
            {storageGroups.length === 1 ? <p className="muted">{t("storageShared").replace("{free}", gib(storageGroups[0].free)).replace("{total}", gib(storageGroups[0].total))}</p>
              : storageGroups.length > 1 && <PagedTable t={t}><table><thead><tr><th>{t("storageVolume")}</th><th>{t("storageFree")}</th><th>{t("status")}</th></tr></thead><tbody>{storageGroups.map(group => <tr key={group.id}><td>{group.names.join(", ")}</td><td>{gib(group.free)} GiB</td><td>{t(group.low ? "storageLow" : "storageHealthy")}</td></tr>)}</tbody></table></PagedTable>}
          </section>
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

        {page === "help" && <HelpCenter locale={locale} topic={helpTopic} onNavigate={navigateHref} />}
        {page === "settings" && <div className="two-column"><section className="panel"><h2>{t("appearance")}</h2><div className="form-stack"><label>{t("language")}<select aria-label={t("language")} value={locale} onChange={event => updatePreference("language", event.target.value)}>{Object.entries(localeNames).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>{t("theme")}<select aria-label={t("theme")} value={theme} onChange={event => updatePreference("theme", event.target.value)}><option value="system">{t("system")}</option><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option></select></label></div></section><section className="panel"><h2>{t("changePassword")}</h2><form className="form-stack" onSubmit={changePassword}><FormLegend t={t} /><Field name="current" label={t("currentPassword")} type="password" required /><Field name="replacement" label={t("newPassword")} type="password" required minLength={8} hint={t("passwordRule")} /><button className="primary">{t("save")}</button></form></section>
        </div>}
  </DashboardShell>;
}

type Chip = [label: string, value: string, context?: string];
function Chips({ items, className }: { items: Chip[]; className?: string }) {
  return <dl className={className ? `metric-chips ${className}` : "metric-chips"}>{items.map(([label, value, context]) => <div key={label}><dt>{label}</dt><dd>{value}{context && <small>{context}</small>}</dd></div>)}</dl>;
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
  const show = (value: unknown) => candidate.key === "review.on_pipeline_failure" && pipelineFailureValue(value, locale) !== null ? pipelineFailureValue(value, locale) : candidate.key === "delivery.draft" && publicationValue(value, locale) !== null ? publicationValue(value, locale) : value == null ? copy.unknown : value === "" ? t("settingNoDefault") : typeof value === "object" ? JSON.stringify(value) : String(value);
  const rows: Array<{ label: string; active: unknown; proposed: unknown }> = [{ label: executorSettingLabel(meta?.key || candidate.key,locale) || branchSettingLabel(candidate.key, locale) || implementationSettingLabel(candidate.key, locale) || localizedSettingLabel(candidate.key, locale) || lifecycleCopy[locale].labels[candidate.key] || (candidate.key === "review.on_pipeline_failure" ? pipelineFailureCopy[locale].label : candidate.key === "labels.control.exclude" ? excludeLabelCopy[locale].label : candidate.key === "delivery.target_branch" ? targetBranchCopy[locale].label : candidate.key === "delivery.reviewers" ? reviewerCopy[locale].label : candidate.key === "delivery.draft" ? publicationCopy[locale].label : locale === "en" ? settingLabel(meta?.key || candidate.key) : t("config")), active, proposed: candidate.proposed_value }];
  if (candidate.key === "executor.selection" && validExecutorSelection(candidate.proposed_value)) {
    const selected=candidate.proposed_value, current=executorSelectionDraft(config.config), c=agentSettingsCopy[locale];
    rows.splice(0,1,{label:c.agent,active:current.agent,proposed:selected.agent},{label:c.command,active:current.command,proposed:selected.command},{label:c.model,active:current.model,proposed:selected.model});
  }
  if (candidate.endpoint) {
    rows.push({ label: t("model"), active: settingValue(config.config, "executor.commands.opencode.model"), proposed: candidate.endpoint.model });
    rows.push({ label: t("endpointProtocol"), active: config.local_endpoint?.protocol, proposed: candidate.endpoint.protocol });
    rows.push({ label: t("endpointAuth"), active: config.local_endpoint ? config.local_endpoint.auth_env ?? t("settingNoDefault") : undefined, proposed: candidate.endpoint.auth_env ?? t("settingNoDefault") });
    rows.push({ label: t("endpointTimeout"), active: config.local_endpoint_timeout_seconds, proposed: candidate.endpoint.timeout_seconds });
    rows.push({ label: t("endpointCa"), active: settingValue(config.config, "container.runtime_env.NODE_EXTRA_CA_CERTS"), proposed: candidate.endpoint.ca_file ?? t("settingNoDefault") });
  }
  // Candidate values are validated JSON; property order is immaterial, array order is retained.
  const canonical = (value: unknown): string => Array.isArray(value) ? `[${value.map(canonical).join(",")}]`
    : value !== null && typeof value === "object" ? `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(",")}}`
    : JSON.stringify(value ?? null);
  const changed = rows.filter(row => canonical(row.active) !== canonical(row.proposed));
  const unchanged = changed.length === 0 && !candidate.execution_plan;
  const compact = compactReviewCopy[locale];
  const comparison = (items: typeof rows, className: string) => <table className={`candidate-table ${className}`}><thead><tr><th scope="col">{compact.setting}</th><th scope="col">{copy.active}</th><th scope="col">{copy.proposed}</th></tr></thead><tbody>{items.map(row => <tr key={row.label}><th scope="row">{row.label}</th><td data-label={copy.active}>{show(row.active)}</td><td data-label={copy.proposed}>{show(row.proposed)}</td></tr>)}</tbody></table>;
  const stale = candidate.base_revision !== config.revision;
  const external = !candidate.endpoint && !BRANCH_NAMING_KEYS.has(candidate.key) && !CHOSEN_ENVIRONMENT_KEYS.has(candidate.key) && ["container.", "execution.", "local.", "worktree."].some(prefix => candidate.key.startsWith(prefix));
  const blocked = unchanged || external || stale || candidate.restart_required && !paused;
  const reviewText = [copy.project + ": " + project, ...rows.map(row => `${row.label}: ${copy.active}: ${show(row.active)} → ${copy.proposed}: ${show(row.proposed)}`), copy.base + ": " + candidate.base_revision, copy.candidate + ": " + candidate.candidate_revision].join("\n");
  return <div className="import-preview candidate-review"><h3 ref={heading} tabIndex={-1}>{t("pendingChange")}</h3>
    <p className="muted"><strong>{copy.project}:</strong> {project}</p>
    {changed.length > 0 && comparison(changed, "candidate-changes")}
    {unchanged && <p role="status">{compact.unchanged}</p>}
    {candidate.execution_plan && <ExecutionPlanReview plan={candidate.execution_plan} locale={locale} />}
    {candidate.restart_required && <p className={!paused ? "alert" : "muted"}>{copy.pause}</p>}{stale && <p className="alert">{copy.stale}</p>}
    {external && <p role="note">{externalEnvironmentCopy[locale].external}</p>}
    <div className="button-row candidate-actions"><button className="primary" disabled={busy || blocked} onClick={() => void onApply()}>{t("apply")}</button><button className="ghost" disabled={busy} onClick={() => void onDiscard()}>{t("discardChange")}</button></div>
    <details className="candidate-details"><summary>{copy.details}</summary>
      <h4>{compact.complete}</h4>{comparison(rows, "candidate-complete")}
      <h4>{copy.effect}</h4><p>{candidate.endpoint ? copy.endpoint : candidate.key === "executor.selection" ? agentSettingsCopy[locale].setup : settingHelp(meta?.key || candidate.key, locale)}</p><p>{copy.future}</p>
      <p>{copy.idle}</p><p>{copy.discard}</p>
      <p>{copy.prepared}: <time dateTime={candidate.created_at}>{new Date(candidate.created_at).toLocaleString(locale)}</time></p>
      <p><code>{candidate.key}</code></p><p>{copy.base}: <code>{candidate.base_revision}</code></p><p>{copy.candidate}: <code>{candidate.candidate_revision}</code></p>
      <div className="button-row"><button className="ghost" onClick={() => void navigator.clipboard.writeText(reviewText).then(() => setCopied(true)).catch(() => setCopied(false))}>{copy.copy}</button>{copied && <span role="status">{copy.copied}</span>}</div>
    </details>
  </div>;
}

function SettingsList({ executorOnly=false, project, revision, csrf, branchCandidate, config, settings, t, locale, canEdit, disabled, onStage, actions, children, header, executorBefore, executorAfter, executorAuthentication }: { executorBefore?:ReactNode; executorAfter?:ReactNode; executorAuthentication?:ReactNode; project?: string; revision?: string; csrf?: string; branchCandidate?: PendingConfig | null; header?: ReactNode; actions?: ReactNode; children?: ReactNode; executorOnly?:boolean; config: Record<string, unknown>; settings: SettingMeta[]; t: (key: MessageKey) => string; locale: Locale; canEdit: boolean; disabled: boolean; onStage: (key: string, value: string) => Promise<boolean> }) {
  const [editing, setEditing] = useState("");
  // Image suggestions from the server while the image row is being edited.
  const [serverImages, setServerImages] = useState<ServerImages | null>(null);
  useEffect(() => {
    if (editing !== "container.image") return;
    let active = true;
    setServerImages(null);
    void readServerImages(String(settingValue(config, "container.runtime") ?? "docker")).then(value => { if (active) setServerImages(value); });
    return () => { active = false; };
  }, [editing, config]);
  const [draft, setDraft] = useState("");
  const [branchPreview, setBranchPreview] = useState<BranchPreview | null>(null);
  const [branchFailure, setBranchFailure] = useState("");
  const template = editing === "worktree.branch_template" ? draft : branchCandidate?.key === "worktree.branch_template" ? String(branchCandidate.proposed_value) : String(settingValue(config, "worktree.branch_template") ?? "");
  const rule = editing === "worktree.branch_rule" ? draft : branchCandidate?.key === "worktree.branch_rule" ? String(branchCandidate.proposed_value) : String(settingValue(config, "worktree.branch_rule") ?? "");
  const branchIdentity = JSON.stringify([project, revision, template, rule]);
  const currentPreview = branchPreview && branchPreview.revision === revision && branchPreview.template === template && branchPreview.rule === rule ? branchPreview : null;
  useEffect(() => {
    if (executorOnly || !project || !revision || !csrf) return;
    let current = true;
    const timer = window.setTimeout(() => {
      void request<unknown>(`/projects/${encodeURIComponent(project)}/config/branch-preview`, "POST", { template, rule, revision }, csrf).then(result => {
        if (!current) return;
        if (!validBranchPreview(result) || result.revision !== revision || result.template !== template || result.rule !== rule || result.slug !== settingValue(config, "agent.slug")) throw new Error("invalid preview");
        setBranchPreview(result); setBranchFailure("");
      }).catch(() => { if (current) { setBranchPreview(null); setBranchFailure(branchIdentity); } });
    }, 250);
    return () => { current = false; window.clearTimeout(timer); };
  }, [executorOnly, project, revision, csrf, template, rule, branchIdentity]);
  const groups = settingGroups(settingRows(config, settings).filter(row => settingVisible(row.key, executorOnly, String(settingValue(config,"executor.default")), String(settingValue(config,"execution.backend") ?? "container"))), false);
  const copy = settingsCopy[locale];
  const shown = (value: unknown) => value == null || value === "" ? "—" :
    Array.isArray(value) || typeof value === "object" ? JSON.stringify(value) : String(value);
  const label = (row: SettingRow) => settingDisplayLabel(row.key, locale);
  const editorCopy = implementationEditorCopy[locale];
  const typedKinds = ["duration", "retry-delays", "stage-timeouts"];
  const typedValue = (row: SettingRow) => {
    if (["agent-selection","credential-names"].includes(row.input)) {
      try { const parsed=JSON.parse(draft); return (row.input==="agent-selection" ? validExecutorSelection(parsed) : validCredentialNames(parsed)) ? draft : null; } catch { return null; }
    }
    return typedKinds.includes(row.input) ? implementationDraft(row.input, draft) : draft;
  };
  let stageValues: Record<string, number> = {};
  try { const parsed = JSON.parse(draft); if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) stageValues = parsed; } catch { /* Incomplete drafts cannot be prepared. */ }
  const submit = async (event: FormEvent<HTMLFormElement>, row: SettingRow) => {
    event.preventDefault();
    if (BRANCH_NAMING_KEYS.has(row.key) && !currentPreview?.valid) return;
    const value = row.input === "reviewers" ? JSON.stringify(draft.split(/\r?\n/).map(name => name.trim()).filter(Boolean)) : typedValue(row);
    if (value === null) return;
    if (await onStage(row.editKey, value)) setEditing("");
  };
  const editor = (row:SettingRow) => <form className="setting-editor" onSubmit={event => void submit(event, row)}>
          {row.input === "agent-selection" ? <ExecutorSelectionEditor value={draft} config={config} settings={settings} locale={locale} disabled={disabled} onChange={setDraft}/>
          : /^executor\.commands\.[^.]+\.command$/.test(row.key) && settingValue(config,"execution.backend")==="local" ? <LocalExecutorPicker
            agent={row.key.split(".")[2]} value={draft} onChange={setDraft} locale={locale} disabled={disabled} autoFill={false}/>
          : row.input === "credential-names" ? <CredentialNamesEditor value={draft} choices={row.choices} locale={locale} disabled={disabled} onChange={setDraft}/>
          : row.input === "duration" ? <div className="duration-inputs">
            <label>{editorCopy.amount}<input type="number" min={1} step={1} aria-label={label(row)} aria-describedby={`help-${row.key}`} disabled={disabled} value={durationParts(draft).amount} onChange={event => setDraft(event.target.value + durationParts(draft).unit)} /></label>
            <label>{editorCopy.unit}<select aria-label={editorCopy.unit} disabled={disabled} value={durationParts(draft).unit} onChange={event => setDraft(durationParts(draft).amount + event.target.value)}>{Object.entries(editorCopy.units).map(([unit, name]) => <option key={unit} value={unit}>{name}</option>)}</select></label>
          </div> : row.input === "stage-timeouts" ? <div className="stage-timeout-inputs">{executionStages.map((stage, index) => {
            const values = stageValues;
            const custom = Object.hasOwn(values, stage);
            const general = Number(settingValue(config, "budgets.per_gate_timeout_seconds"));
            return <div className="stage-timeout-row" key={stage}>
              <label>{editorCopy.stages[index]}<select aria-label={editorCopy.stages[index]} disabled={disabled} value={custom ? "custom" : "general"} onChange={event => { const next = {...values}; if (event.target.value === "general") delete next[stage]; else next[stage] = general; setDraft(JSON.stringify(next)); }}><option value="general">{editorCopy.general}</option><option value="custom">{editorCopy.custom}</option></select></label>
              {custom ? <label>{editorCopy.seconds}<input type="number" min={1} step={1} aria-label={`${editorCopy.stages[index]} ${editorCopy.seconds}`} disabled={disabled} value={values[stage] || ""} onChange={event => setDraft(JSON.stringify({...values, [stage]: Number(event.target.value)}))} /></label> : <small>{general} {editorCopy.seconds.toLowerCase()}</small>}
            </div>;
          })}</div> : row.input === "retry-delays" ? <><textarea rows={6} aria-label={label(row)} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} required /><p className="muted">{editorCopy.schedule}</p></> : row.input === "boolean" || row.input === "choice"
            ? <select aria-label={label(row)} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)}>{row.input === "choice" && !row.choices.includes(draft) && <option value={draft} disabled>{draft}</option>}{(row.input === "boolean" ? ["true", "false"] : row.choices).map(option => <option key={option} value={option}>{row.key === "review.on_pipeline_failure" ? pipelineFailureValue(option, locale) ?? option : row.key === "delivery.draft" ? publicationValue(option, locale) : option}</option>)}</select>
            : row.input === "reviewers" ? <textarea rows={6} aria-label={label(row)} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} />
            : <input aria-label={label(row)} type={row.input === "number" ? "number" : "text"} step={row.step} min={row.minimum ?? undefined} max={row.maximum ?? undefined} maxLength={BRANCH_NAMING_KEYS.has(row.key) ? 512 : undefined} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} required={row.input === "number"}
              list={row.key === "container.image" && serverImages?.images.length ? "setting-image-options" : undefined} />}
          {row.key === "container.image" && !!serverImages?.images.length && <datalist id="setting-image-options">{serverImages.images.map(name => <option value={name} key={name} />)}</datalist>}
          {row.key === "container.image" && serverImages && (!serverImages.available ? <p className="field-hint">{enrollmentCopy[locale].imagesUnavailable}</p>
            : draft.trim() && !serverImages.images.includes(draft.trim()) && <p className="field-hint" role="status">{enrollmentCopy[locale].imageMissing}</p>)}
          <div className="button-row"><button className="primary" disabled={disabled || typedValue(row) === null || BRANCH_NAMING_KEYS.has(row.key) && !currentPreview?.valid || row.input === "choice" && !row.choices.includes(draft)}>{copy.prepare}</button><button type="button" className="ghost" onClick={() => setEditing("")}>{t("cancel")}</button></div>
          {typedValue(row) === null && <p role="alert">{editorCopy.invalid}</p>}
        </form>;
  const renderRow = (row:SettingRow) => <div className="setting-row" key={row.key} id={`setting-${row.key}`} tabIndex={-1}>
        <div>
          <strong>{label(row)}</strong><p className="setting-essential" id={`help-${row.key}`}>{row.key === "container.system_packages" ? systemPackageCopy[locale].help : row.key === "executor.default" ? agentSettingsCopy[locale].setup : row.key === "executor.env_keys" ? agentSettingsCopy[locale].variableHelp : settingHelp(row.key, locale) ?? t("settingGeneralHelp")}</p>
          {row.source !== "project" && <span className="setting-badge">{t("settingDefault")}</span>}
          {canEdit && row.input !== "none" && row.restart && <small className="setting-note">{t("settingRestartShort")}</small>}
          {canEdit && row.input === "none" && <small className="setting-note">{t("settingNotEditableShort")}</small>}
          {editing === row.key && row.input === "agent-selection" && <p className="muted">{credentialEditorCopy[locale].inline}</p>}
        </div>
        {editing === row.key ? editor(row) : editing === "executor.default" && /^executor\.commands\.[^.]+\.(command|model)$/.test(row.key) ? <div className="setting-editor executor-related-editor"><small>{copy.proposed}</small><ExecutorSelectionEditor field={row.key.endsWith(".command") ? "command" : "model"} value={draft} config={config} settings={settings} locale={locale} disabled={disabled} onChange={setDraft}/></div> : <div><div className="setting-value-heading"><small>{copy.active}</small>
          {canEdit && row.input !== "none" && editing !== row.key && <button type="button" className="text-button" disabled={disabled} aria-label={`${t("editSetting")} ${label(row)}`} data-edit-key={row.editKey} onClick={() => { setEditing(row.key); setDraft(row.input === "agent-selection" ? JSON.stringify(executorSelectionDraft(config)) : ["reviewers", "retry-delays"].includes(row.input) && Array.isArray(row.value) ? row.value.join("\n") : editValue(row.value)); }}>{t("editSetting")}</button>}
        </div><code>{row.key === "review.on_pipeline_failure" ? pipelineFailureValue(row.value, locale) ?? shown(row.value) : row.key === "delivery.draft" ? publicationValue(row.value, locale) : shown(row.value)}</code><small>{t("settingDefaultValue")}: {hasDefault(row.defaultValue) ? row.key === "review.on_pipeline_failure" ? pipelineFailureValue(row.defaultValue, locale) ?? shown(row.defaultValue) : row.key === "delivery.draft" ? publicationValue(row.defaultValue, locale) : shown(row.defaultValue) : t("settingNoDefault")}</small></div>}

      </div>;
  return <section className="panel" id="project-settings">
    {header ?? <div className="panel-heading"><div className="heading-with-help"><h2>{executorOnly ? executorCopy[locale].tab : t("projectSettings")}</h2>{!executorOnly && <HelpLink topic={CONTEXT_TOPICS.projectSettings} locale={locale} />}</div>{actions}</div>}
    {!canEdit && <p className="muted">{copy.readOnly}</p>}
    {children}
    {groups.length === 0 ? <Empty label={t("settingsNoneSet")} /> : <div className="setting-groups">{groups.map(group => {
      return <details key={group.name} data-setting-purpose={group.name} open={executorOnly}>
      <summary>{copy[group.name as keyof typeof copy]} <span className="muted">({group.rows.length})</span></summary>
      {group.name === "executor" && <div className="executor-settings-content executor-connection-area">{executorBefore}</div>}
      {group.name === "executor" && canEdit && settingValue(config,"execution.backend")==="local" && <LocalExecutionIdentity locale={locale}/>}
      {group.name === "technical" && <p className="muted">{technicalSettingsHelp[locale]}</p>}
      {group.name === "reviews" && settingValue(config, "delivery.target_branch") !== undefined && <div className="setting-row setting-reference">
        <div><strong>{copy.integrationBranch}</strong><p className="setting-essential">{copy.integrationBranchHelp}</p>
        <a className="text-button" href="#setting-delivery.target_branch" onClick={event => {
          const target = document.getElementById("setting-delivery.target_branch");
          if (!target) return;
          event.preventDefault();
          const category = target.closest("details");
          if (category) category.open = true;
          target.focus(); target.scrollIntoView({ block: "center" });
        }}>{copy.integrationBranchLink}</a></div>
        <div><div className="setting-value-heading"><small>{copy.active}</small></div><code>{shown(settingValue(config, "delivery.target_branch"))}</code></div>
      </div>}
      <div className="setting-list">{group.rows.filter(row => !STATUS_LABEL_KEYS.has(row.key) && !settingSubgroup(row.key)).map(renderRow)}
        {group.name === "repository" && <section className="branch-naming-preview" aria-label={branchNamingCopy[locale].preview}>
          <h3>{branchNamingCopy[locale].preview}</h3>
          <p>{branchNamingCopy[locale].variables}</p>
          <p><code>{`{slug} = ${String(settingValue(config, "agent.slug") ?? "")}, {iid} = 1, {run_id} = sample-run-1`}</code></p>
          <div role="status" aria-live="polite" aria-atomic="true">
            {currentPreview?.name && <p className="branch-example-name"><code>{currentPreview.name}</code></p>}
            {!currentPreview ? <p>{branchFailure === branchIdentity ? branchNamingCopy[locale].unavailable : branchNamingCopy[locale].checking}</p>
              : currentPreview.valid ? <p>{rule ? branchNamingCopy[locale].matched : branchNamingCopy[locale].noRule}</p>
                : <ul>{currentPreview.issues.map(issue => <li key={issue}>{branchNamingCopy[locale].issues[issue as keyof typeof branchNamingCopy.en.issues]}</li>)}</ul>}
          </div>
          <p className="muted">{branchNamingCopy[locale].example}</p>
        </section>}
        {(["clarification", "recovery", "stageLimits", "statisticsFiles", "authentication", "localTechnical"] as const).map(topic => {
          const rows = group.rows.filter(row => settingSubgroup(row.key) === topic);
          return rows.length > 0 && <details className="setting-topic" data-setting-topic={topic} key={topic}>
            <summary>{topic === "localTechnical" ? setupCopy[locale].advanced : copy[topic]} <span className="muted">({rows.length})</span></summary>
            {topic === "localTechnical" && <p className="field-hint">{setupCopy[locale].overrideHelp}</p>}
            <div className="setting-list">{rows.map(renderRow)}</div>
            {topic === "authentication" && executorAuthentication}
          </details>;
        })}
        {group.rows.some(row => STATUS_LABEL_KEYS.has(row.key)) && <details className="status-label-settings">
          <summary>{lifecycleCopy[locale].title} <span className="muted">({group.rows.filter(row => STATUS_LABEL_KEYS.has(row.key)).length})</span></summary>
          <p className="muted">{lifecycleCopy[locale].help}</p>
          <div className="setting-list">{group.rows.filter(row => STATUS_LABEL_KEYS.has(row.key)).map(renderRow)}</div>
        </details>}
      </div>
      {group.name === "executor" && <div className="executor-settings-content">{executorAfter}</div>}
      {group.name === "repository" && canEdit && project && csrf && <ForgeLabelsAction locale={locale} disabled={disabled}
        run={() => request(`/projects/${encodeURIComponent(project)}/labels/ensure`, "POST", undefined, csrf)} />}
    </details>})}</div>}
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

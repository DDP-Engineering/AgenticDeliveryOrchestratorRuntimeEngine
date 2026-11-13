/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { Children, Fragment, cloneElement, isValidElement, useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactElement, type ReactNode } from "react";
import { aggregateMetrics, aggregateUsage } from "./metrics";
import { sortUsageRows, type UsageSortKey } from "./usageSort";
import { PasswordField } from "./PasswordField";
import { messages, type Locale, type MessageKey } from "./i18n";
import { ModelConnection, validModelEvidence, type ModelEvidence } from "./ModelConnection";
import { agentSettingsCopy, agentValue, executorSettingHelp, internetCopy, searchKeyNeeded } from "./executorSettings";
import { localCopy } from "./localExecution";
import { candidateMatchesEdits, pendingSettingEdits, normalizeSettingDraft, prepareSettingDrafts, recoverSettingDrafts, settingDraftValue, settingImpacts, settingsSaveCopy, sameSettingValue, type SettingEdit, type SettingDrafts } from "./settingsSave";
import { CredentialNamesEditor } from "./CredentialNamesEditor";
import { ExecutorCredentials, executorCopy } from "./ExecutorCredentials";
import { ChatGptSignIn } from "./ChatGptSignIn";
import { AgentConnectionEditor } from "./AgentConnectionEditor";
import { CHATGPT, CONNECTION_KEY, connectionCopy, connectionOf } from "./agentConnection";
import { RepositoryConnection } from "./RepositoryConnection";
import { ReadinessEvidence, readinessDetailsLabel, readinessCloseLabel } from "./ReadinessEvidence";
import { readReadiness, validProjectVerification, type ProjectReadiness } from "./readiness";
import { AuditHistory } from "./AuditHistory";
import { groupRelease, type Release } from "./releaseNotes";
import { auditPolicyPayload } from "./auditPolicy";
import { ApiError, describeError } from "./errors";
import { createRequestScope, rawRequest, type Request } from "./request";
import { createReadController, startVisiblePolling, type ReadController, type ReadSnapshot } from "./polling";
import { formatRoute, normalizeRoute, parseRoute, type ProjectTab, type Route } from "./routes";
import { BATCH_KEY, hasDefault, settingGroups, settingRows, type SettingMeta, type SettingRow, settingValue, validSettingCatalog, validPendingConfig, type PendingConfig, settingVisible, settingSubgroup, STATUS_LABEL_KEYS, BRANCH_NAMING_KEYS, validBranchPreview, type BranchPreview, connectionRowVisible } from "./settings";
import { ExecutorEnvironment, type ExecutorEnvironmentInfo } from "./ExecutorEnvironment";
import { ExecutionPlanReview } from "./ExecutionPlanReview";
import { type ExecutionPlan } from "./executionPlan";
import { settingHelp } from "./settingHelp";
import { durationParts, executionStages, implementationEditorCopy } from "./implementationSettings";
import { compactReviewCopy, settingsCopy, technicalSettingsHelp, publicationValue, pipelineFailureValue, lifecycleCopy, branchNamingCopy } from "./settingsCopy";
import { RawImportDialog } from "./RawImportDialog";
import { importCopy } from "./importCopy";
import { RawConfiguration } from "./RawConfiguration";
import { EnrollmentWizard } from "./EnrollmentWizard";
import { createReportingRefresh, type ReportingRefresh, type ReportingReport } from "./statistics";
import { StatisticsEvidence, TrendEvidence } from "./StatisticsEvidence";
import { statisticsCopy } from "./statisticsCopy";
import { JobWorkspace } from "./JobWorkspace";
import { SortHeader } from "./SortHeader";
import { jobCopy } from "./jobCopy";
import { outcomeText } from "./operationReason";
import { AccountAccessEditor, AccessReview, validAccount, type Account } from "./UserCreation";
import { AccountActionDialog, type AccountAction } from "./AccountActionDialog";
import { userCopy } from "./userCopy";
import { companyLogo, DashboardShell, type ShellLink } from "./DashboardShell";
import { TicketWorkspace } from "./TicketWorkspace";
import { readPreferences, type Preferences, type TicketBodyMode } from "./ticketPreferences";
import { ticketCopy, operationResultText } from "./ticketCopy";
import { DataFeedback, RefreshFeedback, ProjectEmpty, StatusBadge, type DataState, type ScopedState } from "./Presentation";
import { HelpCenter, HelpLink } from "./HelpCenter";
import { readServerImages, type ServerImages } from "./serverImages";
import { ContainerRuntimePicker } from "./ContainerRuntimePicker";
import { ForgeLabelsAction } from "./ForgeLabels";
import { settingDisplayLabel } from "./settingLabels";
import { enrollmentCopy } from "./enrollmentCopy";
import { DeleteCloneOption } from "./DeleteCloneOption";
import { CONTEXT_TOPICS, type HelpTopic } from "./help/topics.ts";

type User = { id: number; username: string; role: "admin" | "developer"; disabled: boolean; password_change_required?: boolean; factory_password?: boolean; projects?: string[] };
type AccountUser = User & Account;
type Session = { user: User; csrf: string };
type Project = { display_name: string; pickup_state: string; verification: { status: string; checked_at?: string | null; revision?: string | null; checks?: { forge_auth?: boolean } }; validation: { structural_valid: boolean }; verification_requirements: string[]; id: string; name: string; description: string; platform: string; repo: string; runtime: string; executor: string; readiness: string; last_activity: string | null; paused: boolean; archived: boolean; runs: number; invalid_runs: string[] };
type Config = { executor_environment?: ExecutorEnvironmentInfo; local_execution?: { machine: string; account: string; system: string } | null; execution_plan?: ExecutionPlan | null; model_connection?: ModelEvidence | null; config: Record<string, unknown>; revision: string; issues: string[]; settings?: SettingMeta[] };
type Operation = { id: number; status: string; result?: string; reason?: string; detail?: string; action?: string };
/** Refuse malformed or mismatched operation evidence at the API boundary. */
function readOperation(value: unknown, expected?: number): Operation {
  const item = value as Operation;
  if (!item || !Number.isSafeInteger(item.id) || item.id < 1 || (expected !== undefined && item.id !== expected) ||
      !["pending", "running", "succeeded", "failed", "uncertain"].includes(item.status) ||
      [item.result, item.reason, item.detail, item.action].some(part => part !== undefined && typeof part !== "string")) throw new ApiError("unexpected_response");
  return item;
}
type Price = { id: number; executor: string; model: string; effective_from: string; input_usd_per_million: string; output_usd_per_million: string };
type SettingsBlocker = "settings" | "prices" | "credentials" | "chatgpt";
type Page = "overview" | "projects" | "createProject" | "projectDetails" | "jobs" | "metrics" | "administration" | "adminUsers" | "adminAudit" | "settings" | "help";
type MetricsTab = "summary" | "usage" | "quality" | "trends" | "projects";
type ProjectSortKey = "name" | "repo" | "readiness" | "runs" | "last_activity";
const metricsTabLabels: Record<MetricsTab, MessageKey> = {
  summary: "metricsTabSummary", usage: "metricsTabUsage", quality: "metricsTabQuality",
  trends: "metricsTabTrends", projects: "metricsTabProjects",
};
type WorkerStatus = "checking" | "ready" | "busy" | "unknown" | "unavailable" | "error";
type StorageStatus = { threshold_bytes: number; low: boolean; volumes: Array<{ scope: "home" | "project"; project: string | null; free_bytes: number; total_bytes: number; low: boolean; volume_id: string }> };
type AuditPolicy = { retention_days: number | null; max_bytes: number | null };

const localeNames: Record<Locale, string> = { en: "English", fr: "Français", de: "Deutsch", ro: "Română" };
const initialLocale = (): Locale => {
  const saved = localStorage.getItem("adore-language") as Locale | null;
  if (saved && saved in messages) return saved;
  const browser = navigator.language.slice(0, 2) as Locale;
  return browser in messages ? browser : "en";
};

/** Validate account evidence before it can establish or replace a principal. */
function readSession(value: unknown): Session {
  const item = value as Session, user = item?.user;
  if (!item || typeof item.csrf !== "string" || !item.csrf || !user || !Number.isSafeInteger(user.id) || user.id < 1 ||
    typeof user.username !== "string" || !user.username || !["admin", "developer"].includes(user.role) || user.disabled !== false ||
    [user.password_change_required, user.factory_password].some(flag => flag !== undefined && typeof flag !== "boolean") ||
    user.projects !== undefined && (!Array.isArray(user.projects) || user.projects.some(id => typeof id !== "string") || new Set(user.projects).size !== user.projects.length)) throw new ApiError("unexpected_response");
  return item;
}

async function readPrices(request: Request, path: string, signal?: AbortSignal): Promise<Price[]> {
  const prices = await request<Price[]>(path + "/prices", "GET", undefined, undefined,
    signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000));
  const validRate = (value: unknown) => typeof value === "string" && /^\d+(?:\.\d{1,6})?$/.test(value) && Number(value) <= 1000000;
  if (!Array.isArray(prices) || prices.some(row => !row || !Number.isSafeInteger(row.id) || row.id < 1 ||
    typeof row.executor !== "string" || typeof row.model !== "string" ||
    typeof row.effective_from !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(row.effective_from) ||
    !validRate(row.input_usd_per_million) || !validRate(row.output_usd_per_million)) ||
    new Set(prices.map(row => row.id)).size !== prices.length) throw new ApiError("unexpected_response");
  return prices;
}

const sessionPrincipal = (current: Session) => JSON.stringify([current.csrf, current.user.id, current.user.role, [...(current.user.projects ?? [])].sort()]);
type SessionBoundary = { epoch: number; bootstrap: boolean; signingOut?: boolean; session?: Session; error?: unknown; passwordChanged?: boolean; deniedPrincipal?: string };

/** Only a real security-context transition replaces the application instance. */
export default function App() {
  const [boundary, setBoundary] = useState<SessionBoundary>({ epoch: 0, bootstrap: true });
  const replace = (next: Omit<SessionBoundary, "epoch">) => {
    window.history.replaceState(null, "", "/");
    setBoundary(previous => ({ ...next, epoch: previous.epoch + 1 }));
  };
  const denied = (code: string, previous?: Session) => replace({
    bootstrap: !["authentication_required", "csrf_required"].includes(code), error: new ApiError(code),
    deniedPrincipal: previous ? sessionPrincipal(previous) : undefined,
  });
  const signOut = async (csrf?: string) => {
    replace({ bootstrap: false, signingOut: true });
    let error: unknown;
    try { await rawRequest("/session", "DELETE", undefined, csrf, AbortSignal.timeout(30000)); }
    catch (cause) { error = cause; }
    // Do not admit a new sign-in until DELETE settles: its Set-Cookie belongs
    // to the old account. The browser bound does not imply server rollback.
    replace({ bootstrap: false, error });
  };
  if (boundary.signingOut) return <main className="splash" aria-busy="true">{messages[initialLocale()].logout}…</main>;
  return <AppView key={boundary.epoch} boundary={boundary} onDenied={denied}
    onSession={current => replace({ bootstrap: false, session: current })}
    onPasswordChanged={() => replace({ bootstrap: false, passwordChanged: true })} onSignOut={signOut} />;
}

function AppView({ boundary, onDenied, onSession, onPasswordChanged, onSignOut }: {
  boundary: SessionBoundary; onDenied: (code: string, previous?: Session) => void; onSession: (session: Session) => void;
  onPasswordChanged: () => void; onSignOut: (csrf?: string) => Promise<void>;
}) {
  const sessionIdentity = useRef<Session | undefined>(boundary.session);
  const denial = (code: string) => onDenied(code, sessionIdentity.current);
  const transport = useRef<ReturnType<typeof createRequestScope> | null>(null);
  if (!transport.current) transport.current = createRequestScope(denial);
  const request: Request = useCallback((...args) => transport.current!.request(...args), []);
  useLayoutEffect(() => {
    // Development StrictMode replays setup/cleanup on the same instance.
    if (transport.current!.disposed()) transport.current = createRequestScope(denial);
    if (boundary.session) transport.current!.activate();
    return () => transport.current!.dispose();
  }, []);
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [theme, setTheme] = useState(localStorage.getItem("adore-theme") || "system");
  const [session, setSession] = useState<Session | null>(boundary.session?.user.password_change_required ? null : boundary.session ?? null);
  const [ticketBodyMode, setTicketBodyMode] = useState<TicketBodyMode>("rendered");
  const confirmedTicketMode = useRef<TicketBodyMode>("rendered");
  const ticketModePending = useRef(false);
  const [ticketModeBusy, setTicketModeBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<Page>("overview");
  const [viewRefresh, setViewRefresh] = useState(0);
  const projectsPrincipal = JSON.stringify([session?.csrf, session?.user.id, session?.user.role, [...(session?.user.projects ?? [])].sort()]);
  const [projectsScope, setProjectsScope] = useState("");
  const [projectItems, setProjects] = useState<Project[]>([]);
  // Gate synchronously: a changed principal must not render the previous directory
  // during the render before its layout-effect cleanup can cancel owned reads.
  const projects = projectsScope === projectsPrincipal ? projectItems : [];
  const [projectSortKey, setProjectSortKey] = useState<ProjectSortKey>("name");
  const [projectSortDescending, setProjectSortDescending] = useState(false);
  const [selected, setSelected] = useState("");
  const [reportSnapshot, setReportSnapshot] = useState<ReadSnapshot<ReportingReport> | null>(null);
  const [metricFrom, setMetricFrom] = useState("");
  const [metricTo, setMetricTo] = useState("");
  const [metricTimezone, setMetricTimezone] = useState("UTC");
  const [metricGranularity, setMetricGranularity] = useState<"day" | "week" | "month">("day");
  const [metricAllProjects, setMetricAllProjects] = useState(true);
  const [metricsTab, setMetricsTab] = useState<MetricsTab>("summary");
  const [usageSortKey, setUsageSortKey] = useState<UsageSortKey>("date");
  const [usageSortDescending, setUsageSortDescending] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);
  const [configScope, setConfigScope] = useState("");
  const [pendingConfig, setPendingConfig] = useState<PendingConfig | null>(null);
  const [pendingConfigScope, setPendingConfigScope] = useState("");
  const [settingsStale, setSettingsStale] = useState(false);
  const [settingsConfirmation, setSettingsConfirmation] = useState<{
    candidate: PendingConfig; edits: SettingEdit[]; project: string; config: Config;
    resolve: (accepted: boolean) => void;
  } | null>(null);
  const settingsConfirmationResolve = useRef<((accepted: boolean) => void) | null>(null);
  useEffect(() => () => {
    settingsConfirmationResolve.current?.(false);
    settingsConfirmationResolve.current = null;
    setSettingsConfirmation(null);
  }, [selected, session?.user.id]);
  const [prices, setPrices] = useState<Price[]>([]);
  const [pricesScope, setPricesScope] = useState("");
  const usersKey = page === "adminUsers" && session?.user.role === "admin" ? projectsPrincipal : "";
  const [usersSnapshot, setUsersSnapshot] = useState<ReadSnapshot<AccountUser[]> | null>(null);
  const usersRead = usersSnapshot?.key === usersKey ? usersSnapshot : null;
  const users = usersRead?.data ?? [];
  const usersState: DataState = usersRead?.status === "error" ? "error" : usersRead?.data ? "ready" : "loading";
  const [usersAuthority, setUsersAuthority] = useState(false);
  const [usersMutating, setUsersMutating] = useState(false);
  const usersWriting = useRef(false);
  const usersReader = useRef<ReadController | null>(null);
  const liveUsersKey = useRef(usersKey);
  liveUsersKey.current = usersKey;
  const usersReady = !!usersKey && usersRead?.status === "ready" && usersAuthority && !usersMutating;
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
  const [error, setError] = useState<unknown>(boundary.error ?? "");
  const [passwordMismatch, setPasswordMismatch] = useState(false);
  const [passwordSession, setPasswordSession] = useState<Session | null>(boundary.session?.user.password_change_required ? boundary.session : null);
  useEffect(() => { setPasswordMismatch(false); }, [page, session?.csrf, passwordSession?.csrf]);
  const [projectTab, setProjectTab] = useState<ProjectTab>("overview");
  const [jobsView, setJobsView] = useState<"tickets" | "jobs">("tickets");
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [deleteName, setDeleteName] = useState("");
  const [deleteReviewInvalid, setDeleteReviewInvalid] = useState(false);
  const [deleteClone, setDeleteClone] = useState(false);
  const [projectsLoaded, setProjectsLoaded] = useState(false);
  const [configState, setConfigState] = useState<ScopedState>({ key: "", state: "loading" });
  const [jobScope, setJobScope] = useState("");
  const [requestedRun, setRequestedRun] = useState("");
  const [projectDataState, setProjectsState] = useState<DataState>("loading");
  const projectsState = projectsScope === projectsPrincipal ? projectDataState : "loading";
  const [routeReady, setRouteReady] = useState(false);
  const routedProject = useRef<string | null>(null);
  const preserveError = useRef(!!boundary.error);
  const [notice, setNotice] = useState(boundary.passwordChanged ? messages[locale].passwordChanged : "");
  const [importOpen, setImportOpen] = useState(false);
  const lastRefresh = usersRead?.completedAt == null ? null : new Date(usersRead.completedAt);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [operationProject, setOperationProject] = useState("");
  const operationId = useRef<number | null>(null);
  const operationBusy = useRef(false);
  const operationSubmission = useRef(0);
  const operationRequest = useRef<AbortController | null>(null);
  const operationOrigin = useRef("");
  const [projectNotice, setProjectNotice] = useState<{ key: string; text: string } | null>(null);
  const [operationSubmitting, setOperationSubmitting] = useState(false);
  const [operationVisible, setOperationVisible] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const enrollmentGuard = useRef<(() => boolean) | null>(null);
  const registerSettingsGuard = useCallback((guard: (() => boolean) | null) => {
    enrollmentGuard.current = guard;
  }, []);
  // A result is a reread signal, never a component/context identity. Each
  // authority-bearing owner keeps its own edit/mutation guards.
  const refreshView = () => setViewRefresh(value => value + 1);
  // The address of the page shown now, restored when a guarded wizard refuses browser Back.
  const shownUrl = useRef("");
  const [accountAction, setAccountAction] = useState<AccountAction | null>(null);
  useEffect(() => { setAccountAction(null); }, [page, session?.csrf]);
  const aboutTrigger = useRef<HTMLButtonElement>(null);
  // Switching About views removes the pressed button; focus its counterpart so Escape and Tab keep working.
  const aboutSwitch = useRef<HTMLButtonElement>(null);
  const reportingReader = useRef<ReportingRefresh | null>(null);
  const projectsReader = useRef<ReadController | null>(null);
  const projectsHaveSnapshot = useRef(false);
  const configRequest = useRef(0);
  const configRefresh = useRef<((afterWrite?: boolean) => Promise<void>) | null>(null);
  const configMutation = useRef(false);
  const configView = useRef("");
  configView.current = `${page}:${selected}`;
  const settingsVisible = page === "projectDetails" && projectTab === "configuration";
  const settingsPoll = useRef({ blocked: new Set<SettingsBlocker>(), visible: false });
  const invalidateSettingsPoll = () => { settingsPoll.current = { ...settingsPoll.current }; };
  const setSettingsPollBlocked = useCallback((source: SettingsBlocker, block: boolean) => {
    if (settingsPoll.current.blocked.has(source) === block) return;
    const blocked = new Set(settingsPoll.current.blocked);
    if (block) blocked.add(source);
    else blocked.delete(source);
    settingsPoll.current = { ...settingsPoll.current, blocked };
  }, []);
  const blockSettingsEdits = useCallback((block: boolean) => setSettingsPollBlocked("settings", block), [setSettingsPollBlocked]);
  const blockCredentials = useCallback((block: boolean) => setSettingsPollBlocked("credentials", block), [setSettingsPollBlocked]);
  const blockChatGpt = useCallback((block: boolean) => setSettingsPollBlocked("chatgpt", block), [setSettingsPollBlocked]);
  const priceSaving = useRef<HTMLFormElement | null>(null);
  const priceWrite = useRef(0);
  const priceFormRef = useCallback((form: HTMLFormElement | null) => {
    if (!form) setSettingsPollBlocked("prices", false);
  }, [setSettingsPollBlocked]);
  const updatePriceDraft = (form: HTMLFormElement) => {
    const edited = Array.from(form.querySelectorAll<HTMLInputElement>("input:not([type=hidden])"))
      .some(input => input.value !== input.defaultValue || input.validity.badInput);
    setSettingsPollBlocked("prices", priceSaving.current === form || edited);
  };
  useLayoutEffect(() => {
    settingsPoll.current = { ...settingsPoll.current, visible: settingsVisible };
  }, [settingsVisible]);
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
    confirmedTicketMode.current = saved.ticket_body_mode ?? "rendered";
    setTicketBodyMode(confirmedTicketMode.current);
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
    if (tab !== projectTab && enrollmentGuard.current && !enrollmentGuard.current()) return false;
    setRequestedRun("");
    if (tab === "statistics" && tab !== projectTab) setMetricsTab("summary");
    // The Jobs tab opens on Tickets; job detail links select the Jobs sub-tab explicitly.
    if (tab === "jobs" && tab !== projectTab) setJobsView("tickets");
    setProjectTab(tab);
    return true;
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
    if (selectProjectTab(projectTabs[next])) document.getElementById(`project-tab-${projectTabs[next]}`)?.focus();
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
  const liveSelection = useRef({ page, selected }); liveSelection.current = { page, selected };
  const projectViewKey = page === "projectDetails" ? JSON.stringify([projectsPrincipal, selected]) : "";
  const projectActionBinding = (item: Project | null | undefined) => item ? JSON.stringify([item.id, item.name, item.archived, item.paused]) : "";
  const actionContext = projectViewKey && projectsState === "ready" && selectedProject
    ? JSON.stringify([projectViewKey, projectActionBinding(selectedProject)]) : "";
  const liveActionContext = useRef(actionContext); liveActionContext.current = actionContext;
  const operationView = projectViewKey && projectsState === "ready" && selectedProject && selected === operationProject &&
    operationOrigin.current === JSON.stringify([projectsPrincipal, selectedProject.id, selectedProject.name]) ? operation : null;
  const projectActionBusy = operationSubmitting || !!operationView && ["pending", "running"].includes(operationView.status);
  const deleteReviewCurrent = !deleteReviewInvalid && !!actionContext && !!deleteTarget && !!selectedProject?.archived &&
    projectActionBinding(deleteTarget) === projectActionBinding(selectedProject);
  useLayoutEffect(() => {
    // Aborting browser work cannot undo an accepted server command. It does end
    // the old callback's authority to publish notices/results in another view.
    operationSubmission.current += 1;
    operationRequest.current?.abort(); operationRequest.current = null;
    operationBusy.current = false; setOperationSubmitting(false);
    return () => { operationSubmission.current += 1; operationRequest.current?.abort(); };
  }, [actionContext]);
  useLayoutEffect(() => {
    if (deleteTarget && (!actionContext || projectActionBinding(deleteTarget) !== projectActionBinding(selectedProject))) setDeleteReviewInvalid(true);
  }, [actionContext, deleteTarget]);
  useEffect(() => {
    if (!projectNotice) return;
    const timer = window.setTimeout(() => setProjectNotice(null), 5000);
    return () => window.clearTimeout(timer);
  }, [projectNotice]);
  useEffect(() => {
    if (selectedProject?.verification.status === "stale") setProjectReadiness(null);
  }, [selectedProject?.verification.status]);
  const projectConfig = configScope === selected ? config : null;
  const configDataState = configState.key === selected ? configState.state : "loading";
  const projectPendingConfig = pendingConfigScope === selected ? pendingConfig : null;
  const projectPrices = pricesScope === selected ? prices : [];
  // Prices are recorded only for Pi and the model configured for it in Agent and model.
  const priceExecutor = "pi";
  const configuredPriceModel = projectConfig ? settingValue(projectConfig.config, "executor.model") : undefined;
  const priceModel = typeof configuredPriceModel === "string" && configuredPriceModel.trim() ? configuredPriceModel : "";
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
  const projectCell = (id: string) => { const project = projects.find(item => item.id === id); return <td>{project?.name}{project?.repo && <small className="field-hint">{project.repo}</small>}</td>; };
  const scopeLabel = allProjectScope ? t("metricsAllProjects") : selectedProject?.name || "";
  // View controls are excluded from ownership. Principal, immutable scope and
  // reporting query change the key before any passive cleanup/publication.
  const reportKey = session && statisticsVisible && projectsState === "ready" && (allProjectScope || selectedProject)
    ? JSON.stringify([projectsPrincipal, authorizedMetricsKey, allProjectScope ? "all" : selected, metricSuffix]) : "";
  const liveReportKey = useRef(reportKey);
  liveReportKey.current = reportKey;
  const reportState = reportKey && reportSnapshot?.key === reportKey ? reportSnapshot : null;
  const report = reportState?.data ?? null;
  const reportingDataState: DataState = reportState?.status === "error" ? "error" : report ? "ready" : "loading";
  const allUsage = allProjectScope ? report?.usage ?? null : null;
  const globalRows = Object.entries(report?.metrics ?? {});
  const scopedUsageRows = Object.entries(report?.usage ?? {});
  const metrics = !report ? null : allProjectScope ? aggregateMetrics(Object.values(report.metrics), metricTimezone, metricFrom, metricTo) : report.metrics[selected];
  const metricsEmpty = metrics != null && !((metrics.totals.runs || 0) > 0);
  const usage = !report ? null : allProjectScope ? aggregateUsage(Object.values(report.usage)) : report.usage[selected];
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
    let active = true;
    const generation = viewGeneration.current;
    const currentView = () => active && generation === viewGeneration.current;
    if (!boundary.bootstrap && !boundary.session) { setLoading(false); return; }
    (boundary.session ? Promise.resolve(boundary.session) : request<unknown>("/me").then(readSession)).then(async current => {
      // A denial followed by an unchanged /me is not fresh permission for the
      // rejected resource. Stop at explicit sign-in instead of a retry loop.
      if (boundary.deniedPrincipal === sessionPrincipal(current) && !current.user.password_change_required) throw boundary.error;
      sessionIdentity.current = current;
      transport.current!.activate();
      try {
        const saved = readPreferences(await request<unknown>("/me/preferences"));
        if (currentView()) applyPreferences(saved);
      } catch (cause) { if (currentView()) setError(cause); }
      if (!currentView()) return;
      if (current.user.password_change_required) setPasswordSession(current);
      else setSession(current);
    }).catch(cause => {
      if (!currentView()) return;
      setSession(null);
      if (!(cause instanceof ApiError) || cause.code !== "authentication_required") setError(cause);
    }).finally(() => { if (currentView()) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!session?.user.factory_password) return;
    const principal = projectsPrincipal;
    const reader = createReadController<Session>({ key: principal, deadlineMs: 30000,
      read: async signal => readSession(await request("/me", "GET", undefined, undefined, signal)),
      publish: value => {
        if (value.refreshing) return;
        if (value.status === "error") {
          if (!transport.current!.disposed()) { transport.current!.dispose(); onDenied("authentication_required"); }
          return;
        }
        if (value.status !== "ready" || !value.data) return;
        const current = value.data;
        const nextPrincipal = sessionPrincipal(current);
        if (current.user.password_change_required || nextPrincipal !== principal) {
          transport.current!.dispose(); onSession(current);
        } else setSession(current);
      },
    });
    const stop = startVisiblePolling(() => { void reader.refresh(); }, 15000);
    return () => { stop(); reader.dispose(); };
  }, [projectsPrincipal, session?.user.factory_password]);

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

  /** One in-flight mode save per session; never replay a previous account's result. */
  const updateTicketBodyMode = (value: TicketBodyMode) => {
    const account = session;
    if (!account || ticketModePending.current) return;
    ticketModePending.current = true;
    setTicketModeBusy(true); setError("");
    setTicketBodyMode(value);
    const generation = viewGeneration.current;
    void request<unknown>("/me/preferences", "PATCH", { ticket_body_mode: value }, account.csrf)
      .then(response => {
        const saved = readPreferences(response);
        if (saved.ticket_body_mode !== value) throw new ApiError("unexpected_response");
        if (generation !== viewGeneration.current) return;
        // Other preferences may have changed while this request was in flight.
        confirmedTicketMode.current = value;
      })
      .catch(cause => {
        if (generation !== viewGeneration.current) return;
        setTicketBodyMode(confirmedTicketMode.current); setError(cause);
      })
      .finally(() => {
        if (generation !== viewGeneration.current) return;
        ticketModePending.current = false; setTicketModeBusy(false);
      });
  };

  const overviewProjects = page === "overview" || page === "projectDetails" && projectTab === "overview";
  // Equivalent /me objects (the factory-password notice) do not start new owners.
  const projectsOwnerKey = session ? JSON.stringify([projectsPrincipal, overviewProjects]) : "";
  const liveProjectsOwner = useRef(projectsOwnerKey);
  liveProjectsOwner.current = projectsOwnerKey;
  const refreshProjects = useCallback(() => projectsReader.current?.refresh() ?? Promise.resolve(), []);

  useLayoutEffect(() => {
    if (!projectsOwnerKey) return;
    const key = projectsOwnerKey;
    const generation = viewGeneration.current;
    if (projectsScope !== projectsPrincipal) {
      projectsHaveSnapshot.current = false;
      setProjects([]); setProjectsScope(projectsPrincipal);
      setProjectsLoaded(false); setProjectsState("loading");
    }
    const reader = createReadController<Project[]>({
      key, deadlineMs: 30000,
      read: async signal => {
        const items = await request<Project[]>("/projects", "GET", undefined, undefined, signal).catch((cause: unknown) => {
          if (signal.aborted || !overviewProjects || !(cause instanceof ApiError) || cause.code !== "run_state_corrupt") throw cause;
          return request<Project[]>("/projects?overview=true", "GET", undefined, undefined, signal);
        });
        if (!Array.isArray(items) || items.some(item => !item || typeof item.id !== "string" || typeof item.name !== "string" ||
          typeof item.repo !== "string" || typeof item.display_name !== "string" || !/^[a-f0-9]{32}$/.test(item.id) ||
          typeof item.readiness !== "string" || typeof item.paused !== "boolean" || typeof item.archived !== "boolean" ||
          !validProjectVerification(item.verification, item.id, item.verification_requirements) ||
          !item.validation || typeof item.validation.structural_valid !== "boolean" ||
          item.verification.checked_at != null && (typeof item.verification.checked_at !== "string" || !Number.isFinite(Date.parse(item.verification.checked_at))) ||
          item.verification.revision != null && (typeof item.verification.revision !== "string" || !/^[a-f0-9]{64}$/.test(item.verification.revision)) ||
          item.last_activity !== null && (typeof item.last_activity !== "string" || !Number.isFinite(Date.parse(item.last_activity))) ||
          !Number.isSafeInteger(item.runs) || item.runs < 0) || new Set(items.map(item => item.id)).size !== items.length) throw new ApiError("unexpected_response");
        return items;
      },
      publish: snapshot => {
        if (key !== liveProjectsOwner.current || generation !== viewGeneration.current) return;
        if (snapshot.status === "ready" && snapshot.data) {
          const items = snapshot.data;
          // Reuse the route's explicit unavailable transition rather than put a
          // different project underneath a removed project's current heading.
          const shown = liveSelection.current;
          if (shown.page === "projectDetails" && shown.selected && !routedProject.current &&
            !items.some(item => item.id === shown.selected)) routedProject.current = shown.selected;
          projectsHaveSnapshot.current = true;
          setProjects(items);
          setSelected(current => items.some(item => item.id === current) || routedProject.current ? current : (items[0]?.id || ""));
          setProjectsLoaded(true); setProjectsState("ready");
        } else if (snapshot.status === "error") {
          projectsHaveSnapshot.current = false;
          setProjectsState("error"); setError(snapshot.error);
        } else if (!projectsHaveSnapshot.current) setProjectsState("loading");
      },
    });
    projectsReader.current = reader;
    void reader.refresh();
    const stopPolling = startVisiblePolling(() => { void reader.refresh(); }, 15000);
    return () => {
      stopPolling(); reader.dispose();
      if (projectsReader.current === reader) projectsReader.current = null;
    };
  }, [projectsOwnerKey]);

  useEffect(() => { readinessRequest.current += 1; readinessPending.current = false; setReadinessBusy(false); setReadinessError(null); setProjectReadiness(null); setReadinessExpanded(false); }, [selected, page, session?.user.id]);

  const refreshSelected = useCallback(() => reportingReader.current?.refresh() ?? Promise.resolve(), []);

  useLayoutEffect(() => {
    if (!reportKey) return;
    const key = reportKey, generation = viewGeneration.current;
    // Freeze the name -> immutable-ID binding for this owner's entire lifetime.
    const capturedProjects = allProjectScope ? [...projects] : [selectedProject!];
    const readMap = async (member: "metrics" | "usage", signal: AbortSignal) => {
      const path = allProjectScope ? `/${member}` : `/projects/${encodeURIComponent(selected)}/${member}`;
      const value = await request<unknown>(path + metricSuffix, "GET", undefined, undefined, signal);
      if (!allProjectScope) return { [selected]: value };
      if (!value || typeof value !== "object" || Array.isArray(value) ||
        JSON.stringify(Object.keys(value).sort()) !== JSON.stringify(capturedProjects.map(project => project.name).sort())) throw new ApiError("unexpected_response");
      return Object.fromEntries(capturedProjects.map(project => [project.id, (value as Record<string, unknown>)[project.name]]));
    };
    const reader = createReportingRefresh({
      key, projectIds: capturedProjects.map(project => project.id), admin: isAdmin,
      selection: { from: metricFrom, through: metricTo, timezone: metricTimezone, granularity: metricGranularity },
      readMetrics: signal => readMap("metrics", signal), readUsage: signal => readMap("usage", signal),
      publish: snapshot => {
        if (key !== liveReportKey.current || generation !== viewGeneration.current) return;
        setReportSnapshot(snapshot);
      },
    });
    reportingReader.current = reader;
    void reader.refresh();
    let usageDueAt = Date.now() + 30000;
    const stop = startVisiblePolling(reason => {
      const now = Date.now();
      const full = allProjectScope || reason === "visible" || now >= usageDueAt;
      if (full) usageDueAt = now + 30000;
      void reader.refresh({ metrics: true, usage: full });
    }, allProjectScope ? 30000 : 15000);
    return () => { stop(); reader.dispose(); if (reportingReader.current === reader) reportingReader.current = null; };
  }, [reportKey]);

  // Users is deliberately manual: neither metadata ticks nor viewRefresh owns
  // this resource. Context exit cancels it; same-context clicks join one read.
  useLayoutEffect(() => {
    if (!usersKey) return;
    const key = usersKey, generation = viewGeneration.current;
    usersWriting.current = false;
    setUsersMutating(false); setUsersAuthority(false);
    const reader = createReadController<AccountUser[]>({ key, deadlineMs: 30000,
      read: async signal => {
        const value = await request<AccountUser[]>("/users", "GET", undefined, undefined, signal);
        if (!Array.isArray(value) || value.some(item => !validAccount(item) || typeof item.disabled !== "boolean") || new Set(value.map(item => item.id)).size !== value.length) throw new ApiError("unexpected_response");
        return value;
      },
      publish: snapshot => {
        if (key !== liveUsersKey.current || generation !== viewGeneration.current) return;
        setUsersSnapshot(snapshot);
        if (!snapshot.refreshing) setUsersAuthority(snapshot.status === "ready" && !usersWriting.current);
        if (snapshot.status === "error") setError(snapshot.error);
      },
    });
    usersReader.current = reader;
    void reader.refresh();
    return () => { reader.dispose(); if (usersReader.current === reader) usersReader.current = null; };
  }, [usersKey]);

  // Every Users mutation ends older read authority before sending. Preserve the
  // mounted display/drafts, but withhold actions until strict post-write validation.
  const sendUsers = async (path: string, method: string, body: unknown): Promise<unknown> => {
    const reader = usersReader.current;
    if (!usersReady || usersWriting.current || !reader) throw new ApiError("request_failed");
    usersWriting.current = true; setUsersMutating(true); setUsersAuthority(false);
    reader.cancel();
    try { return await request(path, method, body, session?.csrf); }
    finally {
      if (usersReader.current === reader) {
        usersWriting.current = false; setUsersMutating(false);
        await reader.refresh();
      }
    }
  };

  useEffect(() => {
    if (page === "administration" && isAdmin) {
      const generation = viewGeneration.current;
      request<AuditPolicy>("/audit-policy").then(value => { if (generation === viewGeneration.current) setAuditPolicy(value); }).catch(cause => setError(cause));
    }
  }, [page, isAdmin, projectsPrincipal]);

  useEffect(() => {
    if (page === "projectDetails" && selected) {
      const generation = viewGeneration.current;
      const revision = ++configRequest.current;
      let active = true;
      let reading: AbortController | null = null;
      let readingPrices: AbortController | null = null;
      setConfigState({ key: selected, state: "loading" });
      setPendingReadFailed(false); setPendingReady(false); setSettingsStale(false);
      setConfig(null); setConfigScope(""); setPendingConfig(null); setPendingConfigScope(""); setPrices([]); setPricesScope("");
      const path = `/projects/${encodeURIComponent(selected)}`;
      const load = async (background = false) => {
        const poll = settingsPoll.current;
        if (background && (!poll.visible || poll.blocked.size > 0 || configMutation.current)) return;
        const current = () => active && generation === viewGeneration.current && revision === configRequest.current &&
          (!background || poll === settingsPoll.current && !configMutation.current);
        if (isAdmin && !readingPrices) {
          const priceController = new AbortController();
          readingPrices = priceController;
          const write = priceWrite.current;
          const currentPrices = () => !priceController.signal.aborted && current() && write === priceWrite.current;
          void readPrices(request, path, priceController.signal).then(value => {
            if (currentPrices()) { setPrices(value); setPricesScope(selected); }
          }).catch(cause => {
            if (currentPrices()) { setPrices([]); setError(cause); }
          }).finally(() => { if (readingPrices === priceController) readingPrices = null; });
        }
        if (reading) return;
        const controller = new AbortController();
        reading = controller;
        const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(30000)]);
        const [configuration, pending] = await Promise.allSettled([
          request<Config>(path + "/config", "GET", undefined, undefined, signal).then(value => {
            if (!value || !value.config || typeof value.revision !== "string" || !Array.isArray(value.issues) || !validSettingCatalog(value.settings)) throw new ApiError("unexpected_response");
            const model = String(settingValue(value.config, "executor.model"));
            if (value.model_connection && !validModelEvidence(value.model_connection, selected, value.revision, "pi", model)) throw new ApiError("unexpected_response");
            return value;
          }),
          isAdmin ? request<PendingConfig | null>(path + "/config/pending", "GET", undefined, undefined, signal).then(value => {
            if (!validPendingConfig(value)) throw new ApiError("unexpected_response");
            return value;
          }) : Promise.resolve(null),
        ]);
        if (reading === controller) reading = null;
        if (controller.signal.aborted || !current()) return;
        if (configuration.status === "fulfilled") {
          setConfig(configuration.value); setConfigScope(selected); setConfigState({ key: selected, state: "ready" });
        } else {
          setConfig(null); setConfigState({ key: selected, state: "error" }); setError(configuration.reason);
        }
        if (!isAdmin) return;
        setPendingConfigScope(selected);
        setPendingReady(pending.status === "fulfilled");
        setPendingReadFailed(pending.status === "rejected");
        if (pending.status === "fulfilled") setPendingConfig(pending.value);
        else { setPendingConfig(null); setError(pending.reason); }
      };
      // Cancel pre-result work rather than joining evidence begun before a write.
      // Dirty Settings (including credentials/prices/sign-in) defers to its next
      // eligible tick; neither the draft nor a valid confirmation is discarded.
      const revalidate = async (afterWrite = false) => {
        // An unrelated result must not cancel the confirmed Save's owned
        // post-write validation or invalidate its settingsPoll token. The
        // mutation keeps its barrier until that validation completes.
        if (!afterWrite && configMutation.current) return;
        invalidateSettingsPoll();
        reading?.abort(); reading = null;
        readingPrices?.abort(); readingPrices = null;
        await load(!afterWrite);
      };
      configRefresh.current = revalidate;
      void load();
      const stop = startVisiblePolling(() => void load(true), 15000);
      return () => {
        active = false; stop(); reading?.abort(); readingPrices?.abort();
        if (configRefresh.current === revalidate) configRefresh.current = null;
      };
    }
  }, [page, isAdmin, selected, projectsPrincipal]);

  useEffect(() => { if (viewRefresh) void configRefresh.current?.(); }, [viewRefresh]);

  useLayoutEffect(() => {
    if (page !== "administration" || !isAdmin) return;
    const reader = createReadController<WorkerStatus>({ key: projectsPrincipal, deadlineMs: 30000,
      read: async signal => {
        const value = await request<{ status: string; worker: string; activity: string }>("/ready", "GET", undefined, undefined, signal);
        if (!value || value.status !== "ready" || value.worker !== "ready" ||
          !["busy", "idle", "unknown"].includes(value.activity)) throw new ApiError("unexpected_response");
        return value.activity === "busy" ? "busy" : value.activity === "idle" ? "ready" : "unknown";
      },
      publish: value => {
        if (value.refreshing) return;
        if (value.status === "ready") setWorkerStatus(value.data!);
        else if (value.status === "error") setWorkerStatus(value.error instanceof ApiError && value.error.code === "worker_unavailable" ? "unavailable" : "error");
      },
    });
    setWorkerStatus("checking"); void reader.refresh();
    const stop = startVisiblePolling(() => { void reader.refresh(); }, 5000);
    return () => { stop(); reader.dispose(); };
  }, [page, isAdmin, projectsPrincipal]);

  useLayoutEffect(() => {
    if (page !== "administration" || !isAdmin) return;
    const reader = createReadController<StorageStatus>({ key: projectsPrincipal, deadlineMs: 30000,
      read: async signal => {
        const value = await request<StorageStatus>("/system/storage", "GET", undefined, undefined, signal);
        const bytes = (part: unknown): part is number => Number.isSafeInteger(part) && Number(part) >= 0;
        if (!value || !bytes(value.threshold_bytes) || typeof value.low !== "boolean" || !Array.isArray(value.volumes) ||
          value.volumes.some(volume => !volume || !["home", "project"].includes(volume.scope) ||
            (volume.project !== null && typeof volume.project !== "string") || typeof volume.volume_id !== "string" || !volume.volume_id ||
            !bytes(volume.free_bytes) || !bytes(volume.total_bytes) || volume.free_bytes > volume.total_bytes || typeof volume.low !== "boolean")) throw new ApiError("unexpected_response");
        return value;
      },
      publish: value => {
        if (value.refreshing) return;
        if (value.status === "ready") { setStorageStatus(value.data); setStorageError(false); }
        else if (value.status === "error") { setStorageStatus(null); setStorageError(true); }
      },
    });
    setStorageStatus(null); setStorageError(false); void reader.refresh();
    const stop = startVisiblePolling(() => { void reader.refresh(); }, 30000);
    return () => { stop(); reader.dispose(); };
  }, [page, isAdmin, projectsPrincipal]);

  // Presentation expires independently of worker polling and persisted outcomes.
  useEffect(() => {
    if (!notice) return;
    setOperationVisible(false);
    const timer = window.setTimeout(() => setNotice(""), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    // Failed or uncertain outcomes stay visible until explicitly dismissed.
    if (!operationVisible || !operation || ["pending", "running"].includes(operation.status) ||
      ["failed", "uncertain"].includes(operation.status)) return;
    const timer = window.setTimeout(() => setOperationVisible(false), 5000);
    return () => window.clearTimeout(timer);
  }, [operationVisible, operation?.id, operation?.status]);

  const observedReportRefresh = useRef(viewRefresh);
  useLayoutEffect(() => {
    if (observedReportRefresh.current === viewRefresh) return;
    observedReportRefresh.current = viewRefresh;
    void reportingReader.current?.revalidate();
  }, [viewRefresh]);

  const revalidateOperation = () => {
    // A completed write cannot join directory evidence begun before its result.
    projectsReader.current?.cancel(); void refreshProjects(); refreshView();
  };
  const revalidateTicketOperation = (projectId: string) => {
    if (!projects.some(project => project.id === projectId)) return;
    // Tickets stay on demand. Revalidate only shared metadata; keep ticket
    // bodies, comments, paging and unrelated confirmations mounted.
    projectsReader.current?.cancel(); void refreshProjects();
  };
  const operationPollingKey = session && operationView && ["pending", "running"].includes(operationView.status)
    ? JSON.stringify([projectsPrincipal, operationProject, operationView.id]) : "";
  const liveOperationKey = useRef(operationPollingKey); liveOperationKey.current = operationPollingKey;
  useLayoutEffect(() => {
    if (!operationPollingKey || !operation) return;
    const key = operationPollingKey, id = operation.id, generation = viewGeneration.current;
    const reader = createReadController<Operation>({ key, deadlineMs: 30000,
      read: async signal => readOperation(await request(`/operations/${id}`, "GET", undefined, undefined, signal), id),
      publish: value => {
        if (value.refreshing || key !== liveOperationKey.current || generation !== viewGeneration.current || operationId.current !== id) return;
        if (value.status === "error") { setError(value.error); return; }
        if (value.status !== "ready" || !value.data) return;
        setOperation(value.data);
        if (!["pending", "running"].includes(value.data.status)) {
          operationBusy.current = false; revalidateOperation();
        }
      },
    });
    void reader.refresh();
    const stop = startVisiblePolling(() => { void reader.refresh(); }, 2000);
    return () => { stop(); reader.dispose(); };
  }, [operationPollingKey]);

  useEffect(() => {
    if (preserveError.current) { preserveError.current = false; return; }
    setError("");
  }, [page]);


  const openProject = (id: string) => {
    if (enrollmentGuard.current && !enrollmentGuard.current()) return;
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
    setImportOpen(false);
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
    if (replaced || route.view === "projects" && window.location.pathname !== "/projects")
      window.history.replaceState(null, "", formatRoute(route));
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
    setImportOpen(false);
    viewGeneration.current += 1;
    ticketModePending.current = false; setTicketModeBusy(false);
    confirmedTicketMode.current = "rendered"; setTicketBodyMode("rendered");
    setPage("overview"); setJobScope(""); setMenuOpen(false);
    reportingReader.current?.dispose(); reportingReader.current = null;
    setReportSnapshot(null);
    configRequest.current += 1;
    preferenceRequest.current.language += 1;
    preferenceRequest.current.theme += 1;
    setProjects([]); setSelected(""); setRequestedRun(""); setConfigState({ key: "", state: "loading" });
    projectsReader.current?.dispose(); projectsReader.current = null;
    projectsHaveSnapshot.current = false;
    setProjectsState("loading");
    setProjectsLoaded(false); setProjectTab("overview"); routedProject.current = null;
    setProjectSortKey("name"); setProjectSortDescending(false);
    setMetricFrom(""); setMetricTo("");
    setMetricAllProjects(true); setMetricTimezone("UTC"); setMetricGranularity("day"); setMetricsTab("summary");
    setUsageSortKey("date"); setUsageSortDescending(false);
    setConfig(null); setPendingConfig(null); setPrices([]);
    usersReader.current?.dispose(); usersReader.current = null;
    setUsersSnapshot(null); setUsersAuthority(false); usersWriting.current = false; setUsersMutating(false);
    setAuditPolicy(null); operationSubmission.current += 1; operationBusy.current = false; operationId.current = null; setOperationSubmitting(false); setOperation(null); setOperationProject(""); setOperationVisible(false);
    setWorkerStatus("checking");
    setNotice("");
  };

  const signIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const fields = new FormData(event.currentTarget);
    try {
      clearPrivateView();
      const generation = viewGeneration.current;
      const authenticated = readSession(await request("/session", "POST", Object.fromEntries(fields)));
      if (generation !== viewGeneration.current) return;
      sessionIdentity.current = authenticated;
      transport.current!.activate();
      let saved: Preferences | null = null;
      try { saved = readPreferences(await request<unknown>("/me/preferences")); }
      catch (cause) { if (generation === viewGeneration.current) setError(cause); }
      if (generation !== viewGeneration.current) return;
      if (saved) applyPreferences(saved);
      if (authenticated.user.password_change_required) setPasswordSession(authenticated);
      else setSession(authenticated);
    }
    catch (cause) { setError(cause); }
  };

  const signOut = async () => {
    if (enrollmentGuard.current && !enrollmentGuard.current()) return;
    const csrf = (session ?? passwordSession)?.csrf;
    transport.current!.dispose(); clearPrivateView();
    await onSignOut(csrf);
  };

  /** Serialize project writes and bind every callback to live metadata/view authority. */
  const submitProjectOperation = async (path: string, body: unknown, deleting = false) => {
    if (!session || !isAdmin || !actionContext || actionContext !== liveActionContext.current ||
      !selectedProject || operationBusy.current || projectActionBusy) return;
    operationBusy.current = true; setOperationSubmitting(true);
    const submission = ++operationSubmission.current, key = actionContext;
    const controller = new AbortController(); operationRequest.current = controller;
    const current = () => !controller.signal.aborted && submission === operationSubmission.current && key === liveActionContext.current;
    setError(""); setNotice(""); setProjectNotice(null);
    projectsReader.current?.cancel();
    try {
      const op = readOperation(await request(path, "POST", body, session.csrf, controller.signal));
      if (!current()) return;
      operationOrigin.current = JSON.stringify([projectsPrincipal, selectedProject.id, selectedProject.name]);
      operationId.current = op.id; setOperationProject(selectedProject.id); setOperation(op); setOperationVisible(true);
      if (deleting) { setDeleteTarget(null); setDeleteName(""); }
      if (!["pending", "running"].includes(op.status)) revalidateOperation();
    } catch (cause) {
      if (current()) { setError(cause); revalidateOperation(); }
    } finally {
      if (current()) { operationBusy.current = false; operationRequest.current = null; setOperationSubmitting(false); }
    }
  };
  const operate = async (action: "pause" | "resume", projectId = selected) => {
    if (!selectedProject || selectedProject.id !== projectId || selectedProject.archived ||
      action !== (selectedProject.paused ? "resume" : "pause")) return;
    await submitProjectOperation(`/projects/${encodeURIComponent(projectId)}/operations/${action}`, { idempotency_key: crypto.randomUUID() });
  };

  const deleteProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setNotice("");
    if (!deleteReviewCurrent || !deleteTarget || deleteName !== deleteTarget.name) return;
    await submitProjectOperation(`/projects/${encodeURIComponent(deleteTarget.id)}/delete`,
      { confirm_name: deleteName, idempotency_key: crypto.randomUUID(), remove_clone: deleteClone }, true);
  };

  useEffect(() => { setDeleteTarget(null); setDeleteName(""); }, [page, selected, projectTab]);

  const setProjectArchive = async (archive: boolean, projectId = selected) => {
    if (!session || !isAdmin || !actionContext || actionContext !== liveActionContext.current || !selectedProject ||
      selectedProject.id !== projectId || selectedProject.archived === archive || operationBusy.current || projectActionBusy) return;
    operationBusy.current = true; setOperationSubmitting(true);
    const submission = ++operationSubmission.current, key = actionContext;
    const controller = new AbortController(); operationRequest.current = controller;
    const current = () => !controller.signal.aborted && submission === operationSubmission.current && key === liveActionContext.current;
    setError(""); setNotice(""); setProjectNotice(null);
    projectsReader.current?.cancel();
    try {
      const result = await request<Project>(`/projects/${encodeURIComponent(projectId)}/${archive ? "archive" : "restore"}`,
        "POST", undefined, session.csrf, controller.signal);
      if (!current()) return;
      if (!result || result.id !== projectId || result.name !== selectedProject.name || result.archived !== archive) throw new ApiError("unexpected_response");
      setProjectNotice({ key: projectViewKey, text: t(archive ? "projectArchived" : "projectRestored") });
      revalidateOperation();
    } catch (cause) { if (current()) { setError(cause); revalidateOperation(); } }
    finally { if (current()) { operationBusy.current = false; operationRequest.current = null; setOperationSubmitting(false); } }
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
      if (!usersReady || !users.some(item => item.id === userId && item.id !== session?.user.id && item.disabled === enabled)) return;
      const result = await sendUsers(`/users/${userId}/${enabled ? "enable" : "disable"}`, "POST", {});
      if (!result || typeof result !== "object" || !("ok" in result) || result.ok !== true) throw new ApiError("unexpected_response");
    } catch (cause) { setError(cause); }
  };

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const values = new FormData(event.currentTarget);
    const current = String(values.get("current") ?? "");
    const replacement = String(values.get("replacement") ?? "");
    if (replacement !== values.get("confirmation")) { setPasswordMismatch(true); return; }
    setPasswordMismatch(false);
    try {
      await request("/me/password", "POST", { current, replacement }, (session ?? passwordSession)?.csrf);
      transport.current!.dispose(); clearPrivateView(); onPasswordChanged();
    } catch (cause) { setError(cause); }
  };

  const saveSettings = async (edits: SettingEdit[], base: string): Promise<boolean> => {
    if (!projectConfig || !selected || configMutation.current || pendingReadFailed || !pendingReady
      || projectConfig.revision !== base) return false;
    const target = selected, generation = viewGeneration.current, revision = configRequest.current, scope = configView.current;
    const current = () => generation === viewGeneration.current && revision === configRequest.current && scope === configView.current;
    const rows = settingRows(projectConfig.config, projectConfig.settings || []);
    let writeAttempted = false, pendingReadAttempted = false;
    configMutation.current = true; setConfigBusy(true); setError("");
    try {
      let candidate = projectPendingConfig;
      const confirm = async (value:PendingConfig, changes:SettingEdit[]) => {
        if (!current()) return false;
        setConfigBusy(false);
        const accepted = await new Promise<boolean>(resolve => {
          settingsConfirmationResolve.current = resolve;
          setSettingsConfirmation({candidate:value,edits:changes,project:target,config:projectConfig,resolve});
        });
        settingsConfirmationResolve.current = null;setSettingsConfirmation(null);
        if (!accepted || !current()) return false;
        setConfigBusy(true);return true;
      };
      if (edits.length) {
        const body = {
          key: BATCH_KEY, value: JSON.stringify(edits), revision: base,
          ...(candidate ? {pending_revision: candidate.candidate_revision} : {}),
        };
        let preview: PendingConfig | null = null;
        if (settingImpacts(edits, rows).length) {
          const proposed = await request<unknown>(`/projects/${encodeURIComponent(target)}/config/preview`, "POST", body, session?.csrf);
          if (!validPendingConfig(proposed) || !proposed || proposed.base_revision !== base
            || !candidateMatchesEdits(proposed, edits, rows)) throw new ApiError("unexpected_response");
          preview = proposed;
          if (!await confirm(proposed,edits)) return false;
        }
        writeAttempted = true;
        const prepared = await request<unknown>(`/projects/${encodeURIComponent(target)}/config/pending`, "POST", body, session?.csrf);
        if (!validPendingConfig(prepared) || !prepared || prepared.base_revision !== base
          || !candidateMatchesEdits(prepared, edits, rows)
          || preview && (preview.candidate_revision !== prepared.candidate_revision
            || !sameSettingValue(preview.execution_plan,prepared.execution_plan))) throw new ApiError("unexpected_response");
        candidate = prepared;
        if (!current()) return false;
        setPendingConfig(candidate); setPendingConfigScope(target);
      } else if (!candidate) return false;
      else if (candidate.candidate_revision !== base) {
        // API-only keys retain read-only rows. Confirm and apply their exact stored candidate.
        pendingReadAttempted = true;
        const verified=await request<unknown>(`/projects/${encodeURIComponent(target)}/config/pending`);
        if (!validPendingConfig(verified) || !verified || verified.base_revision!==base
          || !sameSettingValue(verified,candidate)) throw new ApiError("stale_pending_revision");
        if (!await confirm(verified,pendingSettingEdits(verified))) return false;
        candidate=verified;
      }
      if (!candidate || !current()) return false;
      writeAttempted = true;
      const applied = await request<{revision:string}>(`/projects/${encodeURIComponent(target)}/config/apply`, "POST", {
        candidate_revision: candidate.candidate_revision, base_revision: candidate.base_revision,
      }, session?.csrf);
      if (applied.revision !== candidate.candidate_revision) throw new ApiError("unexpected_response");
      if (!current()) return false;
      setPendingConfig(null);
      // Our own confirmed Save is not an unrelated poll: validate saved state
      // before releasing the editor's mutation/draft barrier, without remounting.
      await configRefresh.current?.(true);
      if (!current()) return false;
      setNotice(t("changeApplied"));
      projectsReader.current?.cancel(); await refreshProjects();
      return true;
    } catch (cause) {
      if (current()) {
        setError(cause);
        if (cause instanceof ApiError && (["pending_config_exists", "stale_pending_revision"].includes(cause.code)
          || (writeAttempted || pendingReadAttempted) && ["unexpected_response", "network_error", "pending_config_corrupt"].includes(cause.code))) setPendingReadFailed(true);
        if (cause instanceof ApiError && cause.code === "stale_config_revision") setSettingsStale(true);
      }
      return false;
    } finally { configMutation.current = false; setConfigBusy(false); }
  };

  const discardPendingConfig = async () => {
    if (!selected || configMutation.current) return false;
    if (!projectPendingConfig && !pendingReadFailed) {
      if (settingsStale) { setSettingsStale(false); await configRefresh.current?.(true); }
      return true;
    }
    const target = selected, key = projectPendingConfig?.key, generation = viewGeneration.current, revision = configRequest.current, scope = configView.current;
    const current = () => generation === viewGeneration.current && revision === configRequest.current && scope === configView.current;
    configMutation.current = true; setConfigBusy(true); setError("");
    try {
      try {
        await request(`/projects/${encodeURIComponent(target)}/config/pending`, "DELETE", undefined, session?.csrf);
      } catch (cause) {
        // Explicitly confirmed absence also completes a requested draft discard.
        if (!(cause instanceof ApiError) || cause.code !== "pending_config_not_found") throw cause;
      }
      if (current()) { setPendingConfig(null); setPendingReadFailed(false); setPendingReady(true); setNotice(t("changeDiscarded"));
        if (settingsStale) { setSettingsStale(false); await configRefresh.current?.(true); }
        configDiscardFocus.current = () => {
          if (!current()) return;
          const button = Array.from(document.querySelectorAll<HTMLButtonElement>("button[data-edit-key]")).find(item => item.dataset.editKey === key);
          button?.focus();
        };
      }
      return current();
    } catch (cause) { if (current()) setError(cause); return false; }
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
      if (!selectedProject || [...result.required_checks].sort().join() !== [...selectedProject.verification_requirements].sort().join())
        throw new ApiError("readiness_corrupt");
      if (generation === viewGeneration.current && revision === readinessRequest.current) {
        // A project-list read already in flight may predate this saved check.
        // Supersede it before publishing the newer evidence; later polls still apply.
        projectsReader.current?.invalidate();
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
    if (priceSaving.current === form) return;
    const generation = viewGeneration.current;
    const current = () => generation === viewGeneration.current && form.isConnected;
    const path = `/projects/${encodeURIComponent(selected)}`;
    priceSaving.current = form;
    priceWrite.current += 1;
    setSettingsPollBlocked("prices", true);
    try {
      await request(path + "/prices", "POST", Object.fromEntries(new FormData(form)), session?.csrf);
      const rates = await readPrices(request, path);
      if (current()) {
        setPrices(rates); setPricesScope(selected);
        setNotice(t("priceSaved")); form.reset();
      }
    } catch (cause) { if (current()) setError(cause); }
    finally {
      if (priceSaving.current === form) priceSaving.current = null;
      if (current()) updatePriceDraft(form);
    }
  };

  if (loading) return <main className="splash" aria-busy="true">ADORE</main>;

  const loginPreferences = <div className="login-preferences"><label>{t("language")}<select aria-label={t("language")} value={locale} onChange={event => updatePreference("language", event.target.value)}>{Object.entries(localeNames).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>{t("theme")}<select aria-label={t("theme")} value={theme} onChange={event => updatePreference("theme", event.target.value)}><option value="system">{t("system")}</option><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option></select></label></div>;

  if (passwordSession) return <main className="login-page">
    <section className="login-card">
      <div className="brand-mark">A</div><p className="eyebrow">ADORE</p><h1>{t("passwordRequiredTitle")}</h1><p className="muted">{t("passwordRequiredReason")}</p>
      {error ? <p className="alert" role="alert">{describeError(locale, error)}</p> : null}
      <form onSubmit={changePassword} onInput={() => setPasswordMismatch(false)} className="form-stack"><FormLegend t={t} />
        <PasswordChangeFields t={t} mismatch={passwordMismatch} autoFocus />
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

  const workspaceProps = { locale, projects, scope: jobScope, principal: JSON.stringify([session.user.id, session.user.role, session.csrf]), csrf: session.csrf, request, t, refresh: viewRefresh,
    onScope: (id: string) => { setJobScope(id); if (id) setSelected(id); setRequestedRun(""); },
    onOpen: (id: string, runId: string) => { setSelected(id); setJobScope(id); setRequestedRun(runId); setJobsView("jobs"); setPage("jobs"); },
    onClose: () => setRequestedRun("") };
  const hubWorkspaceProps = { ...workspaceProps, scope: selected,
    onOpen: (id: string, runId: string) => { setSelected(id); setRequestedRun(runId); setJobsView("jobs"); setProjectTab("jobs"); } };
  const manualRefresh = page === "adminUsers";
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
    active: target === page || (target === "projects" && ["createProject", "projectDetails"].includes(page)),
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
        <RefreshFeedback snapshot={reportState ? { ...reportState, completedAt: report?.fullReportAt ?? null } : null}
          locale={locale} t={t} onRefresh={() => { void refreshSelected(); }}
          sources={report ? [{ label: t("metricsUpdated"), at: report.metricsAt }, { label: t("usageUpdated"), at: report.usageAt }] : []}>
          {reportState?.status === "stale" && <span>{t("staleExportHelp")}</span>}
        </RefreshFeedback>
        <div className="metrics-tabs" role="tablist" aria-label={t("metrics")}>
          {metricsTabs.map(tab => <button key={tab} id={`metrics-tab-${tab}`} type="button" role="tab" aria-controls="metrics-tab-panel" aria-selected={metricsTab === tab} tabIndex={metricsTab === tab ? 0 : -1} onClick={() => setMetricsTab(tab)} onKeyDown={event => onMetricsTabKeyDown(event, tab)}>{t(metricsTabLabels[tab])}</button>)}
        </div>
        <div key={reportKey} id="metrics-tab-panel" role="tabpanel" aria-labelledby={`metrics-tab-${metricsTab}`} tabIndex={0}>
        {reportingDataState !== "ready" ? <DataFeedback state={reportingDataState} t={t} /> : <>
        {metricsTab === "usage" && <>
        <section className="panel"><h2>{t("attributedUsage")}</h2>
          {usage && <Chips items={usageTotals} className="usage-totals" />}
          {usage?.daily.length ? <PagedTable key={`${usageSortKey}-${usageSortDescending}`} t={t}><table className="usage-table"><thead><tr>{usageColumns.map(([key, label]) => <SortHeader key={key} label={t(label)} sortKey={key} activeKey={usageSortKey} descending={usageSortDescending} onSort={changeUsageSort} />)}</tr></thead><tbody>{sortUsageRows(usage.daily, usageSortKey, usageSortDescending, locale).map(row => <tr key={JSON.stringify([row.date, row.executor, row.model])}><td>{row.date}</td><td>{row.executor || "—"}</td><td>{row.model || "—"}</td><td>{formatNumber(row.events)}</td><td>{formatNumber(row.tokens_in)}</td><td>{formatNumber(row.tokens_out)}</td><td>{row.cache_read_tokens == null ? "\u2014" : formatNumber(row.cache_read_tokens)}</td><td>{row.cache_write_tokens == null ? "\u2014" : formatNumber(row.cache_write_tokens)}</td>{isAdmin && <td>{formatMoney(row.reported_cost_usd)}</td>}{isAdmin && <td>{formatMoney(row.estimated_cost_usd)}</td>}</tr>)}</tbody></table></PagedTable> : <Empty label={t("noMatchingMetrics")} />}
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
    onSignOut={signOut} context={<>{session.user.factory_password && <p className="notice" role="status">{t("factoryPasswordNotice")} <a href="/account" onClick={event => { event.preventDefault(); navigatePage("settings"); }}>{t("changePassword")}</a></p>}{projectContext}</>}
    controls={page === "overview" && projectsState === "ready" && projects.length > 0 && <label className="overview-header-scope" htmlFor="overview-project">{t("project")}<select id="overview-project" aria-label={t("project")} value={jobScope} onChange={event => workspaceProps.onScope(event.target.value)}><option value="">{jc.allProjects}</option>{projects.map(item => <option key={item.id} value={item.id}>{item.display_name || item.name}</option>)}</select></label>}
    actions={<>{manualRefresh && <div className="users-refresh"><span className="refresh-stamp">{lastRefresh && <>{t("lastRefresh")}: <time dateTime={lastRefresh.toISOString()}>{formatDate(lastRefresh.toISOString())}</time></>}</span>
      <button className="ghost" aria-disabled={!!usersRead?.refreshing || usersMutating} onClick={() => { if (!usersWriting.current) void usersReader.current?.refresh(); }}>{t("refresh")}</button>
      <span className="refresh-progress">{usersRead?.refreshing ? t("refreshingData") : ""}</span></div>}
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
        {(notice || projectNotice?.key === projectViewKey || (operationVisible && operationView)) && <div className="notice" role="status">
          {notice || (projectNotice?.key === projectViewKey ? projectNotice.text : "") || (operationView && <>{t("operationStatus")}: #{operationView.id} · {operationView.status}{(operationView.reason ? outcomeText(locale, operationView) : operationResultText(operationView.result || "", locale)) && operationView.result !== "completed" ? ` · ${(operationView.reason ? outcomeText(locale, operationView) : operationResultText(operationView.result || "", locale))}` : ""}{operationView.status === "pending" && <small>{t("workerQueueHelp")}</small>}{operationView.status !== "succeeded" && operationView.detail && <pre className="operation-detail" tabIndex={0}>{operationView.detail}</pre>}</>)}
          <button onClick={() => { setNotice(""); setProjectNotice(null); setOperationVisible(false); }} aria-label={t("close")}>×</button>
        </div>}
        {["overview", "projects", "projectDetails", "jobs", "metrics"].includes(page) && projectsState !== "ready" && <DataFeedback state={projectsState} t={t} />}
        {["overview", "projects", "projectDetails", "jobs", "metrics"].includes(page) && projectsState === "ready" && projects.length === 0 && <ProjectEmpty isAdmin={isAdmin} t={t} onEnroll={page === "overview" ? () => setPage("createProject") : undefined} />}
        {page === "overview" && projectsState === "ready" && projects.length > 0 && <JobWorkspace admin={isAdmin} {...workspaceProps} mode="overview" />}

        {page === "projects" && projectsState === "ready" && <>
          <div className="section-actions">{isAdmin && <><button className="primary" onClick={() => { setError(""); setPage("createProject"); }}>{t("createProject")}</button><button className="ghost" onClick={() => setImportOpen(true)}>{t("importProject")}</button></>}</div>
          {projects.length > 0 && <section className="panel">
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
          </section>}
        </>}

        {page === "createProject" && isAdmin && <EnrollmentWizard locale={locale} csrf={session.csrf} t={t}
          registerGuard={registerSettingsGuard}
          onCancel={() => { setError(""); setPage("projects"); }}
          onCreated={() => { void refreshProjects(); }} onOpen={id => openProject(id)} />}

        {page === "projects" && importOpen && isAdmin && <RawImportDialog key={session.user.id} locale={locale} csrf={session.csrf}
          registerGuard={registerSettingsGuard}
          onClose={() => setImportOpen(false)}
          onImported={() => { setImportOpen(false); setNotice(importCopy[locale].imported); void refreshProjects(); }} />}

        {page === "projectDetails" && projectsState === "ready" && selectedProject && <>
          <div id="project-tab-panel" role="tabpanel" aria-labelledby={`project-tab-${projectTab}`}>
          {projectTab === "overview" && <>
          <JobWorkspace admin={isAdmin} {...hubWorkspaceProps} mode="overview" fixedScope summaryHeader={evidence => <section className="panel project-summary">
            <dl className="summary-facts">
              <div className="summary-fact"><dt>{selectedProject.runtime === "local" ? enrollmentCopy[locale].runsIn : t("containerType")}</dt><dd>{selectedProject.runtime === "local" ? enrollmentCopy[locale].installed : ({ docker: "Docker", podman: "Podman" } as Record<string, string>)[selectedProject.runtime] || selectedProject.runtime}</dd></div>
              <div className="summary-fact"><dt>{t("executor")}</dt><dd>{selectedProject.executor === "pi" ? "Pi" : selectedProject.executor || "—"}</dd></div>
              <div className="summary-fact"><dt>{jc.pickup}</dt><dd><StatusBadge code={selectedProject.archived ? "archived" : selectedProject.paused ? "paused" : "working"}>{selectedProject.archived ? t("archived") : selectedProject.paused ? jc.pickupStopped : jc.pickupActive}</StatusBadge></dd></div>
              <div className="summary-fact"><dt>{jc.verification}</dt><dd>{verificationLabel(selectedProject)}</dd></div>
              {[{ label: t("activeJobs"), value: evidence?.groups.active }, { label: jc.waiting, value: evidence?.groups.waiting }, { label: t("inReviewStatus"), value: evidence ? evidence.counts["in-review"] || 0 : undefined }, { label: t("failedJobs"), value: evidence ? evidence.counts.failed || 0 : undefined }].map(fact => <div className="summary-fact" key={fact.label}><dt>{fact.label}</dt><dd>{fact.value === undefined ? "—" : new Intl.NumberFormat(locale).format(fact.value)}</dd></div>)}
            </dl>
            {isAdmin && <div className="summary-actions button-row">{!selectedProject.archived && <button className="ghost" disabled={!actionContext || projectActionBusy} onClick={() => void operate(selectedProject.paused ? "resume" : "pause", selectedProject.id)}>{selectedProject.paused ? jc.startPickup : jc.stopPickup}</button>}
              <button className="ghost" disabled={!actionContext || projectActionBusy} onClick={() => void setProjectArchive(!selectedProject.archived, selectedProject.id)}>{t(selectedProject.archived ? "restoreProject" : "archiveProject")}</button>
              {selectedProject.archived && <button className="danger" disabled={!actionContext || projectActionBusy} onClick={() => { setError(""); setDeleteName(""); setDeleteClone(false); setDeleteReviewInvalid(false); setDeleteTarget(selectedProject); }}>{t("deleteProject")}</button>}
              <button ref={readinessTrigger} type="button" className="ghost" aria-disabled={readinessBusy} aria-controls="host-check-details" aria-expanded={readinessExpanded} onClick={() => void checkProjectReadiness()}>{t("checkHostPrerequisites")}</button>

            {!selectedProject.archived && <RepositoryConnection key={`${session.user.id}:${selectedProject.id}`} project={selectedProject.id} provider={selectedProject.platform} repository={selectedProject.repo} locale={locale}
              connect={body => request(`/projects/${encodeURIComponent(selectedProject.id)}/repository-connection`, "POST", body, session.csrf)}
              onConnected={() => { setProjectReadiness(null); setProjects(items => items.map(item => item.id === selectedProject.id && item.verification.status !== "unverified" ? { ...item, verification: { ...item.verification, status: "stale" } } : item)); void refreshProjects(); }} />}
            </div>}
            <section id="host-check-details" hidden={!readinessExpanded} aria-busy={readinessBusy} aria-labelledby="host-check-title">
              <div className="panel-heading"><h3 id="host-check-title">{readinessDetailsLabel(locale)}</h3><button type="button" className="ghost" onClick={() => { setReadinessExpanded(false); readinessTrigger.current?.focus(); }}>{readinessCloseLabel(locale)}</button></div>
              {readinessBusy && <p role="status">{t("workerChecking")}</p>}
              {readinessError !== null && <p role="alert" className="alert">{describeError(locale, readinessError)}</p>}
              {projectReadiness && <ReadinessEvidence modelEvidence={projectConfig?.model_connection} evidence={projectReadiness} locale={locale} local={selectedProject.runtime === "local"} />}
            </section>
          </section>} />
          {isAdmin && deleteTarget?.id === selectedProject.id && <ProjectDeleteDialog onClose={() => setDeleteTarget(null)}><section className="delete-confirm">
            <h2 id="delete-project-title">{t("deleteProjectTitle").replace("{project}", deleteTarget.name)}</h2>
            <p>{t("deleteProjectRemoves")}</p>
            <p className="muted">{t("deleteProjectKeeps")}</p>
            <form className="form-stack" onSubmit={deleteProject}><FormLegend t={t} />
              <DeleteCloneOption locale={locale} project={deleteTarget.id} read={path => request(path)} checked={deleteClone} onChange={setDeleteClone} />
              <label><span className="delete-confirm-label">{t("deleteProjectConfirm").split("{project}").map((part, index) => <Fragment key={index}>{index > 0 && <strong className="delete-confirm-name">{deleteTarget.name}</strong>}{part}</Fragment>)}<RequiredMark /></span><input value={deleteName} onChange={event => setDeleteName(event.target.value)} autoComplete="off" spellCheck={false} required /></label>
              {!deleteReviewCurrent && <p role="status">{userCopy[locale].reviewChanged}</p>}
              <div className="button-row"><button className="danger" type="submit" disabled={projectActionBusy || !deleteReviewCurrent || deleteName !== deleteTarget.name}>{t("deleteProject")}</button><button className="ghost" type="button" onClick={() => setDeleteTarget(null)}>{t("cancel")}</button></div>
            </form>
          </section></ProjectDeleteDialog>}
          </>}
          {projectTab === "history" && selectedProject?.id && <AuditHistory key={JSON.stringify([session.user.id, session.user.role, projects.map(item => item.id).sort(), selectedProject.id])} refresh={viewRefresh} locale={locale} projects={projects} fixedProject={selectedProject.id} read={(path, signal) => request(path, "GET", undefined, undefined, signal)} />}
          {projectTab === "jobs" && selectedProject && <>
            {jobsSubtabs}
            <div id="jobs-subtab-panel" role="tabpanel" aria-labelledby={`jobs-subtab-${jobsView}`}>
              {jobsView === "tickets" ? <TicketWorkspace key={`${session.user.id}:${selectedProject.id}`} principal={projectsPrincipal} projects={[selectedProject]} locale={locale} csrf={session.csrf} request={request} onOperationComplete={revalidateTicketOperation} bodyMode={ticketBodyMode} modeBusy={ticketModeBusy} onBodyMode={updateTicketBodyMode} />
                : <JobWorkspace admin={isAdmin} {...hubWorkspaceProps} mode="jobs" run={requestedRun} fixedScope />}
            </div>
          </>}
          {projectTab === "statistics" && statisticsView(true)}
          {projectTab === "history" && <JobWorkspace admin={isAdmin} {...hubWorkspaceProps} mode="history" fixedScope />}
          {projectTab === "configuration" && <>
          {configDataState !== "ready" && <DataFeedback state={configDataState} t={t} />}
          {projectConfig && <SettingsList request={request} key={selected} project={selected} revision={projectConfig.revision} csrf={session.csrf} branchCandidate={projectPendingConfig} config={projectConfig.config} localIdentity={projectConfig.local_execution} settings={projectConfig.settings || []} t={t} locale={locale} canEdit={isAdmin} disabled={configBusy || isAdmin && !pendingReady && !pendingReadFailed} readFailed={pendingReadFailed} stale={settingsStale} onSave={saveSettings} onDiscard={discardPendingConfig} registerGuard={registerSettingsGuard} setPollBlocked={blockSettingsEdits} executorBefore={selectedProject && <><ModelConnection heading={agentSettingsCopy[locale].connection} key={`${session.user.id}:${selected}:${projectConfig.revision}:${projectConfig.model_connection?.checked_at || "untested"}`} project={selectedProject.id} revision={projectConfig.revision} executor={selectedProject.executor} model={String(settingValue(projectConfig.config,"executor.model"))} locale={locale} saved={projectConfig.model_connection} readOnly={!isAdmin || selectedProject.archived} onResult={value=>{ invalidateSettingsPoll(); setConfig(current=>current?{...current,model_connection:value}:current); }} test={()=>request(`/projects/${encodeURIComponent(selected)}/model-connection-test`,"POST",{},session.csrf)} />
                  <p className="muted">{executorCopy[locale].modelHelp}</p></>} executorAuthentication={selectedProject && <>{isAdmin && !selectedProject.archived && <>{String(settingValue(projectConfig.config, "executor.provider") ?? "") === CHATGPT && <ChatGptSignIn setPollBlocked={blockChatGpt} key={`${session.user.id}:chatgpt`} locale={locale} read={() => request("/chatgpt-sign-in")} start={() => request(`/projects/${encodeURIComponent(selected)}/chatgpt-sign-in`, "POST", undefined, session.csrf)} complete={(redirect_url: string) => request("/chatgpt-sign-in", "PUT", {redirect_url}, session.csrf)} cancel={() => request("/chatgpt-sign-in/pending", "DELETE", undefined, session.csrf)} disconnect={() => request("/chatgpt-sign-in", "DELETE", undefined, session.csrf)} />}{(String(settingValue(projectConfig.config, "executor.provider") ?? "") !== CHATGPT || searchKeyNeeded(projectConfig.config)) && <ExecutorCredentials embedded setPollBlocked={blockCredentials} key={`${session.user.id}:${selected}:${projectConfig.revision}`} provider={String(settingValue(projectConfig.config, "executor.provider") ?? "")} project={selectedProject.id} revision={projectConfig.revision} locale={locale} disabled={!!projectPendingConfig || configBusy || pendingReadFailed || !pendingReady || !selectedProject.paused} read={() => request(`/projects/${encodeURIComponent(selected)}/executor-credentials`)} write={(method,body)=>request(`/projects/${encodeURIComponent(selected)}/executor-credentials`,method,body,session.csrf)} onChanged={()=>{ invalidateSettingsPoll(); setConfig(current=>current?{...current,model_connection:null}:current); }} />}</>}</>} executorAfter={selectedProject && <><ExecutorEnvironment environment={projectConfig.executor_environment} executor={selectedProject.executor} locale={locale} />
                  {isAdmin && selected && <section className="executor-prices"><h3>{t("estimatedPrices")}</h3><p className="muted">{t("priceHelp")}</p>
                    {priceModel ? <form key={`${selected}:${priceModel}`} ref={priceFormRef} className="form-grid" onChange={event=>updatePriceDraft(event.currentTarget)} onSubmit={savePrice}><FormLegend t={t} /><input type="hidden" name="executor" value={priceExecutor} /><input type="hidden" name="model" value={priceModel} /><label><span>{t("effectiveFrom")}<RequiredMark /></span><input name="effective_from" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label><span>{t("inputRate")}<RequiredMark /></span><input name="input_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><label><span>{t("outputRate")}<RequiredMark /></span><input name="output_usd_per_million" type="number" min="0" max="1000000" step="0.000001" required /></label><button className="primary form-submit" type="submit">{t("save")}</button></form> : <p className="muted">{t("priceNeedsModel")}</p>}
                    {projectPrices.length > 0 && <PagedTable t={t}><table><thead><tr><th>{t("executor")}</th><th>{t("model")}</th><th>{t("effectiveFrom")}</th><th>{t("inputRate")}</th><th>{t("outputRate")}</th></tr></thead><tbody>{projectPrices.map(price => <tr key={price.id}><td>{price.executor}</td><td>{price.model}</td><td>{price.effective_from}</td><td>{price.input_usd_per_million}</td><td>{price.output_usd_per_million}</td></tr>)}</tbody></table></PagedTable>}
                  </section>}</>} actions={isAdmin && <RawConfiguration key={`${session.user.id}:${selected}:${projectConfig.revision}`} project={selected} locale={locale} />}>
            {isAdmin && <>
            {projectConfig.issues.length > 0 && <div className="alert">{projectConfig.issues.join(" · ")}</div>}
            {settingsConfirmation && settingsConfirmation.project === selected && <SettingsImpactDialog config={settingsConfirmation.config} candidate={settingsConfirmation.candidate} edits={settingsConfirmation.edits} project={selectedProject?.display_name || selected} paused={selectedProject?.paused === true} locale={locale} onDecision={accepted => settingsConfirmation.resolve(accepted)} />}
            {pendingReadFailed && <div className="alert"><p>{settingsCopy[locale].readFailed}</p></div>}
            </>}
          </SettingsList>}
          </>}
          {projectTab === "access" && isAdmin && selectedProject && <ProjectAccess request={request} key={`${projectsPrincipal}:${selected}`} project={selectedProject!} ready={projectsState === "ready"} refresh={viewRefresh} csrf={session?.csrf} locale={locale} t={t} onError={setError} onNotice={setNotice} />}
          </div>
        </>}

        {page === "jobs" && projectsState === "ready" && projects.length > 0 && <>
          <section className="panel compact"><div className="workspace-controls"><label htmlFor="jobs-project">{jc.scope}<select id="jobs-project" aria-label={jc.scope} value={jobScope} onChange={event => workspaceProps.onScope(event.target.value)}><option value="">{jc.all}</option>{projects.map(item => <option key={item.id} value={item.id}>{item.display_name || item.name}</option>)}</select></label></div></section>
          {jobsSubtabs}
            <div id="jobs-subtab-panel" role="tabpanel" aria-labelledby={`jobs-subtab-${jobsView}`}>
              {jobsView === "tickets" ? <TicketWorkspace key={`${session.user.id}:${jobScopeProject?.id ?? ""}`} principal={projectsPrincipal} projects={jobScopeProject ? [jobScopeProject] : projects.filter(item => !item.archived)} showProject={!jobScopeProject} locale={locale} csrf={session.csrf} request={request} onOperationComplete={revalidateTicketOperation} bodyMode={ticketBodyMode} modeBusy={ticketModeBusy} onBodyMode={updateTicketBodyMode} />
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
              <span className="system-indicator"><span>{t("workerReadiness")}</span><strong className={`readiness readiness-${workerStatus}`}>{t(workerStatus === "ready" ? "workerReady" : workerStatus === "busy" ? "workerBusy" : workerStatus === "unknown" ? "workerActivityUnknown" : workerStatus === "unavailable" ? "workerUnavailable" : workerStatus === "error" ? "workerCheckFailed" : "workerChecking")}</strong><small>{t("workerQueueHelp")}</small></span>
              <span className="system-indicator"><span>{t("storageStatus")}</span><strong className={`readiness readiness-${storageError ? "error" : storageStatus?.low ? "unavailable" : storageStatus ? "ready" : "checking"}`}>{t(storageError ? "storageCheckFailed" : storageStatus?.low ? "storageLow" : storageStatus ? "storageHealthy" : "workerChecking")}</strong></span>
            </div>
            {storageGroups.length === 1 ? <p className="muted">{t("storageShared").replace("{free}", gib(storageGroups[0].free)).replace("{total}", gib(storageGroups[0].total))}</p>
              : storageGroups.length > 1 && <PagedTable t={t}><table><thead><tr><th>{t("storageVolume")}</th><th>{t("storageFree")}</th><th>{t("status")}</th></tr></thead><tbody>{storageGroups.map(group => <tr key={group.id}><td>{group.names.join(", ")}</td><td>{gib(group.free)} GiB</td><td>{t(group.low ? "storageLow" : "storageHealthy")}</td></tr>)}</tbody></table></PagedTable>}
          </section>
        </div>}

        {page === "adminUsers" && isAdmin && <>
          <section className="panel">
            <div className="panel-heading"><h2>{t("userAccounts")}</h2>
              <button type="button" className="primary" onClick={() => setAccountAction({ kind: "add" })}>{t("createUser")}</button>
            </div>
            {usersState !== "ready" ? <DataFeedback state={usersState} t={t} /> : users.length === 0 ? <Empty label={t("empty")} /> : <div className="user-list">{users.map(item =>
            <div className="user-row" key={item.id}>
              <span className="user-avatar">{item.username.charAt(0).toUpperCase()}</span>
              <div><strong>{item.username}</strong><small>{t(item.role)}{item.disabled ? ` · ${t("disable")}` : ""}</small></div>
              {item.role === "developer" && <details className="membership-editor"><summary>{t("assignedProjects")}</summary>
                <AccountAccessEditor key={item.id} account={item} projects={projects} ready={usersReady && projectsState === "ready"} locale={locale} saveLabel={t("save")} send={sendUsers} onError={setError} onApplied={setNotice} />
              </details>}
              {item.id !== session.user.id && <button type="button" className="ghost" disabled={!usersReady} onClick={() => setAccountEnabled(item.id, item.disabled)}>{t(item.disabled ? "enable" : "disable")}</button>}
              <button type="button" className="ghost" onClick={() => setAccountAction({ kind: "reset", account: item })}>{t("resetPassword")}</button>
            </div>
          )}</div>}</section>
          {accountAction && <AccountActionDialog action={accountAction} projects={projects}
            ready={usersReady && projectsState === "ready" && (accountAction.kind === "add" || users.some(item => item.id === accountAction.account.id && item.username === accountAction.account.username && item.role === accountAction.account.role && item.disabled === accountAction.account.disabled))}
            locale={locale} send={sendUsers}
            onCreated={() => {}} onReset={() => setNotice(t("passwordResetDone"))}
            onClose={() => setAccountAction(null)} />}
        </>}

        {page === "adminAudit" && isAdmin && <AuditHistory key={JSON.stringify([session.user.id, session.user.role])} refresh={viewRefresh} locale={locale} projects={projects} read={(path, signal) => request(path, "GET", undefined, undefined, signal)} />}

        {page === "help" && <HelpCenter locale={locale} topic={helpTopic} onNavigate={navigateHref} />}
        {page === "settings" && <div className="two-column"><section className="panel"><h2>{t("appearance")}</h2><div className="form-stack"><label>{t("language")}<select aria-label={t("language")} value={locale} onChange={event => updatePreference("language", event.target.value)}>{Object.entries(localeNames).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>{t("theme")}<select aria-label={t("theme")} value={theme} onChange={event => updatePreference("theme", event.target.value)}><option value="system">{t("system")}</option><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option></select></label></div></section><section className="panel"><h2>{t("changePassword")}</h2><form className="form-stack" onSubmit={changePassword} onInput={() => setPasswordMismatch(false)}><FormLegend t={t} /><PasswordChangeFields t={t} mismatch={passwordMismatch} /><button className="primary">{t("save")}</button></form></section>
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

function PasswordChangeFields({ t, mismatch, autoFocus }: { t: (key: MessageKey) => string; mismatch: boolean; autoFocus?: boolean }) {
  return <>
    <PasswordField name="current" label={t("currentPassword")} show={t("showCurrentPassword")} hide={t("hideCurrentPassword")} autoComplete="current-password" autoFocus={autoFocus} />
    <PasswordField name="replacement" label={t("newPassword")} show={t("showNewPassword")} hide={t("hideNewPassword")} autoComplete="new-password" minLength={8} hint={t("passwordRule")} />
    <PasswordField name="confirmation" label={t("repeatNewPassword")} show={t("showRepeatPassword")} hide={t("hideRepeatPassword")} autoComplete="new-password" minLength={8} invalid={mismatch} />
    {mismatch && <p className="alert" role="alert">{t("passwordMismatch")}</p>}
  </>;
}

function FormLegend({ t }: { t: (key: MessageKey) => string }) {
  return <p className="form-legend"><span className="required-mark" aria-hidden="true">*</span> {t("requiredLegend")}</p>;
}

type ProjectDeveloper = { id: number; username: string; disabled: boolean; granted: boolean };
const validDevelopers = (value: unknown): value is { developers: ProjectDeveloper[] } => !!value && typeof value === "object" && "developers" in value && Array.isArray(value.developers) && value.developers.every(row => row && Number.isSafeInteger(row.id) && row.id > 0 && typeof row.username === "string" && typeof row.disabled === "boolean" && typeof row.granted === "boolean") && new Set(value.developers.map(row => row.id)).size === value.developers.length;

/** Strict grant authority with stable reviews and serialized post-write validation. */
function ProjectAccess({ request, project, ready, refresh, csrf, locale, t, onError, onNotice }: { request: Request; project: Project; ready: boolean; refresh: number; csrf?: string; locale: Locale; t: (key: MessageKey) => string; onError: (cause: unknown) => void; onNotice: (text: string) => void }) {
  const path = `/projects/${encodeURIComponent(project.id)}/access`;
  const [snapshot, setSnapshot] = useState<ReadSnapshot<ProjectDeveloper[]> | null>(null);
  const current = snapshot?.key === path ? snapshot : null;
  const developers = current?.data ?? null;
  const failed = current?.status === "error";
  const [busy, setBusy] = useState(false);
  const changing = useRef(false);
  const reader = useRef<ReadController | null>(null);
  const [review, setReview] = useState<{ developer: ProjectDeveloper; project: string } | null>(null);
  const [reviewInvalid, setReviewInvalid] = useState(false);
  const projectBinding = JSON.stringify([project.id, project.name, project.archived]);
  const liveProject = useRef({ binding: projectBinding, ready });
  liveProject.current = { binding: projectBinding, ready };
  const sameDeveloper = (row: ProjectDeveloper, previous: ProjectDeveloper) => row.id === previous.id &&
    row.username === previous.username && row.granted === previous.granted && row.disabled === previous.disabled;
  const authority = ready && !project.archived && current?.status === "ready" && !busy;
  const reviewValid = authority && !!review && !reviewInvalid && review.project === projectBinding &&
    !!developers?.some(row => sameDeveloper(row, review.developer));
  // Latch invalidation: later equal-looking values must not revive an old review.
  useEffect(() => {
    if (review && (!ready || project.archived || failed || review.project !== projectBinding ||
      developers !== null && !developers.some(row => sameDeveloper(row, review.developer)))) setReviewInvalid(true);
  }, [review, ready, projectBinding, failed, developers]);
  const copy = userCopy[locale];
  useLayoutEffect(() => {
    const owner = createReadController<ProjectDeveloper[]>({ key: path, deadlineMs: 30000,
      read: async signal => {
        const value = await request<unknown>(path, "GET", undefined, undefined, signal);
        if (!validDevelopers(value)) throw new ApiError("unexpected_response");
        return value.developers;
      },
      publish: value => { setSnapshot(value); if (value.status === "error") onError(value.error); },
    });
    reader.current = owner;
    void owner.refresh();
    const stop = startVisiblePolling(() => { if (!changing.current) void owner.refresh(); }, 15000);
    return () => { stop(); owner.dispose(); if (reader.current === owner) reader.current = null; };
  }, [path, onError]);
  const previousRefresh = useRef(refresh);
  useEffect(() => {
    if (previousRefresh.current === refresh) return;
    previousRefresh.current = refresh;
    if (changing.current) return;
    // An operation result cannot join a read that began before that result.
    reader.current?.cancel(); void reader.current?.refresh();
  }, [refresh]);
  const change = async () => {
    const owner = reader.current;
    if (changing.current || !review || !reviewValid || !owner) return;
    const developer = review.developer, binding = projectBinding;
    changing.current = true; setBusy(true); onError("");
    owner.cancel();
    const stillOwned = () => reader.current === owner && liveProject.current.ready && liveProject.current.binding === binding;
    try {
      const result = await request<{ id: number; granted: boolean }>(`${path}/${developer.id}`, "PUT", { granted: !developer.granted }, csrf);
      if (!result || result.id !== developer.id || result.granted !== !developer.granted) throw new ApiError("unexpected_response");
      if (!stillOwned()) return;
      setReview(null); setReviewInvalid(false);
      onNotice(`${copy.applied}: ${developer.username} · ${t(result.granted ? "hasAccess" : "noAccess")}`);
    } catch (cause) { if (stillOwned()) { setReviewInvalid(true); onError(cause); } }
    finally {
      if (reader.current === owner) {
        // Keep actions disabled until a strict post-write read has validated.
        await owner.refresh();
        if (reader.current === owner) { changing.current = false; setBusy(false); }
      }
    }
  };
  return <section className="panel wide-panel"><h2>{t("projectAccessTab")}</h2><p className="muted">{t("projectAccessHelp")}</p>
    {developers === null ? <DataFeedback state={failed ? "error" : "loading"} t={t} /> : (developers.length === 0 ? <p className="empty">{t("noDevelopers")}</p> : <div className="user-list">{developers.map(developer =>
      <div className="user-row" key={developer.id}>
        <span className="user-avatar">{developer.username.charAt(0).toUpperCase()}</span>
        <div><strong>{developer.username}</strong><small>{t("developer")}{developer.disabled ? ` · ${t("accountDisabled")}` : ""}</small></div>
        <span className={developer.granted ? "status status-working" : "status"}>{t(developer.granted ? "hasAccess" : "noAccess")}</span>
        <button type="button" className="ghost" disabled={!authority || review !== null} aria-label={`${t(developer.granted ? "removeAccess" : "grantAccess")}: ${developer.username}`} onClick={() => { setReview({ developer, project: projectBinding }); setReviewInvalid(false); }}>{t(developer.granted ? "removeAccess" : "grantAccess")}</button>
      </div>)}</div>)}
    {review && (reviewInvalid || !reviewValid && !busy) && <p role="alert" className="alert">{copy.reviewChanged}</p>}
    {review && <AccessReview subject={`${review.developer.username} · ${project.name}`} before={t(review.developer.granted ? "hasAccess" : "noAccess")} after={t(review.developer.granted ? "noAccess" : "hasAccess")} copy={copy} busy={busy} canApply={reviewValid} correct={() => { setReview(null); setReviewInvalid(false); }} apply={() => void change()} />}
  </section>;
}

function SettingsImpactDialog({config, candidate, edits, project, paused, locale, onDecision}: {
  config: Config; candidate: PendingConfig; edits: SettingEdit[]; project: string;
  paused: boolean; locale: Locale; onDecision: (accepted: boolean) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null), cancelButton = useRef<HTMLButtonElement>(null);
  const copy = settingsSaveCopy[locale];
  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.current?.showModal(); cancelButton.current?.focus();
    return () => { dialog.current?.close(); if (trigger?.isConnected) trigger.focus(); };
  }, []);
  const rows = settingRows(config.config, config.settings || []);
  const proposed = candidate.key === BATCH_KEY ? candidate.proposed_value as Record<string,unknown> : {[candidate.key]:candidate.proposed_value};
  const show = (key: string, value: unknown) => agentValue(key,value,locale)
    ?? (key === "delivery.draft" ? publicationValue(value,locale) : key === "review.on_pipeline_failure" ? pipelineFailureValue(value,locale) : null)
    ?? (Array.isArray(value) || value && typeof value === "object" ? JSON.stringify(value) : String(value ?? ""));
  const changed = edits.flatMap(({key}) => {
    if (key === CONNECTION_KEY) {
      const before = connectionOf(config.config), after = proposed[key] as typeof before;
      return ([["executor.provider", "provider"], ["executor.model", "model"], ["executor.thinking", "thinking"], ["executor.endpoint.base_url", "base_url"], ["executor.endpoint.api", "api"]] as const)
        .filter(([,field])=>!sameSettingValue(before[field],after[field]))
        .map(([key,field])=>({key,before:before[field],after:after[field]}));
    }
    return [{key,before:settingValue(config.config,key),after:proposed[key]}];
  });
  return <dialog ref={dialog} className="settings-impact-dialog" aria-labelledby="settings-impact-title"
    onCancel={event=>{event.preventDefault();onDecision(false);}}>
    <h2 id="settings-impact-title">{copy.title}</h2>
    <p><strong>{copy.project}:</strong> {project}</p>
    <div className="table-scroll"><table className="settings-impact-values"><thead><tr><th>{compactReviewCopy[locale].setting}</th><th>{copy.before}</th><th>{copy.after}</th></tr></thead>
      <tbody>{changed.map(row=><tr key={row.key}><th scope="row">{settingDisplayLabel(row.key,locale)}</th>
        <td data-label={copy.before}>{show(row.key,row.before)}</td><td data-label={copy.after}>{show(row.key,row.after)}</td></tr>)}</tbody></table></div>
    <ul>{settingImpacts(edits,rows).map(impact=><li key={impact}>{impact === "network" && settingValue(config.config,"execution.backend") === "local" ? internetCopy[locale].internetLocal : copy.effects[impact]}</li>)}</ul>
    {proposed["executor.internet"] === true && settingValue(config.config,"execution.backend") !== "local"
      && <p className="alert" role="note">{internetCopy[locale].internetWarning}</p>}
    <p className="muted">{copy.future}</p>
    {candidate.execution_plan && <details><summary>{settingsCopy[locale].details}</summary><ExecutionPlanReview plan={candidate.execution_plan} locale={locale} /></details>}
    {candidate.restart_required && !paused && <p role="alert" className="alert">{copy.pause}</p>}
    <div className="button-row"><button ref={cancelButton} type="button" className="ghost" onClick={()=>onDecision(false)}>{copy.cancel}</button>
      <button type="button" className="primary" disabled={candidate.restart_required && !paused} onClick={()=>onDecision(true)}>{copy.confirm}</button></div>
  </dialog>;
}

function SettingsList({ request, executorOnly=false, project, revision, csrf, branchCandidate=null, config, localIdentity, settings, t, locale, canEdit, disabled: externallyDisabled, stale: externallyStale=false, readFailed=false, onSave, onDiscard, registerGuard, setPollBlocked, actions, children, header, executorBefore, executorAfter, executorAuthentication }: {
  request: Request;
  executorBefore?:ReactNode; executorAfter?:ReactNode; executorAuthentication?:ReactNode;
  project?:string; revision?:string; csrf?:string; branchCandidate?:PendingConfig|null;
  header?:ReactNode; actions?:ReactNode; children?:ReactNode; executorOnly?:boolean;
  config:Record<string,unknown>; localIdentity?:Config["local_execution"]; settings:SettingMeta[];
  t:(key:MessageKey)=>string; locale:Locale; canEdit:boolean; disabled:boolean; stale?:boolean; readFailed?:boolean;
  onSave:(edits:SettingEdit[],base:string)=>Promise<boolean>; onDiscard:()=>Promise<boolean>;
  registerGuard:(guard:(()=>boolean)|null)=>void;
  setPollBlocked:(blocked:boolean)=>void;
}) {
  const rows = settingRows(config, settings);
  const recoveryBackend=branchCandidate?.key===BATCH_KEY
    ? (branchCandidate.proposed_value as Record<string,unknown>)["execution.backend"] : undefined;
  const exactRecovery=!!branchCandidate && pendingSettingEdits(branchCandidate).some(edit=>!rows.some(row=>
    row.editKey===edit.key && row.input!=="none" && settingVisible(row.key,executorOnly,String(recoveryBackend ?? settingValue(config,"execution.backend") ?? "container"))
    && connectionRowVisible(row.key,settingValue(config,"executor.provider"))));
  const recoveredEditors = (values:SettingDrafts) => new Set(rows.filter(row=>values[row.editKey]!==undefined
    && (row.input!=="connection" || row.key==="executor.model")).map(row=>row.key));
  const [drafts, setDrafts] = useState<SettingDrafts>(()=>exactRecovery ? {} : recoverSettingDrafts(config,rows,branchCandidate));
  const [editing, setEditing] = useState<Set<string>>(()=>recoveredEditors(drafts));
  const [saving, setSaving] = useState(false), [conflict, setConflict] = useState(false);
  const disabled = externallyDisabled || saving || readFailed;
  const saveBar = useRef<HTMLDivElement>(null), wasSaving = useRef(false);
  useEffect(() => {
    if (wasSaving.current && !saving) {
      const button=saveBar.current?.querySelector<HTMLButtonElement>("button.primary:not(:disabled)");
      if (button) button.focus(); else saveBar.current?.focus();
    }
    wasSaving.current=saving;
  }, [saving]);
  const base = useRef({config,rows,revision});
  const live = useRef({config,rows,revision}); live.current = {config,rows,revision};
  const pendingRevision = useRef(branchCandidate?.candidate_revision || "");
  const prepared = prepareSettingDrafts(base.current.config,base.current.rows,drafts);
  const dirty = prepared.edits.length + prepared.invalid.length > 0;
  const alreadyApplied = !!branchCandidate && branchCandidate.candidate_revision === revision;
  useLayoutEffect(() => { setPollBlocked(dirty || saving || !!branchCandidate && !alreadyApplied); });
  useLayoutEffect(() => () => setPollBlocked(false), [setPollBlocked]);
  const stale = externallyStale || conflict || dirty && base.current.revision !== revision
    || !!branchCandidate && branchCandidate.base_revision !== revision && !alreadyApplied;
  const saveCopy = settingsSaveCopy[locale];
  useEffect(() => {
    const next = branchCandidate?.candidate_revision || "";
    if (saving) return;
    const revisionChanged = base.current.revision !== revision;
    if (!dirty && revisionChanged) base.current = live.current;
    if (next && (next !== pendingRevision.current || revisionChanged && !dirty)) {
      if (!dirty) {
        const recovered=exactRecovery ? {} : recoverSettingDrafts(config,rows,branchCandidate);
        setDrafts(recovered);setEditing(recoveredEditors(recovered));
      }
      else if (pendingRevision.current) setConflict(true);
    } else if (!dirty && revisionChanged) { setDrafts({}); setEditing(new Set()); }
    pendingRevision.current = next;
  }, [branchCandidate?.candidate_revision, revision, dirty, saving]);
  useEffect(() => {
    registerGuard(dirty || saving ? ()=>!saving && window.confirm(saveCopy.leave) : null);
    const unload = (event:BeforeUnloadEvent) => { if (dirty || saving) {event.preventDefault();event.returnValue="";} };
    window.addEventListener("beforeunload",unload);
    return () => {registerGuard(null);window.removeEventListener("beforeunload",unload);};
  }, [dirty,saving,saveCopy.leave,registerGuard]);
  const draftFor = (row:SettingRow) => drafts[row.editKey] ?? settingDraftValue(row,config);
  const updateDraft = (row:SettingRow,value:string) => {
    setPollBlocked(true);
    setDrafts(previous=>({...previous,[row.editKey]:value}));
  };
  const beginEdit = (row:SettingRow) => {
    setEditing(previous=>{
      const next=new Set(previous);
      if (row.input==="connection") for (const item of rows) if (item.editKey===row.editKey) next.delete(item.key);
      next.add(row.key);return next;
    });
  };
  const cancelEdit = (row:SettingRow) => {
    setDrafts(previous=>{const next={...previous};delete next[row.editKey];return next;});
    setEditing(previous=>{const next=new Set(previous);next.delete(row.key);return next;});
  };
  const saveAll = async () => {
    if (disabled || stale || prepared.invalid.length || branchInvalid || !base.current.revision) return;
    setPollBlocked(true);
    setSaving(true);
    try {
      if (await onSave(prepared.edits,base.current.revision)) {
        base.current=live.current;setDrafts({});setEditing(new Set());setConflict(false);
      }
    } finally {setSaving(false);}
  };
  const discardAll = async () => {
    if (externallyDisabled || saving) return;
    setPollBlocked(true);
    setSaving(true);
    try {
      if (await onDiscard()) {
        base.current=live.current;setDrafts({});setEditing(new Set());setConflict(false);
      }
    } finally {setSaving(false);}
  };
  // Image suggestions from the server while the image row is being edited.
  const [serverImages, setServerImages] = useState<ServerImages | null>(null);
  const imageRuntime = drafts["container.runtime"] ?? String(settingValue(config,"container.runtime") ?? "docker");
  useEffect(() => {
    if (!editing.has("container.image")) return;
    let active = true;
    setServerImages(null);
    void readServerImages(imageRuntime).then(value => { if (active) setServerImages(value); });
    return () => { active = false; };
  }, [editing, imageRuntime]);
  const [branchPreview, setBranchPreview] = useState<BranchPreview | null>(null);
  const [branchFailure, setBranchFailure] = useState("");
  const template = drafts["worktree.branch_template"] ?? String(settingValue(config, "worktree.branch_template") ?? "");
  const rule = drafts["worktree.branch_rule"] ?? String(settingValue(config, "worktree.branch_rule") ?? "");
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
  const backend = drafts["execution.backend"] ?? String(settingValue(config, "execution.backend") ?? "container");
  const groups = settingGroups(settingRows(config, settings).filter(row => settingVisible(row.key, executorOnly, backend)
    && connectionRowVisible(row.key, settingValue(config, "executor.provider"))), false);
  const copy = settingsCopy[locale];
  const shown = (value: unknown) => value == null || value === "" ? "—" :
    Array.isArray(value) || typeof value === "object" ? JSON.stringify(value) : String(value);
  const label = (row: SettingRow) => settingDisplayLabel(row.key, locale);
  const editorCopy = implementationEditorCopy[locale];
  const typedValue = (row:SettingRow) => normalizeSettingDraft(row,draftFor(row));
  const branchInvalid = prepared.edits.some(edit=>BRANCH_NAMING_KEYS.has(edit.key)) && !currentPreview?.valid;
  const editor = (row:SettingRow) => {
    const draft=draftFor(row), setDraft=(value:string)=>updateDraft(row,value);
    let stageValues:Record<string,number>={};
    try { const parsed=JSON.parse(draft);if(parsed && typeof parsed==="object" && !Array.isArray(parsed)) stageValues=parsed; } catch { /* Incomplete input remains local. */ }
    return <div className="setting-editor">
          {row.input === "connection" ? <AgentConnectionEditor value={draft} locale={locale} disabled={disabled} onChange={setDraft}/>
          : row.key === "container.runtime" ? <ContainerRuntimePicker value={draft} label={label(row)}
            descriptionId={`help-${row.key}`} locale={locale} disabled={disabled} onChange={setDraft} />
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
            ? <select aria-label={label(row)} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)}>{row.input === "choice" && !row.choices.includes(draft) && <option value={draft} disabled>{draft}</option>}{(row.input === "boolean" ? ["true", "false"] : row.choices).map(option => <option key={option} value={option}>{agentValue(row.key, option, locale) ?? (row.key === "review.on_pipeline_failure" ? pipelineFailureValue(option, locale) ?? option : row.key === "delivery.draft" ? publicationValue(option, locale) : option)}</option>)}</select>
            : row.key === "workflow.verify_command" ? <textarea rows={1} aria-label={label(row)} aria-describedby={`help-${row.key}` + (typedValue(row) === null ? ` error-${row.key}` : "")} aria-invalid={typedValue(row) === null || undefined} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} />
            : row.input === "reviewers" ? <textarea rows={6} aria-label={label(row)} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} />
            : <input aria-label={label(row)} type={row.input === "number" ? "number" : "text"} step={row.step} min={row.minimum ?? undefined} max={row.maximum ?? undefined} maxLength={BRANCH_NAMING_KEYS.has(row.key) ? 512 : undefined} aria-describedby={`help-${row.key}`} disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} required={row.input === "number"}
              list={row.key === "container.image" && serverImages?.images.length ? "setting-image-options" : undefined} />}
          {row.key === "container.image" && !!serverImages?.images.length && <datalist id="setting-image-options">{serverImages.images.map(name => <option value={name} key={name} />)}</datalist>}
          {row.key === "container.image" && serverImages && (!serverImages.available ? <p className="field-hint">{enrollmentCopy[locale].imagesUnavailable}</p>
            : draft.trim() && !serverImages.images.includes(draft.trim()) && <p className="field-hint" role="status">{enrollmentCopy[locale].imageMissing}</p>)}
          <div className="button-row"><button type="button" className="ghost" disabled={disabled} onClick={() => cancelEdit(row)}>{t("cancel")}</button></div>
          {typedValue(row) === null && <p role="alert" id={`error-${row.key}`}>{row.key === "workflow.verify_command" ? t("verificationCommandInvalid") : row.input === "connection" ? connectionCopy[locale].invalid : editorCopy.invalid}</p>}
        </div>;
  };
  const renderRow = (row:SettingRow) => <div className="setting-row" key={row.key} id={`setting-${row.key}`} tabIndex={-1}>
        <div>
          <strong>{label(row)}</strong><p className="setting-essential" id={`help-${row.key}`}>{executorSettingHelp(row.key, locale) ?? settingHelp(row.key, locale) ?? t("settingGeneralHelp")}</p>
          {row.source !== "project" && <span className="setting-badge">{t("settingDefault")}</span>}
          {canEdit && row.input !== "none" && row.restart && <small className="setting-note">{t("settingRestartShort")}</small>}
          {canEdit && row.input === "none" && <small className="setting-note">{t("settingNotEditableShort")}</small>}
        </div>
        {editing.has(row.key) ? <div className="setting-control">{editor(row)}</div> : <div className="setting-control"><div className="setting-value-heading"><small>{copy.active}</small>
          {canEdit && row.input !== "none" && !editing.has(row.key) && <button type="button" className="text-button" disabled={disabled || exactRecovery} aria-label={`${t("editSetting")} ${label(row)}`} data-edit-key={row.editKey} onClick={() => beginEdit(row)}>{t("editSetting")}</button>}
        </div><code>{agentValue(row.key, row.value, locale) ?? (row.key === "review.on_pipeline_failure" ? pipelineFailureValue(row.value, locale) ?? shown(row.value) : row.key === "delivery.draft" ? publicationValue(row.value, locale) : shown(row.value))}</code><small>{t("settingDefaultValue")}: {hasDefault(row.defaultValue) ? agentValue(row.key, row.defaultValue, locale) ?? (row.key === "review.on_pipeline_failure" ? pipelineFailureValue(row.defaultValue, locale) ?? shown(row.defaultValue) : row.key === "delivery.draft" ? publicationValue(row.defaultValue, locale) : shown(row.defaultValue)) : t("settingNoDefault")}</small></div>}
        {row.key === "executor.internet" && (backend === "local"
          ? <p className="setting-note" role="note">{internetCopy[locale].internetLocal}</p>
          : (editing.has(row.key) ? draftFor(row) === "true" : row.value === true) && <p className="alert" role="note">{internetCopy[locale].internetWarning}</p>)}

      </div>;
  return <section className="panel" id="project-settings">
    {header ?? <div className="panel-heading"><div className="heading-with-help"><h2>{executorOnly ? executorCopy[locale].tab : t("projectSettings")}</h2>{!executorOnly && <HelpLink topic={CONTEXT_TOPICS.projectSettings} locale={locale} />}</div>{actions}</div>}
    {!canEdit && <p className="muted">{copy.readOnly}</p>}
    {canEdit && <div ref={saveBar} tabIndex={-1} className="settings-save-bar" aria-label={saveCopy.save}>
      <div><span role="status" aria-live="polite">{dirty ? saveCopy.dirty.replace("{count}",String(prepared.edits.length+prepared.invalid.length)) : branchCandidate ? saveCopy.prepared : saveCopy.clean}</span>
      {stale && <p role="alert">{saveCopy.stale}</p>}
      {(prepared.invalid.length>0 || branchInvalid) && <p role="alert">{saveCopy.invalid}</p>}</div>
      <div className="button-row"><button type="button" className="ghost" disabled={externallyDisabled || saving || !dirty && !branchCandidate && !readFailed} onClick={()=>void discardAll()}>{saveCopy.discard}</button>
      <button type="button" className="primary" disabled={disabled || stale || prepared.invalid.length>0 || branchInvalid || !prepared.edits.length && !alreadyApplied && !exactRecovery} onClick={()=>void saveAll()}>{saving ? saveCopy.saving : saveCopy.save}</button></div>
    </div>}
    {children}
    {groups.length === 0 ? <Empty label={t("settingsNoneSet")} /> : <div className="setting-groups">{groups.map(group => {
      return <details key={group.name} data-setting-purpose={group.name} open={executorOnly}>
      <summary>{copy[group.name as keyof typeof copy]} <span className="muted">({group.rows.length})</span></summary>
      {group.name === "executor" && <div className="executor-settings-content executor-connection-area">{executorBefore}</div>}
      {group.name === "executor" && backend === "local" && <p className="field-hint">{localCopy[locale].account}{localIdentity && <>: <strong>{localIdentity.account}</strong> · {localIdentity.machine} · {localIdentity.system}</>}. {localCopy[locale].notice}</p>}
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
        <div className="setting-control"><div className="setting-value-heading"><small>{copy.active}</small></div><code>{shown(settingValue(config, "delivery.target_branch"))}</code></div>
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
        {(["clarification", "recovery", "stageLimits", "statisticsFiles", "authentication"] as const).map(topic => {
          const rows = group.rows.filter(row => settingSubgroup(row.key) === topic);
          return rows.length > 0 && <details className="setting-topic" data-setting-topic={topic} key={topic}>
            <summary>{copy[topic]} <span className="muted">({rows.length})</span></summary>
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

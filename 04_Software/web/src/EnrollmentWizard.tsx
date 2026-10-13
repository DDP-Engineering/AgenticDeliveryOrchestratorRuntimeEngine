/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { Locale, MessageKey } from "./i18n";
import { ApiError, describeError } from "./errors";
import { enrollmentCopy } from "./enrollmentCopy";
import { transferCopy, validTransferSettings, type TransferSource } from "./transferCopy";
import { portableFields } from "./portable";
import { localCopy } from "./localExecution";
import { proposeImage, readServerImages, type ServerImages } from "./serverImages";
import { HelpLink } from "./HelpCenter";
import { CONTEXT_TOPICS } from "./help/topics.ts";

type Draft = {
  clone_url: string; name: string; display_name: string; description: string; kind: string; repo: string;
  repo_path: string; target_branch: string; login: string; executor_cli: string; model: string;
  runtime: string; image: string; auth_mode: string; env_keys: string; reviewers: string;
  execution_backend: string; local_account: string; local_home: string; local_path: string; local_cgroup_root: string;
  executor_command: string;
  ready_label: string; approval_label: string; max_iterations: string;
  max_wall_clock_seconds: string; max_cost_usd: string; max_files_touched: string;
};
type FieldName = keyof Draft;
type Finding = { code: string; field: string; remediation: string };
type Preview = { structural_valid: boolean; issues: Finding[]; revision: string | null;
  config_revision: string | null; review: Record<string, unknown> | null; source_revision?: string;
  mapping?: { key: string; source_value: unknown; server_value: unknown; effect: string }[] };
type Verification = { status: "failed" | "partial" | "verified"; draft_revision: string; revision: string;
  checked_at: string; checks: Record<string, boolean | null | "not-checked"> };
type Created = { id: string; name: string; display_name: string; pickup_state: string; paused: boolean };
/** What Read repository found for a repository URL; nothing is written on the server yet. */
type Detected = { url: string; kind: string | null; login: string; repo: string; default_branch: string | null;
  name: string; display_name: string; repo_path: string; clone: "new" | "existing" };
const validDetected = (value: unknown): value is Detected => {
  const item = value as Detected;
  return !!item && typeof item.url === "string" && (item.kind === null || ["gitlab", "github", "gitea"].includes(item.kind))
    && typeof item.login === "string" && typeof item.repo === "string" && (item.default_branch === null || typeof item.default_branch === "string")
    && /^[a-z0-9][a-z0-9._-]{0,63}$/.test(item.name) && typeof item.display_name === "string" && typeof item.repo_path === "string"
    && ["new", "existing"].includes(item.clone);
};
/** Locale-neutral example values shown in empty fields. */
const examples: Partial<Record<string, string>> = { clone_url: "https://github.com/owner/repository",
  login: "gitea-main", repo_path: "/home/adore/repos/payments", target_branch: "main", model: "provider/model-name",
  reviewers: "alice, bob", env_keys: "OPENAI_API_KEY" };
class SetupError extends ApiError {
  constructor(code: string, readonly findings: Finding[]) { super(code); }
}
const initial: Draft = { clone_url: "", name: "", display_name: "", description: "", kind: "gitlab", repo: "", repo_path: "",
  execution_backend: "container", local_account: "current", local_home: "", local_path: "", local_cgroup_root: "",
  executor_command: "",
  target_branch: "main", login: "", executor_cli: "opencode", model: "", runtime: "docker", image: "adore-executor-base:1.0.0",
  auth_mode: "api-key", env_keys: "", reviewers: "", ready_label: "agent-ready", approval_label: "agent-approved",
  max_iterations: "12", max_wall_clock_seconds: "5400", max_cost_usd: "5", max_files_touched: "120" };
const fields: FieldName[][] = [[], ["clone_url", "display_name", "name", "description", "kind", "repo", "login", "repo_path", "target_branch"],
  ["executor_cli", "model", "execution_backend", "runtime", "image", "executor_command", "local_account",
    "local_home", "local_path", "local_cgroup_root", "auth_mode", "env_keys"],
  ["ready_label", "approval_label", "reviewers", "max_iterations", "max_wall_clock_seconds", "max_cost_usd", "max_files_touched"]];
const numeric = ["max_iterations", "max_wall_clock_seconds", "max_cost_usd", "max_files_touched"] as const;
const digest = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const isFindings = (value: unknown): value is Finding[] => Array.isArray(value) && value.every(item =>
  item && typeof item.code === "string" && typeof item.field === "string" && typeof item.remediation === "string");
const payload = (draft: Draft): Omit<Draft, typeof numeric[number] | "env_keys"> & {
  env_keys: string[]; max_iterations: number; max_wall_clock_seconds: number; max_cost_usd: number; max_files_touched: number;
} => ({ ...draft, env_keys: ["host-auth", "existing"].includes(draft.auth_mode) ? [] :
  draft.env_keys.split(",").map(value => value.trim()).filter(Boolean),
  max_iterations: Number(draft.max_iterations), max_wall_clock_seconds: Number(draft.max_wall_clock_seconds),
  max_cost_usd: Number(draft.max_cost_usd), max_files_touched: Number(draft.max_files_touched) });
const fieldFor = (path: string): FieldName | undefined => {
  const aliases: Record<string, FieldName> = { "executor.env_keys": "env_keys", "worktree.repo_path": "repo_path",
    "platform.repo": "repo", "container.runtime": "runtime", "container.image": "image",
    "executor.default": "executor_cli", "delivery.reviewers": "reviewers", "delivery.target_branch": "target_branch" };
  const first = path.split(".")[0], last = path.split(".").at(-1) ?? path;
  return aliases[path] ?? (path in initial ? path as FieldName : first in initial ? first as FieldName :
    last in initial ? last as FieldName : undefined);
};

/** Mounted memory-only enrollment; server owns canonical setup and stopped publication. */
export function EnrollmentWizard({ locale, csrf, t, onCancel, onOpen, onCreated, registerGuard, transfer, onSourceReview, checkSource }: {
  locale: Locale; csrf: string; t: (key: MessageKey) => string; onCancel: () => void;
  onOpen: (id: string) => void; onCreated: () => void;
  registerGuard: (guard: (() => boolean) | null) => void;
  transfer?: TransferSource; onSourceReview?: () => void; checkSource?: () => Promise<void>;
}) {
  const c = enrollmentCopy[locale];
  const tc = transferCopy[locale];
  const [draft, setDraft] = useState<Draft>(() => ({ ...initial, ...(transfer ?
    Object.fromEntries(numeric.map(key => [key, String(transfer.settings.budgets[key])])) : {}) }));
  // Enrollment starts at Repository and identity; the clone requirement is that step's clone-path help.
  const [step, setStep] = useState(1);
  const [referencesConfirmed, setReferencesConfirmed] = useState(false);
  // Step 1 reads a repository URL; an existing clone is reused when its path is the clone path.
  const [detected, setDetected] = useState<Detected | null>(null);
  const [detecting, setDetecting] = useState(false);
  // Tagged images on the server for the chosen runtime (suggestions, never a limit).
  const [images, setImages] = useState<ServerImages | null>(null);
  const proposedImage = useRef("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [stale, setStale] = useState(false);
  const [reviewed, setReviewed] = useState<{ draft: ReturnType<typeof payload>; preview: Preview } | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState<"preview" | "probe" | "create" | null>(null);
  const [created, setCreated] = useState<Created | null>(null);
  const generation = useRef(0);
  const operation = useRef<"preview" | "probe" | "create" | null>(null);
  const dirty = useRef(false);
  const alive = useRef(true);
  const heading = useRef<HTMLHeadingElement>(null);
  const summary = useRef<HTMLDivElement>(null);
  const focusTarget = useRef<string | null>(null);

  const guard = () => {
    if (operation.current === "create") { heading.current?.focus(); return false; }
    if (!dirty.current) return true;
    if (!window.confirm(c.loss)) return false;
    dirty.current = false;
    return true;
  };
  useEffect(() => {
    registerGuard(guard);
    const unload = (event: BeforeUnloadEvent) => {
      if (dirty.current || operation.current === "create") { event.preventDefault(); event.returnValue = ""; }
    };
    // Capture links from project context as well as the shared shell.
    const click = (event: MouseEvent) => {
      const link = (event.target as Element).closest?.("a[href]") as HTMLAnchorElement | null;
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
        link.getAttribute("href")?.startsWith("#")) return;
      if (!guard()) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener("beforeunload", unload);
    document.addEventListener("click", click, true);
    return () => {
      registerGuard(null); window.removeEventListener("beforeunload", unload);
      document.removeEventListener("click", click, true);
    };
  }, [locale, registerGuard]);
  useEffect(() => { alive.current = true; return () => { alive.current = false; generation.current++; }; }, []);
  useEffect(() => { if (created) heading.current?.focus(); }, [created]);
  useEffect(() => {
    const target = focusTarget.current;
    const element = target ? document.getElementById(target) : null;
    focusTarget.current = null;
    if (element) element.focus();
    else heading.current?.focus({ preventScroll: true });
  }, [step]);
  useEffect(() => { if (findings.length || failure) summary.current?.focus(); }, [findings, failure]);

  const move = (next: number, field?: FieldName) => {
    if (operation.current === "create") return;
    focusTarget.current = field ? "enroll-" + field : null;
    setStep(next);
    if (next === step) {
      if (field) document.getElementById("enroll-" + field)?.focus();
      else heading.current?.focus();
    }
  };
  const correct = (finding: Finding) => {
    if (finding.field === "references_confirmed") { move(2); return; }
    const field = fieldFor(finding.field);
    const target = field ? fields.findIndex(group => group.includes(field)) : 4;
    move(Math.max(1, target), field);
  };
  const change = (field: FieldName, value: string) => {
    dirty.current = true; generation.current++;
    if (preview || verification || reviewed) setStale(true);
    setPreview(null); setVerification(null); setReviewed(null); setFindings([]); setFailure(null);
    if (fields[1].includes(field) || fields[2].includes(field)) setReferencesConfirmed(false);
    operation.current = null; setBusy(null);
    const prefilled = field === "clone_url" && detected ? detected.display_name : null;
    if (field === "clone_url") setDetected(null);
    setDraft(current => ({ ...current, [field]: value,
      ...(prefilled !== null && current.display_name === prefilled ? { display_name: "" } : {}),
      // A new URL needs a new read and a new derived ID.
      ...(field === "clone_url" ? { name: "", repo: "", repo_path: "" } : {}),
      ...(field === "execution_backend" ? {auth_mode: value === "local" ? "existing" : "api-key"} : {}),
      ...(field === "executor_cli" && current.execution_backend !== "local" && !["opencode", "codex"].includes(value) ? { auth_mode: "api-key" } : {}) }));
  };
  const validateLocal = (groups: number[]) => {
    const errors: Finding[] = [];
    for (const key of groups.flatMap(index => fields[index])) {
      if (["description", "login", "executor_command", "local_home", "local_path", "local_cgroup_root", "name"].includes(key)
          || key === "reviewers" && !draft.reviewers.trim()
          || key === "env_keys" && !draft.env_keys.trim()
          || key === "repo"
          || key.startsWith("local_") && draft.execution_backend !== "local"
          || ["runtime", "image"].includes(key) && draft.execution_backend === "local"
          || key === "env_keys" && ["host-auth", "existing"].includes(draft.auth_mode)) continue;
      const value = draft[key];
      let valid = !!value.trim();
      if (key === "clone_url") valid = !!detected && detected.url === value;
      if (key === "kind") valid = ["gitlab", "github", "gitea"].includes(value);
      if (key === "name") valid = /^[a-z0-9][a-z0-9._-]{0,63}$/.test(value);
      if (key === "display_name") valid = value === value.trim() && value.length > 0 && value.length <= 120 &&
        !/[\p{Cc}\p{Cf}]/u.test(value);
      if (key === "env_keys") valid = value.split(",").every(name => /^[A-Z][A-Z0-9_]{0,63}$/.test(name.trim()));
      if (numeric.includes(key as typeof numeric[number])) {
        const number = Number(value); valid = !!value.trim() && Number.isFinite(number) &&
          (key === "max_cost_usd" ? number >= 0 : Number.isSafeInteger(number) && number > 0);
      }
      if (!valid) errors.push({ code: "invalid_input", field: key, remediation: c.invalid });
    }
    if (transfer && groups.includes(2) && !referencesConfirmed)
      errors.push({ code: "invalid_input", field: "references_confirmed", remediation: tc.confirm });
    setFindings(errors); setFailure(null);
    return errors.length === 0;
  };
  const call = async (path: string, body: unknown): Promise<unknown> => {
    if (transfer) await checkSource?.();
    let response: Response;
    try {
      response = await fetch("/api/v1/projects/" + path, { method: "POST", credentials: "same-origin",
        cache: "no-store", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) });
    } catch { throw new ApiError("network_error"); }
    const value = await response.json().catch(() => { throw new ApiError("unexpected_response"); });
    if (!response.ok) {
      if (typeof value?.detail?.code !== "string") throw new ApiError("unexpected_response");
      throw new SetupError(value.detail.code, isFindings(value.detail.issues) ? value.detail.issues : []);
    }
    return value;
  };
  const targetPayload = () => ({ ...payload(draft), ...(transfer ? {
    max_iterations: 12, max_wall_clock_seconds: 5400, max_cost_usd: 5, max_files_touched: 120,
  } : {}) });
  const requestBody = (target: unknown, revision?: string) => transfer ? {
    ...transfer.selection, source_revision: transfer.source_revision, target,
    references_confirmed: referencesConfirmed, ...(revision ? { revision } : {}),
  } : { ...(target as object), ...(revision ? { revision } : {}) };
  const reject = (cause: unknown) => {
    setFailure(cause);
    setFindings(cause instanceof SetupError ? cause.findings : []);
  };
  useEffect(() => {
    if (step !== 2 || draft.execution_backend !== "container") return;
    let active = true;
    setImages(null);
    void readServerImages(draft.runtime).then(value => { if (active) setImages(value); });
    return () => { active = false; };
  }, [step, draft.execution_backend, draft.runtime]);
  useEffect(() => {
    // Replace only the built-in default or an earlier proposal, never a typed image.
    if (!images?.available || ![initial.image, "", proposedImage.current].includes(draft.image)) return;
    const next = proposeImage(images.images, draft.executor_cli);
    // A proposal is not a user edit: it keeps confirmations and is skipped once a preview exists.
    if (next && next !== draft.image && !preview) { proposedImage.current = next; setDraft(current => ({ ...current, image: next })); }
  }, [images, draft.executor_cli]);
  const readRepository = async () => {
    if (detecting) return;
    if (!draft.clone_url.trim()) { setFindings([{ code: "invalid_input", field: "clone_url", remediation: c.readFirst }]); return; }
    const token = generation.current;
    setDetecting(true); setFailure(null); setFindings([]);
    try {
      const value = await call("repository-source", { url: draft.clone_url.trim() });
      if (!alive.current || token !== generation.current) return;
      if (!validDetected(value)) throw new ApiError("unexpected_response");
      dirty.current = true; generation.current++;
      if (preview || verification || reviewed) setStale(true);
      setPreview(null); setVerification(null); setReviewed(null); setReferencesConfirmed(false);
      setDetected(value);
      setDraft(current => ({ ...current, clone_url: value.url, name: value.name, repo: value.repo, repo_path: value.repo_path,
        kind: value.kind ?? "", login: value.login, target_branch: value.default_branch ?? current.target_branch,
        display_name: current.display_name.trim() ? current.display_name : value.display_name }));
    } catch (cause) { if (alive.current && token === generation.current) reject(cause); }
    finally { if (alive.current) setDetecting(false); }
  };
  const runPreview = async () => {
    if (operation.current || !validateLocal([1, 2, 3])) return;
    const token = generation.current;
    operation.current = "preview"; setBusy("preview"); setFailure(null); setReviewed(null);
    setPreview(null); setVerification(null);
    try {
      const value = await call(transfer ? "transfer-preview" : "setup-preview", requestBody(targetPayload())) as Preview;
      if (!alive.current || token !== generation.current) return;
      if (typeof value?.structural_valid !== "boolean" || !isFindings(value.issues) ||
        value.structural_valid !== (value.issues.length === 0) ||
        value.structural_valid && (!digest(value.revision) || !digest(value.config_revision) ||
          !value.review || value.review.name !== draft.name || value.review.display_name !== draft.display_name ||
          ["config_path", "store_root", "worktree_root"].some(key => typeof value.review?.[key] !== "string")))
        throw new ApiError("unexpected_response");
      if (transfer && value.structural_valid) {
        const expected = Object.entries(portableFields).flatMap(([section, keys]) => keys.map(key => section + "." + key));
        if (value.source_revision !== transfer.source_revision || !Array.isArray(value.mapping) || value.mapping.length !== expected.length ||
          expected.some(key => value.mapping!.filter(row => row.key === key).length !== 1) ||
          value.mapping.some(row => row.effect !== "copy-rule" || !Object.hasOwn(row, "server_value") ||
            JSON.stringify(row.source_value) !== JSON.stringify(transfer.settings[row.key.split(".")[0]][row.key.split(".")[1]])) ||
          ["metrics_db", "metrics_jsonl", "metrics_html"].some(key => typeof value.review?.[key] !== "string"))
          throw new ApiError("unexpected_response");
        const server = Object.fromEntries(Object.entries(portableFields).map(([section, keys]) => [section,
          Object.fromEntries(keys.map(key => [key, value.mapping!.find(row => row.key === section + "." + key)!.server_value]))]));
        if (!validTransferSettings(server)) throw new ApiError("unexpected_response");
      }
      setPreview(value); setFindings(value.issues); setStale(false);
    } catch (cause) { if (alive.current && token === generation.current) reject(cause); }
    finally { if (alive.current && token === generation.current) { operation.current = null; setBusy(null); } }
  };
  const runProbe = async () => {
    if (operation.current || !preview?.structural_valid || !preview.revision) return;
    const token = generation.current;
    operation.current = "probe"; setBusy("probe"); setVerification(null); setFailure(null); setFindings([]);
    try {
      const value = await call(transfer ? "transfer-check" : "setup-check", requestBody(targetPayload(), preview.revision)) as Verification;
      if (!alive.current || token !== generation.current) return;
      const expected = ["git", "forge_cli", "forge_auth", "container_runtime", "executor_cli", "aegis_files", "model_endpoint"];
      if (!value || !["failed", "partial", "verified"].includes(value.status) || value.draft_revision !== preview.revision ||
        value.revision !== preview.config_revision || typeof value.checked_at !== "string" ||
        !Number.isFinite(Date.parse(value.checked_at)) || !value.checks ||
        Object.keys(value.checks).length !== expected.length || expected.some(key => !(key in value.checks) ||
          typeof value.checks[key] !== "boolean" && !(key === "container_runtime" && value.checks[key] === null) &&
          // AEGIS files are checked at creation when the repository is cloned then.
          !(["model_endpoint", "aegis_files"].includes(key) && value.checks[key] === "not-checked")))
        throw new ApiError("unexpected_response");
      if (value.status === "verified" && Object.values(value.checks).some(result => result !== true))
        throw new ApiError("unexpected_response");
      setVerification(value);
    } catch (cause) { if (alive.current && token === generation.current) reject(cause); }
    finally { if (alive.current && token === generation.current) { operation.current = null; setBusy(null); } }
  };
  const confirm = async () => {
    if (operation.current || !reviewed?.preview.revision) return;
    operation.current = "create"; setBusy("create"); setFailure(null); setFindings([]);
    const token = generation.current;
    try {
      const value = await call(transfer ? "transfer-create" : "setup-create", requestBody(reviewed.draft, reviewed.preview.revision)) as Created;
      if (!alive.current || token !== generation.current) return;
      if (!value || !/^[0-9a-f]{32}$/.test(value.id) || value.name !== reviewed.draft.name ||
        value.display_name !== reviewed.draft.display_name || !value.paused || value.pickup_state !== "stopped")
        throw new ApiError("unexpected_response");
      dirty.current = false; setCreated(value); onCreated();
    } catch (cause) { if (alive.current && token === generation.current) { setReviewed(null); reject(cause); } }
    finally { if (alive.current && token === generation.current) { operation.current = null; setBusy(null); } }
  };
  const labels: Record<FieldName, string> = {
    execution_backend: c.runsIn, local_account: localCopy[locale].account,
    executor_command: localCopy[locale].argv,
    local_home: localCopy[locale].home, local_path: localCopy[locale].path, local_cgroup_root: localCopy[locale].cgroup,
    clone_url: c.url, name: c.id, display_name: c.display, description: t("description"), kind: t("forge"), repo: t("repository"),
    login: "Gitea tea login", repo_path: t("clonePath"), target_branch: t("targetBranch"),
    executor_cli: t("executor"), model: t("model"), runtime: t("runtime"), image: t("image"),
    auth_mode: t("authMode"), env_keys: c.env, reviewers: t("reviewers"), ready_label: c.ready, approval_label: c.approval,
    max_iterations: c.iterations, max_wall_clock_seconds: c.seconds, max_cost_usd: c.cost, max_files_touched: c.files,
  };
  const helpId = (key: FieldName) => ["clone_url", "kind", "target_branch", "repo", "repo_path"].includes(key) ? "url" :
    ["name", "display_name", "description"].includes(key) ? "identity" : key === "login" ? "login" :
    ["env_keys", "auth_mode"].includes(key) ? "credentials" : fields[2].includes(key) ? "environment" :
    numeric.includes(key as typeof numeric[number]) ? "limits" : "rules";
  const control = (key: FieldName) => {
    if (key === "login" && draft.kind !== "gitea" || key === "env_keys" && ["host-auth", "existing"].includes(draft.auth_mode)
        || key.startsWith("local_") && draft.execution_backend !== "local"
        || key === "executor_command" && draft.execution_backend !== "local"
        || ["runtime", "image"].includes(key) && draft.execution_backend === "local") return null;
    const options: Partial<Record<FieldName, string[]>> = { kind: [...(draft.kind ? [] : [""]), "gitlab", "github", "gitea"],
      // A cloned WSL-wrapped runtime stays selectable instead of silently showing docker.
      execution_backend: ["container", "local"], runtime: ["docker", "podman", ...(draft.runtime && !["docker", "podman"].includes(draft.runtime) ? [draft.runtime] : [])],
      executor_cli: ["opencode", "codex", "pi", "qwen"],
      auth_mode: draft.execution_backend === "local" ? ["existing", "api-key"] : ["api-key", ...(["opencode", "codex"].includes(draft.executor_cli) ? ["host-auth"] : [])] };
    const error = findings.some(item => fieldFor(item.field) === key);
    const common = { id: "enroll-" + key, value: draft[key],
      "aria-describedby": "enrollment-help-" + helpId(key) + (error ? " error-" + key : ""),
      "aria-invalid": error || undefined, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => change(key, event.target.value) };
    return <div className="enrollment-field" key={key}>
      <label htmlFor={common.id}>{labels[key]}{!["description", "login", "local_home", "local_path", "local_cgroup_root", "executor_command", "reviewers", "env_keys"].includes(key) && <span aria-hidden="true"> *</span>}</label>
      {options[key] ? <select {...common}>{options[key]?.map(value => <option value={value} key={value}>{value === "existing" ? localCopy[locale].existing : value === "" ? c.chooseForge
        : key === "execution_backend" ? (value === "local" ? c.installed : c.container) : value}</option>)}</select> :
        <input {...common} readOnly={!!transfer && numeric.includes(key as typeof numeric[number])} type={numeric.includes(key as typeof numeric[number]) ? "number" : "text"}
          step={key === "max_cost_usd" ? "any" : "1"} autoComplete="off"
          placeholder={(key === "display_name" ? c.exampleDisplay : key === "description" ? c.exampleDescription : examples[key]) ? t("examplePrefix") + " " +
            (key === "display_name" ? c.exampleDisplay : key === "description" ? c.exampleDescription : examples[key]) : undefined}
          maxLength={key === "display_name" ? 120 : key === "name" ? 64 : 1024}
          list={key === "image" && images?.available ? "enroll-image-options" : undefined} />}
      {key === "image" && images?.available && <datalist id="enroll-image-options">{images.images.map(name => <option value={name} key={name} />)}</datalist>}
      {key === "image" && images && (!images.available ? <p className="field-hint">{c.imagesUnavailable}</p>
        : draft.image.trim() && !images.images.includes(draft.image.trim()) && <p className="field-hint" role="status">{c.imageMissing}</p>)}
      {error && <p className="field-hint" id={"error-" + key}><strong>{c.invalid}</strong></p>}
    </div>;
  };
  const status = stale ? c.stale : !verification ? c.unverified : verification.status === "failed" ? c.failedCheck :
    verification.status === "partial" ? c.partial : c.verified;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (step >= 4 || step === 1 && !detected || !validateLocal([step])) return;
    move(step + 1);
  };
  if (created) return <section className="panel enrollment" role="status">
    <h2 tabIndex={-1} ref={heading}>{c.completion}</h2>
    <p><strong>{created.display_name}</strong> · {created.name}</p><p>{c.stopped}</p>
    <button className="primary" onClick={() => onOpen(created.id)}>{c.open}</button>
  </section>;
  return <section className="panel enrollment">
    <nav aria-label={c.stepsLabel}><ol className="enrollment-steps">{c.steps.map((label, index) =>
      <li key={index} aria-current={index + 1 === step ? "step" : undefined}>
        <span>{index + 1}. {label}</span>
      </li>)}</ol></nav>
    <div className="heading-with-help"><h2 tabIndex={-1} ref={heading}>{c.steps[step - 1]}</h2><HelpLink topic={CONTEXT_TOPICS.addProject} locale={locale} /></div>
    {(failure || findings.length > 0) && <div ref={summary} tabIndex={-1} role="alert" className="enrollment-errors">
      <h3>{c.errorTitle}</h3>{!!failure && <p>{describeError(locale, failure)} {c.failed}</p>}
      <ul>{findings.map((item, index) => <li key={index}>
        <button className="text-button" onClick={() => correct(item)}>{item.field === "references_confirmed" ? tc.confirm : fieldFor(item.field) ?
          labels[fieldFor(item.field)!] : c.steps[3]} — {c.correction}</button>
        <p>{item.code === "project_exists" ? c.idExists :
          item.code === "reserved_project_name" ? c.idReserved :
          item.code === "invalid_input" ? c.invalid : fieldFor(item.field) ?
            (helpId(fieldFor(item.field)!) === "url" ? c.urlHelp : c[helpId(fieldFor(item.field)!) as "identity" | "login" |
              "environment" | "credentials" | "rules" | "limits"]) : c.failed}</p>
        <span> · {item.code}</span>
      </li>)}</ul>
      {!findings.length && <button className="text-button" onClick={() => move(4)}>{c.validate}</button>}
      {transfer && <>{failure instanceof ApiError && failure.code === "portable_settings_changed" && <p>{tc.changed}</p>}
        <button type="button" className="text-button" onClick={onSourceReview}>{tc.back}</button></>}
    </div>}
    <form onSubmit={submit} noValidate>
      <fieldset disabled={busy === "create"} className="enrollment-fields">
        {step < 4 && <>
          {(step === 1 ? ["url", "identity", ...(draft.kind === "gitea" ? ["login"] : [])] : step === 2 ? ["environment", "credentials"] :
            ["rules", "limits"]).map(key => <p id={"enrollment-help-" + key} key={key}>{step === 2 && draft.execution_backend === "local" ? (key === "environment" ? localCopy[locale].notice : c.noSecrets) : key === "url" ? c.urlHelp : c[key as
              "identity" | "login" | "environment" | "credentials" | "rules" | "limits"]}</p>)}
          {step === 1 ? <>
            <div className="enrollment-field enrollment-url">
              <label htmlFor="enroll-clone_url">{c.url}<span aria-hidden="true"> *</span></label>
              <div className="inline-field">
                <input id="enroll-clone_url" value={draft.clone_url} autoComplete="off" maxLength={512}
                  placeholder={t("examplePrefix") + " " + examples.clone_url} aria-describedby="enrollment-help-url"
                  aria-invalid={findings.some(item => fieldFor(item.field) === "clone_url") || undefined}
                  onChange={event => change("clone_url", event.target.value)}
                  onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); void readRepository(); } }} />
                <button type="button" className={detected ? "ghost" : "primary"} onClick={() => void readRepository()} disabled={detecting} aria-busy={detecting}>{detecting ? c.reading : c.read}</button>
              </div>
            </div>
            {detected && <section className="enrollment-review detected-source" aria-label={c.detected}>
              <h3>{c.detected}</h3>
              <dl>
                <div><dt>{t("repository")}</dt><dd>{draft.repo}</dd></div>
                <div><dt>{c.id}</dt><dd>{draft.name}</dd></div>
              </dl>
            </section>}
            <p className="visually-hidden" role="status">{detected ? c.detected : ""}</p>
            {detected && <>{detected.kind === null && <p role="note">{c.forgeUnknown}</p>}
              <div className="enrollment-grid">{(["display_name", "description", "kind", "login", "repo_path", "target_branch"] as FieldName[]).map(control)}</div>
              <p className="field-hint" id="enrollment-clone-note">{draft.repo_path === detected.repo_path && detected.clone === "existing" ? c.cloneExisting : c.cloneEdited}</p></>}
          </> : <div className="enrollment-grid">{fields[step].map(control)}</div>}

          {transfer && step === 2 && <><p id="transfer-reference-help">{tc.references}</p><label><input id="transfer-references" aria-describedby="transfer-reference-help" type="checkbox" checked={referencesConfirmed}
            onChange={event => { dirty.current = true; generation.current++; setReferencesConfirmed(event.target.checked);
              setPreview(null); setVerification(null); setReviewed(null); setFindings([]); setFailure(null);
              operation.current = null; setBusy(null); }} /> {tc.confirm}</label></>}
        </>}
        {step === 4 && <>
          <p>{draft.execution_backend === "local" ? localCopy[locale].notice : c.effects}</p><p>{c.noSecrets}</p>
          <button type="button" className="primary" disabled={!!busy} onClick={() => void runPreview()}>{c.validate}</button>
          {preview?.structural_valid && <><p role="status">{c.valid}</p>
            <button type="button" className="ghost" disabled={!!busy} onClick={() => void runProbe()}>{verification ? c.recheck : c.check}</button>
          </>}
          {transfer && preview?.structural_valid && <Mapping preview={preview} locale={locale} />}
          <p role="status">{status}</p>
          {verification && <><p>{c.checked}: {verification.checked_at}</p><ul>{Object.entries(verification.checks).filter(([key]) => draft.execution_backend !== "local" || key !== "container_runtime").map(([key, result]) =>
            <li key={key}><strong>{key}</strong>: {result === true ? "✓" : result === false ? "✕" : "?"} {result === true ? c.checkPassed : result === false ? c.checkFailed : c.notChecked}
              {result !== true && <p>{key === "aegis_files" && result === "not-checked" ? c.aegisAtCreate : c.checkHelp[key as keyof typeof c.checkHelp]}</p>}
              {result !== true && result !== "not-checked" && <button type="button" className="text-button" onClick={() => move(["git", "aegis_files", "forge_cli", "forge_auth"].includes(key) ? 1 : 2)}>{c.correction}</button>}
            </li>)}</ul></>}
          <button type="button" className="primary" disabled={!!busy || !preview?.structural_valid} onClick={() => {
            if (!preview?.structural_valid || !preview.revision) return;
            setReviewed({ draft: structuredClone(targetPayload()), preview: structuredClone(preview) }); move(5);
          }}>{c.review}</button>
        </>}
        {step === 5 && reviewed && <>
          <p>{c.reviewHelp}</p><p>{c.status}: {status}</p>
          {transfer && <><p>{tc.exclusions}</p><p>{tc.confirm}</p><Mapping preview={reviewed.preview} locale={locale} /></>}
          {reviewed.draft.execution_backend === "local" && <section className="enrollment-review"><h3>{localCopy[locale].title}</h3><p>{localCopy[locale].notice}</p><p>{localCopy[locale].machine}: {String((reviewed.preview.review?.local_execution as Record<string, unknown>)?.machine ?? "—")} · {localCopy[locale].account}: {String((reviewed.preview.review?.local_execution as Record<string, unknown>)?.account ?? "—")}</p></section>}
          {fields.slice(1).map((group, index) => <section className="enrollment-review" key={index}>
            <h3>{c.steps[index]}</h3><button type="button" className="text-button" onClick={() => move(index + 1)}>{c.change} — {c.steps[index]}</button>
            <dl>{group.filter(key => (key !== "clone_url" || !!reviewed.draft.clone_url) && (reviewed.draft.execution_backend === "local" ? !["runtime", "image"].includes(key) : !key.startsWith("local_") && key !== "executor_command")).map(key => <div key={key}><dt>{labels[key]}</dt><dd>{(Array.isArray(reviewed.preview.review?.[key]) ?
              (reviewed.preview.review?.[key] as string[]).join(", ") : String(reviewed.preview.review?.[key] ?? "")) || "—"}</dd></div>)}
              {(index === 0 ? [["branch_template", c.branches]] : index === 1 ? [] :
                [["hold_label", c.hold], ["exclude_label", c.exclude]]).map(([key, label]) =>
                  <div key={key}><dt>{label}</dt><dd>{String(reviewed.preview.review?.[key] ?? "—")}</dd></div>)}
            </dl>
          </section>)}
          <section className="enrollment-review"><h3>{transfer ? tc.paths : c.paths}</h3><dl>{["config_path", "store_root", "worktree_root", "repo_path", ...(transfer ? ["metrics_db", "metrics_jsonl", "metrics_html"] : [])].map(key =>
            <div key={key}><dt>{{ config_path: c.configFile, store_root: c.jobState,
              worktree_root: c.worktrees, repo_path: t("clonePath"), metrics_db: "metrics.db", metrics_jsonl: "metrics JSONL", metrics_html: "metrics HTML" }[key]}</dt>
              <dd>{String(reviewed.preview.review?.[key] ?? "—")}</dd></div>)}</dl></section>
          <p className="enrollment-digest">{c.revision}: {reviewed.preview.revision}</p><p>{c.createEffect}</p>
          <button type="button" className="primary" onClick={() => void confirm()} disabled={!!busy}>{c.create}</button>
        </>}
      </fieldset>
      {busy && <p role="status">{c.busy} {c.checkingHelp}</p>}
      <div className="enrollment-actions">
        {(step > 1 || transfer) && <button type="button" className="ghost" disabled={busy === "create"} onClick={() => transfer && step === 1 ? onSourceReview?.() : move(step - 1)}>{c.back}</button>}
        {/* From a URL, the wizard cannot continue until the repository has been read. */}
        {/* Until the repository is read, Read repository is the primary action. */}
        {step < 4 && <button className={step === 1 && !detected ? "ghost" : "primary"} type="submit" disabled={step === 1 && !detected}>{c.continue}</button>}
        <button type="button" className="ghost" disabled={busy === "create"} onClick={() => { if (guard()) onCancel(); }}>{c.cancel}</button>
      </div>
    </form>
  </section>;
}

/** Exact source/installed-default mapping; long values stack in the existing responsive review. */
function Mapping({ preview, locale }: { preview: Preview; locale: Locale }) {
  const c = transferCopy[locale];
  return <section className="enrollment-review"><h3>{c.recognized}</h3><p>{c.defaults}</p>
    <p className="enrollment-digest">{c.revision}: {preview.source_revision}</p>
    {preview.mapping?.map(row => <div key={row.key}><h4>{row.key}</h4><dl>
      <div><dt>{c.sourceValue}</dt><dd>{JSON.stringify(row.source_value)}</dd></div>
      <div><dt>{c.serverValue}</dt><dd>{JSON.stringify(row.server_value)}</dd></div>
      <div><dt>{c.effect}</dt><dd>{c.copied}</dd></div>
    </dl></div>)}
  </section>;
}

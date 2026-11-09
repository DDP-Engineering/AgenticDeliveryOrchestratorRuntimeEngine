/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, describeError } from "./errors";
import { messages, type Locale } from "./i18n";
import { NewPasswordFields, readConfirmedPassword } from "./PasswordField";
import { userCopy, type UserCopy } from "./userCopy";

export type AccessProject = { id: string; name: string; display_name: string; archived: boolean; platform?: string; repo?: string };
export type Account = { id: number; username: string; role: "admin" | "developer"; project_ids: string[] };
export type UserTransport = (path: string, method: string, body: unknown) => Promise<unknown>;
type Intent = { username: string; password: string; role: "admin" | "developer"; project_ids: string[]; allow_no_projects: boolean };
const initial = (): Intent => ({ username: "", password: "", role: "developer", project_ids: [], allow_no_projects: false });
const validIds = (value: unknown): value is string[] => Array.isArray(value) && value.every(id => typeof id === "string" && /^[0-9a-f]{32}$/.test(id)) && new Set(value).size === value.length;
export const validAccount = (value: unknown): value is Account => !!value && typeof value === "object" &&
  "id" in value && Number.isSafeInteger(value.id) && Number(value.id) > 0 &&
  "username" in value && typeof value.username === "string" &&
  "role" in value && ["admin", "developer"].includes(String(value.role)) &&
  "project_ids" in value && validIds(value.project_ids);
const sameIds = (a: string[], b: string[]) => [...a].sort().join() === [...b].sort().join();
/** Choice text: the display name, plus the unique name when another project shows the same text. */
const choiceName = (project: AccessProject, projects: AccessProject[]) => {
  const shown = project.display_name || project.name;
  return projects.some(other => other.id !== project.id && (other.display_name || other.name) === shown) ? `${shown} · ${project.name}` : shown;
};
/** Forge and repository path, so a grant names the code it opens. */
const repository = (project: AccessProject) => [project.platform, project.repo].filter(Boolean).join(" · ");
/** Reviews and results keep the repository and the immutable identifier that defines each grant. */
const labels = (ids: string[], projects: AccessProject[]) => ids.map(id => {
  const project = projects.find(p => p.id === id);
  if (!project) return id;
  const where = repository(project);
  return `${choiceName(project, projects)}${where ? ` (${where})` : ""} · ${id}`;
});
const ChoiceText = ({ project, projects }: { project: AccessProject; projects: AccessProject[] }) =>
  <span>{choiceName(project, projects)}{repository(project) && <small className="access-repo">{repository(project)}</small>}</span>;

/** Transient credential draft; only the reviewed identity/role/IDs are rendered. */
export function UserCreation({ projects, ready, locale, send, onCreated, onBusyChange }: {
  projects: AccessProject[]; ready: boolean; locale: Locale; send: UserTransport;
  onCreated: () => void; onBusyChange: (busy: boolean) => void;
}) {
  const copy = userCopy[locale];
  const { username: usernameLabel, password: passwordLabel, role: roleLabel, requiredLegend } = messages[locale];
  const [draft, setDraft] = useState<Intent>(initial);
  const [step, setStep] = useState<"identity" | "access" | "review" | "result">("identity");
  const [reviewed, setReviewed] = useState<Omit<Intent, "password"> | null>(null);
  const [result, setResult] = useState<Account | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [mismatch, setMismatch] = useState(false);
  const active = useRef(true), sending = useRef(false), heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  useEffect(() => { heading.current?.focus(); }, [step]);
  const selectedValid = draft.project_ids.every(id => projects.some(p => p.id === id && !p.archived));
  const accessValid = ready && selectedValid && (draft.role === "admin" || draft.project_ids.length > 0 || draft.allow_no_projects);
  const correction = (next: "identity" | "access") => { setReviewed(null); setStep(next); setError(null); };
  const submit = async () => {
    if (sending.current || !reviewed || !ready || !active.current) return;
    sending.current = true; setBusy(true); onBusyChange(true); setError(null);
    const intent = reviewed;
    try {
      const value = await send("/users/with-access", "POST", { ...intent, password: draft.password });
      if (!active.current) return;
      if (!validAccount(value) || value.username !== intent.username || value.role !== intent.role || !sameIds(value.project_ids, intent.project_ids)) throw new ApiError("unexpected_response");
      setResult(value); setDraft(initial()); setReviewed(null); setStep("result"); onCreated();
    } catch (cause) { if (active.current) setError(cause); }
    finally { if (active.current) { sending.current = false; setBusy(false); onBusyChange(false); } }
  };
  const identity = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const password = readConfirmedPassword(event.currentTarget, "password");
    if (password === null) { setMismatch(true); return; }
    setDraft(previous => ({ ...previous, password }));
    setMismatch(false);
    setError(null);
    setStep("access");
  };
  return <div className="user-access">
    <p className="muted">1. {copy.identity} → 2. {copy.access} → 3. {copy.review}</p>
    <h3 ref={heading} tabIndex={-1}>{step === "result" ? copy.created : copy[step]}</h3>
    {error !== null && <div role="alert" className="banner error">{describeError(locale, error)}</div>}
    {step === "identity" && <form className="form-stack" onSubmit={identity}>
      <p className="form-legend"><span className="required-mark" aria-hidden="true">*</span> {requiredLegend}</p>
      <label><span>{usernameLabel}<span className="required-mark" aria-hidden="true">*</span></span><input aria-label={usernameLabel} autoComplete="off" required maxLength={64} value={draft.username} onChange={e => setDraft({ ...draft, username: e.target.value })} /></label>
      <NewPasswordFields locale={locale} name="password" label={passwordLabel} hint={copy.passwordHelp}
        initialPassword={draft.password} maxLength={1024} mismatch={mismatch} onEdit={() => setMismatch(false)} />
      <button className="primary" type="submit">{copy.next}</button>
    </form>}
    {step === "access" && <div className="form-stack">
      <label>{roleLabel}<select value={draft.role} onChange={e => setDraft({ ...draft, role: e.target.value as Intent["role"], project_ids: [], allow_no_projects: false })}><option value="developer">Dev</option><option value="admin">Admin</option></select></label>
      <p>{draft.role === "admin" ? copy.adminHelp : copy.devHelp}</p>
      {draft.role === "admin" ? <strong>{copy.global}</strong> : <fieldset><legend>{copy.projects}</legend>
        {!ready && <p role="status">{copy.loading}</p>}
        {ready && <div className="access-choices">{projects.filter(p => !p.archived).map(p => <label key={p.id} className="access-choice"><input type="checkbox" checked={draft.project_ids.includes(p.id)} onChange={e => setDraft({ ...draft, allow_no_projects: false, project_ids: e.target.checked ? [...draft.project_ids, p.id] : draft.project_ids.filter(id => id !== p.id) })} /><ChoiceText project={p} projects={projects} /></label>)}</div>}
        <label className="access-choice"><input type="checkbox" checked={draft.allow_no_projects} onChange={e => setDraft({ ...draft, project_ids: [], allow_no_projects: e.target.checked })} /><span>{copy.emptyChoice}</span></label>
      </fieldset>}
      <div className="actions"><button className="ghost" onClick={() => correction("identity")}>{copy.correctIdentity}</button><button className="primary" disabled={!accessValid} onClick={() => { setReviewed({ username: draft.username, role: draft.role, project_ids: [...draft.project_ids], allow_no_projects: draft.allow_no_projects }); setStep("review"); }}>{copy.review}</button></div>
    </div>}
    {step === "review" && reviewed && <div className="form-stack">
      <dl><dt>{usernameLabel}</dt><dd>{reviewed.username}</dd><dt>{roleLabel}</dt><dd>{reviewed.role === "admin" ? "Admin" : "Dev"}</dd><dt>{copy.projects}</dt><dd>{reviewed.role === "admin" ? copy.global : reviewed.project_ids.length ? <ul>{reviewed.project_ids.map((id, index) => <li key={id}>{labels(reviewed.project_ids, projects)[index]}</li>)}</ul> : copy.empty}</dd></dl>
      <p>{reviewed.role === "admin" ? copy.adminHelp : copy.devHelp}</p>
      <div className="actions"><button className="ghost" disabled={busy} onClick={() => correction("identity")}>{copy.correctIdentity}</button><button className="ghost" disabled={busy} onClick={() => correction("access")}>{copy.correctAccess}</button><button className="primary" disabled={busy || !ready} onClick={() => void submit()}>{copy.submit}</button></div>
      {busy && <p role="status">{copy.creating}</p>}
    </div>}
    {step === "result" && result && <><p role="status">{copy.created}: {result.username} · {result.role === "admin" ? copy.global : labels(result.project_ids, projects).join(", ") || copy.empty}</p><button className="ghost" onClick={() => { setResult(null); setStep("identity"); }}>{copy.another}</button></>}
  </div>;
}

/** Shared visible confirmation; correction sends no mutation. */
export function AccessReview({ before, after, subject, copy, busy, apply, correct }: {
  before: string; after: string; subject: string; copy: UserCopy; busy: boolean;
  apply: () => void; correct: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return <section className="panel wide-panel user-access" aria-label={copy.reviewAccess}>
    <h3 ref={heading} tabIndex={-1}>{copy.reviewAccess}: {subject}</h3>
    <dl><dt>{copy.before}</dt><dd>{before}</dd><dt>{copy.after}</dt><dd>{after}</dd></dl>
    <button className="ghost" disabled={busy} onClick={correct}>{copy.correctAccess}</button>
    <button className="primary" disabled={busy} onClick={apply}>{copy.apply}</button>
    {busy && <p role="status">{copy.pending}</p>}
  </section>;
}

/** Whole-account compatibility editor, mapping current ID selection to names. */
export function AccountAccessEditor({ account, projects, ready, locale, saveLabel, send, onApplied, onError }: {
  account: Account; projects: AccessProject[]; ready: boolean; locale: Locale; saveLabel: string;
  send: UserTransport; onApplied: (result: string) => void; onError: (cause: unknown) => void;
}) {
  const copy = userCopy[locale];
  const [ids, setIds] = useState(account.project_ids);
  const [review, setReview] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false), active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const apply = async () => {
    if (lock.current || !review || !ready) return;
    const selected = review.map(id => projects.find(p => p.id === id));
    if (selected.some(p => !p)) { onError(new ApiError("project_changed")); return; }
    const names = selected.map(p => p!.name);
    lock.current = true; setBusy(true);
    try {
      const result = await send(`/users/${account.id}/projects`, "PUT", { projects: names });
      if (!active.current) return;
      if (!result || typeof result !== "object" || !("projects" in result) || !Array.isArray(result.projects) || result.projects.some(name => typeof name !== "string") || new Set(result.projects).size !== result.projects.length || !sameIds(result.projects, names)) throw new ApiError("unexpected_response");
      setReview(null); onApplied(`${copy.applied}: ${account.username} · ${labels(review, projects).join(", ") || copy.none}`);
    } catch (cause) { if (active.current) onError(cause); }
    finally { if (active.current) { lock.current = false; setBusy(false); } }
  };
  return <div className="form-stack user-access">
    <div className="access-choices">{projects.map(p => <label key={p.id} className="access-choice"><input type="checkbox" disabled={!ready || busy || review !== null} checked={ids.includes(p.id)} onChange={e => setIds(e.target.checked ? [...ids, p.id] : ids.filter(id => id !== p.id))} /><ChoiceText project={p} projects={projects} /></label>)}</div>
    <button className="ghost" disabled={!ready || busy || review !== null} onClick={() => setReview([...ids])}>{saveLabel}</button>
    {review && <AccessReview subject={account.username} before={labels(account.project_ids, projects).join(", ") || copy.none} after={labels(review, projects).join(", ") || copy.none} copy={copy} busy={busy} apply={() => void apply()} correct={() => setReview(null)} />}
  </div>;
}

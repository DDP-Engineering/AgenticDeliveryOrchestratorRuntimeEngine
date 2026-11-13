/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { ApiError, describeError } from "./errors";
import { messages, type Locale } from "./i18n";
import { NewPasswordFields, readConfirmedPassword } from "./PasswordField";
import { UserCreation, type AccessProject, type Account, type UserTransport } from "./UserCreation";

export type AccountAction = { kind: "add" } | { kind: "reset"; account: Account & { disabled: boolean } };

export function AccountActionDialog({ action, projects, ready, locale, send, onCreated, onReset, onClose }: {
  action: AccountAction;
  projects: AccessProject[];
  ready: boolean;
  locale: Locale;
  send: UserTransport;
  onCreated: () => void;
  onReset: () => void;
  onClose: () => void;
}) {
  const text = messages[locale];
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [busy, setBusy] = useState(false);
  const title = action.kind === "add" ? text.createUser : text.resetPasswordFor.replace("{user}", () => action.account.username);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);

  const close = () => {
    dialog.current?.close();
    onClose();
  };

  return <dialog ref={dialog} className="account-action-dialog" aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); if (!busy) close(); }}>
    <div className="panel-heading">
      <h2 id={titleId}>{title}</h2>
      <button type="button" className="ghost" disabled={busy} onClick={close}>{text.close}</button>
    </div>
    {action.kind === "add"
      ? <UserCreation projects={projects} ready={ready} locale={locale} send={send} onCreated={onCreated} onBusyChange={setBusy} />
      : <PasswordResetForm accountId={action.account.id} ready={ready} locale={locale} send={send} busy={busy} onBusyChange={setBusy}
          onReset={() => { close(); onReset(); }} />}
  </dialog>;
}

function PasswordResetForm({ accountId, ready, locale, send, busy, onBusyChange, onReset }: {
  accountId: number;
  ready: boolean;
  locale: Locale;
  send: UserTransport;
  busy: boolean;
  onBusyChange: (busy: boolean) => void;
  onReset: () => void;
}) {
  const text = messages[locale];
  const [mismatch, setMismatch] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const sending = useRef(false);
  const active = useRef(false);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (sending.current || !ready) return;
    setError(null);
    const replacement = readConfirmedPassword(event.currentTarget, "replacement");
    if (replacement === null) { setMismatch(true); return; }
    sending.current = true;
    onBusyChange(true);
    try {
      const result = await send(`/users/${accountId}/reset-password`, "POST", { replacement });
      if (!result || typeof result !== "object" || !("ok" in result) || result.ok !== true) {
        throw new ApiError("unexpected_response");
      }
      if (active.current) onReset();
    } catch (cause) {
      if (active.current) setError(cause);
    } finally {
      if (active.current) {
        sending.current = false;
        onBusyChange(false);
      }
    }
  };

  return <form className="form-stack" onSubmit={submit} aria-busy={busy}>
    <p className="muted">{text.resetPasswordEffect}</p>
    <p className="form-legend"><span className="required-mark" aria-hidden="true">*</span> {text.requiredLegend}</p>
    {error !== null && <p className="alert" role="alert">{describeError(locale, error)}</p>}
    <fieldset className="form-stack account-password-fields" disabled={busy}>
      <NewPasswordFields locale={locale} name="replacement" label={text.newPassword} hint={text.passwordRule}
        mismatch={mismatch} onEdit={() => { setMismatch(false); setError(null); }} />
      <button type="submit" className="primary" disabled={!ready}>{text.save}</button>
    </fieldset>
  </form>;
}

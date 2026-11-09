/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useId, useState, type ChangeEventHandler } from "react";
import { messages, type Locale } from "./i18n";

/** Required password input with local, independently toggled visibility. */
export function PasswordField({
  name, label, show, hide, autoComplete, minLength, maxLength, hint, invalid, autoFocus, defaultValue, onChange,
}: {
  name: string;
  label: string;
  show: string;
  hide: string;
  autoComplete: "current-password" | "new-password";
  minLength?: number;
  maxLength?: number;
  hint?: string;
  invalid?: boolean;
  autoFocus?: boolean;
  defaultValue?: string;
  onChange?: ChangeEventHandler<HTMLInputElement>;
}) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const action = visible ? hide : show;

  return <div className="password-field">
    <label htmlFor={id}><span>{label}<span className="required-mark" aria-hidden="true">*</span></span></label>
    <div className="password-input">
      <input id={id} name={name} aria-label={label} type={visible ? "text" : "password"}
        autoComplete={autoComplete} autoFocus={autoFocus} required minLength={minLength} maxLength={maxLength}
        spellCheck={false} autoCorrect="off" autoCapitalize="none"
        defaultValue={defaultValue} onChange={onChange} aria-invalid={invalid || undefined}
        aria-describedby={hint ? id + "-help" : undefined} />
      <button type="button" className="ghost password-visibility" aria-label={action} title={action}
        aria-pressed={visible} onClick={() => setVisible(shown => !shown)}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
          strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
          <circle cx="12" cy="12" r="3" />
          {visible && <path d="M4 4l16 16" />}
        </svg>
      </button>
    </div>
    {hint && <small id={id + "-help"} className="field-hint">{hint}</small>}
  </div>;
}

/** Read only the original password after checking both fields in the current form. */
export function readConfirmedPassword(form: HTMLFormElement, name: string): string | null {
  const password = form.elements.namedItem(name);
  const confirmation = form.elements.namedItem("confirmation");
  if (password instanceof HTMLInputElement && confirmation instanceof HTMLInputElement &&
    password.value !== "" && password.value === confirmation.value) {
    return password.value;
  }
  if (confirmation instanceof HTMLInputElement) confirmation.focus();
  return null;
}

export function NewPasswordFields({ locale, name, label, hint, initialPassword, maxLength, mismatch, onEdit }: {
  locale: Locale;
  name: string;
  label: string;
  hint: string;
  initialPassword?: string;
  maxLength?: number;
  mismatch: boolean;
  onEdit: () => void;
}) {
  const text = messages[locale];
  return <>
    <PasswordField name={name} label={label} show={text.showNewPassword} hide={text.hideNewPassword}
      autoComplete="new-password" minLength={8} maxLength={maxLength} defaultValue={initialPassword}
      hint={hint} onChange={onEdit} />
    <PasswordField name="confirmation" label={text.repeatNewPassword} show={text.showRepeatPassword}
      hide={text.hideRepeatPassword} autoComplete="new-password" maxLength={maxLength}
      invalid={mismatch} onChange={onEdit} />
    {mismatch && <p className="alert" role="alert">{text.passwordMismatch}</p>}
  </>;
}

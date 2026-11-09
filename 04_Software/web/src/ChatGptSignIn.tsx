/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import type { Locale } from "./i18n";
import { describeError } from "./errors";
import { chatgptCopy, readChatGptStart, readChatGptView, type ChatGptView } from "./chatgptCopy";
import { startVisiblePolling } from "./polling";

/**
 * The server's ChatGPT sign-in: status, Pi's OpenAI sign-in link, the pasted
 * redirect address, Cancel and Disconnect. The link and the pasted address live
 * only in component memory; the address is cleared after every attempt.
 */
export function ChatGptSignIn({ locale, read, start, complete, cancel, disconnect, setPollBlocked }: {
  locale: Locale;
  read: () => Promise<unknown>;
  start: () => Promise<unknown>;
  complete: (redirectUrl: string) => Promise<unknown>;
  cancel: () => Promise<unknown>;
  disconnect: () => Promise<unknown>;
  setPollBlocked: (blocked: boolean) => void;
}) {
  const c = chatgptCopy[locale];
  const [view, setView] = useState<ChatGptView | null>(null);
  const [link, setLink] = useState("");
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const waiting = !!link && !!view?.pending;
  useLayoutEffect(() => { setPollBlocked(busy || waiting); }, [busy, waiting, setPollBlocked]);
  useLayoutEffect(() => () => setPollBlocked(false), [setPollBlocked]);
  const active = useRef(true);
  const acting = useRef(false);
  const readStatus = useRef(read);
  readStatus.current = read;
  const statusRead = useRef<Promise<ChatGptView> | null>(null);
  const latest = useRef<ChatGptView | null>(null);
  // Every status read joins the same tracked request. Mutations wait for it so
  // an automatic callback cannot be followed by an obsolete manual completion.
  const loadStatus = () => {
    if (statusRead.current) return statusRead.current;
    const request = readStatus.current().then(raw => {
      const next = readChatGptView(raw);
      latest.current = next;
      return next;
    }).finally(() => { if (statusRead.current === request) statusRead.current = null; });
    statusRead.current = request;
    return request;
  };

  useEffect(() => {
    active.current = true;
    void loadStatus().then(next => { if (active.current) setView(next); })
      .catch(() => { if (active.current) setError(c.unreadable); });
    return () => { active.current = false; };
  }, []);

  useEffect(() => {
    if (!view?.pending) return;
    let current = true, reading = false;
    const refresh = async () => {
      if (reading || acting.current) return;
      reading = true;
      try {
        const next = await loadStatus();
        if (!current) return;
        setView(next);
        if (!next.pending) {
          setLink(""); setAddress("");
          if (next.status === "signed-in") { setNotice(c.signedIn); setError(""); }
        }
      } catch (failure) { if (current) setError(describeError(locale, failure)); }
      finally { reading = false; }
    };
    const halt = startVisiblePolling(() => { void refresh(); }, 1000);
    const expiry = window.setTimeout(() => {
      halt(); setLink(""); setAddress("");
      setView(previous => previous ? {...previous, pending: false} : previous);
    }, 900_000);
    return () => { current = false; halt(); window.clearTimeout(expiry); };
  }, [view?.pending, locale]);

  const act = async (work: () => Promise<unknown>, after: (raw: unknown) => void, completing = false) => {
    if (acting.current) return;
    acting.current = true;
    setPollBlocked(true);
    setBusy(true); setError(""); setNotice("");
    try {
      // A failed status read does not replace the mutation's own authority.
      await statusRead.current?.catch(() => undefined);
      const observed = latest.current;
      const raw = completing && observed?.status === "signed-in" && !observed.pending
        ? observed : await work();
      if (active.current) after(raw);
    }
    catch (failure) { if (active.current) setError(describeError(locale, failure)); }
    finally {
      // Keep mutations serialized through their authoritative status refresh.
      try {
        const next = await loadStatus();
        if (active.current) { setView(next); if (!next.pending) setLink(""); }
      } catch { /* Preserve the mutation's own result if this refresh fails. */ }
      acting.current = false;
      if (active.current) setBusy(false);
    }
  };
  const begin = () => act(start, raw => { setLink(readChatGptStart(raw).authorize_url); setAddress(""); });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const pasted = address.trim();
    setAddress("");
    void act(() => complete(pasted), raw => { setView(readChatGptView(raw)); setLink(""); setNotice(c.signedIn); }, true);
  };
  const stop = () => act(cancel, raw => { setView(readChatGptView(raw)); setLink(""); });
  const remove = () => act(disconnect, raw => { setView(readChatGptView(raw)); setLink(""); setNotice(c.disconnected); });
  return <section className="executor-credentials-embedded" id="chatgpt-sign-in">
    <h3>{c.title}</h3>
    <p className="muted">{c.help}</p>
    {view && <p>{c.status}: <strong data-chatgpt-status={view.status}>{c[view.status]}</strong></p>}
    {view?.status === "sign-in-again" && <p role="note" className="alert">{c.againHelp}</p>}
    {!waiting && <div className="button-row">
      <button className="primary" type="button" disabled={busy || !view} onClick={() => void begin()}>
        {view?.status === "not-signed-in" ? c.start : c.restart}</button>
      <button className="ghost" type="button" disabled={busy || !view || view.status === "not-signed-in"}
        onClick={() => void remove()}>{c.disconnect}</button>
    </div>}
    {waiting && <form className="form-stack" onSubmit={submit}><fieldset disabled={busy}>
      <ol>
        <li>{c.step1} <a href={link} target="_blank" rel="noopener noreferrer">{c.link}</a></li>
        <li>{c.step2}</li>
      </ol>
      <p className="field-hint">{c.expires}</p>
      <label>{c.field}<input aria-label={c.field} type="text" value={address} autoComplete="off" spellCheck={false}
        maxLength={8192} placeholder="http://127.0.0.1:1455/auth/callback?…" onChange={event => setAddress(event.target.value)} required /></label>
      <div className="button-row">
        <button className="primary" disabled={!address.trim()}>{c.complete}</button>
        <button className="ghost" type="button" onClick={() => void stop()}>{c.cancel}</button>
      </div>
    </fieldset></form>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert" className="alert">{error}</p>}
  </section>;
}

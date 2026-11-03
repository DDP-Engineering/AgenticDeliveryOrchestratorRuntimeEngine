/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { Locale } from "./i18n";
import { describeError } from "./errors";
import { chatgptCopy, readChatGptStart, readChatGptView, type ChatGptView } from "./chatgptCopy";

/**
 * The server's ChatGPT sign-in: status, Pi's OpenAI sign-in link, the pasted
 * redirect address, Cancel and Disconnect. The link and the pasted address live
 * only in component memory; the address is cleared after every attempt.
 */
export function ChatGptSignIn({ locale, read, start, complete, cancel, disconnect }: {
  locale: Locale;
  read: () => Promise<unknown>;
  start: () => Promise<unknown>;
  complete: (redirectUrl: string) => Promise<unknown>;
  cancel: () => Promise<unknown>;
  disconnect: () => Promise<unknown>;
}) {
  const c = chatgptCopy[locale];
  const [view, setView] = useState<ChatGptView | null>(null);
  const [link, setLink] = useState("");
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const active = useRef(true);

  useEffect(() => {
    active.current = true;
    void read().then(raw => { if (active.current) setView(readChatGptView(raw)); })
      .catch(() => { if (active.current) setError(c.unreadable); });
    return () => { active.current = false; };
  }, []);

  const act = async (work: () => Promise<unknown>, after: (raw: unknown) => void) => {
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try { const raw = await work(); if (active.current) after(raw); }
    catch (failure) { if (active.current) setError(describeError(locale, failure)); }
    finally {
      if (active.current) setBusy(false);
      // A refused attempt may have ended the sign-in on the server.
      void read().then(raw => { if (active.current) { const next = readChatGptView(raw); setView(next); if (!next.pending) setLink(""); } })
        .catch(() => undefined);
    }
  };
  const begin = () => act(start, raw => { setLink(readChatGptStart(raw).authorize_url); setAddress(""); });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const pasted = address.trim();
    setAddress("");
    void act(() => complete(pasted), raw => { setView(readChatGptView(raw)); setLink(""); setNotice(c.signedIn); });
  };
  const stop = () => act(cancel, raw => { setView(readChatGptView(raw)); setLink(""); });
  const remove = () => act(disconnect, raw => { setView(readChatGptView(raw)); setLink(""); setNotice(c.disconnected); });
  const waiting = !!link && !!view?.pending;

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

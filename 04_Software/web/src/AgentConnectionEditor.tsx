/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useId, useState } from "react";
import type { Locale } from "./i18n";
import {
  CHATGPT, CUSTOM, ENDPOINT_APIS, connectionCopy, credentialNote, providerModels, providerThinking, thinkingCopy, readProviderCatalog,
  type Connection, type ProviderCatalog,
} from "./agentConnection";

/** Provider, model and endpoint fields edited together; the draft is the JSON wire value. */
export function AgentConnectionEditor({ value, locale, disabled, onChange }: {
  value: string; locale: Locale; disabled: boolean; onChange: (value: string) => void;
}) {
  const copy = connectionCopy[locale];
  const id = useId();
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let active = true;
    void readProviderCatalog().then(result => { if (active) { setCatalog(result); setLoaded(true); } });
    return () => { active = false; };
  }, []);
  let draft: Connection = { provider: "", model: "", thinking: "", base_url: "", api: "" };
  try { draft = { ...draft, ...JSON.parse(value) }; } catch { /* An unreadable draft starts empty. */ }
  const update = (change: Partial<Connection>) => {
    const next = { ...draft, ...change };
    if (change.provider !== undefined || change.model !== undefined) next.thinking = "";
    if (next.provider !== CUSTOM) { next.base_url = ""; next.api = ""; }
    else if (!next.api) next.api = ENDPOINT_APIS[0];
    onChange(JSON.stringify(next));
  };
  const providers = catalog?.providers ?? [];
  const models = providerModels(draft.provider, catalog);
  const known = [CUSTOM, CHATGPT, ...providers.map(item => item.id)];
  const note = credentialNote(draft.provider, catalog, locale);
  return <div className="connection-editor form-stack">
    <label>{copy.provider}
      <select aria-label={copy.provider} aria-describedby={`${id}-provider`} disabled={disabled} value={draft.provider}
        onChange={event => update({ provider: event.target.value })}>
        {!known.includes(draft.provider) && <option value={draft.provider} disabled>{draft.provider || "—"}</option>}
        <option value={CUSTOM}>{copy.custom}</option>
        <option value={CHATGPT}>{copy.chatgpt}</option>
        <optgroup label={copy.apiKeys}>{providers.map(item => <option key={item.id} value={item.id}>{item.name} ({item.id})</option>)}</optgroup>
      </select>
    </label>
    <p className="field-hint" id={`${id}-provider`}>{copy.providerHelp}</p>
    <label>{copy.model}
      <input aria-label={copy.model} aria-describedby={`${id}-model`} disabled={disabled} value={draft.model} maxLength={200}
        autoComplete="off" list={models.length ? `${id}-models` : undefined} onChange={event => update({ model: event.target.value.trim() })} />
    </label>
    {models.length > 0 && <datalist id={`${id}-models`}>{models.map(model => <option key={model} value={model} />)}</datalist>}
    <p className="field-hint" id={`${id}-model`}>{loaded && !catalog ? copy.catalogUnavailable : copy.modelHelp}</p>
    <label>{thinkingCopy[locale].label}
      <select disabled={disabled} value={draft.thinking} onChange={event => update({ thinking: event.target.value })}>
        <option value="">{thinkingCopy[locale].default}</option>
        {providerThinking(draft.provider, draft.model, catalog).map(level => <option key={level} value={level}>{level}</option>)}
      </select>
    </label>
    {draft.provider === CUSTOM && <>
      <label>{copy.baseUrl}
        <input aria-label={copy.baseUrl} aria-describedby={`${id}-url`} disabled={disabled} value={draft.base_url} maxLength={512}
          autoComplete="off" placeholder="http://192.168.1.20:1234/v1" onChange={event => update({ base_url: event.target.value.trim() })} />
      </label>
      <p className="field-hint" id={`${id}-url`}>{copy.baseUrlHelp}</p>
      <label>{copy.api}
        <select aria-label={copy.api} disabled={disabled} value={draft.api || ENDPOINT_APIS[0]} onChange={event => update({ api: event.target.value })}>
          {ENDPOINT_APIS.map(api => <option key={api} value={api}>{api}</option>)}
        </select>
      </label>
      <p className="field-hint">{copy.apiHelp}</p>
    </>}
    {note && <p role="note" className="muted">{note}</p>}
  </div>;
}

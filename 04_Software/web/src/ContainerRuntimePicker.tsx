/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";

const copy = {
  en: { manual: "Manual runtime command", loading: "Detecting container runtimes…",
        empty: "No container runtimes detected.", failed: "Could not detect container runtimes." },
  fr: { manual: "Commande de conteneur manuelle", loading: "Détection des moteurs de conteneurs…",
        empty: "Aucun moteur de conteneurs détecté.", failed: "Impossible de détecter les moteurs de conteneurs." },
  de: { manual: "Manueller Container-Befehl", loading: "Container-Laufzeiten werden gesucht…",
        empty: "Keine Container-Laufzeiten erkannt.", failed: "Container-Laufzeiten konnten nicht erkannt werden." },
  ro: { manual: "Comandă manuală pentru container", loading: "Se detectează runtime-urile de containere…",
        empty: "Nu s-a detectat niciun runtime de containere.", failed: "Runtime-urile de containere nu au putut fi detectate." },
};

type Props = {
  value: string;
  label: string;
  descriptionId: string;
  locale: Locale;
  disabled: boolean;
  onChange: (value: string) => void;
  id?: string;
  invalid?: boolean;
  autoSelect?: boolean;
};

/** Show server suggestions without overwriting the current draft. */
export function ContainerRuntimePicker({ value, label, descriptionId, locale, disabled, onChange, id, invalid, autoSelect = false }: Props) {
  const [commands, setCommands] = useState<string[] | null>();
  const [manual, setManual] = useState(false);
  const edited = useRef(false);
  const text = copy[locale];

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch("/api/v1/executor-runtimes", {
          credentials: "same-origin", cache: "no-store", signal: controller.signal,
        });
        const body = response.ok ? await response.json() : null;
        const list: unknown = body?.commands;
        if (!Array.isArray(list) || list.length > 18
            || !list.every(item => typeof item === "string" && item.length > 0 && item.length <= 160)) {
          throw new Error("Invalid runtime inventory");
        }
        if (!controller.signal.aborted) {
          const available = [...new Set<string>(list)];
          setCommands(available);
          if (autoSelect && !edited.current && value === "docker" && !available.includes(value) && available.length)
            onChange(available[0]);
        }
      } catch {
        if (!controller.signal.aborted) setCommands(null);
      }
    })();
    return () => controller.abort();
  }, []);

  const selection = !manual && commands?.includes(value) ? value : "";
  const status = commands === undefined ? text.loading : commands === null ? text.failed
    : commands.length === 0 ? text.empty : "";
  return <>
    <select id={id} aria-label={label} aria-describedby={descriptionId} aria-invalid={invalid || undefined} disabled={disabled}
      value={selection} onChange={event => {
        const command = event.target.value;
        edited.current = true;
        setManual(!command);
        if (command) onChange(command);
      }}>
      {commands?.map(command => <option key={command} value={command}>{command}</option>)}
      <option value="">{text.manual}</option>
    </select>
    {!selection && <input type="text" aria-label={text.manual} aria-describedby={descriptionId}
      disabled={disabled} value={value} onChange={event => {
        setManual(true);
        edited.current = true;
        onChange(event.target.value);
      }} />}
    {status && <p className="field-hint" role="status">{status}</p>}
  </>;
}

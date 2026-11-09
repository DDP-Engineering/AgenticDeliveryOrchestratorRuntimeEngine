/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useState } from "react";
import { ApiError, describeError } from "./errors";
import type { Locale } from "./i18n";

/** What creating the project's labels did in the repository. */
export type LabelReport = { created: string[]; existing: string[]; failed: Array<{ name: string; reason: string }> };

const names = (value: unknown) => Array.isArray(value) && value.length <= 200 && value.every(item => typeof item === "string");

/** A well-formed label report from the server. */
export function validLabelReport(value: unknown): value is LabelReport {
  const item = value as Partial<LabelReport> | null;
  return !!item && names(item.created) && names(item.existing) && Array.isArray(item.failed) && item.failed.length <= 200
    && item.failed.every(entry => !!entry && typeof entry.name === "string" && typeof entry.reason === "string");
}

export const forgeLabelsCopy: Record<Locale, {
  title: string; help: string; button: string; working: string; created: string; existing: string; failed: string;
  none: string; option: string; result: string;
}> = {
  en: {
    title: "Repository labels", help: "Create in the repository the ADORE labels this project uses. Labels that already exist are kept unchanged.",
    button: "Create missing labels", working: "Creating labels…", created: "Created", existing: "Already in the repository", failed: "Not created",
    none: "none", option: "Create the ADORE labels in the repository (missing ones only)", result: "Labels in the repository",
  },
  fr: {
    title: "Étiquettes du dépôt", help: "Crée dans le dépôt les étiquettes ADORE utilisées par ce projet. Les étiquettes existantes restent inchangées.",
    button: "Créer les étiquettes manquantes", working: "Création des étiquettes…", created: "Créées", existing: "Déjà dans le dépôt", failed: "Non créées",
    none: "aucune", option: "Créer les étiquettes ADORE dans le dépôt (seulement les manquantes)", result: "Étiquettes du dépôt",
  },
  de: {
    title: "Repository-Labels", help: "Legt im Repository die ADORE-Labels dieses Projekts an. Vorhandene Labels bleiben unverändert.",
    button: "Fehlende Labels anlegen", working: "Labels werden angelegt…", created: "Angelegt", existing: "Bereits im Repository", failed: "Nicht angelegt",
    none: "keine", option: "ADORE-Labels im Repository anlegen (nur fehlende)", result: "Labels im Repository",
  },
  ro: {
    title: "Etichetele repository-ului", help: "Creează în repository etichetele ADORE folosite de acest proiect. Etichetele existente rămân neschimbate.",
    button: "Creează etichetele lipsă", working: "Se creează etichetele…", created: "Create", existing: "Deja în repository", failed: "Necreate",
    none: "niciuna", option: "Creează etichetele ADORE în repository (doar cele lipsă)", result: "Etichetele din repository",
  },
};

/** The created / existing / not created lists of a label report. */
export function LabelReportView({ report, locale }: { report: LabelReport; locale: Locale }) {
  const c = forgeLabelsCopy[locale];
  const list = (items: string[]) => items.length ? items.map(name => <span className="ticket-label" key={name}>{name}</span>) : <span className="muted">{c.none}</span>;
  return <dl className="label-report">
    <div><dt>{c.created} ({report.created.length})</dt><dd>{list(report.created)}</dd></div>
    <div><dt>{c.existing} ({report.existing.length})</dt><dd>{list(report.existing)}</dd></div>
    {report.failed.length > 0 && <div><dt>{c.failed} ({report.failed.length})</dt><dd><ul>{report.failed.map(item =>
      <li key={item.name}><span className="ticket-label">{item.name}</span> — {item.reason}</li>)}</ul></dd></div>}
  </dl>;
}

/** Settings → Repository: create the missing labels on demand and show the report. */
export function ForgeLabelsAction({ locale, run, disabled = false }: {
  locale: Locale; run: () => Promise<unknown>; disabled?: boolean;
}) {
  const c = forgeLabelsCopy[locale];
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<LabelReport | null>(null);
  const [error, setError] = useState<unknown>(null);
  const create = async () => {
    setBusy(true); setError(null); setReport(null);
    try {
      const value = await run();
      if (!validLabelReport(value)) throw new ApiError("unexpected_response");
      setReport(value);
    } catch (cause) { setError(cause); }
    finally { setBusy(false); }
  };
  return <section className="forge-labels" aria-labelledby="forge-labels-title">
    <h3 id="forge-labels-title">{c.title}</h3>
    <p className="muted">{c.help}</p>
    <button type="button" className="ghost" disabled={disabled || busy} onClick={() => void create()}>{busy ? c.working : c.button}</button>
    {error !== null && <p className="alert" role="alert">{describeError(locale, error)}</p>}
    {/* The live region stays on the page so screen readers announce the report when it arrives. */}
    <div role="status" className="label-report-status">{report && <LabelReportView report={report} locale={locale} />}</div>
  </section>;
}

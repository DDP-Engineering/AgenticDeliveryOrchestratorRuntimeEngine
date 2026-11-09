/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";
const en = {
  allTime: "All time", started: "Started jobs", completed: "Completed jobs", failed: "Failed jobs",
  total: "Known total tokens", unavailable: "Not available", zero: "Measured zero", partial: "Partial · known subtotal", measured: "Known measurement",
  jobs: "Job consumption", events: "Usage observations", 
  reported: "Reported cost", estimated: "Estimated cost", 
  table: "Trend data", empty: "No dated events in this scope.",
};
type Copy = typeof en;
const fr: Copy = {
  allTime: "Toute la période", started: "Jobs démarrés", completed: "Jobs terminés", failed: "Jobs échoués",
  total: "Total connu des jetons", unavailable: "Non disponible", zero: "Zéro mesuré", partial: "Partiel · sous-total connu", measured: "Mesure connue",
  jobs: "Consommation du job", events: "Observations d'utilisation", 
  reported: "Coût déclaré", estimated: "Coût estimé",
  table: "Données de tendance", empty: "Aucun événement daté dans ce périmètre.",
};
const de: Copy = {
  allTime: "Gesamter Zeitraum", started: "Gestartete Jobs", completed: "Abgeschlossene Jobs", failed: "Fehlgeschlagene Jobs",
  total: "Bekannte Token insgesamt", unavailable: "Nicht verfügbar", zero: "Gemessene Null", partial: "Teilweise · bekannte Teilsumme", measured: "Bekannte Messung",
  jobs: "Jobverbrauch", events: "Verbrauchsbeobachtungen", 
  reported: "Gemeldete Kosten", estimated: "Geschätzte Kosten",
  table: "Trenddaten", empty: "Keine datierten Ereignisse in diesem Bereich.",
};
const ro: Copy = {
  allTime: "Tot istoricul", started: "Joburi începute", completed: "Joburi terminate", failed: "Joburi eșuate",
  total: "Total tokeni cunoscuți", unavailable: "Indisponibil", zero: "Zero măsurat", partial: "Parțial · subtotal cunoscut", measured: "Măsurătoare cunoscută",
  jobs: "Consumul jobului", events: "Observații de consum", 
  reported: "Cost raportat", estimated: "Cost estimat",
  table: "Date de tendință", empty: "Nu există evenimente datate în selecție.",
};
export const statisticsCopy: Record<Locale, Copy> = { en, fr, de, ro };

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
  jobs: "Job consumption", lifetime: "Lifetime", selected: "Selected period", undated: "Unallocated", source: "Source", events: "Usage observations", projectId: "Project ID", runId: "Run ID",
  sourceJournal: "Recorded usage observations", sourceSummary: "Legacy recorded summary · date unavailable", sourceUnavailable: "No reported consumption",
  missingJob: "No consumption projection is available for this job in the selected scope.",
  reported: "Reported cost", estimated: "Estimated cost", 
  trend: "Job trend chart", table: "Trend data · accessible equivalent", empty: "No dated events in this scope.",
  periodHelp: "Change the reporting period in Statistics. This job uses the same dates, timezone and grouping.",
};
type Copy = typeof en;
const fr: Copy = {
  allTime: "Toute la période", started: "Jobs démarrés", completed: "Jobs terminés", failed: "Jobs échoués",
  total: "Total connu des jetons", unavailable: "Non disponible", zero: "Zéro mesuré", partial: "Partiel · sous-total connu", measured: "Mesure connue",
  jobs: "Consommation du job", lifetime: "Durée de vie", selected: "Période sélectionnée", undated: "Non attribué", source: "Source", events: "Observations d'utilisation", projectId: "ID du projet", runId: "ID du job",
  sourceJournal: "Observations enregistrées", sourceSummary: "Résumé historique · date indisponible", sourceUnavailable: "Aucune consommation déclarée",
  missingJob: "Aucune projection de consommation pour ce job dans ce périmètre.", reported: "Coût déclaré", estimated: "Coût estimé",
  trend: "Graphique des jobs", table: "Données de tendance · équivalent accessible", empty: "Aucun événement daté dans ce périmètre.",
  periodHelp: "Modifiez la période dans Statistiques. Ce job utilise les mêmes dates, fuseau et regroupement.",
};
const de: Copy = {
  allTime: "Gesamter Zeitraum", started: "Gestartete Jobs", completed: "Abgeschlossene Jobs", failed: "Fehlgeschlagene Jobs",
  total: "Bekannte Token insgesamt", unavailable: "Nicht verfügbar", zero: "Gemessene Null", partial: "Teilweise · bekannte Teilsumme", measured: "Bekannte Messung",
  jobs: "Jobverbrauch", lifetime: "Gesamtlaufzeit", selected: "Gewählter Zeitraum", undated: "Nicht zugeordnet", source: "Quelle", events: "Verbrauchsbeobachtungen", projectId: "Projekt-ID", runId: "Job-ID",
  sourceJournal: "Aufgezeichnete Verbrauchsbeobachtungen", sourceSummary: "Historische Zusammenfassung · Datum nicht verfügbar", sourceUnavailable: "Kein gemeldeter Verbrauch",
  missingJob: "Für diesen Job ist im gewählten Bereich kein Verbrauchsnachweis verfügbar.", reported: "Gemeldete Kosten", estimated: "Geschätzte Kosten",
  trend: "Jobtrend-Diagramm", table: "Trenddaten · zugängliche Entsprechung", empty: "Keine datierten Ereignisse in diesem Bereich.",
  periodHelp: "Ändern Sie den Berichtszeitraum unter Statistik. Dieser Job nutzt dieselben Daten, Zeitzone und Gruppierung.",
};
const ro: Copy = {
  allTime: "Tot istoricul", started: "Joburi începute", completed: "Joburi terminate", failed: "Joburi eșuate",
  total: "Total tokeni cunoscuți", unavailable: "Indisponibil", zero: "Zero măsurat", partial: "Parțial · subtotal cunoscut", measured: "Măsurătoare cunoscută",
  jobs: "Consumul jobului", lifetime: "Tot istoricul jobului", selected: "Perioada selectată", undated: "Nealocat", source: "Sursă", events: "Observații de consum", projectId: "ID proiect", runId: "ID job",
  sourceJournal: "Observații de consum înregistrate", sourceSummary: "Sumar istoric · dată indisponibilă", sourceUnavailable: "Niciun consum raportat",
  missingJob: "Nu există o proiecție de consum pentru acest job în selecția curentă.", reported: "Cost raportat", estimated: "Cost estimat",
  trend: "Graficul joburilor", table: "Date de tendință · echivalent accesibil", empty: "Nu există evenimente datate în selecție.",
  periodHelp: "Schimbă perioada în Statistici. Acest job folosește aceleași date, fus orar și grupare.",
};
export const statisticsCopy: Record<Locale, Copy> = { en, fr, de, ro };

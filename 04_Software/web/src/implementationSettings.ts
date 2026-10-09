/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

export const executionStages = ["frame", "specify", "design", "build", "validate", "deliver"] as const;

/** Exact collection domains shared by draft and persisted candidate validation. */
export function validImplementationCollection(key: string, value: unknown): boolean {
 if (key === "recovery.retry_backoff_seconds") return Array.isArray(value) && value.length > 0 && value.length <= 1000
  && value.every(item => Number.isSafeInteger(item) && item >= 0);
 if (key === "workflow.stage_timeout_overrides") return !!value && typeof value === "object" && !Array.isArray(value)
  && Object.entries(value).every(([stage, seconds]) => executionStages.includes(stage as typeof executionStages[number]) && Number.isSafeInteger(seconds) && seconds > 0);
 return false;
}

export function durationParts(value: string): { amount: string; unit: string } {
 const match = /^([0-9]*)([smhd]?)$/i.exec(value);
 return match ? { amount: match[1], unit: (match[2] || "s").toLowerCase() } : { amount: "", unit: "h" };
}

/** Serialize the visible draft only when its complete declared domain is valid. */
export function implementationDraft(kind: string, draft: string): string | null {
 if (kind === "duration") {
  const { amount, unit } = durationParts(draft);
  const seconds = Number(amount) * ({s:1, m:60, h:3600, d:86400}[unit] || 0);
  return amount && Number.isSafeInteger(seconds) && seconds > 0 ? `${Number(amount)}${unit}` : null;
 }
 if (kind === "retry-delays") {
  const lines = draft.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  if (!lines.length || lines.some(line => !/^\d+$/.test(line))) return null;
  const values = lines.map(Number);
  return validImplementationCollection("recovery.retry_backoff_seconds", values) ? JSON.stringify(values) : null;
 }
 if (kind === "stage-timeouts") {
  try {
   const value = JSON.parse(draft);
   if (!validImplementationCollection("workflow.stage_timeout_overrides", value)) return null;
   return JSON.stringify(Object.fromEntries(executionStages.filter(stage => Object.hasOwn(value, stage)).map(stage => [stage, value[stage]])));
  } catch { return null; }
 }
 return draft;
}

/** Localized editor terminology; stable AEGIS identifiers remain configuration keys. */
export const implementationEditorCopy = {
 en: { amount: "Answer waiting time", unit: "Time unit", units: {s:"Seconds",m:"Minutes",h:"Hours",d:"Days"}, general:"Use general limit", custom:"Custom limit", seconds:"Seconds", schedule:"One nonnegative whole number per line. With three attempts, only the first two delays are used; later retries repeat the last delay.", stages:["Framing", "Specification", "Design", "Implementation", "Validation", "Delivery"], invalid:"Enter a positive duration, whole retry delays, or positive stage limits." },
 ro: { amount: "Timp de așteptare a răspunsului", unit: "Unitatea de timp", units: {s:"Secunde",m:"Minute",h:"Ore",d:"Zile"}, general:"Folosește limita generală", custom:"Limită proprie", seconds:"Secunde", schedule:"Un număr întreg nenegativ pe linie. Cu trei încercări se folosesc doar primele două pauze; reluările ulterioare repetă ultima pauză.", stages:["Încadrare", "Specificare", "Proiectare", "Implementare", "Validare", "Livrare"], invalid:"Introdu o durată pozitivă, pauze întregi de retry sau limite pozitive pe etape." },
 fr: { amount: "Temps d’attente de la réponse", unit: "Unité de temps", units: {s:"Secondes",m:"Minutes",h:"Heures",d:"Jours"}, general:"Utiliser la limite générale", custom:"Limite personnalisée", seconds:"Secondes", schedule:"Un entier non négatif par ligne. Avec trois tentatives, seuls les deux premiers délais sont utilisés ; les relances suivantes répètent le dernier délai.", stages:["Cadrage", "Spécification", "Conception", "Implémentation", "Validation", "Livraison"], invalid:"Saisissez une durée positive, des délais entiers ou des limites positives par étape." },
 de: { amount: "Wartezeit auf Antwort", unit: "Zeiteinheit", units: {s:"Sekunden",m:"Minuten",h:"Stunden",d:"Tage"}, general:"Allgemeines Limit verwenden", custom:"Eigenes Limit", seconds:"Sekunden", schedule:"Eine nichtnegative ganze Zahl je Zeile. Bei drei Versuchen werden nur die ersten zwei Pausen verwendet; weitere Wiederholungen nutzen die letzte Pause.", stages:["Rahmen", "Spezifikation", "Entwurf", "Implementierung", "Validierung", "Lieferung"], invalid:"Positive Dauer, ganze Wiederholungspausen oder positive Phasenlimits eingeben." },
} satisfies Record<Locale, object>;

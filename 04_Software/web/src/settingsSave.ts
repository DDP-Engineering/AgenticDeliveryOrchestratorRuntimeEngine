/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import {connectionOf, validConnection} from "./agentConnection.ts";
import {validCredentialNames} from "./executorSettings.ts";
import {durationParts, implementationDraft} from "./implementationSettings.ts";
import {BATCH_KEY, editValue, validBatchValues, type PendingConfig, type SettingRow} from "./settings.ts";
import type {Locale} from "./i18n";

export type SettingEdit = {key: string; value: string};
export type SettingDrafts = Record<string, string>;
export type SettingImpact = "identity" | "runtime" | "network" | "packages" | "budget" | "publication";

/** Stable structural comparison; object order is immaterial, list order is retained. */
export function sameSettingValue(left: unknown, right: unknown): boolean {
  if (Array.isArray(left) || Array.isArray(right)) return Array.isArray(left) && Array.isArray(right)
    && left.length === right.length && left.every((value,index)=>sameSettingValue(value,right[index]));
  if (left && right && typeof left === "object" && typeof right === "object") {
    const a=Object.entries(left), b=Object.entries(right);
    return a.length===b.length && a.every(([key,value])=>Object.hasOwn(right,key)
      && sameSettingValue(value,(right as Record<string,unknown>)[key]));
  }
  return left===right;
}

/** Visible editor input for a saved value or a recovered candidate member. */
export function settingDraftValue(row: SettingRow, config: Record<string,unknown>, value: unknown = row.value): string {
  if (row.input==="connection") return JSON.stringify(value===row.value ? connectionOf(config) : value);
  if (["reviewers","retry-delays"].includes(row.input) && Array.isArray(value)) return value.join("\n");
  return editValue(value);
}

/** Normalize only declared domains; incomplete input remains an unsaved draft. */
export function normalizeSettingDraft(row: SettingRow, raw: string): string | null {
  if (row.input==="none") return null;
  if (row.input==="connection" || row.input==="credential-names") {
    try {
      const parsed=JSON.parse(raw);
      if (row.input==="connection") return validConnection(parsed) ? JSON.stringify({
        provider:parsed.provider,model:parsed.model,base_url:parsed.base_url,api:parsed.api,
      }) : null;
      return validCredentialNames(parsed) ? JSON.stringify(parsed) : null;
    } catch { return null; }
  }
  if (row.input==="reviewers") {
    const names=raw.split(/\r?\n/).map(value=>value.trim()).filter(Boolean);
    return validBatchValues({"delivery.reviewers":names}) ? JSON.stringify(names) : null;
  }
  if (["duration","retry-delays","stage-timeouts"].includes(row.input)) return implementationDraft(row.input,raw);
  if (row.input==="boolean") return ["true","false"].includes(raw) ? raw : null;
  if (row.input==="choice") return row.choices.includes(raw) ? raw : null;
  if (row.input==="number") {
    if (!raw.trim()) return null;
    const value=Number(raw);
    return Number.isFinite(value) && (row.step!=="1" || Number.isSafeInteger(value))
      && (row.minimum==null || value>=row.minimum) && (row.maximum==null || value<=row.maximum)
      ? String(value) : null;
  }
  return raw;
}

function typedDraft(row: SettingRow, wire: string): unknown {
  if (["connection","credential-names","reviewers","retry-delays","stage-timeouts"].includes(row.input)) return JSON.parse(wire);
  if (row.input==="number") return Number(wire);
  if (row.input==="boolean" || typeof row.value==="boolean") return wire==="true";
  return wire;
}

function durationSeconds(value: string): number {
  const {amount,unit}=durationParts(value);
  return Number(amount)*({s:1,m:60,h:3600,d:86400}[unit] || 0);
}

/** Coalesce virtual connection rows and omit edits with unchanged semantic values. */
export function prepareSettingDrafts(config: Record<string,unknown>, rows: SettingRow[], drafts: SettingDrafts): {edits: SettingEdit[]; invalid: string[]} {
  const edits: SettingEdit[]=[], invalid: string[]=[];
  for (const [key,raw] of Object.entries(drafts).sort(([a],[b])=>a.localeCompare(b))) {
    const row=rows.find(item=>item.editKey===key && item.input!=="none");
    const value=row ? normalizeSettingDraft(row,raw) : null;
    if (!row || value===null) { invalid.push(key); continue; }
    const previous=normalizeSettingDraft(row,settingDraftValue(row,config));
    const equal=previous!==null && (row.input==="duration" ? durationSeconds(previous)===durationSeconds(value)
      : sameSettingValue(typedDraft(row,previous),typedDraft(row,value)));
    if (!equal) edits.push({key,value});
  }
  return {edits,invalid};
}

/** Exact typed server values as wire edits, including API-only recovery keys. */
export function pendingSettingEdits(candidate: PendingConfig): SettingEdit[] {
  const values=candidate.key===BATCH_KEY ? candidate.proposed_value as Record<string,unknown>
    : {[candidate.key]:candidate.proposed_value};
  return Object.entries(values).map(([key,value])=>({key,value:editValue(value)}));
}

/** Recovered pending settings remain one local project draft, including scalar API edits. */
export function recoverSettingDrafts(config: Record<string,unknown>, rows: SettingRow[], candidate: PendingConfig | null): SettingDrafts {
  if (!candidate) return {};
  const values=candidate.key===BATCH_KEY ? candidate.proposed_value as Record<string,unknown>
    : {[candidate.key]:candidate.proposed_value};
  return Object.fromEntries(Object.entries(values).map(([key,value])=>{
    const row=rows.find(item=>item.editKey===key && item.input!=="none");
    return [key,row ? settingDraftValue(row,config,value) : editValue(value)];
  }));
}

/** Treat candidate revision hashes as necessary but insufficient response binding. */
export function candidateMatchesEdits(candidate: PendingConfig, edits: SettingEdit[], rows: SettingRow[]): boolean {
  if (candidate.key!==BATCH_KEY || !validBatchValues(candidate.proposed_value)) return false;
  const values=candidate.proposed_value;
  return Object.keys(values).length===edits.length && edits.every(edit=>{
    const row=rows.find(item=>item.editKey===edit.key && item.input!=="none");
    return row && Object.hasOwn(values,edit.key) && sameSettingValue(values[edit.key],typedDraft(row,edit.value));
  });
}

/** Important effects are explicit and shared between fresh and recovered drafts. */
export function settingImpacts(edits: SettingEdit[], rows: SettingRow[]): SettingImpact[] {
  const impacts=new Set<SettingImpact>();
  for (const {key} of edits) {
    if (key==="container.system_packages") impacts.add("packages");
    else if (key==="executor.internet") impacts.add("network");
    else if (key.startsWith("budgets.") || key==="workflow.stage_timeout_overrides" || key==="polling.max_concurrent_runs") impacts.add("budget");
    else if (key.startsWith("delivery.") || key==="review.on_pipeline_failure") impacts.add("publication");
    else if (key.startsWith("agent.") || key.startsWith("platform.") || key.startsWith("worktree.")) impacts.add("identity");
    else if (rows.some(row=>row.editKey===key && row.restart)) impacts.add("runtime");
  }
  return [...impacts];
}

export const settingsSaveCopy = {
 en: {save:"Save",saving:"Saving…",discard:"Discard changes",clean:"No unsaved changes",dirty:"{count} unsaved changes",invalid:"Correct the invalid values before saving.",stale:"Settings changed on the server. Discard your draft to reload them.",leave:"Discard your unsaved project settings?",title:"Confirm important changes",confirm:"Save changes",cancel:"Keep editing",project:"Project",before:"Current value",after:"New value",prepared:"Recovered unsaved settings are ready to save.",pause:"Pause monitoring and wait for active work to finish before saving.",future:"These changes apply to future execution. Existing jobs keep their settings.",effects:{identity:"Changes the project or repository identity.",runtime:"Changes the agent or its execution environment.",network:"Changes the agent's internet access.",packages:"Changes permission to install system packages inside the container.",budget:"Changes execution limits, including time or cost.",publication:"Changes publication or review policy."}},
 ro: {save:"Salvează",saving:"Se salvează…",discard:"Renunță la modificări",clean:"Nu există modificări nesalvate",dirty:"{count} modificări nesalvate",invalid:"Corectează valorile nevalide înainte de salvare.",stale:"Setările s-au schimbat pe server. Renunță la modificările locale pentru a le reîncărca.",leave:"Renunți la modificările nesalvate ale proiectului?",title:"Confirmă modificările importante",confirm:"Salvează modificările",cancel:"Continuă editarea",project:"Proiect",before:"Valoare curentă",after:"Valoare nouă",prepared:"Modificările nesalvate recuperate pot fi salvate.",pause:"Pune monitorizarea în pauză și așteaptă terminarea lucrului activ înainte de salvare.",future:"Modificările se aplică execuțiilor viitoare. Joburile existente își păstrează setările.",effects:{identity:"Schimbă identitatea proiectului sau a repository-ului.",runtime:"Schimbă agentul sau mediul său de execuție.",network:"Schimbă accesul agentului la internet.",packages:"Schimbă permisiunea de a instala pachete de sistem în container.",budget:"Schimbă limitele de execuție, inclusiv timpul sau costul.",publication:"Schimbă regulile de publicare sau review."}},
 fr: {save:"Enregistrer",saving:"Enregistrement…",discard:"Annuler les modifications",clean:"Aucune modification non enregistrée",dirty:"{count} modifications non enregistrées",invalid:"Corrigez les valeurs incorrectes avant d’enregistrer.",stale:"Les paramètres ont changé sur le serveur. Annulez le brouillon pour les recharger.",leave:"Abandonner les modifications non enregistrées du projet ?",title:"Confirmer les modifications importantes",confirm:"Enregistrer les modifications",cancel:"Continuer la modification",project:"Projet",before:"Valeur actuelle",after:"Nouvelle valeur",prepared:"Les modifications récupérées peuvent être enregistrées.",pause:"Mettez la surveillance en pause et attendez la fin du travail actif avant d’enregistrer.",future:"Ces modifications s’appliquent aux prochaines exécutions. Les jobs existants conservent leurs paramètres.",effects:{identity:"Modifie l’identité du projet ou du dépôt.",runtime:"Modifie l’agent ou son environnement d’exécution.",network:"Modifie l’accès Internet de l’agent.",packages:"Modifie l’autorisation d’installer des paquets système dans le conteneur.",budget:"Modifie les limites d’exécution, notamment le temps ou le coût.",publication:"Modifie les règles de publication ou de revue."}},
 de: {save:"Speichern",saving:"Wird gespeichert…",discard:"Änderungen verwerfen",clean:"Keine ungespeicherten Änderungen",dirty:"{count} ungespeicherte Änderungen",invalid:"Ungültige Werte vor dem Speichern korrigieren.",stale:"Die Einstellungen wurden auf dem Server geändert. Entwurf zum Neuladen verwerfen.",leave:"Ungespeicherte Projekteinstellungen verwerfen?",title:"Wichtige Änderungen bestätigen",confirm:"Änderungen speichern",cancel:"Weiter bearbeiten",project:"Projekt",before:"Aktueller Wert",after:"Neuer Wert",prepared:"Wiederhergestellte Änderungen können gespeichert werden.",pause:"Überwachung pausieren und aktive Arbeit vor dem Speichern abschließen lassen.",future:"Diese Änderungen gelten für zukünftige Ausführungen. Bestehende Jobs behalten ihre Einstellungen.",effects:{identity:"Ändert die Identität des Projekts oder Repositorys.",runtime:"Ändert den Agenten oder seine Ausführungsumgebung.",network:"Ändert den Internetzugriff des Agenten.",packages:"Ändert die Berechtigung zur Installation von Systempaketen im Container.",budget:"Ändert Ausführungsgrenzen wie Zeit oder Kosten.",publication:"Ändert Veröffentlichungs- oder Review-Regeln."}},
} satisfies Record<Locale, object>;

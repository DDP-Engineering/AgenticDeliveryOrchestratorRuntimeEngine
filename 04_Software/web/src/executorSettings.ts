/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type {Locale} from "./i18n";

export const codingAgents = ["opencode", "pi", "codex", "qwen"] as const;
export const agentNames: Record<string,string> = {opencode:"OpenCode",pi:"Pi",codex:"Codex",qwen:"Qwen Code"};
export type ExecutorSelection = {agent:string;command:string;model:string};
export const agentSettingsCopy = {
 en:{agent:"Default coding agent",command:"Executor launch command",model:"Executor model identifier",variables:"Allowed credential variables",authentication:"Authentication",connection:"AI connection",setup:"Select the coding agent, its launch command and model together. The agent must already be installed on the ADORE server or in the configured image. Applying settings does not install software.",variableHelp:"Select only the provider variables this project needs. These are names, not API key values. An empty list is valid when using existing server sign-in.",modelHelp:"Enter the model ID accepted by the selected agent and provider. There is no universal model default. Existing agents retain their saved command and model."},
 ro:{agent:"Agent de programare implicit",command:"Comanda de lansare a executorului",model:"Identificatorul modelului executorului",variables:"Variabile de autentificare permise",authentication:"Autentificare",connection:"Conexiune AI",setup:"Alege împreună agentul de programare, comanda și modelul. Agentul trebuie instalat deja pe serverul ADORE sau în imaginea configurată. Aplicarea setărilor nu instalează software.",variableHelp:"Selectează doar variabilele furnizorilor necesari proiectului. Sunt nume, nu valorile cheilor API. Lista poate fi goală când folosești autentificarea existentă pe server.",modelHelp:"Introdu ID-ul modelului acceptat de agentul ales și furnizor. Nu există un model implicit universal. Agenții existenți își păstrează comanda și modelul salvate."},
 fr:{agent:"Agent de programmation par défaut",command:"Commande de lancement de l’exécuteur",model:"Identifiant du modèle de l’exécuteur",variables:"Variables d’identification autorisées",authentication:"Authentification",connection:"Connexion IA",setup:"Choisissez ensemble l’agent, sa commande et son modèle. L’agent doit être installé sur le serveur ADORE ou dans l’image configurée. L’application des paramètres n’installe aucun logiciel.",variableHelp:"Sélectionnez uniquement les variables nécessaires aux fournisseurs du projet. Ce sont des noms, pas les clés API. Une liste vide convient à une connexion existante sur le serveur.",modelHelp:"Saisissez l’ID accepté par l’agent et le fournisseur. Aucun modèle universel par défaut. Les agents existants conservent leur commande et leur modèle."},
 de:{agent:"Standard-Coding-Agent",command:"Executor-Startbefehl",model:"Executor-Modellkennung",variables:"Erlaubte Zugangsdaten-Variablen",authentication:"Authentifizierung",connection:"KI-Verbindung",setup:"Wählen Sie Agent, Startbefehl und Modell gemeinsam. Der Agent muss auf dem ADORE-Server oder im konfigurierten Image installiert sein. Einstellungen installieren keine Software.",variableHelp:"Wählen Sie nur benötigte Anbieter-Variablen. Dies sind Namen, keine API-Schlüsselwerte. Für eine vorhandene Server-Anmeldung ist eine leere Liste möglich.",modelHelp:"Geben Sie die Modell-ID des gewählten Agenten und Anbieters ein. Es gibt kein universelles Standardmodell. Bestehende Agenten behalten ihren Befehl und ihr Modell."},
};

/** Exact complete review transport; partial drafts cannot enable preparation. */
export function validExecutorSelection(value:unknown):value is ExecutorSelection {
 if (!value || typeof value !== "object" || Array.isArray(value)) return false;
 const v=value as ExecutorSelection;
 return Object.keys(v).sort().join()==="agent,command,model" && codingAgents.some(a=>a===v.agent)
  && typeof v.command==="string" && v.command.length>0 && v.command.length<=4096 && v.command.includes("{prompt}") && !/[\u0000-\u001f]/.test(v.command)
  && typeof v.model==="string" && /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$/.test(v.model);
}

/** Names-only list, including retained custom names; server verifies provider/forge scope. */
export function validCredentialNames(value:unknown):value is string[] {
 return Array.isArray(value) && value.length<=32 && value.every(v=>typeof v==="string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(v)) && new Set(value).size===value.length;
}

/** Generic labels follow the selected agent rather than embedding its name. */
export function executorSettingLabel(key:string,locale:Locale):string|null {
 const c=agentSettingsCopy[locale];
 if (["executor.default","executor.selection"].includes(key)) return c.agent;
 if (key==="executor.env_keys") return c.variables;
 if (/^executor\.(?:commands\.)?(opencode|pi|codex|qwen)\.command$/.test(key)) return c.command;
 if (/^executor\.(?:commands\.)?(opencode|pi|codex|qwen)\.model$/.test(key)) return c.model;
 return null;
}

/** Read a complete draft for an existing agent without inventing provider/model defaults. */
export function executorSelectionDraft(config:Record<string,unknown>,agent?:string):ExecutorSelection {
 const executor=(config.executor || {}) as {default?:string;commands?:Record<string,{command?:string;model?:string}>};
 const name=agent || executor.default || "opencode", command=executor.commands?.[name];
 return {agent:name,command:command?.command || "",model:command?.model || ""};
}


export const credentialEditorCopy = {
 en:{add:"Add credential variable",choose:"Choose a variable…",selected:"Selected variables",remove:"Remove",inline:"Edit the command and model in their rows below, then prepare the complete change here."},
 ro:{add:"Adaugă o variabilă de autentificare",choose:"Alege o variabilă…",selected:"Variabile selectate",remove:"Elimină",inline:"Editează comanda și modelul pe rândurile de mai jos, apoi pregătește aici schimbarea completă."},
 fr:{add:"Ajouter une variable d’identification",choose:"Choisir une variable…",selected:"Variables sélectionnées",remove:"Supprimer",inline:"Modifiez la commande et le modèle dans leurs lignes ci-dessous, puis préparez ici la modification complète."},
 de:{add:"Zugangsdaten-Variable hinzufügen",choose:"Variable auswählen…",selected:"Ausgewählte Variablen",remove:"Entfernen",inline:"Bearbeiten Sie Befehl und Modell in ihren Zeilen unten und bereiten Sie hier die vollständige Änderung vor."},
};

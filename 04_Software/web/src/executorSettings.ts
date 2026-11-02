/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type {Locale} from "./i18n";
import {connectionCopy} from "./agentConnection.ts";

/** Pi is ADORE's only coding agent; these settings configure how it runs. */
export const agentSettingsCopy = {
 en:{command:"Executor launch command",model:"Model",variables:"Additional credential variables",authentication:"Authentication",connection:"AI connection",variableHelp:"Extra secret variables Pi receives besides the provider's own key variable. These are names, not values; most projects need none.",modelHelp:"The model within the provider, such as gpt-5.5 for OpenAI. There is no universal model default.",commandHelp:"Container projects run the Pi pinned in the executor image and use the preset. Local projects run the installed Pi with this argv."},
 ro:{command:"Comanda de lansare a executorului",model:"Model",variables:"Variabile de autentificare suplimentare",authentication:"Autentificare",connection:"Conexiune AI",variableHelp:"Variabile secrete suplimentare primite de Pi pe lângă variabila cheii furnizorului. Sunt nume, nu valori; majoritatea proiectelor nu au nevoie de ele.",modelHelp:"Modelul furnizorului, de exemplu gpt-5.5 pentru OpenAI. Nu există un model implicit universal.",commandHelp:"Proiectele în container rulează Pi fixat în imaginea executorului și folosesc presetarea. Proiectele locale rulează Pi instalat cu aceste argumente."},
 fr:{command:"Commande de lancement de l’exécuteur",model:"Modèle",variables:"Variables d’identification supplémentaires",authentication:"Authentification",connection:"Connexion IA",variableHelp:"Variables secrètes supplémentaires reçues par Pi en plus de la variable de clé du fournisseur. Ce sont des noms, pas des valeurs ; la plupart des projets n’en ont pas besoin.",modelHelp:"Le modèle du fournisseur, par exemple gpt-5.5 pour OpenAI. Aucun modèle universel par défaut.",commandHelp:"Les projets en conteneur exécutent le Pi épinglé dans l’image et utilisent le préréglage. Les projets locaux exécutent le Pi installé avec ces arguments."},
 de:{command:"Executor-Startbefehl",model:"Modell",variables:"Zusätzliche Zugangsdaten-Variablen",authentication:"Authentifizierung",connection:"KI-Verbindung",variableHelp:"Zusätzliche geheime Variablen, die Pi neben der Schlüsselvariable des Anbieters erhält. Dies sind Namen, keine Werte; die meisten Projekte brauchen keine.",modelHelp:"Das Modell des Anbieters, z. B. gpt-5.5 für OpenAI. Es gibt kein universelles Standardmodell.",commandHelp:"Container-Projekte führen das im Executor-Image fixierte Pi mit der Vorgabe aus. Lokale Projekte führen das installierte Pi mit diesen Argumenten aus."},
};

/** Names-only list, including retained custom names; server verifies provider/forge scope. */
export function validCredentialNames(value:unknown):value is string[] {
 return Array.isArray(value) && value.length<=32 && value.every(v=>typeof v==="string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(v)) && new Set(value).size===value.length;
}

/** Labels of the Agent and model settings. */
export function executorSettingLabel(key:string,locale:Locale):string|null {
 const c=agentSettingsCopy[locale], connection=connectionCopy[locale];
 if (key==="executor.env_keys") return c.variables;
 if (key==="executor.command") return c.command;
 if (key==="executor.model") return c.model;
 if (key==="executor.provider") return connection.provider;
 if (key==="executor.endpoint.base_url") return connection.baseUrl;
 if (key==="executor.endpoint.api") return connection.api;
 if (key==="executor.connection") return c.connection;
 return null;
}

/** Row help of the Agent and model settings. */
export function executorSettingHelp(key:string,locale:Locale):string|null {
 const c=agentSettingsCopy[locale], connection=connectionCopy[locale];
 if (key==="executor.env_keys") return c.variableHelp;
 if (key==="executor.command") return c.commandHelp;
 if (key==="executor.model") return c.modelHelp;
 if (key==="executor.provider" || key==="executor.connection") return connection.providerHelp;
 if (key==="executor.endpoint.base_url") return connection.baseUrlHelp;
 if (key==="executor.endpoint.api") return connection.apiHelp;
 return null;
}


export const credentialEditorCopy = {
 en:{add:"Add credential variable",choose:"Choose a variable…",selected:"Selected variables",remove:"Remove"},
 ro:{add:"Adaugă o variabilă de autentificare",choose:"Alege o variabilă…",selected:"Variabile selectate",remove:"Elimină"},
 fr:{add:"Ajouter une variable d’identification",choose:"Choisir une variable…",selected:"Variables sélectionnées",remove:"Supprimer"},
 de:{add:"Zugangsdaten-Variable hinzufügen",choose:"Variable auswählen…",selected:"Ausgewählte Variablen",remove:"Entfernen"},
};

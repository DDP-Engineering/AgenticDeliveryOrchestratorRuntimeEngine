/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type {Locale} from "./i18n";

/** Pi is ADORE's only coding agent; these settings configure how it runs. */
export const agentSettingsCopy = {
 en:{command:"Executor launch command",model:"Executor model identifier",variables:"Allowed credential variables",authentication:"Authentication",connection:"AI connection",variableHelp:"Select only the provider variables this project needs. These are names, not API key values. An empty list is valid when a local Pi uses its own sign-in.",modelHelp:"Enter the Pi model ID in provider/model form, such as openai/gpt-5.5. There is no universal model default.",commandHelp:"Container projects run the Pi pinned in the executor image and use the preset. Local projects run the installed Pi with this argv."},
 ro:{command:"Comanda de lansare a executorului",model:"Identificatorul modelului executorului",variables:"Variabile de autentificare permise",authentication:"Autentificare",connection:"Conexiune AI",variableHelp:"Selectează doar variabilele furnizorilor necesari proiectului. Sunt nume, nu valorile cheilor API. Lista poate fi goală când un Pi local folosește propria autentificare.",modelHelp:"Introdu ID-ul modelului Pi în forma furnizor/model, de exemplu openai/gpt-5.5. Nu există un model implicit universal.",commandHelp:"Proiectele în container rulează Pi fixat în imaginea executorului și folosesc presetarea. Proiectele locale rulează Pi instalat cu aceste argumente."},
 fr:{command:"Commande de lancement de l’exécuteur",model:"Identifiant du modèle de l’exécuteur",variables:"Variables d’identification autorisées",authentication:"Authentification",connection:"Connexion IA",variableHelp:"Sélectionnez uniquement les variables nécessaires aux fournisseurs du projet. Ce sont des noms, pas les clés API. Une liste vide convient quand un Pi local utilise sa propre connexion.",modelHelp:"Saisissez l’ID du modèle Pi au format fournisseur/modèle, par exemple openai/gpt-5.5. Aucun modèle universel par défaut.",commandHelp:"Les projets en conteneur exécutent le Pi épinglé dans l’image et utilisent le préréglage. Les projets locaux exécutent le Pi installé avec ces arguments."},
 de:{command:"Executor-Startbefehl",model:"Executor-Modellkennung",variables:"Erlaubte Zugangsdaten-Variablen",authentication:"Authentifizierung",connection:"KI-Verbindung",variableHelp:"Wählen Sie nur benötigte Anbieter-Variablen. Dies sind Namen, keine API-Schlüsselwerte. Eine leere Liste ist möglich, wenn ein lokales Pi seine eigene Anmeldung nutzt.",modelHelp:"Geben Sie die Pi-Modell-ID im Format Anbieter/Modell ein, z. B. openai/gpt-5.5. Es gibt kein universelles Standardmodell.",commandHelp:"Container-Projekte führen das im Executor-Image fixierte Pi mit der Vorgabe aus. Lokale Projekte führen das installierte Pi mit diesen Argumenten aus."},
};

/** Names-only list, including retained custom names; server verifies provider/forge scope. */
export function validCredentialNames(value:unknown):value is string[] {
 return Array.isArray(value) && value.length<=32 && value.every(v=>typeof v==="string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(v)) && new Set(value).size===value.length;
}

/** Labels of the Agent and model settings. */
export function executorSettingLabel(key:string,locale:Locale):string|null {
 const c=agentSettingsCopy[locale];
 if (key==="executor.env_keys") return c.variables;
 if (key==="executor.command") return c.command;
 if (key==="executor.model") return c.model;
 return null;
}

/** Row help of the Agent and model settings. */
export function executorSettingHelp(key:string,locale:Locale):string|null {
 const c=agentSettingsCopy[locale];
 if (key==="executor.env_keys") return c.variableHelp;
 if (key==="executor.command") return c.commandHelp;
 if (key==="executor.model") return c.modelHelp;
 return null;
}


export const credentialEditorCopy = {
 en:{add:"Add credential variable",choose:"Choose a variable…",selected:"Selected variables",remove:"Remove"},
 ro:{add:"Adaugă o variabilă de autentificare",choose:"Alege o variabilă…",selected:"Variabile selectate",remove:"Elimină"},
 fr:{add:"Ajouter une variable d’identification",choose:"Choisir une variable…",selected:"Variables sélectionnées",remove:"Supprimer"},
 de:{add:"Zugangsdaten-Variable hinzufügen",choose:"Variable auswählen…",selected:"Ausgewählte Variablen",remove:"Entfernen"},
};

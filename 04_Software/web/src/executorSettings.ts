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

/** Internet access for the agent and its web search, in four locales. */
export const internetCopy = {
 en:{internet:"Internet access for the agent",internetHelp:"Off (default): a container run reaches only the model provider; web search, page reading and downloads are unavailable. On: open network, web search and page reading, downloads with curl, npm or pip.",search:"Web search",searchHelp:"Search service used while internet access for the agent is on: exa (no key), brave or tavily (key saved in Agent and model) or none (no web search or page reading).",on:"On",off:"Off",internetWarning:"With internet access on, a malicious web page could try to make the agent send its API key or ChatGPT token out. Prefer limited, short-lived keys.",internetLocal:"Not enforced: this project runs Pi installed on the server, which reaches whatever the server reaches.",exa:"Exa (no key)",brave:"Brave (key needed)",tavily:"Tavily (key needed)",none:"None"},
 ro:{internet:"Acces la internet pentru agent",internetHelp:"Dezactivat (implicit): o rulare în container ajunge doar la furnizorul modelului; căutarea web, citirea paginilor și descărcările nu sunt disponibile. Activat: rețea deschisă, căutare web, citirea paginilor și descărcări cu curl, npm sau pip.",search:"Căutare web",searchHelp:"Serviciul de căutare folosit când accesul la internet al agentului este activat: exa (fără cheie), brave sau tavily (cheie salvată în Agent și model) sau none (fără căutare web sau citirea paginilor).",on:"Activat",off:"Dezactivat",internetWarning:"Cu accesul la internet activat, o pagină web rău intenționată ar putea încerca să facă agentul să trimită cheia API sau tokenul ChatGPT. Preferă chei limitate și de scurtă durată.",internetLocal:"Neaplicat: acest proiect rulează Pi instalat pe server, care ajunge oriunde ajunge serverul.",exa:"Exa (fără cheie)",brave:"Brave (necesită cheie)",tavily:"Tavily (necesită cheie)",none:"Niciuna"},
 fr:{internet:"Accès Internet de l’agent",internetHelp:"Désactivé (par défaut) : une exécution en conteneur n’atteint que le fournisseur du modèle ; recherche web, lecture de pages et téléchargements sont indisponibles. Activé : réseau ouvert, recherche web, lecture de pages et téléchargements avec curl, npm ou pip.",search:"Recherche web",searchHelp:"Service de recherche utilisé quand l’accès Internet de l’agent est activé : exa (sans clé), brave ou tavily (clé enregistrée dans Agent et modèle) ou none (ni recherche web ni lecture de pages).",on:"Activé",off:"Désactivé",internetWarning:"Avec l’accès Internet activé, une page web malveillante pourrait tenter de faire envoyer par l’agent sa clé API ou son jeton ChatGPT. Préférez des clés limitées et de courte durée.",internetLocal:"Non appliqué : ce projet exécute Pi installé sur le serveur, qui atteint tout ce que le serveur atteint.",exa:"Exa (sans clé)",brave:"Brave (clé requise)",tavily:"Tavily (clé requise)",none:"Aucune"},
 de:{internet:"Internetzugang für den Agenten",internetHelp:"Aus (Standard): Ein Containerlauf erreicht nur den Modellanbieter; Websuche, Seitenlesen und Downloads sind nicht verfügbar. An: offenes Netzwerk, Websuche, Seitenlesen und Downloads mit curl, npm oder pip.",search:"Websuche",searchHelp:"Suchdienst bei eingeschaltetem Internetzugang des Agenten: exa (ohne Schlüssel), brave oder tavily (Schlüssel unter Agent und Modell gespeichert) oder none (keine Websuche und kein Seitenlesen).",on:"An",off:"Aus",internetWarning:"Bei eingeschaltetem Internetzugang könnte eine bösartige Webseite versuchen, den Agenten seinen API-Schlüssel oder sein ChatGPT-Token versenden zu lassen. Verwenden Sie möglichst eingeschränkte, kurzlebige Schlüssel.",internetLocal:"Nicht durchgesetzt: Dieses Projekt führt das auf dem Server installierte Pi aus, das alles erreicht, was der Server erreicht.",exa:"Exa (ohne Schlüssel)",brave:"Brave (Schlüssel nötig)",tavily:"Tavily (Schlüssel nötig)",none:"Keine"},
};

/** Web search choices of `[executor.web] search`. */
export const WEB_SEARCH_CHOICES = ["exa", "brave", "tavily", "none"] as const;

/** The displayed value of the internet switch or the web search, else null. */
export function agentValue(key:string,value:unknown,locale:Locale):string|null {
 const c=internetCopy[locale];
 if (key==="executor.internet") return value===true || value==="true" ? c.on : value===false || value==="false" ? c.off : null;
 if (key==="executor.web.search" && (WEB_SEARCH_CHOICES as readonly unknown[]).includes(value)) return c[value as typeof WEB_SEARCH_CHOICES[number]];
 return null;
}

/** Whether a project's configuration needs a Brave or Tavily key (internet on). */
export function searchKeyNeeded(config:Record<string, unknown>):boolean {
 const executor=config.executor as {internet?:unknown; web?:{search?:unknown}}|undefined;
 return executor?.internet===true && ["brave","tavily"].includes(String(executor.web?.search));
}

/** Names-only list, including retained custom names; server verifies provider/forge scope. */
export function validCredentialNames(value:unknown):value is string[] {
 return Array.isArray(value) && value.length<=32 && value.every(v=>typeof v==="string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(v)) && new Set(value).size===value.length;
}

/** Labels of the Agent and model settings. */
export function executorSettingLabel(key:string,locale:Locale):string|null {
 if (key==="container.system_packages") return systemPackageCopy[locale].label;
 const c=agentSettingsCopy[locale], connection=connectionCopy[locale];
 if (key==="executor.env_keys") return c.variables;
 if (key==="executor.command") return c.command;
 if (key==="executor.model") return c.model;
 if (key==="executor.provider") return connection.provider;
 if (key==="executor.endpoint.base_url") return connection.baseUrl;
 if (key==="executor.endpoint.api") return connection.api;
 if (key==="executor.connection") return c.connection;
 if (key==="executor.internet") return internetCopy[locale].internet;
 if (key==="executor.web.search") return internetCopy[locale].search;
 return null;
}

/** Row help of the Agent and model settings. */
export function executorSettingHelp(key:string,locale:Locale):string|null {
 if (key==="container.system_packages") return systemPackageCopy[locale].help;
 const c=agentSettingsCopy[locale], connection=connectionCopy[locale];
 if (key==="executor.env_keys") return c.variableHelp;
 if (key==="executor.command") return c.commandHelp;
 if (key==="executor.model") return c.modelHelp;
 if (key==="executor.provider" || key==="executor.connection") return connection.providerHelp;
 if (key==="executor.endpoint.base_url") return connection.baseUrlHelp;
 if (key==="executor.endpoint.api") return connection.apiHelp;
 if (key==="executor.internet") return internetCopy[locale].internetHelp;
 if (key==="executor.web.search") return internetCopy[locale].searchHelp;
 return null;
}


export const credentialEditorCopy = {
 en:{add:"Add credential variable",choose:"Choose a variable…",selected:"Selected variables",remove:"Remove"},
 ro:{add:"Adaugă o variabilă de autentificare",choose:"Alege o variabilă…",selected:"Variabile selectate",remove:"Elimină"},
 fr:{add:"Ajouter une variable d’identification",choose:"Choisir une variable…",selected:"Variables sélectionnées",remove:"Supprimer"},
 de:{add:"Zugangsdaten-Variable hinzufügen",choose:"Variable auswählen…",selected:"Ausgewählte Variablen",remove:"Entfernen"},
};

export const systemPackageCopy = {
 en:{label:"Allow agent system package installation",help:"The agent installs system packages directly in its container. Network access is configured separately. A compatible image with sudo is required; start a fresh job after changing this permission."},
 fr:{label:"Autoriser l’installation de paquets système par l’agent",help:"L’agent installe directement les paquets système dans son conteneur. L’accès réseau est distinct. Une image compatible avec sudo est requise ; lancez une nouvelle tâche après modification."},
 de:{label:"Systempaketinstallation durch den Agenten erlauben",help:"Der Agent installiert Systempakete direkt im Container. Netzwerkzugriff wird separat festgelegt. Ein kompatibles Image mit sudo ist nötig; nach Änderungen einen neuen Auftrag starten."},
 ro:{label:"Permite agentului instalarea pachetelor de sistem",help:"Agentul instalează direct pachetele de sistem în container. Accesul la rețea se configurează separat. Este necesară o imagine compatibilă cu sudo; porniți o lucrare nouă după schimbarea permisiunii."},
};

/** Read a complete draft for an existing agent without inventing provider/model defaults. */
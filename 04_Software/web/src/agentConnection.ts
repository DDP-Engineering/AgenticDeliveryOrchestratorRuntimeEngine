/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

/** The reviewed provider/model/endpoint selection (`executor.connection`). */
export type Connection = { provider: string; model: string; base_url: string; api: string };
export type CatalogProvider = { id: string; name: string; variable: string; models: string[] };
/** Pi's API-key providers and models from the pinned Pi, plus the two ADORE choices. */
export type ProviderCatalog = {
  pi_version: string; providers: CatalogProvider[];
  chatgpt: { id: "chatgpt" }; custom: { id: "custom"; variable: string; apis: string[] };
};

export const CONNECTION_KEY = "executor.connection";
export const CHATGPT = "chatgpt";
export const CUSTOM = "custom";
export const ENDPOINT_APIS = ["openai-completions", "openai-responses", "anthropic-messages", "google-generative-ai"];
const MODEL_ID = /^[A-Za-z0-9~][A-Za-z0-9._:/@+~-]{0,199}$/;
const VARIABLE = /^[A-Z][A-Z0-9_]{0,63}$/;

export const connectionCopy = {
 en: {provider:"Provider", model:"Model", baseUrl:"Endpoint base URL", api:"Endpoint API type", custom:"OpenAI-compatible endpoint", chatgpt:"ChatGPT subscription", apiKeys:"API-key providers",
  providerHelp:"Pi's provider for this project: one of Pi's API-key providers, a ChatGPT subscription, or an OpenAI-compatible endpoint such as LM Studio, Ollama or vLLM. Changing it is reviewed like other settings.",
  modelHelp:"The model within the provider. Choose from Pi's list or type any model ID the provider accepts.",
  baseUrlHelp:"The endpoint address as seen from the container, for example http://192.168.1.20:1234/v1. localhost is the container itself; host.docker.internal reaches the host only on Docker Desktop.",
  apiHelp:"The API the endpoint speaks; LM Studio, Ollama and vLLM use openai-completions.",
  chatgptNote:"Sign in with ChatGPT is not available yet. Choose an API-key provider or an endpoint to run jobs.",
  keyNote:"The API key is saved below in the project's credential store as {variable}, never in the configuration file.",
  endpointKeyNote:"An endpoint key is optional; when the endpoint needs one, save it below as {variable}.",
  catalogUnavailable:"Pi's model list could not be loaded; type the model ID.", invalid:"Choose a provider, enter one model ID without spaces and, for an endpoint, an http or https address."},
 ro: {provider:"Furnizor", model:"Model", baseUrl:"Adresa de bază a endpointului", api:"Tipul API al endpointului", custom:"Endpoint compatibil OpenAI", chatgpt:"Abonament ChatGPT", apiKeys:"Furnizori cu cheie API",
  providerHelp:"Furnizorul Pi al proiectului: unul dintre furnizorii Pi cu cheie API, un abonament ChatGPT sau un endpoint compatibil OpenAI, de exemplu LM Studio, Ollama sau vLLM. Modificarea se revizuiește ca celelalte setări.",
  modelHelp:"Modelul furnizorului. Alege din lista Pi sau scrie orice ID de model acceptat de furnizor.",
  baseUrlHelp:"Adresa endpointului văzută din container, de exemplu http://192.168.1.20:1234/v1. localhost este containerul însuși; host.docker.internal ajunge la gazdă doar cu Docker Desktop.",
  apiHelp:"API-ul folosit de endpoint; LM Studio, Ollama și vLLM folosesc openai-completions.",
  chatgptNote:"Autentificarea cu ChatGPT nu este încă disponibilă. Alege un furnizor cu cheie API sau un endpoint pentru a rula joburi.",
  keyNote:"Cheia API se salvează mai jos în depozitul de credențiale al proiectului ca {variable}, niciodată în fișierul de configurare.",
  endpointKeyNote:"Cheia endpointului este opțională; dacă endpointul o cere, salveaz-o mai jos ca {variable}.",
  catalogUnavailable:"Lista de modele Pi nu a putut fi încărcată; scrie ID-ul modelului.", invalid:"Alege un furnizor, introdu un ID de model fără spații și, pentru un endpoint, o adresă http sau https."},
 fr: {provider:"Fournisseur", model:"Modèle", baseUrl:"URL de base du point de terminaison", api:"Type d’API du point de terminaison", custom:"Point de terminaison compatible OpenAI", chatgpt:"Abonnement ChatGPT", apiKeys:"Fournisseurs à clé API",
  providerHelp:"Le fournisseur Pi du projet : un fournisseur Pi à clé API, un abonnement ChatGPT ou un point de terminaison compatible OpenAI comme LM Studio, Ollama ou vLLM. Le changement est revu comme les autres paramètres.",
  modelHelp:"Le modèle du fournisseur. Choisissez dans la liste de Pi ou saisissez tout ID de modèle accepté par le fournisseur.",
  baseUrlHelp:"L’adresse du point de terminaison vue depuis le conteneur, par exemple http://192.168.1.20:1234/v1. localhost est le conteneur lui-même ; host.docker.internal n’atteint l’hôte qu’avec Docker Desktop.",
  apiHelp:"L’API du point de terminaison ; LM Studio, Ollama et vLLM utilisent openai-completions.",
  chatgptNote:"La connexion avec ChatGPT n’est pas encore disponible. Choisissez un fournisseur à clé API ou un point de terminaison pour exécuter des tâches.",
  keyNote:"La clé API s’enregistre ci-dessous dans le magasin d’identifiants du projet sous {variable}, jamais dans le fichier de configuration.",
  endpointKeyNote:"Une clé de point de terminaison est facultative ; si nécessaire, enregistrez-la ci-dessous sous {variable}.",
  catalogUnavailable:"La liste des modèles de Pi n’a pas pu être chargée ; saisissez l’ID du modèle.", invalid:"Choisissez un fournisseur, saisissez un ID de modèle sans espace et, pour un point de terminaison, une adresse http ou https."},
 de: {provider:"Anbieter", model:"Modell", baseUrl:"Endpunkt-Basis-URL", api:"Endpunkt-API-Typ", custom:"OpenAI-kompatibler Endpunkt", chatgpt:"ChatGPT-Abonnement", apiKeys:"Anbieter mit API-Schlüssel",
  providerHelp:"Der Pi-Anbieter des Projekts: ein Pi-Anbieter mit API-Schlüssel, ein ChatGPT-Abonnement oder ein OpenAI-kompatibler Endpunkt wie LM Studio, Ollama oder vLLM. Änderungen werden wie andere Einstellungen geprüft.",
  modelHelp:"Das Modell des Anbieters. Wählen Sie aus der Pi-Liste oder geben Sie eine vom Anbieter akzeptierte Modell-ID ein.",
  baseUrlHelp:"Die Endpunkt-Adresse aus Sicht des Containers, z. B. http://192.168.1.20:1234/v1. localhost ist der Container selbst; host.docker.internal erreicht den Host nur mit Docker Desktop.",
  apiHelp:"Die API des Endpunkts; LM Studio, Ollama und vLLM nutzen openai-completions.",
  chatgptNote:"Die Anmeldung mit ChatGPT ist noch nicht verfügbar. Wählen Sie einen Anbieter mit API-Schlüssel oder einen Endpunkt, um Aufträge auszuführen.",
  keyNote:"Der API-Schlüssel wird unten im Zugangsdatenspeicher des Projekts als {variable} gespeichert, nie in der Konfigurationsdatei.",
  endpointKeyNote:"Ein Endpunkt-Schlüssel ist optional; falls nötig, speichern Sie ihn unten als {variable}.",
  catalogUnavailable:"Die Pi-Modellliste konnte nicht geladen werden; geben Sie die Modell-ID ein.", invalid:"Wählen Sie einen Anbieter, geben Sie eine Modell-ID ohne Leerzeichen und für einen Endpunkt eine http- oder https-Adresse ein."},
};

/** An http(s) address with a host and no credentials, query, fragment, quotes or spaces. */
export function validEndpointUrl(value: string): boolean {
  if (value.length > 512 || /[\s"\\?#]/.test(value) || /[\u0000-\u001f\u007f]/.test(value)) return false;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !!url.hostname && !url.username && !url.password;
  } catch { return false; }
}

/** Exact connection transport, mirroring the server rule (provider membership is the server's). */
export function validConnection(value: unknown): value is Connection {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const item = value as Connection;
  if (Object.keys(item).sort().join() !== "api,base_url,model,provider") return false;
  if (![item.provider, item.model, item.base_url, item.api].every(part => typeof part === "string")) return false;
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(item.provider) || !MODEL_ID.test(item.model)) return false;
  return item.provider === CUSTOM ? validEndpointUrl(item.base_url) && ENDPOINT_APIS.includes(item.api)
    : item.base_url === "" && item.api === "";
}

/** The active connection read from a configuration view. */
export function connectionOf(config: Record<string, unknown>): Connection {
  const executor = (config.executor ?? {}) as Record<string, unknown>;
  const endpoint = (executor.endpoint ?? {}) as Record<string, unknown>;
  const custom = executor.provider === CUSTOM;
  return { provider: String(executor.provider ?? ""), model: String(executor.model ?? ""),
    base_url: custom ? String(endpoint.base_url ?? "") : "", api: custom ? String(endpoint.api ?? ENDPOINT_APIS[0]) : "" };
}

/** Closed catalog transport; malformed data is treated as unavailable. */
export function validProviderCatalog(value: unknown): value is ProviderCatalog {
  const item = value as ProviderCatalog;
  return !!item && typeof item.pi_version === "string" && Array.isArray(item.providers)
    && item.providers.every(entry => !!entry && typeof entry.id === "string" && typeof entry.name === "string"
      && VARIABLE.test(entry.variable) && Array.isArray(entry.models) && entry.models.every(model => typeof model === "string"))
    && item.chatgpt?.id === CHATGPT && item.custom?.id === CUSTOM && VARIABLE.test(item.custom.variable)
    && Array.isArray(item.custom.apis);
}

let cached: Promise<ProviderCatalog | null> | null = null;
/** Read the provider catalog once per page; null when it cannot be read. */
export function readProviderCatalog(): Promise<ProviderCatalog | null> {
  cached ??= fetch("/api/v1/pi-providers", { credentials: "same-origin", cache: "no-store" })
    .then(response => response.ok ? response.json() : null)
    .then(value => validProviderCatalog(value) ? value : null)
    .catch(() => null)
    .then(value => { if (value === null) cached = null; return value; });
  return cached;
}

/** The name a provider has in the interface. */
export function providerName(id: string, catalog: ProviderCatalog | null, locale: Locale): string {
  if (id === CUSTOM) return connectionCopy[locale].custom;
  if (id === CHATGPT) return connectionCopy[locale].chatgpt;
  return catalog?.providers.find(item => item.id === id)?.name ?? id;
}

/** The credential variable a provider needs, or null (ChatGPT signs in instead). */
export function providerVariable(id: string, catalog: ProviderCatalog | null): string | null {
  if (id === CUSTOM) return catalog?.custom.variable ?? "ADORE_ENDPOINT_API_KEY";
  return catalog?.providers.find(item => item.id === id)?.variable ?? null;
}

/** The sentence naming where a provider's credential goes. */
export function credentialNote(id: string, catalog: ProviderCatalog | null, locale: Locale): string {
  const copy = connectionCopy[locale];
  if (id === CHATGPT) return copy.chatgptNote;
  const variable = providerVariable(id, catalog);
  if (!variable) return "";
  return (id === CUSTOM ? copy.endpointKeyNote : copy.keyNote).replace("{variable}", variable);
}

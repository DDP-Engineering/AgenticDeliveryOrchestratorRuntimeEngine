/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

/** The server's ChatGPT sign-in as the API reports it. */
export type ChatGptStatus = "signed-in" | "not-signed-in" | "sign-in-again";
export type ChatGptView = { status: ChatGptStatus; pending: boolean };
export type ChatGptStart = { authorize_url: string; expires_in: number };

const STATUSES = ["signed-in", "not-signed-in", "sign-in-again"];

export const chatgptCopy = {
  en: {
    title: "ChatGPT sign-in",
    help: "One ChatGPT Plus or Pro sign-in serves every project on this ADORE server that uses the ChatGPT subscription. It stays on the server; each stage receives only a short-lived access token.",
    status: "Status", "signed-in": "Signed in", "not-signed-in": "Not signed in", "sign-in-again": "Sign in again",
    againHelp: "The stored sign-in can no longer be refreshed. Sign in again; jobs fail until you do.",
    start: "Sign in with ChatGPT", restart: "Sign in again",
    step1: "Open this link on your own computer and sign in with the ChatGPT account:",
    link: "Open the ChatGPT sign-in page",
    step2: "Return here after signing in. Native sign-in may finish automatically. If it stays pending, copy the full redirect address at 127.0.0.1:1455 and paste it here.",
    expires: "The link is valid for 15 minutes.",
    field: "Redirect address", complete: "Complete sign-in", cancel: "Cancel",
    disconnect: "Disconnect ChatGPT", signedIn: "Signed in with ChatGPT.", disconnected: "ChatGPT disconnected.",
    unreadable: "The ChatGPT sign-in could not be read.",
  },
  ro: {
    title: "Autentificare ChatGPT",
    help: "O singură autentificare ChatGPT Plus sau Pro servește toate proiectele de pe acest server ADORE care folosesc abonamentul ChatGPT. Rămâne pe server; fiecare etapă primește doar un token de acces de scurtă durată.",
    status: "Stare", "signed-in": "Autentificat", "not-signed-in": "Neautentificat", "sign-in-again": "Autentifică-te din nou",
    againHelp: "Autentificarea salvată nu mai poate fi reîmprospătată. Autentifică-te din nou; joburile eșuează până atunci.",
    start: "Autentificare cu ChatGPT", restart: "Autentifică-te din nou",
    step1: "Deschide acest link pe calculatorul tău și autentifică-te cu contul ChatGPT:",
    link: "Deschide pagina de autentificare ChatGPT",
    step2: "Revino aici după autentificare. Autentificarea nativă se poate încheia automat. Dacă rămâne în așteptare, copiază adresa completă de redirecționare de la 127.0.0.1:1455 și lipește-o aici.",
    expires: "Linkul este valabil 15 minute.",
    field: "Adresa de redirecționare", complete: "Finalizează autentificarea", cancel: "Anulează",
    disconnect: "Deconectează ChatGPT", signedIn: "Autentificat cu ChatGPT.", disconnected: "ChatGPT a fost deconectat.",
    unreadable: "Autentificarea ChatGPT nu a putut fi citită.",
  },
  fr: {
    title: "Connexion ChatGPT",
    help: "Une seule connexion ChatGPT Plus ou Pro sert tous les projets de ce serveur ADORE qui utilisent l’abonnement ChatGPT. Elle reste sur le serveur ; chaque étape ne reçoit qu’un jeton d’accès de courte durée.",
    status: "État", "signed-in": "Connecté", "not-signed-in": "Non connecté", "sign-in-again": "Reconnectez-vous",
    againHelp: "La connexion enregistrée ne peut plus être renouvelée. Reconnectez-vous ; les tâches échouent d’ici là.",
    start: "Se connecter avec ChatGPT", restart: "Se reconnecter",
    step1: "Ouvrez ce lien sur votre ordinateur et connectez-vous avec le compte ChatGPT :",
    link: "Ouvrir la page de connexion ChatGPT",
    step2: "Revenez ici après la connexion. En natif, elle peut se terminer automatiquement. Sinon, copiez l’adresse complète de redirection à 127.0.0.1:1455 et collez-la ici.",
    expires: "Le lien est valable 15 minutes.",
    field: "Adresse de redirection", complete: "Terminer la connexion", cancel: "Annuler",
    disconnect: "Déconnecter ChatGPT", signedIn: "Connecté avec ChatGPT.", disconnected: "ChatGPT déconnecté.",
    unreadable: "La connexion ChatGPT n’a pas pu être lue.",
  },
  de: {
    title: "ChatGPT-Anmeldung",
    help: "Eine ChatGPT-Plus- oder -Pro-Anmeldung dient allen Projekten dieses ADORE-Servers, die das ChatGPT-Abonnement nutzen. Sie bleibt auf dem Server; jede Phase erhält nur ein kurzlebiges Zugriffstoken.",
    status: "Status", "signed-in": "Angemeldet", "not-signed-in": "Nicht angemeldet", "sign-in-again": "Erneut anmelden",
    againHelp: "Die gespeicherte Anmeldung kann nicht mehr erneuert werden. Melden Sie sich erneut an; bis dahin schlagen Aufträge fehl.",
    start: "Mit ChatGPT anmelden", restart: "Erneut anmelden",
    step1: "Öffnen Sie diesen Link auf Ihrem eigenen Computer und melden Sie sich mit dem ChatGPT-Konto an:",
    link: "ChatGPT-Anmeldeseite öffnen",
    step2: "Kehren Sie nach der Anmeldung hierher zurück. Nativ kann sie automatisch enden. Andernfalls die vollständige Weiterleitungsadresse unter 127.0.0.1:1455 hier einfügen.",
    expires: "Der Link ist 15 Minuten gültig.",
    field: "Weiterleitungsadresse", complete: "Anmeldung abschließen", cancel: "Abbrechen",
    disconnect: "ChatGPT trennen", signedIn: "Mit ChatGPT angemeldet.", disconnected: "ChatGPT getrennt.",
    unreadable: "Die ChatGPT-Anmeldung konnte nicht gelesen werden.",
  },
} satisfies Record<Locale, Record<string, string>>;

/** The exact status transport; anything else is unreadable. */
export function readChatGptView(value: unknown): ChatGptView {
  const item = value as ChatGptView;
  if (!item || typeof item !== "object" || Object.keys(item).sort().join() !== "pending,status"
    || !STATUSES.includes(item.status) || typeof item.pending !== "boolean") throw new Error("invalid ChatGPT status");
  return item;
}

/** The exact start transport: an OpenAI authorization link and its lifetime. */
export function readChatGptStart(value: unknown): ChatGptStart {
  const item = value as ChatGptStart;
  if (!item || typeof item !== "object" || Object.keys(item).sort().join() !== "authorize_url,expires_in"
    || typeof item.authorize_url !== "string" || !item.authorize_url.startsWith("https://auth.openai.com/")
    || item.authorize_url.length > 8192 || !Number.isInteger(item.expires_in) || item.expires_in <= 0) {
    throw new Error("invalid ChatGPT sign-in start");
  }
  return item;
}

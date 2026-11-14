/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

const en = {current:"Current session",newMessages:"New messages",queue:"Queue message",received:"Received by agent",message:"Message to the agent",invalid:"Enter 1–4000 characters without NUL.",session:"Session",open:"Open conversation",event:"Job updated",usage:"Usage recorded",artifacts:"Artifacts saved",observation:"Consumption updated",initial:"Initial prompt",agent:"Agent"};
export const conversationCopy:Record<Locale,typeof en>={
 en,
 fr:{current:"Session actuelle",newMessages:"Nouveaux messages",queue:"Mettre en attente",received:"Reçu par l’agent",message:"Message à l’agent",invalid:"Saisissez 1 à 4000 caractères sans NUL.",session:"Session",open:"Ouvrir la conversation",event:"Travail mis à jour",usage:"Utilisation enregistrée",artifacts:"Artefacts enregistrés",observation:"Consommation actualisée",initial:"Consigne initiale",agent:"Agent"},
 de:{current:"Aktuelle Sitzung",newMessages:"Neue Nachrichten",queue:"Nachricht einreihen",received:"Vom Agenten empfangen",message:"Nachricht an den Agenten",invalid:"1–4000 Zeichen ohne NUL eingeben.",session:"Sitzung",open:"Unterhaltung öffnen",event:"Job aktualisiert",usage:"Nutzung erfasst",artifacts:"Artefakte gespeichert",observation:"Verbrauch aktualisiert",initial:"Ursprüngliche Anweisung",agent:"Agent"},
 ro:{current:"Sesiunea curentă",newMessages:"Mesaje noi",queue:"Pune mesajul în așteptare",received:"Primit de agent",message:"Mesaj pentru agent",invalid:"Introdu 1–4000 de caractere fără NUL.",session:"Sesiune",open:"Deschide conversația",event:"Job actualizat",usage:"Consum înregistrat",artifacts:"Artefacte salvate",observation:"Consum actualizat",initial:"Prompt inițial",agent:"Agent"},
};

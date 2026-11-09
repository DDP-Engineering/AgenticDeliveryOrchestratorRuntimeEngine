/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

const en = {
  identity: "Identity and credentials", access: "Role and project access", review: "Review account",
  next: "Continue to access", correctIdentity: "Correct identity", correctAccess: "Correct access",
  submit: "Create reviewed account", global: "All projects and system administration",
  adminHelp: "Admin can access all current and future projects, system controls and costs.",
  devHelp: "Dev can access only selected projects. Administration and costs remain restricted.",
  emptyChoice: "Create Dev without project access", empty: "No projects: deliberately selected",
  passwordHelp: "At least 8 characters. The password is used only to create the account and is omitted from review.",
  created: "Account created", another: "Create another user", projects: "Project access",
  reviewAccess: "Review access change", before: "Before", after: "After", none: "No projects",
  apply: "Apply reviewed access", applied: "Access updated", pending: "Applying reviewed access…",
  creating: "Creating reviewed account…", loading: "Load project access before continuing.",
};
export type UserCopy = typeof en;
export const userCopy: Record<Locale, UserCopy> = {
  en,
  fr: {
    identity: "Identité et identifiants", access: "Rôle et accès aux projets", review: "Vérifier le compte",
    next: "Continuer vers les accès", correctIdentity: "Corriger l’identité", correctAccess: "Corriger les accès",
    submit: "Créer le compte vérifié", global: "Tous les projets et administration du système",
    adminHelp: "Admin accède aux projets actuels et futurs, aux commandes système et aux coûts.",
    devHelp: "Dev accède seulement aux projets sélectionnés. Administration et coûts restent restreints.",
    emptyChoice: "Créer Dev sans accès aux projets", empty: "Aucun projet : choix délibéré",
    passwordHelp: "Au moins 8 caractères. Le mot de passe sert uniquement à créer le compte et reste absent de la vérification.",
    created: "Compte créé", another: "Créer un autre utilisateur", projects: "Accès aux projets",
    reviewAccess: "Vérifier le changement d’accès", before: "Avant", after: "Après", none: "Aucun projet",
    apply: "Appliquer les accès vérifiés", applied: "Accès mis à jour", pending: "Application des accès vérifiés…",
    creating: "Création du compte vérifié…", loading: "Charger les accès aux projets avant de continuer.",
  },
  de: {
    identity: "Identität und Zugangsdaten", access: "Rolle und Projektzugriff", review: "Konto prüfen",
    next: "Weiter zum Zugriff", correctIdentity: "Identität korrigieren", correctAccess: "Zugriff korrigieren",
    submit: "Geprüftes Konto erstellen", global: "Alle Projekte und Systemverwaltung",
    adminHelp: "Admin hat Zugriff auf aktuelle und zukünftige Projekte, Systemsteuerung und Kosten.",
    devHelp: "Dev hat nur Zugriff auf ausgewählte Projekte. Verwaltung und Kosten bleiben eingeschränkt.",
    emptyChoice: "Dev ohne Projektzugriff erstellen", empty: "Keine Projekte: bewusst ausgewählt",
    passwordHelp: "Mindestens 8 Zeichen. Das Passwort dient nur zur Kontoerstellung und erscheint nicht in der Prüfung.",
    created: "Konto erstellt", another: "Weiteren Benutzer erstellen", projects: "Projektzugriff",
    reviewAccess: "Zugriffsänderung prüfen", before: "Vorher", after: "Nachher", none: "Keine Projekte",
    apply: "Geprüften Zugriff anwenden", applied: "Zugriff aktualisiert", pending: "Geprüfter Zugriff wird angewendet…",
    creating: "Geprüftes Konto wird erstellt…", loading: "Projektzugriff vor dem Fortfahren laden.",
  },
  ro: {
    identity: "Identitate și credențiale", access: "Rol și acces la proiecte", review: "Revizuiește contul",
    next: "Continuă la acces", correctIdentity: "Corectează identitatea", correctAccess: "Corectează accesul",
    submit: "Creează contul revizuit", global: "Toate proiectele și administrarea sistemului",
    adminHelp: "Admin are acces la proiectele curente și viitoare, comenzile sistemului și costuri.",
    devHelp: "Dev are acces numai la proiectele selectate. Administrarea și costurile rămân restricționate.",
    emptyChoice: "Creează Dev fără acces la proiecte", empty: "Niciun proiect: alegere deliberată",
    passwordHelp: "Cel puțin 8 caractere. Parola este folosită numai la creare și nu apare în revizuire.",
    created: "Cont creat", another: "Creează alt utilizator", projects: "Acces la proiecte",
    reviewAccess: "Revizuiește modificarea accesului", before: "Înainte", after: "După", none: "Niciun proiect",
    apply: "Aplică accesul revizuit", applied: "Acces actualizat", pending: "Se aplică accesul revizuit…",
    creating: "Se creează contul revizuit…", loading: "Încarcă accesul la proiecte înainte de a continua.",
  },
};

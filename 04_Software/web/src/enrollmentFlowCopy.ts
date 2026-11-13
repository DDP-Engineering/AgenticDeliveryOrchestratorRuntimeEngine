/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";
const en = {
  subscription: "Uses this server’s ChatGPT sign-in. No API key is needed. You can sign in after creation in Agent and model.",
  environment: "Choose where the agent runs. Shared container images are prepared automatically when you create the project.",
  extras: "Additional credentials (optional)",
  verify: "Check the configuration and server access before creating the project. The agent chooses project tests according to the repository’s instructions.",
  details: "What these checks do",
};
export const enrollmentFlowCopy: Record<Locale, typeof en> = {
  en,
  ro: { subscription: "Folosește autentificarea ChatGPT a acestui server. Nu este necesară o cheie API. Te poți autentifica după creare, în Agent și model.", environment: "Alege unde rulează agentul. Imaginile comune de container se pregătesc automat la crearea proiectului.", extras: "Credențiale suplimentare (opțional)", verify: "Verifică configurația și accesul serverului înainte să creezi proiectul. Agentul alege testele conform instrucțiunilor repository-ului.", details: "Ce fac aceste verificări" },
  fr: { subscription: "Utilise la connexion ChatGPT de ce serveur. Aucune clé API n’est nécessaire. Connectez-vous après la création dans Agent et modèle.", environment: "Choisissez où s’exécute l’agent. Les images de conteneur communes sont préparées automatiquement à la création du projet.", extras: "Identifiants supplémentaires (facultatif)", verify: "Vérifiez la configuration et l’accès du serveur avant de créer le projet. L’agent choisit les tests selon les instructions du dépôt.", details: "Détail des contrôles" },
  de: { subscription: "Verwendet die ChatGPT-Anmeldung dieses Servers. Kein API-Schlüssel erforderlich. Melden Sie sich nach der Erstellung unter Agent und Modell an.", environment: "Wählen Sie den Ausführungsort des Agenten. Gemeinsame Container-Images werden bei der Projekterstellung automatisch vorbereitet.", extras: "Zusätzliche Zugangsdaten (optional)", verify: "Prüfen Sie Konfiguration und Serverzugriff vor der Projekterstellung. Der Agent wählt Tests gemäß den Repository-Anweisungen.", details: "Was diese Prüfungen tun" },
};

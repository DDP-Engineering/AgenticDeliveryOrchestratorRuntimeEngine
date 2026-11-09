/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
// Help center topics, in table-of-contents order; content lives in content/<locale>/<topic>.md.

export const HELP_LOCALES = ["en", "fr", "de", "ro"] as const;
export const HELP_TOPICS = ["overview", "interface", "projects", "settings", "executors", "tickets", "jobs", "statistics", "administration", "glossary"] as const;
export type HelpTopic = typeof HELP_TOPICS[number];

/** Pages that link to their help topic, and the topic each opens. */
export const CONTEXT_TOPICS = { tickets: "tickets", addProject: "projects", projectSettings: "settings" } as const satisfies Record<string, HelpTopic>;

export const isHelpTopic = (value: string): value is HelpTopic => (HELP_TOPICS as readonly string[]).includes(value);

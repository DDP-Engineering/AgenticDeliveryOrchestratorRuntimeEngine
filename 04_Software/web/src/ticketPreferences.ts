/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { ApiError } from "./errors.ts";
import type { Locale } from "./i18n.ts";

export type TicketBodyMode = "rendered" | "source";
export type Preferences = { language: Locale | null; theme: "light" | "dark" | "system" | null; ticket_body_mode: TicketBodyMode | null };

/** Refuse malformed account responses; null alone represents an unsaved preference. */
export function readPreferences(value: unknown): Preferences {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new ApiError("unexpected_response");
  const saved = value as Preferences;
  if (!(saved.language === null || ["en", "fr", "de", "ro"].includes(saved.language)) ||
    !(saved.theme === null || ["light", "dark", "system"].includes(saved.theme)) ||
    !(saved.ticket_body_mode === null || saved.ticket_body_mode === "rendered" || saved.ticket_body_mode === "source")) {
    throw new ApiError("unexpected_response");
  }
  return { language: saved.language, theme: saved.theme, ticket_body_mode: saved.ticket_body_mode };
}

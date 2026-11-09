/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
/// <reference types="vite/client" />
// Bundled help documents (Vite inlines the Markdown at build time), parsed once per locale and topic.
import { parseHelp, type HelpDoc } from "./markdown.ts";
import { HELP_LOCALES, type HelpTopic } from "./topics.ts";

const files = import.meta.glob("./content/*/*.md", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const parsed = new Map<string, HelpDoc>();

/** The topic in the user's language, falling back to English. */
export function helpDoc(locale: string, topic: HelpTopic): HelpDoc {
  const language = (HELP_LOCALES as readonly string[]).includes(locale) && files[`./content/${locale}/${topic}.md`] ? locale : "en";
  const key = `./content/${language}/${topic}.md`;
  let doc = parsed.get(key);
  if (!doc) { doc = parseHelp(files[key] ?? `# ${topic}`); parsed.set(key, doc); }
  return doc;
}

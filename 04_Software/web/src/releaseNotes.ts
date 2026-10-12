/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
// Release notes served by /api/v1/about for the What's new window.

export type ReleaseCategory = "new" | "improved" | "fixed";
export type LocalTexts = Partial<Record<string, string>>;
export type ReleaseEntry = { category: ReleaseCategory; topic: LocalTexts; text: LocalTexts };
export type Release = { version: string; date: string | null; entries: ReleaseEntry[] };
export type ReleaseGroup = { category: ReleaseCategory; topics: Array<{ topic: string; texts: string[] }> };

export const releaseCategories: ReleaseCategory[] = ["new", "improved", "fixed"];

/** The text in the user's language, or English when that locale is missing or empty. */
export function localText(texts: LocalTexts, locale: string): string {
  return texts[locale]?.trim() || texts.en || "";
}

/** One release's notes grouped New, Improved, Fixed, with topics in first-appearance order. */
export function groupRelease(release: Release, locale: string): ReleaseGroup[] {
  return releaseCategories.flatMap(category => {
    const topics: ReleaseGroup["topics"] = [];
    for (const entry of release.entries.filter(item => item.category === category)) {
      const topic = localText(entry.topic, locale);
      const group = topics.find(item => item.topic === topic) ?? topics[topics.push({ topic, texts: [] }) - 1];
      group.texts.push(localText(entry.text, locale));
    }
    return topics.length ? [{ category, topics }] : [];
  });
}

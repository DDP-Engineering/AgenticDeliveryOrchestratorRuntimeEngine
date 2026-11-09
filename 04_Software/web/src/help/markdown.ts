/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
// Parser for the help Markdown subset (see help/README.md). It never produces HTML: the help
// page renders the blocks as React elements. Anything outside the subset is shown as plain text
// at runtime (links only to safe in-app targets), while `issues` lets the tests reject it.

export type Inline = { type: "text" | "strong" | "code"; text: string } | { type: "link"; text: string; href: string };
export type HelpBlock =
  | { type: "heading"; level: 2 | 3; id: string; text: string }
  | { type: "paragraph"; inline: Inline[] }
  | { type: "list"; ordered: boolean; items: Inline[][] }
  | { type: "table"; header: Inline[][]; rows: Inline[][][] }
  | { type: "note"; inline: Inline[] }
  | { type: "code"; text: string };
export type HelpDoc = { title: string; blocks: HelpBlock[]; issues: string[] };

const HEADING = /^(#{2,3}) (.+?) \{#([a-z0-9]+(?:-[a-z0-9]+)*)\}$/;
const INLINE = /\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)/;
const BLOCK_START = /^(#|- |\d+\. |\||> ?|```)/;
/** In-app targets only: an absolute path (never `//host`), optional query, optional `#id`, or a bare `#id`. */
const SAFE_LINK = /^(?:\/(?!\/)[A-Za-z0-9/_.-]*(?:\?[A-Za-z0-9=&_.-]*)?)?(?:#[a-z0-9]+(?:-[a-z0-9]+)*)?$/;

function inline(text: string, issues: string[]): Inline[] {
  const out: Inline[] = [];
  let rest = text;
  while (rest) {
    const match = INLINE.exec(rest);
    const plain = match ? rest.slice(0, match.index) : rest;
    if (plain) {
      if (/\*\*|`/.test(plain)) issues.push(`unmatched bold or code marker in: ${text}`);
      out.push({ type: "text", text: plain });
    }
    if (!match) break;
    if (match[1] !== undefined) {
      if (/`|\]\(/.test(match[1])) issues.push(`bold text cannot contain code or links: ${match[0]}`);
      out.push({ type: "strong", text: match[1] });
    } else if (match[2] !== undefined) out.push({ type: "code", text: match[2] });
    else if (match[4] && SAFE_LINK.test(match[4])) out.push({ type: "link", text: match[3], href: match[4] });
    else { issues.push(`link target must be an in-app address: ${match[4]}`); out.push({ type: "text", text: match[3] }); }
    rest = rest.slice(match.index + match[0].length);
  }
  return out;
}

const cells = (line: string) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(cell => cell.trim());

/** Parse one help document; `issues` lists every construct outside the subset. */
export function parseHelp(source: string): HelpDoc {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const issues: string[] = [];
  const blocks: HelpBlock[] = [];
  const ids = new Set<string>();
  const title = /^# (.+)$/.exec(lines[0] ?? "")?.[1].trim() ?? "";
  if (!title) issues.push("line 1 must be the title: # Title");
  let index = title ? 1 : 0;
  // HTML and images are rejected on every line outside code blocks, not only on block starts.
  let fenced = false;
  lines.forEach((line, number) => {
    if (line.startsWith("```")) { fenced = !fenced; return; }
    if (fenced) return;
    if (/<\/?[a-zA-Z][^>]*>/.test(line)) issues.push(`raw HTML is not supported (line ${number + 1}): ${line}`);
    if (line.includes("![")) issues.push(`images are not supported (line ${number + 1}): ${line}`);
  });
  const take = (test: (line: string) => boolean) => {
    const taken: string[] = [];
    while (index < lines.length && test(lines[index])) taken.push(lines[index++]);
    return taken;
  };
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }
    if (line.startsWith("```")) {
      index += 1;
      const body = take(item => !item.startsWith("```"));
      if (index >= lines.length) issues.push("unterminated code block");
      index += 1;
      blocks.push({ type: "code", text: body.join("\n") });
      continue;
    }
    if (line.startsWith("#")) {
      index += 1;
      const heading = HEADING.exec(line.trimEnd());
      const asText = () => blocks.push({ type: "paragraph", inline: inline(line.replace(/^#+\s*/, ""), issues) });
      if (/^#{4,} /.test(line) || /^# /.test(line)) { issues.push(`unsupported heading level: ${line}`); asText(); continue; }
      if (!heading) { issues.push(`heading needs an explicit {#id}: ${line}`); asText(); continue; }
      if (/\*\*|`|\]\(/.test(heading[2])) issues.push(`headings are plain text: ${line}`);
      if (ids.has(heading[3])) issues.push(`duplicate heading id: ${heading[3]}`);
      ids.add(heading[3]);
      blocks.push({ type: "heading", level: heading[1].length as 2 | 3, id: heading[3], text: heading[2].trim() });
      continue;
    }
    if (/^\s+(- |\d+\. )/.test(line)) {
      issues.push(`nested lists are not supported: ${line}`);
      blocks.push({ type: "paragraph", inline: inline(line.trim(), issues) });
      index += 1; continue;
    }
    if (line.startsWith("- ") || /^\d+\. /.test(line)) {
      const ordered = !line.startsWith("- ");
      const items = take(item => ordered ? /^\d+\. /.test(item) : item.startsWith("- "));
      blocks.push({ type: "list", ordered, items: items.map(item => inline(item.replace(/^(- |\d+\. )/, ""), issues)) });
      continue;
    }
    if (line.startsWith("|")) {
      const rows = take(item => item.startsWith("|")).map(cells);
      const width = rows[0].length;
      if (rows.length < 2 || !rows[1].every(cell => /^:?-{3,}:?$/.test(cell))) issues.push("a table needs a header row and a |---| separator");
      rows.forEach((row, number) => { if (row.length !== width) issues.push(`table row ${number + 1} has ${row.length} cells, expected ${width}`); });
      blocks.push({ type: "table", header: rows[0].map(cell => inline(cell, issues)), rows: rows.slice(2).map(row => row.map(cell => inline(cell, issues))) });
      continue;
    }
    if (/^> ?/.test(line)) {
      blocks.push({ type: "note", inline: inline(take(item => /^> ?/.test(item)).map(item => item.replace(/^> ?/, "")).join(" "), issues) });
      continue;
    }
    const paragraph = [line, ...(index += 1, take(item => !!item.trim() && !BLOCK_START.test(item) && !/^\s+(- |\d+\. )/.test(item)))];
    blocks.push({ type: "paragraph", inline: inline(paragraph.map(item => item.trim()).join(" "), issues) });
  }
  return { title, blocks, issues };
}

/** The `##` and `###` sections, for the outline and for link checks. */
export const helpOutline = (doc: HelpDoc) => doc.blocks.flatMap(block => block.type === "heading" ? [{ level: block.level, id: block.id, text: block.text }] : []);

const inlines = (block: HelpBlock): Inline[] => block.type === "paragraph" || block.type === "note" ? block.inline :
  block.type === "list" ? block.items.flat() : block.type === "table" ? [...block.header.flat(), ...block.rows.flat(2)] : [];

/** Every link target in document order. */
export const helpLinks = (doc: HelpDoc) => doc.blocks.flatMap(inlines).flatMap(item => item.type === "link" ? [item.href] : []);

const fold = (text: string) => text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const plain = (doc: HelpDoc) => [doc.title, ...doc.blocks.map(block => block.type === "heading" || block.type === "code" ? block.text :
  inlines(block).map(item => item.text).join(" "))].join(" ");

/** Topics whose title or text contains the query, ignoring case and accents; all topics for a blank query. */
export function searchHelp<T extends string>(entries: Array<{ topic: T; doc: HelpDoc }>, query: string): T[] {
  const wanted = fold(query.trim());
  return entries.filter(entry => !wanted || fold(plain(entry.doc)).includes(wanted)).map(entry => entry.topic);
}

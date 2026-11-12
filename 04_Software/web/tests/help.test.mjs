/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { helpLinks, helpOutline, parseHelp, searchHelp } from "../src/help/markdown.ts";
import { CONTEXT_TOPICS, HELP_LOCALES, HELP_TOPICS } from "../src/help/topics.ts";
import { parseRoute } from "../src/routes.ts";

const root = new URL("../src/help/content/", import.meta.url);
const read = (locale, topic) => readFileSync(new URL(`${locale}/${topic}.md`, root), "utf8");
let parsed;
const docs = () => parsed ??= Object.fromEntries(HELP_LOCALES.map(locale => [locale, Object.fromEntries(HELP_TOPICS.map(topic => [topic, parseHelp(read(locale, topic))]))]));

test("the parser reads the supported subset into blocks with explicit heading ids", () => {
  const doc = parseHelp([
    "# Sample", "", "Intro with **bold**, `code` and [a link](/help/jobs#stages).", "",
    "## First part {#first}", "", "- one", "- two", "", "1. step", "2. next", "",
    "| A | B |", "|---|---|", "| x | [y](#first) |", "", "> A note.", "", "### Detail {#detail}", "", "```", "raw | text", "```",
  ].join("\n"));
  assert.deepEqual(doc.issues, []);
  assert.equal(doc.title, "Sample");
  assert.deepEqual(doc.blocks.map(block => block.type), ["paragraph", "heading", "list", "list", "table", "note", "heading", "code"]);
  assert.deepEqual(doc.blocks[0].inline, [{ type: "text", text: "Intro with " }, { type: "strong", text: "bold" },
    { type: "text", text: ", " }, { type: "code", text: "code" }, { type: "text", text: " and " },
    { type: "link", text: "a link", href: "/help/jobs#stages" }, { type: "text", text: "." }]);
  assert.deepEqual(helpOutline(doc), [{ level: 2, id: "first", text: "First part" }, { level: 3, id: "detail", text: "Detail" }]);
  assert.deepEqual(helpLinks(doc), ["/help/jobs#stages", "#first"]);
  assert.equal(doc.blocks[7].text, "raw | text");
});

test("the parser reports constructs outside the subset", () => {
  const issues = text => parseHelp(text).issues.join("\n");
  assert.match(issues("No title"), /title/);
  assert.match(issues("# T\n\n## Missing id"), /id/);
  assert.match(issues("# T\n\n## A {#a}\n\n## B {#a}"), /duplicate/);
  assert.match(issues("# T\n\n#### Deep {#d}"), /heading level/);
  assert.match(issues("# T\n\n<div>html</div>"), /HTML/);
  assert.match(issues("# T\n\n![image](/x.png)"), /image/);
  assert.match(issues("# T\n\n- a\n  - nested"), /nested/);
  assert.match(issues("# T\n\n| A | B |\n|---|---|\n| one |"), /cells/);
  assert.match(issues("# T\n\n```\nopen"), /code block/);
  assert.match(issues("# T\n\nHalf **bold"), /unmatched/);
  // Continuation lines are checked too, and links stay inside the app.
  assert.match(issues("# T\n\nText line\n<div>x</div>"), /HTML/);
  assert.match(issues("# T\n\n- ok\n- ![img](/x.png)"), /image/);
  assert.match(issues("# T\n\n[x](//evil.invalid)"), /in-app/);
  assert.match(issues("# T\n\n[x](javascript:alert(1))"), /in-app/);
  assert.match(issues("# T\n\n**see [x](/help/jobs)**"), /bold/);
  assert.match(issues("# T\n\n## A **b** {#a}"), /plain text/);
  assert.deepEqual(parseHelp("# T\n\n```\n<div>kept</div>\n```").issues, []);
  assert.deepEqual(parseHelp("# T\n\n[x](javascript:void)").blocks[0].inline, [{ type: "text", text: "x" }]);
});

test("every topic exists in every locale and nothing else is shipped", () => {
  for (const locale of HELP_LOCALES) {
    assert.deepEqual(readdirSync(new URL(`${locale}/`, root)).sort(), HELP_TOPICS.map(topic => `${topic}.md`).sort(), locale);
  }
  assert.deepEqual(readdirSync(root).sort(), [...HELP_LOCALES].sort());
});

test("every topic uses only the subset and keeps a short title", () => {
  for (const locale of HELP_LOCALES) for (const topic of HELP_TOPICS) {
    const doc = docs()[locale][topic];
    assert.deepEqual(doc.issues, [], `${locale}/${topic}`);
    assert.ok(doc.title.length > 0 && doc.title.length <= 40, `${locale}/${topic} title`);
    assert.ok(helpOutline(doc).some(item => item.level === 2), `${locale}/${topic} sections`);
  }
});

test("translations keep the English outline, tables, lists, notes and link targets", () => {
  const shape = doc => doc.blocks.map(block => block.type === "heading" ? `h${block.level}#${block.id}` :
    block.type === "table" ? `table${block.header.length}x${block.rows.length}` :
    block.type === "list" ? `${block.ordered ? "ol" : "ul"}${block.items.length}` : block.type === "paragraph" ? "p" : block.type);
  for (const topic of HELP_TOPICS) {
    const english = docs().en[topic];
    for (const locale of HELP_LOCALES.filter(item => item !== "en")) {
      const other = docs()[locale][topic];
      assert.deepEqual(shape(other).filter(item => item !== "p"), shape(english).filter(item => item !== "p"), `${locale}/${topic} structure`);
      assert.deepEqual([...helpLinks(other)].sort(), [...helpLinks(english)].sort(), `${locale}/${topic} links`);
    }
  }
});

test("links point to existing topics, sections or interface addresses", () => {
  const ids = topic => new Set(helpOutline(docs().en[topic]).map(item => item.id));
  for (const locale of HELP_LOCALES) for (const topic of HELP_TOPICS) for (const href of helpLinks(docs()[locale][topic])) {
    const where = `${locale}/${topic} -> ${href}`;
    assert.ok(!/^[a-z]+:/i.test(href) && !href.startsWith("//"), `${where}: external`);
    const [path, anchor] = href.split("#");
    if (path === "") { assert.ok(ids(topic).has(anchor), `${where}: section`); continue; }
    const help = /^\/help\/([a-z]+)$/.exec(path);
    if (help) {
      assert.ok(HELP_TOPICS.includes(help[1]), `${where}: topic`);
      if (anchor !== undefined) assert.ok(ids(help[1]).has(anchor), `${where}: section`);
      continue;
    }
    const url = new URL(path, "http://localhost");
    assert.notEqual(parseRoute(url.pathname, url.search), null, `${where}: route`);
    assert.equal(anchor, undefined, `${where}: interface addresses take no section`);
  }
});

test("tickets explain shared body modes, exact source, account retention and inert images in every locale", async () => {
  const { ticketCopy } = await import("../src/ticketCopy.ts");
  for (const locale of HELP_LOCALES) {
    const text = read(locale, "tickets");
    assert.ok(helpOutline(docs()[locale].tickets).some(item => item.id === "reading-bodies"), `${locale} reading bodies section`);
    for (const key of ["bodyDisplay", "rendered", "markdownSource", "imageNotLoaded"]) assert.ok(text.includes(ticketCopy[locale][key]), `${locale}: ${key}`);
    assert.match(text, /http.*https.*mailto/i);
  }
});

test("help explains both workflows and exact optional verification in every locale", async () => {
  const { messages } = await import("../src/i18n.ts");
  const { workflowCopy } = await import("../src/readiness.ts");
  const terms = { en: "Direct workflow", fr: "Workflow direct", de: "Direkter Workflow", ro: "Flux direct" };
  for (const locale of HELP_LOCALES) {
    const projects = read(locale, "projects"), settings = read(locale, "settings");
    const glossary = read(locale, "glossary"), tickets = read(locale, "tickets");
    const command = messages[locale].verificationCommand;
    for (const text of [projects, settings, glossary]) assert.ok(text.includes(command), `${locale}: command label`);
    for (const value of [workflowCopy[locale].aegis, workflowCopy[locale].direct]) assert.ok(projects.includes(value), `${locale}: ${value}`);
    assert.ok(helpOutline(docs()[locale].projects).some(item => item.id === "workflows"), `${locale}: workflows section`);
    assert.ok(helpOutline(docs()[locale].settings).some(item => item.id === "verification-command"), `${locale}: command section`);
    assert.ok(glossary.includes(`| ${terms[locale]} |`), `${locale}: direct glossary term`);
    assert.ok(glossary.includes(`| ${command} |`), `${locale}: command glossary term`);
    assert.ok(tickets.includes(".agentic/aegis.py"), `${locale}: live file presence gate`);
    assert.ok(helpLinks(docs()[locale].tickets).includes("/help/projects#workflows"), `${locale}: workflow guidance link`);
    for (const text of [projects, settings, glossary, tickets]) {
      assert.doesNotMatch(text, /Install AEGIS|AEGIS installed|aegis_missing|AEGIS install[ée]|AEGIS, installiert|AEGIS instalat/i);
      assert.doesNotMatch(text, /(?:suggested|pre-filled|prefilled) verification command/i);
    }
  }
});

test("contextual help targets existing topics", () => {
  for (const [place, topic] of Object.entries(CONTEXT_TOPICS)) assert.ok(HELP_TOPICS.includes(topic), place);
  assert.deepEqual(CONTEXT_TOPICS, { tickets: "tickets", addProject: "projects", projectSettings: "settings" });
});

test("the glossary keeps the delivery terms and human boundaries", () => {
  const text = read("en", "glossary");
  for (const term of ["Job", "Enrolled project", "Pickup stopped", "Waiting for clarification", "Waiting for approval", "Human review"]) {
    assert.ok(text.includes(term), term);
  }
  assert.match(text, /does not pause an active job/);
  assert.match(text, /recorded on the forge/);
  assert.match(text, /human decision/);
  for (const locale of HELP_LOCALES) assert.ok(docs()[locale].glossary.blocks.some(block => block.type === "table" && block.rows.length >= 12), locale);
});

test("help names settings as the localized interface shows them", async () => {
  const { localizedSettingLabel } = await import("../src/settingsCopy.ts");
  const keys = ["readiness.require_priority_label", "readiness.require_acceptance_criteria", "delivery.remove_source_branch",
    "metrics.enabled", "metrics.capture_tokens", "review.max_review_rounds"];
  for (const locale of ["fr", "de", "ro"]) {
    const text = HELP_TOPICS.map(topic => read(locale, topic)).join("\n");
    for (const key of keys) {
      const label = localizedSettingLabel(key, locale);
      assert.ok(label, `${locale}: ${key}`);
      assert.ok(text.includes(`**${label}**`), `${locale}: help names ${key} as "${label}"`);
    }
  }
  assert.equal(localizedSettingLabel("metrics.enabled", "en"), undefined);
});

test("search matches titles and text regardless of case and accents", () => {
  const english = HELP_TOPICS.map(topic => ({ topic, doc: docs().en[topic] }));
  assert.ok(searchHelp(english, "LABELS").includes("tickets"));
  assert.deepEqual(searchHelp(english, "zzzz-no-such-word"), []);
  assert.deepEqual(searchHelp(english, "  "), HELP_TOPICS);
  const romanian = HELP_TOPICS.map(topic => ({ topic, doc: docs().ro[topic] }));
  assert.ok(searchHelp(romanian, "eticheta").includes("tickets") || searchHelp(romanian, "etichete").includes("tickets"), "accent-insensitive");
});

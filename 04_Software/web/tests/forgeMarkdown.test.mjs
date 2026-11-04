/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const moduleUrl = new URL("../src/forgeMarkdown.ts", import.meta.url);
const renderer = existsSync(moduleUrl) ? await import(moduleUrl.href) : null;
const render = source => renderToStaticMarkup(createElement(renderer.ForgeMarkdown, {
  source, imageLabel: "Image not loaded", codeLabel: "Code", tableLabel: "Table",
}));
const options = { skip: renderer === null };

test("a public React forge Markdown renderer is available", () => {
  assert.equal(typeof renderer?.ForgeMarkdown, "function", "forge bodies still have no rich-text renderer");
});

test("renders the requested semantic GFM subset with nested and immutable task lists", options, () => {
  const html = render([
    "# Heading", "", "Paragraph **bold** and *italic*, `inline`.", "",
    "```js", "const value = '<tag>';", "```", "",
    "1. first", "2. second", "   - nested", "     - deeper", "",
    "- [ ] pending", "- [x] done", "", "> quoted", "",
    "| Left | Right |", "| --- | --- |", "| cell | value |", "", "---",
  ].join("\n"));
  for (const tag of ["h1", "p", "strong", "em", "code", "pre", "ol", "ul", "li", "blockquote", "table", "thead", "tbody", "th", "td", "hr"]) {
    assert.match(html, new RegExp(`<${tag}(?:[ />])`), tag);
  }
  assert.match(html, /<ul>[\s\S]*nested[\s\S]*<ul>[\s\S]*deeper/);
  assert.equal((html.match(/type="checkbox"/g) ?? []).length, 2);
  for (const input of html.match(/<input[^>]*>/g) ?? []) assert.match(input, /disabled=""/);
  assert.match(html, /checked=""/);
  assert.match(html, /const value = &#x27;&lt;tag&gt;&#x27;;/);
});

test("incomplete syntax and unsupported constructs remain readable and inert", options, () => {
  assert.match(render("unmatched **emphasis"), /unmatched \*\*emphasis/);
  assert.match(render("```\nunclosed <tag>"), /<pre[\s\S]*unclosed &lt;tag&gt;/);
  assert.match(render("::: unknown\nbody\n:::"), /::: unknown[\s\S]*body/);
});

test("raw HTML is visible text rather than an element or execution pipeline", options, () => {
  for (const source of [
    '<script>globalThis.forgeSentinel = true</script>',
    '<img src="https://tracker.invalid/pixel" onerror="alert(1)">',
    '<b onclick="alert(1)">raw</b>',
    '<iframe src="https://tracker.invalid/frame"></iframe>',
    '<div>\nraw block\n</div>',
    'inline <span>raw</span> HTML',
    '<style>body { background: url(https://tracker.invalid/x) }</style>',
  ]) {
    const html = render(source);
    const escaped = renderToStaticMarkup(createElement("span", null, source)).slice(6, -7);
    assert.ok(html.includes(escaped), `raw HTML must remain visible verbatim: ${source}`);
    assert.doesNotMatch(html, /<(?:script|img|b|iframe|div|span|style)\b[^>]*(?:src|onclick|onerror)|<script\b|<iframe\b|<style\b/);
    assert.equal(globalThis.forgeSentinel, undefined);
  }
  for (const path of [moduleUrl, new URL("../src/TicketWorkspace.tsx", import.meta.url)]) {
    assert.doesNotMatch(readFileSync(path, "utf8"), /dangerouslySetInnerHTML|rehype-raw|innerHTML\s*=/);
  }
});

test("safe inline and reference links are user-activated protected anchors", options, () => {
  for (const destination of ["http://example.invalid/a", "https://example.invalid/a?q=x&b=y", "mailto:reader@example.invalid", "HTTPS://example.invalid/a"]) {
    for (const source of [`[label](${destination} "Title")`, `[label][ref]\n\n[ref]: ${destination} "Title"`]) {
      const html = render(source);
      assert.match(html, /<a /);
      assert.match(html, /target="_blank"/);
      assert.match(html, /rel="noopener noreferrer"/);
      assert.match(html, /title="Title"/);
      assert.match(html, />label<\/a>/);
      assert.match(html, /href="(?:http|https|mailto)/i);
      assert.doesNotMatch(html, /<(?:img|iframe|script|link|video|audio|source)\b/);
    }
  }
});

test("unsafe, relative, malformed and obfuscated links have readable labels but no anchors", options, () => {
  for (const destination of [
    "javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,evil", "vbscript:evil", "file:///secret",
    "//evil.invalid/x", "/relative", "../relative", "#anchor", "https://", "http:///", "https:example.invalid",
    "javascript&#58;alert(1)", "jav&#x61;script:evil", "java&#x09;script:evil", "%6aavascript:evil",
    "https%3A%2F%2Fevil.invalid", "java&#x00;script:evil", "https&#x0a;://evil.invalid", "java%09script:evil",
  ]) {
    const html = render(`[label](${destination})`);
    assert.match(html, /label/);
    assert.doesNotMatch(html, /<a\b/, destination);
  }
  assert.match(render("[control](https://example.invalid)"), /<a\b/);
});

test("inline and reference images always become localized inert placeholders", options, () => {
  for (const destination of ["https://tracker.invalid/pixel", "/local.png", "javascript:evil", "data:image/png;base64,AAAA"]) {
    for (const source of [`![alternative](${destination})`, `![alternative][ref]\n\n[ref]: ${destination}`, `![](${destination})`]) {
      const html = render(source);
      assert.match(html, /Image not loaded/);
      if (source.includes("alternative")) assert.match(html, /alternative/);
      assert.doesNotMatch(html, /<(?:img|iframe|script|link|video|audio|source|a)\b|\bsrc=|\bsrcset=|url\(/);
      assert.doesNotMatch(html, /tracker\.invalid/);
    }
  }
});

test("forged image alternative text and link labels cannot inject attributes or elements", options, () => {
  const html = render('![<img onerror="evil">](https://tracker.invalid) [<script>evil</script>](https://example.invalid)');
  assert.match(html, /Image not loaded: &lt;img onerror=&quot;evil&quot;&gt;/);
  assert.match(html, /&lt;script&gt;evil&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<(?:img|script)\b|<[^>]*\sonerror=/);
});

test("wide code and tables expose named keyboard-focusable local scroll regions", options, () => {
  const html = render("```\nwide\n```\n\n| A | B |\n|---|---|\n| a | b |");
  assert.match(html, /role="region"[^>]*aria-label="Code"[^>]*tabindex="0"/);
  assert.match(html, /role="region"[^>]*aria-label="Table"[^>]*tabindex="0"/);
});

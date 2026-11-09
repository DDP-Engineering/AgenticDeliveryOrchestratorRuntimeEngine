/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { messages, type Locale } from "./i18n";
import { helpDoc } from "./help/content.ts";
import { helpOutline, searchHelp, type HelpBlock, type Inline } from "./help/markdown.ts";
import { HELP_TOPICS, type HelpTopic } from "./help/topics.ts";

/** A plain left click that the single-page app should handle itself. */
const ownClick = (event: MouseEvent) => event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;

/** Help center: table of contents with search, the topic article and its outline. */
export function HelpCenter({ locale, topic = "overview", onNavigate }: { locale: Locale; topic?: HelpTopic; onNavigate: (href: string) => void }) {
  const t = messages[locale];
  const [query, setQuery] = useState("");
  const [anchor, setAnchor] = useState("");
  const entries = useMemo(() => HELP_TOPICS.map(item => ({ topic: item, doc: helpDoc(locale, item) })), [locale]);
  const shown = searchHelp(entries, query);
  const doc = helpDoc(locale, topic);
  const outline = helpOutline(doc).filter(item => item.level === 2);
  const heading = useRef<HTMLHeadingElement>(null);
  const shownTopic = useRef(topic);
  // After the app has updated the address (next frame): scroll to a section named by the address
  // or by a link into another topic, otherwise announce a newly opened topic by focusing its title.
  useEffect(() => {
    const changed = shownTopic.current !== topic;
    shownTopic.current = topic;
    const frame = window.requestAnimationFrame(() => {
      const id = anchor || window.location.hash.slice(1);
      if (id) {
        document.getElementById(id)?.scrollIntoView();
        if (anchor) { window.history.replaceState(null, "", `/help/${topic}#${id}`); setAnchor(""); }
      } else if (changed) heading.current?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [topic, anchor]);
  // Scrollable tables and code blocks are named after the section that holds them.
  const sections = doc.blocks.reduce<string[]>((names, item) => [...names, item.type === "heading" ? item.text : names.at(-1) ?? doc.title], []);
  const follow = (href: string) => (event: MouseEvent) => {
    if (href.startsWith("#") || !ownClick(event)) return;
    event.preventDefault();
    const [path, id] = href.split("#");
    onNavigate(path);
    if (id) setAnchor(id); else window.scrollTo(0, 0);
  };
  const inline = (items: Inline[]) => items.map((item, index): ReactNode =>
    item.type === "strong" ? <strong key={index}>{item.text}</strong> :
    item.type === "code" ? <code key={index}>{item.text}</code> :
    item.type === "link" ? <a key={index} href={item.href} onClick={follow(item.href)}>{item.text}</a> : item.text);
  const block = (item: HelpBlock, index: number): ReactNode => {
    switch (item.type) {
      case "heading": return item.level === 2 ? <h3 key={index} id={item.id}>{item.text}</h3> : <h4 key={index} id={item.id}>{item.text}</h4>;
      case "paragraph": return <p key={index}>{inline(item.inline)}</p>;
      case "note": return <p key={index} className="help-note">{inline(item.inline)}</p>;
      case "code": return <pre key={index} tabIndex={0} role="region" aria-label={sections[index]}><code>{item.text}</code></pre>;
      case "list": { const items = item.items.map((entry, number) => <li key={number}>{inline(entry)}</li>);
        return item.ordered ? <ol key={index}>{items}</ol> : <ul key={index}>{items}</ul>; }
      case "table": return <div key={index} className="table-wrap" tabIndex={0} role="region" aria-label={sections[index]}><table>
        <thead><tr>{item.header.map((cell, number) => <th key={number} scope="col">{inline(cell)}</th>)}</tr></thead>
        <tbody>{item.rows.map((row, number) => <tr key={number}>{row.map((cell, column) => <td key={column}>{inline(cell)}</td>)}</tr>)}</tbody>
      </table></div>;
    }
  };
  return <div className="help-layout">
    <aside className="panel help-sidebar">
      <input type="search" aria-label={t.searchHelp} placeholder={t.searchHelp} value={query} onChange={event => setQuery(event.target.value)} />
      <nav aria-label={t.helpTopics}>
        {shown.length ? <ul>{shown.map(item => <li key={item}>
          <a href={`/help/${item}`} aria-current={item === topic ? "page" : undefined} onClick={follow(`/help/${item}`)}>{helpDoc(locale, item).title}</a>
        </li>)}</ul> : <p className="muted">{t.helpNoMatch}</p>}
      </nav>
    </aside>
    <article className="panel help-article">
      <h2 className="help-title" ref={heading} tabIndex={-1}>{doc.title}</h2>
      {outline.length > 1 && <nav className="help-outline" aria-label={t.onThisPage}><strong>{t.onThisPage}</strong>
        <ul>{outline.map(item => <li key={item.id}><a href={`#${item.id}`}>{item.text}</a></li>)}</ul></nav>}
      {doc.blocks.map(block)}
    </article>
  </div>;
}

/** Small "?" link that opens a help topic in a new tab, so the current page and its input stay put. */
export function HelpLink({ topic, locale }: { topic: HelpTopic; locale: Locale }) {
  const label = messages[locale].helpFor.replace("{topic}", helpDoc(locale, topic).title);
  // Named by its (visually hidden) text, not aria-label, so form-field label lookups never match it.
  return <a className="help-link" href={`/help/${topic}`} target="_blank" rel="noopener" title={label}><span aria-hidden="true">?</span><span className="visually-hidden">{label}</span></a>;
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { createElement } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Closed navigation boundary; do not resolve forge-relative URLs against the app. */
function safeDestination(destination: string): string {
  if (/[\s\u0000-\u001f\u007f-\u009f]/u.test(destination)
      || !/^(?:https?:\/\/|mailto:)/i.test(destination)) return "";
  try {
    const url = new URL(destination);
    if ((url.protocol === "http:" || url.protocol === "https:") && url.hostname) return destination;
    if (url.protocol === "mailto:" && url.pathname) return destination;
  } catch { /* Invalid destinations remain readable but non-navigable. */ }
  return "";
}

export type ForgeMarkdownProps = {
  source: string;
  imageLabel: string;
  codeLabel: string;
  tableLabel: string;
};

/**
 * Render untrusted forge Markdown as React elements only. Raw HTML remains text;
 * images never become resources. Labels are supplied by the active UI locale.
 * No parser/token props are forwarded onto navigation or resource elements.
 */
export function ForgeMarkdown({ source, imageLabel, codeLabel, tableLabel }: ForgeMarkdownProps) {
  return createElement("div", { className: "forge-markdown" }, createElement(Markdown, {
    remarkPlugins: [remarkGfm],
    urlTransform: safeDestination,
    components: {
      a: ({ href, title, children }) => {
        const safe = safeDestination(href ?? "");
        return safe ? createElement("a", {
          href: safe, title, target: "_blank", rel: "noopener noreferrer",
        }, children) : createElement("span", null, children);
      },
      img: ({ alt }) => createElement("span", { className: "forge-image-placeholder" },
        alt ? `${imageLabel}: ${alt}` : imageLabel),
      input: ({ checked }) => createElement("input", { type: "checkbox", disabled: true, checked: Boolean(checked) }),
      pre: ({ children }) => createElement("pre", {
        className: "forge-scroll", role: "region", "aria-label": codeLabel, tabIndex: 0,
      }, children),
      table: ({ children }) => createElement("div", {
        className: "forge-scroll", role: "region", "aria-label": tableLabel, tabIndex: 0,
      }, createElement("table", null, children)),
    },
  }, source));
}

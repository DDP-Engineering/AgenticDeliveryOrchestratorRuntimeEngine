/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, type ReactNode } from "react";
import type { MessageKey } from "./i18n";
const companyLogo = new URL("./assets/DDP_Engineering_logo_dark.png", import.meta.url).href;

export type ShellLink = { id: string; label: string; href: string; active: boolean; onNavigate: () => void };

/** A real link retains open-in-new-tab behavior while ordinary clicks use the existing router. */
export function NavigationLink({ item }: { item: ShellLink }) {
  return <a className={`nav-item${item.active ? " active" : ""}`} href={item.href}
    aria-current={item.active ? "page" : undefined} onClick={event => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); item.onNavigate();
    }}>{item.label}</a>;
}

/** Shared authenticated frame; session, authorization, routing and operations remain owned by App. */
export function DashboardShell({ t, title, links, adminLinks, account, username, role, menuOpen, onMenu,
  adminOpen, onAdmin, onSignOut, actions, controls, context, children, modal }: {
  t: (key: MessageKey) => string; title: string; links: ShellLink[]; adminLinks: ShellLink[];
  account: ShellLink; username: string; role: string; menuOpen: boolean; onMenu: () => void;
  adminOpen: boolean; onAdmin: () => void; onSignOut: () => void; actions: ReactNode;
  controls?: ReactNode; context: ReactNode; children: ReactNode; modal: ReactNode;
}) {
  const previousTitle = useRef(title);
  useEffect(() => {
    if (title !== previousTitle.current) document.getElementById("main-content")?.focus({ preventScroll: true });
    previousTitle.current = title;
  }, [title]);
  return <div className="shell">
    <a className="skip-link" href="#main-content" inert={!!modal} onClick={event => {
      event.preventDefault(); document.getElementById("main-content")?.focus();
    }}>{t("skipToContent")}</a>
    <aside className="sidebar" inert={!!modal}>
      <div className="company-brand"><img src={companyLogo} alt="DDP Engineering" width="630" height="300" /></div>
      <div className="brand"><span className="brand-mark" aria-hidden="true">↗</span><div><strong>ADORE</strong><small>{t("subtitle")}</small></div></div>
      <button className="mobile-menu" type="button" aria-controls="primary-navigation" aria-expanded={menuOpen} onClick={onMenu}>☰ {t("menu")}</button>
      <nav id="primary-navigation" aria-label={t("primaryNavigation")} className={menuOpen ? "nav-open" : ""}>
        {links.map(item => <NavigationLink key={item.id} item={item} />)}
        {adminLinks.length > 0 && <>
          <button className="nav-item nav-parent" type="button" aria-expanded={adminOpen} aria-controls="admin-navigation" onClick={onAdmin}>
            {t("administration")} <span aria-hidden="true">{adminOpen ? "▴" : "▾"}</span>
          </button>
          {adminOpen && <div id="admin-navigation" className="nav-submenu">{adminLinks.map(item => <NavigationLink key={item.id} item={item} />)}</div>}
        </>}
        <NavigationLink item={account} />
      </nav>
      <div className="sidebar-bottom"><span className="user-avatar" aria-hidden="true">{username.charAt(0).toUpperCase()}</span>
        <div><strong>{username}</strong><small>{role}</small></div>
        <button className="icon-button" onClick={onSignOut} aria-label={t("logout")}><span aria-hidden="true">⇥</span></button>
      </div>
    </aside>
    <div className="workspace" inert={!!modal}>
      <header className="topbar"><h1 className="topbar-title" aria-label={title}><span className="topbar-brand">ADORE</span><span aria-hidden="true">/</span>{title}</h1>
        {controls}
        <div className="top-actions">{actions}<button className="ghost mobile-signout" onClick={onSignOut}>{t("logout")}</button></div>
      </header>
      <main id="main-content" className="content" tabIndex={-1}>{context}{children}</main>
    </div>
    {modal}
  </div>;
}

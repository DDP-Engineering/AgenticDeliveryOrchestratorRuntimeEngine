import React from "react";

const text: Record<string, [string, string]> = {
  en: ["The page could not be displayed.", "Reload"],
  fr: ["La page n’a pas pu être affichée.", "Recharger"],
  de: ["Die Seite konnte nicht angezeigt werden.", "Neu laden"],
  ro: ["Pagina nu a putut fi afișată.", "Reîncarcă"],
};

/** Replace a render failure with a reload prompt instead of an empty page. */
export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    console.error(error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    const [message, reload] = text[document.documentElement.lang] ?? text.en;
    return <main className="login-page">
      <section className="login-card">
        <p className="alert" role="alert">{message}</p>
        <button className="primary" type="button" onClick={() => window.location.reload()}>{reload}</button>
      </section>
    </main>;
  }
}

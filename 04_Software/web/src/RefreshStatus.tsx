import type { Locale } from "./i18n";

import { refreshCopy } from "./refreshCopy";

/** Quiet success timestamps; announce failures, not each automatic read. Never remount the view to retry. */
export function RefreshStatus({ locale, reading, failure, updatedAt, refresh, stale = false }: {
  locale: Locale; reading: boolean; failure: unknown; updatedAt: string | null; refresh: () => void; stale?: boolean;
}) {
  const c = refreshCopy[locale];
  return <div className="refresh-status">
    {stale && !!failure && <span className="alert" role="status">{c.failed}</span>}
    {updatedAt && <span className="muted">{c.updated}: <time dateTime={updatedAt}>{new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "medium" }).format(new Date(updatedAt))}</time></span>}
    <button type="button" className="ghost" aria-disabled={reading} onClick={refresh}>{failure ? c.retry : c.refresh}</button>
  </div>;
}

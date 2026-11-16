import type { Locale } from "./i18n";
import { environmentCopy, type EnvironmentProgress as Progress } from "./environmentPreparation";

/** Stage progress stays visible during long image builds without exposing build logs. */
export function EnvironmentProgress({ value, locale }: { value: Progress | null; locale: Locale }) {
  if (!value) return null;
  const c = environmentCopy[locale];
  return <section className="enrollment-review" aria-label={c.title} aria-busy={value.status === "running"}>
    <h3>{c.title}</h3>
    <p role="status" aria-live="polite">{c[value.stage]}</p>
    {value.status === "running" && <progress aria-label={c.title} />}
    <p className="muted">{c.help}</p>
  </section>;
}

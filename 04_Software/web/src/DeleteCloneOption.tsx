/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";
import { deleteCloneCopy, validClonePreview, type CloneReason, type ClonePreview } from "./deleteCloneCopy";

/**
 * Opt-in removal of the ADORE-made local clone inside the Delete project dialog.
 * Unchecked by default; a clone that cannot be removed always shows why it stays.
 */
export function DeleteCloneOption({ locale, project, read, checked, onChange }: {
  locale: Locale; project: string; read: (path: string) => Promise<unknown>;
  checked: boolean; onChange: (value: boolean) => void;
}) {
  const c = deleteCloneCopy[locale];
  const [clone, setClone] = useState<ClonePreview | null>(null);
  const reader = useRef(read); reader.current = read;
  const change = useRef(onChange); change.current = onChange;
  useEffect(() => {
    let active = true;
    setClone(null); change.current(false);
    reader.current(`/projects/${encodeURIComponent(project)}/delete-preview`)
      .then(value => { if (active && validClonePreview(value)) setClone(value.clone); })
      .catch(() => undefined);
    return () => { active = false; };
  }, [project]);
  if (!clone) return null;
  if (clone.removable) return <label className="delete-clone">
    <input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)} />
    <span>{c.remove} <code>{clone.path}</code></span>
  </label>;
  return <p className="muted delete-clone-kept">{c.kept} {clone.path && <><code>{clone.path}</code> — </>}{c.reasons[clone.reason as CloneReason]}</p>;
}

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

/** The server's decision about an archived project's local clone. */
export type ClonePreview = { path: string; removable: boolean; reason: string };

export const cloneReasons = ["outside-repos", "missing", "not-a-clone", "origin-mismatch", "shared", "worktrees", "uncommitted", "unknown"] as const;
export type CloneReason = typeof cloneReasons[number];

/** Only a well-formed preview can offer removal. */
export function validClonePreview(value: unknown): value is { clone: ClonePreview } {
  const clone = (value as { clone?: Partial<ClonePreview> } | null)?.clone;
  return !!clone && typeof clone.path === "string" && typeof clone.removable === "boolean" && typeof clone.reason === "string"
    && (clone.removable ? clone.reason === "" && clone.path.length > 0 : (cloneReasons as readonly string[]).includes(clone.reason));
}

export const deleteCloneCopy: Record<Locale, { remove: string; kept: string; reasons: Record<CloneReason, string> }> = {
  en: {
    remove: "Also remove the local clone",
    kept: "The local clone stays:",
    reasons: {
      "outside-repos": "ADORE removes only clones in its own repos folder.", missing: "its folder no longer exists.", "not-a-clone": "the folder is not a git clone.",
      "origin-mismatch": "it is a clone of another repository.", shared: "another project uses it.",
      worktrees: "a worktree that deletion keeps is linked to it.", uncommitted: "it has uncommitted changes.",
      unknown: "the project configuration could not be read.",
    },
  },
  fr: {
    remove: "Supprimer aussi le clone local",
    kept: "Le clone local est conservé :",
    reasons: {
      "outside-repos": "ADORE ne supprime que les clones de son propre dossier repos.", missing: "son dossier n’existe plus.", "not-a-clone": "le dossier n’est pas un clone git.",
      "origin-mismatch": "c’est un clone d’un autre dépôt.", shared: "un autre projet l’utilise.",
      worktrees: "un worktree que la suppression conserve y est lié.", uncommitted: "il contient des modifications non validées.",
      unknown: "la configuration du projet n’a pas pu être lue.",
    },
  },
  de: {
    remove: "Auch den lokalen Klon entfernen",
    kept: "Der lokale Klon bleibt erhalten:",
    reasons: {
      "outside-repos": "ADORE entfernt nur Klone in seinem eigenen Ordner repos.", missing: "sein Ordner existiert nicht mehr.", "not-a-clone": "der Ordner ist kein Git-Klon.",
      "origin-mismatch": "er ist ein Klon eines anderen Repositorys.", shared: "ein anderes Projekt verwendet ihn.",
      worktrees: "ein Worktree, den das Löschen behält, ist mit ihm verknüpft.", uncommitted: "er enthält nicht committete Änderungen.",
      unknown: "die Projektkonfiguration konnte nicht gelesen werden.",
    },
  },
  ro: {
    remove: "Elimină și clona locală",
    kept: "Clona locală se păstrează:",
    reasons: {
      "outside-repos": "ADORE elimină doar clonele din propriul dosar repos.", missing: "dosarul ei nu mai există.", "not-a-clone": "dosarul nu este o clonă git.",
      "origin-mismatch": "este o clonă a altui repository.", shared: "o folosește alt proiect.",
      worktrees: "un worktree păstrat la ștergere este legat de ea.", uncommitted: "are modificări necomise.",
      unknown: "configurația proiectului nu a putut fi citită.",
    },
  },
};

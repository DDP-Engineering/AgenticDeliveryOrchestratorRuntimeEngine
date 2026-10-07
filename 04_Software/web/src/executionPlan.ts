/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
export type ExecutionPlan = { schema: 1; backend: "container" | "local"; selection: string; image: string; image_source: "profile" | "recipe" | "local"; source_sha256: string; fingerprint: string; steps: Array<{ name: string; run: string }> };
export type PreparationEvidence = { status: "pending" | "running" | "success" | "failed" | "interrupted" | "cancelled"; attempts: number; image: string; fingerprint: string; steps: Array<{ index: number; name: string; started_at: string; finished_at: string; exit_code: number; timed_out: boolean; cancelled: boolean }> };
const selection = (value: string) => {
  const match = /^(.+\.ya?ml)#([A-Za-z_][A-Za-z0-9_-]{0,63})@(?:[a-f0-9]{40}|[a-f0-9]{64})$/.exec(value);
  return !!match && !match[1].startsWith("/") && !/[\\:\x00-\x1f]/.test(match[1]) && !match[1].split("/").some(part => ["", ".", "..", ".git", ".adore", ".agentic"].includes(part));
};
const digest = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);

/** Admit only a complete normalized review, including every setup command. */
export function validExecutionPlan(value: unknown): value is ExecutionPlan {
  if (!value || typeof value !== "object") return false;
  const plan = value as ExecutionPlan;
  return Object.keys(plan).sort().join() === ["schema", "backend", "selection", "image", "image_source", "source_sha256", "fingerprint", "steps"].sort().join()
    && plan.schema === 1 && ["container", "local"].includes(plan.backend) && typeof plan.selection === "string"
    && typeof plan.image === "string" && (plan.backend === "local" ? plan.image === "" && plan.image_source === "local" : /^[A-Za-z0-9][A-Za-z0-9._/:@-]{0,255}$/.test(plan.image) && ["profile", "recipe"].includes(plan.image_source))
    && digest(plan.fingerprint)
    && (plan.image_source === "recipe" ? digest(plan.source_sha256) && selection(plan.selection) : plan.source_sha256 === "" && plan.selection === "")
    && Array.isArray(plan.steps) && plan.steps.length <= 32 && (plan.image_source === "recipe" ? plan.steps.length > 0 : plan.steps.length === 0)
    && plan.steps.every(step => step && Object.keys(step).sort().join() === "name,run" && typeof step.name === "string" && step.name.trim().length > 0 && typeof step.run === "string" && step.run.trim().length > 0 && new TextEncoder().encode(step.run).length <= 8192);
}

/** Reject forged or incomplete preparation outcomes before rendering success. */
export function validPreparationEvidence(value: unknown): value is PreparationEvidence {
  if (!value || typeof value !== "object") return false;
  const item = value as PreparationEvidence;
  return Object.keys(item).sort().join() === ["status", "attempts", "image", "fingerprint", "steps"].sort().join()
    && ["pending", "running", "success", "failed", "interrupted", "cancelled"].includes(item.status)
    && Number.isInteger(item.attempts) && item.attempts >= 0 && item.attempts <= 3 && digest(item.fingerprint)
    && typeof item.image === "string" && /^[A-Za-z0-9][A-Za-z0-9._/:@-]{0,255}$/.test(item.image) && Array.isArray(item.steps) && item.steps.length <= 32
    && item.steps.every((step, index) => step && typeof step === "object" && Object.keys(step).sort().join() === ["index", "name", "started_at", "finished_at", "exit_code", "timed_out", "cancelled"].sort().join() && step.index === index && typeof step.name === "string" && Number.isInteger(step.exit_code) && step.exit_code >= -255 && step.exit_code <= 255 && typeof step.timed_out === "boolean" && typeof step.cancelled === "boolean" && [step.started_at, step.finished_at].every(stamp => typeof stamp === "string" && /(?:Z|[+-]\d{2}:\d{2})$/.test(stamp) && Number.isFinite(Date.parse(stamp))) && Date.parse(step.finished_at) >= Date.parse(step.started_at))
    && (item.status !== "success" || item.attempts > 0 && item.steps.length > 0 && item.steps.every(step => step.exit_code === 0 && !step.timed_out && !step.cancelled));
}

export const preparationCopy = {
  en: { title: "Container preparation", image: "Effective image", source: "Image source", selection: "Reviewed recipe / job / commit", commands: "Preparation commands", help: "Review these project commands before applying. They run only at job start in the execution container. Host checks do not install dependencies.", status: "Preparation result", attempts: "Preparation attempts", recovery: "Interrupted or failed setup requires an operator to inspect evidence and explicitly retry with --reprepare. All steps replay in a fresh container with the retained worktree." },
  fr: { title: "Préparation du conteneur", image: "Image effective", source: "Source de l’image", selection: "Recette / tâche / commit examinés", commands: "Commandes de préparation", help: "Examinez les commandes avant application. Elles s’exécutent au démarrage dans le conteneur. Les vérifications de l’hôte n’installent pas les dépendances.", status: "Résultat de préparation", attempts: "Tentatives de préparation", recovery: "Une préparation interrompue ou échouée exige un examen des preuves et une relance explicite avec --reprepare. Toutes les étapes sont rejouées dans un nouveau conteneur avec le worktree conservé." },
  de: { title: "Container-Vorbereitung", image: "Wirksames Image", source: "Image-Quelle", selection: "Geprüftes Rezept / Job / Commit", commands: "Vorbereitungsbefehle", help: "Prüfen Sie die Projektbefehle vor der Übernahme. Sie laufen beim Jobstart im Container. Hostprüfungen installieren keine Abhängigkeiten.", status: "Vorbereitungsergebnis", attempts: "Vorbereitungsversuche", recovery: "Unterbrochene oder fehlgeschlagene Vorbereitung erfordert die Prüfung der Nachweise und einen ausdrücklichen Neustart mit --reprepare. Alle Schritte werden im neuen Container mit dem erhaltenen Worktree wiederholt." },
  ro: { title: "Pregătirea containerului", image: "Imagine efectivă", source: "Sursa imaginii", selection: "Rețetă / job / commit revizuit", commands: "Comenzi de pregătire", help: "Revizuiți comenzile înainte de aplicare. Acestea rulează la pornirea jobului în container. Verificările gazdei nu instalează dependențe.", status: "Rezultatul pregătirii", attempts: "Încercări de pregătire", recovery: "Pregătirea întreruptă sau eșuată cere examinarea dovezilor și reluarea explicită cu --reprepare. Toți pașii rulează din nou într-un container nou, cu worktree-ul păstrat." },
};

/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { MessageKey } from "./i18n";

/** Per-setting metadata returned by GET /projects/{name}/config. */
export type SettingMeta = {
  key: string;
  edit_key: string;
  source: "project" | "default";
  editable: boolean;
  restart: boolean;
};

/** How a row's value is edited in the browser; `none` means not editable here. */
export type InputKind = "boolean" | "number" | "choice" | "text" | "none";

type CommonKind = "text" | "positive" | "forge" | "runtime" | "executor";

/** The settings most projects tune, shown first with their own help text. */
export const COMMON_SETTINGS: Array<{ key: string; label: MessageKey; help: MessageKey; kind: CommonKind }> = [
  { key: "platform.repo", label: "repository", help: "settingHelpRepository", kind: "text" },
  { key: "platform.kind", label: "forge", help: "settingHelpForge", kind: "forge" },
  { key: "container.runtime", label: "runtime", help: "settingHelpRuntime", kind: "runtime" },
  { key: "container.image", label: "image", help: "settingHelpImage", kind: "text" },
  { key: "executor.default", label: "executor", help: "settingHelpExecutor", kind: "executor" },
  { key: "polling.poll_interval_seconds", label: "pollInterval", help: "settingHelpPollInterval", kind: "positive" },
  { key: "polling.max_concurrent_runs", label: "concurrentJobs", help: "settingHelpConcurrent", kind: "positive" },
  { key: "budgets.max_iterations", label: "maxIterations", help: "settingHelpIterations", kind: "positive" },
  { key: "budgets.max_wall_clock_seconds", label: "maxWallClock", help: "settingHelpWallClock", kind: "positive" },
  { key: "budgets.max_files_touched", label: "maxFilesTouched", help: "settingHelpFiles", kind: "positive" },
];

const CHOICES: Partial<Record<CommonKind, string[]>> = {
  forge: ["gitlab", "github", "gitea"],
  executor: ["opencode", "pi", "codex", "qwen"],
};

export type SettingRow = {
  key: string;
  group: string;
  /** Position of the row's section in the configuration, for group order. */
  groupIndex: number;
  value: unknown;
  source: "project" | "default";
  editKey: string;
  restart: boolean;
  input: InputKind;
  choices: string[];
  common: boolean;
  label?: MessageKey;
  help?: MessageKey;
  hint?: "positive" | "runtime";
  /** Number input step: whole numbers for positive settings, any otherwise. */
  step?: "1" | "any";
};

export type SettingGroup = { name: string; rows: SettingRow[] };

const lookup = (config: Record<string, unknown>, key: string): unknown =>
  key.split(".").reduce<unknown>((current, part) =>
    current && typeof current === "object" ? (current as Record<string, unknown>)[part] : undefined, config);

const inputKind = (value: unknown, editable: boolean, kind?: CommonKind): InputKind => {
  if (!editable) return "none";
  if (kind && CHOICES[kind]) return "choice";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  return "text";
};

/**
 * One row per setting the server described, in the server's key order, with
 * the value read from the effective configuration.
 */
export function settingRows(config: Record<string, unknown>, settings: SettingMeta[]): SettingRow[] {
  const sections = Object.keys(config);
  return settings.map(item => {
    const common = COMMON_SETTINGS.find(entry => entry.key === item.key);
    const value = lookup(config, item.key);
    const group = item.key.split(".")[0];
    return {
      key: item.key,
      group,
      groupIndex: sections.indexOf(group),
      value,
      source: item.source,
      editKey: item.edit_key,
      restart: item.restart,
      input: inputKind(value, item.editable, common?.kind),
      choices: (common && CHOICES[common.kind]) || [],
      common: !!common,
      label: common?.label,
      help: common?.help,
      hint: common?.kind === "positive" || common?.kind === "runtime" ? common.kind : undefined,
      step: typeof value === "number" && item.editable ? (common?.kind === "positive" ? "1" : "any") : undefined,
    };
  });
}

/**
 * Groups rows for display: the common settings first in their defined order,
 * then one group per configuration section in configuration order. With
 * `projectOnly`, only settings the project's file sets remain, and groups
 * left empty are dropped.
 */
export function settingGroups(rows: SettingRow[], projectOnly: boolean): SettingGroup[] {
  const shown = projectOnly ? rows.filter(row => row.source === "project") : rows;
  const common = COMMON_SETTINGS
    .map(entry => shown.find(row => row.key === entry.key))
    .filter((row): row is SettingRow => !!row);
  const sections: SettingGroup[] = [];
  for (const row of shown) {
    if (row.common) continue;
    let group = sections.find(item => item.name === row.group);
    if (!group) { group = { name: row.group, rows: [] }; sections.push(group); }
    group.rows.push(row);
  }
  sections.sort((left, right) => left.rows[0].groupIndex - right.rows[0].groupIndex);
  return [{ name: "common", rows: common }, ...sections].filter(group => group.rows.length > 0);
}

/** The text an editor starts from for a setting's current value. */
export function editValue(value: unknown): string {
  return value === null || value === undefined ? "" : String(value);
}

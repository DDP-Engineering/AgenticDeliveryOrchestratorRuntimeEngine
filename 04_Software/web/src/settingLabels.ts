/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { executorSettingLabel } from "./executorSettings";
import { localCopy } from "./localExecution";
import { messages, type Locale } from "./i18n";
import { COMMON_SETTINGS } from "./settings";
import { settingHelp } from "./settingHelp";
import {
  branchSettingLabel, excludeLabelCopy, implementationSettingLabel, lifecycleCopy, localizedSettingLabel, pipelineFailureCopy,
  publicationCopy, reviewerCopy, settingLabel, statisticsDatabaseCopy, targetBranchCopy,
} from "./settingsCopy";

/** The name a setting has in Settings, in the chosen language (shared by Settings and enrollment). */
export function settingDisplayLabel(key: string, locale: Locale): string {
  if (key === "local.path") return localCopy[locale].path;
  if (key === "labels.selection.type_epic") return { en: "Epic label", fr: "Étiquette épopée", de: "Epic-Label", ro: "Etichetă epic" }[locale];
  const common = COMMON_SETTINGS.find(entry => entry.key === key)?.label;
  return executorSettingLabel(key, locale) || branchSettingLabel(key, locale) || implementationSettingLabel(key, locale)
    || localizedSettingLabel(key, locale) || lifecycleCopy[locale].labels[key]
    || (key === "metrics.db_path" ? statisticsDatabaseCopy[locale].label : key === "review.on_pipeline_failure" ? pipelineFailureCopy[locale].label
      : key === "labels.control.exclude" ? excludeLabelCopy[locale].label : key === "delivery.target_branch" ? targetBranchCopy[locale].label
      : key === "delivery.reviewers" ? reviewerCopy[locale].label : key === "delivery.draft" ? publicationCopy[locale].label
      : locale === "en" ? settingLabel(key) : common ? messages[locale][common] : (settingHelp(key, locale)?.split(". ")[0] || settingLabel(key)));
}

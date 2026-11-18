import limitsJson from "../../adore/setting_limits.json" with { type: "json" };

type Rule = { default: number | string | null; minimum: number; maximum: number; unit: string; provider_maximum?: Record<string, number> };
const rules: Record<string, unknown> = limitsJson;
export const settingConstraints = limitsJson._constraints;
export function settingLimit(key: string, provider = ""): Rule | undefined {
  const rule = rules[key.startsWith("workflow.stage_timeout_overrides.") ? "budgets.per_gate_timeout_seconds" : key] as Rule | undefined;
  return rule ? {...rule, maximum: rule.provider_maximum?.[provider] ?? rule.maximum} : undefined;
}
export function settingDefault(key: string): string { return String((rules[key] as Rule).default); }
export function validSettingNumber(key: string, value: number, provider = ""): boolean {
  const rule = settingLimit(key, provider);
  return !!rule && Number.isFinite(value) && (key === "budgets.max_cost_usd" || Number.isSafeInteger(value))
    && value >= rule.minimum && value <= rule.maximum;
}

export function settingTextLimit(key: string): number | undefined {
  if (key.startsWith("labels.") || key === "delivery.approval_label" || key === "review.revise_label") return settingConstraints.label_length;
  if (key === "executor.endpoint.base_url") return settingConstraints.endpoint_length;
  return undefined;
}

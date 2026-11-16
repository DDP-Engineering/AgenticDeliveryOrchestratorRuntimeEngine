import type { Usage } from "./metrics";

export type UsageRow = Usage["daily"][number];
export type UsageSortKey = keyof UsageRow;

/** Sorts usage rows by one column; unknown values stay last in both directions and ties keep server order. */
export function sortUsageRows(rows: UsageRow[], key: UsageSortKey, descending: boolean, locale?: string): UsageRow[] {
  return [...rows].sort((left, right) => {
    const a = left[key], b = right[key];
    const aUnknown = a == null || a === "", bUnknown = b == null || b === "";
    if (aUnknown || bUnknown) return aUnknown === bUnknown ? 0 : aUnknown ? 1 : -1;
    const comparison = typeof a === "number" && typeof b === "number" ? a - b :
      String(a).localeCompare(String(b), locale, { numeric: true, sensitivity: "base" });
    return descending ? -comparison : comparison;
  });
}

/** Convert visible audit limits to the existing nullable API contract, rejecting invalid input. */
export function auditPolicyPayload(days: string, mebibytes: string): { retention_days: number | null; max_bytes: number | null } {
  const dayCount = Number(days.trim());
  const size = Number(mebibytes.trim());
  const bytes = Math.round(size * 1024**2);
  if (!Number.isSafeInteger(dayCount) || dayCount < 0 || dayCount > 36500 ||
    !Number.isFinite(size) || size < 0 || size > 1024 || (size > 0 && bytes < 1)) {
    throw new RangeError("Invalid audit retention limits");
  }
  return { retention_days: dayCount === 0 ? null : dayCount, max_bytes: size === 0 ? null : bytes };
}

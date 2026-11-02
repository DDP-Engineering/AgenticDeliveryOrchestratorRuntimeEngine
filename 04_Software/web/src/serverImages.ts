/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/

/** Tagged container images on the ADORE server for one runtime. */
export type ServerImages = { runtime: string; available: boolean; images: string[] };

/** A well-formed image list from the server. */
export function validServerImages(value: unknown): value is ServerImages {
  const item = value as Partial<ServerImages> | null;
  return !!item && typeof item.runtime === "string" && typeof item.available === "boolean" && Array.isArray(item.images)
    && item.images.length <= 1000 && item.images.every(name => typeof name === "string" && name.length > 0 && name.length <= 255);
}

/** The server image for the coding agent: tag `<agent>-*`, preferring adore-executor-base. */
export function proposeImage(names: string[], executor: string): string {
  const matching = names.filter(name => name.slice(name.lastIndexOf(":") + 1).startsWith(executor + "-"));
  return matching.find(name => name.startsWith("adore-executor-base:")) ?? matching[0] ?? "";
}

/** Read the server's images; a runtime that cannot be listed (or any failure) is unavailable. */
export async function readServerImages(runtime: string): Promise<ServerImages> {
  const unavailable = { runtime, available: false, images: [] };
  if (!["docker", "podman"].includes(runtime)) return unavailable;
  try {
    const response = await fetch("/api/v1/executor-images?runtime=" + runtime, { credentials: "same-origin", cache: "no-store" });
    const value: unknown = response.ok ? await response.json() : null;
    return validServerImages(value) && value.runtime === runtime ? value : unavailable;
  } catch { return unavailable; }
}

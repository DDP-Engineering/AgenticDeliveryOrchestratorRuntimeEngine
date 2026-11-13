/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { expect, type Page, type Request } from "@playwright/test";

/** Isolate virtual deadline jumps from unrelated, real session/directory IO. */
export function trackScopeReads(page: Page): () => Promise<void> {
  const pending = new Set<Request>();
  page.on("request", request => { if (/\/api\/v1\/(?:me|projects)(?:\?overview=true)?$/.test(request.url())) pending.add(request); });
  page.on("requestfinished", request => pending.delete(request));
  page.on("requestfailed", request => pending.delete(request));
  return async () => { await expect.poll(() => pending.size).toBe(0); };
}

/** Exercise a visibility transition, not a duplicate event on an already visible page. */
export async function revalidateVisiblePage(page: Page): Promise<void> {
  await page.evaluate(() => {
    const original = Object.getOwnPropertyDescriptor(document, "visibilityState");
    try {
      Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
      document.dispatchEvent(new Event("visibilitychange"));
      Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
      document.dispatchEvent(new Event("visibilitychange"));
    } finally {
      if (original) Object.defineProperty(document, "visibilityState", original);
      else Reflect.deleteProperty(document, "visibilityState");
    }
  });
}

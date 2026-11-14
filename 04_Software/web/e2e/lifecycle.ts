/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { expect, type BrowserContext, type Page } from "@playwright/test";

/** Stop both route layers after the body, then restore the account for the next case. */
export async function cleanupBrowserPage(context: BrowserContext, page: Page) {
  // Detach the fallback layer first: an ignored page callback can fall through to it.
  // This is teardown-only; live-body handler errors retain normal failure reporting.
  // Neither layer waits for deliberately held response fixtures.
  await context.unrouteAll({ behavior: "ignoreErrors" });
  await page.unrouteAll({ behavior: "ignoreErrors" });
  try {
    await page.goto("about:blank", { timeout: 5_000 });
  } finally {
    const session = await page.request.get("/api/v1/me", { timeout: 5_000 });
    if (session.status() !== 401) {
      expect(session.ok()).toBe(true);
      const me = await session.json();
      const reset = await page.request.patch("/api/v1/me/preferences", {
        headers: { "X-CSRF-Token": me.csrf },
        data: { language: "en", theme: "light" }, timeout: 5_000,
      });
      expect(reset.ok()).toBe(true);
      expect(await reset.json()).toMatchObject({ language: "en", theme: "light" });
    }
  }
}

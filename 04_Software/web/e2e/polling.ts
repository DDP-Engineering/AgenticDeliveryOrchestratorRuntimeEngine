/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Page } from "@playwright/test";

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

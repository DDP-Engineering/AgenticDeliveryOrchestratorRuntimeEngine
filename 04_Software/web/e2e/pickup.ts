/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { expect, request } from "@playwright/test";

/**
 * Start or stop a fixture project's pickup as the administrator and wait for the worker.
 * The offline fixture keeps pickup stopped; a ticket Start needs it active.
 */
export async function setPickup(project: string, active: boolean) {
  const api = await request.newContext({ baseURL: "http://127.0.0.1:18765" });
  try {
    const session = await (await api.post("/api/v1/session", { data: { username: "admin", password: "admin" } })).json();
    const queued = await api.post(`/api/v1/projects/${project}/operations/${active ? "resume" : "pause"}`, {
      headers: { "X-CSRF-Token": session.csrf }, data: { idempotency_key: crypto.randomUUID() } });
    expect(queued.status()).toBe(200);
    const { id } = await queued.json();
    await expect.poll(async () => (await (await api.get(`/api/v1/operations/${id}`)).json()).status).toBe("succeeded");
  } finally {
    await api.dispose();
  }
}

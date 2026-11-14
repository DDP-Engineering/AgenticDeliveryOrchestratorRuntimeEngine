/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { expect, type APIRequestContext, type APIResponse } from "@playwright/test";

/** Domain assertions consume the actual durable result, after transport acceptance. */
export async function configurationResponse(
  response: Pick<APIResponse, "status" | "ok" | "json">, api: APIRequestContext,
) {
  if (response.status() !== 202) return response;
  const accepted = await response.json();
  if (!["configuration_project", "configuration_global"].includes(accepted.domain)) return response;
  expect(Number.isSafeInteger(accepted.id) && accepted.id > 0).toBe(true);
  expect(accepted.status).toBe("pending");
  let operation: Awaited<ReturnType<APIResponse["json"]>>;
  await expect.poll(async () => {
    const observed = await api.get(`/api/v1/operations/${accepted.id}`);
    expect(observed.status()).toBe(200);
    operation = await observed.json();
    expect(operation.id).toBe(accepted.id);
    expect(operation.action).toBe("configure");
    expect(operation.domain).toBe(accepted.domain);
    expect(operation.project_id).toBe(accepted.project_id);
    return operation.status;
  }).toMatch(/^(succeeded|failed|uncertain)$/);
  expect(operation.status).not.toBe("uncertain");
  expect(Number.isInteger(operation.outcome?.status_code)).toBe(true);
  const { status_code: status, body } = operation.outcome;
  expect(status).toBeGreaterThanOrEqual(200);
  expect(status).toBeLessThanOrEqual(599);
  expect(operation.status === "succeeded").toBe(status < 400);
  return { status: () => status as number, ok: () => status < 400, json: async () => body };
}

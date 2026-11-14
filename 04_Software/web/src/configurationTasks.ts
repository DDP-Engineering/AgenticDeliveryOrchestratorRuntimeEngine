// Copyright (c) 2026 DDP Engineering
// This software is licensed under the PolyForm Noncommercial License 1.0.0.
// Commercial use requires a separate commercial license.
// See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

/** Await the durable result of an accepted configuration request. */
export async function completedConfiguration(response: Response, signal?: AbortSignal): Promise<Response> {
  if (response.status !== 202) return response;
  const accepted: unknown = await response.clone().json();
  if (!accepted || typeof accepted !== "object" || !("domain" in accepted) ||
      !["configuration_project", "configuration_global"].includes(String(accepted.domain))) return response;
  if (!("id" in accepted) || !Number.isSafeInteger(accepted.id) || Number(accepted.id) < 1 ||
      !("status" in accepted) || accepted.status !== "pending") throw new Error("unexpected_response");
  const id = Number(accepted.id);
  const deadline = Date.now() + 3660000;
  while (Date.now() < deadline) {
    signal?.throwIfAborted();
    const status = await fetch(`/api/v1/operations/${id}`, {
      credentials: "same-origin", cache: "no-store", signal,
    });
    if (!status.ok) return status;
    const operation = await status.json();
    if (operation?.id !== id || operation?.action !== "configure" ||
        operation?.domain !== accepted.domain || !("project_id" in accepted) ||
        operation?.project_id !== accepted.project_id) throw new Error("unexpected_response");
    if (operation.status === "pending" || operation.status === "running") {
      await new Promise<void>((resolve, reject) => {
        const cancel = () => { clearTimeout(timer); reject(signal?.reason); };
        const timer = setTimeout(() => { signal?.removeEventListener("abort", cancel); resolve(); }, 150);
        signal?.addEventListener("abort", cancel, { once: true });
      });
      continue;
    }
    if (operation.status === "uncertain") return Response.json({ detail: {
      code: "configuration_uncertain", operation_id: id,
    } }, { status: 409 });
    const outcome = operation.outcome;
    if (!["succeeded", "failed"].includes(operation.status) || !outcome ||
        !Number.isInteger(outcome.status_code) || outcome.status_code < 200 ||
        outcome.status_code > 599 || !("body" in outcome) ||
        (operation.status === "succeeded") !== (outcome.status_code < 400)) {
      throw new Error("unexpected_response");
    }
    return Response.json(outcome.body, { status: outcome.status_code });
  }
  return Response.json({ detail: { code: "configuration_timeout", operation_id: id } }, { status: 504 });
}

// Copyright (c) 2026 DDP Engineering
// This software is licensed under the PolyForm Noncommercial License 1.0.0.
// Commercial use requires a separate commercial license.
// See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
import { ApiError } from "./errors.ts";

// Most requests end within a second, so the first questions come quickly; a
// long one (an image build) is then asked about every two seconds at most.
const FIRST_WAIT_MS = 150;
const LONGEST_WAIT_MS = 2000;
const WAIT_GROWTH = 1.5;
// Unreachable-server answers in a row before the wait is given up. The request
// itself continues on the server either way.
const UNREACHABLE_LIMIT = 4;

/** Wait, and end the wait at once when the caller aborts. */
function pause(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const cancel = () => { clearTimeout(timer); reject(signal?.reason); };
    const timer = setTimeout(() => { signal?.removeEventListener("abort", cancel); resolve(); }, milliseconds);
    signal?.addEventListener("abort", cancel, { once: true });
  });
}

/** Await the durable result of an accepted configuration request. */
export async function completedConfiguration(response: Response, signal?: AbortSignal): Promise<Response> {
  if (response.status !== 202) return response;
  const accepted: unknown = await response.clone().json();
  if (!accepted || typeof accepted !== "object" || !("domain" in accepted) ||
      !["configuration_project", "configuration_global"].includes(String(accepted.domain))) return response;
  if (!("id" in accepted) || !Number.isSafeInteger(accepted.id) || Number(accepted.id) < 1 ||
      !("status" in accepted) || accepted.status !== "pending") throw new ApiError("unexpected_response");
  const id = Number(accepted.id);
  const deadline = Date.now() + 3660000;
  let wait = FIRST_WAIT_MS, unreachable = 0;
  const waitLonger = async () => {
    await pause(wait, signal);
    wait = Math.min(LONGEST_WAIT_MS, wait * WAIT_GROWTH);
  };
  while (Date.now() < deadline) {
    signal?.throwIfAborted();
    let status: Response;
    try {
      status = await fetch(`/api/v1/operations/${id}`, {
        credentials: "same-origin", cache: "no-store", signal,
      });
    } catch (cause) {
      signal?.throwIfAborted();
      unreachable += 1;
      if (unreachable >= UNREACHABLE_LIMIT) {
        throw new ApiError("network_error", String((cause as Error)?.message ?? cause));
      }
      await waitLonger();
      continue;
    }
    unreachable = 0;
    if (!status.ok) return status;
    const operation = await status.json().catch(() => null);
    if (operation?.id !== id || operation?.action !== "configure" ||
        operation?.domain !== accepted.domain || !("project_id" in accepted) ||
        operation?.project_id !== accepted.project_id) throw new ApiError("unexpected_response");
    if (operation.status === "pending" || operation.status === "running") {
      await waitLonger();
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
      throw new ApiError("unexpected_response");
    }
    return Response.json(outcome.body, { status: outcome.status_code });
  }
  return Response.json({ detail: { code: "configuration_timeout", operation_id: id } }, { status: 504 });
}

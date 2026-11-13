/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { ApiError, ReadTransportError } from "./errors.ts";

export type Request = <T>(path: string, method?: string, body?: unknown, csrf?: string, signal?: AbortSignal) => Promise<T>;

/** HTTP denial is distinct from a server string claiming a transport failure. */
class RequestDenied extends ApiError {}

/** JSON transport; successful bodies still need the resource's own validator. */
export const rawRequest: Request = async <T>(path: string, method = "GET", body?: unknown, csrf?: string, signal?: AbortSignal): Promise<T> => {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method, credentials: "same-origin", cache: "no-store", signal,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    if (signal?.aborted) throw cause;
    throw new ReadTransportError();
  }
  signal?.throwIfAborted();
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    signal?.throwIfAborted();
    const detail = payload?.detail;
    const code = typeof detail?.code === "string" ? detail.code : "request_failed";
    const message = typeof detail?.message === "string" ? detail.message : "";
    if (response.status === 401 || response.status === 403) throw new RequestDenied(code, message);
    throw new ApiError(code, message);
  }
  if (!response.headers.get("content-type")?.includes("application/json")) throw new ApiError("unexpected_response");
  try {
    const value = await response.json() as T;
    signal?.throwIfAborted();
    return value;
  } catch (cause) {
    if (signal?.aborted) throw cause;
    throw new ApiError("unexpected_response");
  }
};

/**
 * One application principal owns every request, including child explicit reads
 * and prices. Disposal aborts all browser work and refuses late callbacks/new
 * requests. It does not claim to roll back accepted server mutations.
 */
export function createRequestScope(onDenied: (code: string) => void, transport: Request = rawRequest) {
  const lifetime = new AbortController();
  let authenticated = false;
  const request: Request = async <T>(path: string, method?: string, body?: unknown, csrf?: string, signal?: AbortSignal): Promise<T> => {
    const owned = signal ? AbortSignal.any([lifetime.signal, signal]) : lifetime.signal;
    owned.throwIfAborted();
    try {
      const value = await transport<T>(path, method, body, csrf, owned);
      owned.throwIfAborted();
      return value;
    } catch (cause) {
      owned.throwIfAborted();
      if (authenticated && cause instanceof RequestDenied) {
        lifetime.abort();
        onDenied(cause.code);
      }
      throw cause;
    }
  };
  return { request, activate: () => { authenticated = true; }, dispose: () => lifetime.abort(), disposed: () => lifetime.signal.aborted };
}

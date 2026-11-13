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

/**
 * JSON transport; successful bodies still need the resource's own validator.
 * An authenticated owner can handle denial at headers without awaiting a body.
 * Unauthenticated/raw callers retain detailed error-body codes (notably login).
 */
export const rawRequest = async <T>(path: string, method = "GET", body?: unknown, csrf?: string, signal?: AbortSignal,
  onDeniedStatus?: (code: string) => boolean): Promise<T> => {
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
    const denied = response.status === 401 || response.status === 403;
    // Status is sufficient authority evidence. A body can stall or be corrupt;
    // it must not turn a received denial into a later informational deadline.
    const denialCode = response.status === 401 ? "authentication_required" : "request_rejected";
    if (denied && onDeniedStatus?.(denialCode)) {
      void response.body?.cancel().catch(() => {});
      throw new RequestDenied(denialCode);
    }
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
export function createRequestScope(onDenied: (code: string) => void, transport: typeof rawRequest = rawRequest) {
  const lifetime = new AbortController();
  let authenticated = false;
  const request: Request = async <T>(path: string, method?: string, body?: unknown, csrf?: string, signal?: AbortSignal): Promise<T> => {
    const owned = signal ? AbortSignal.any([lifetime.signal, signal]) : lifetime.signal;
    owned.throwIfAborted();
    let deniedAtHeaders = false;
    try {
      const value = await transport<T>(path, method, body, csrf, owned, code => {
        if (!authenticated || owned.aborted) return false;
        deniedAtHeaders = true;
        lifetime.abort();
        onDenied(code);
        return true;
      });
      owned.throwIfAborted();
      return value;
    } catch (cause) {
      // This attempt's received denial is a closed HTTP failure, not a transport
      // abort. Other disposed/obsolete attempts still cannot deliver callbacks.
      if (deniedAtHeaders && cause instanceof RequestDenied) throw cause;
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

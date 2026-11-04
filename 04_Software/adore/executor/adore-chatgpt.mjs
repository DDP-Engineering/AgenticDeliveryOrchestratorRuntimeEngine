#!/usr/bin/env node
/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
/**
 * ADORE's ChatGPT helper: Pi's own "Sign in with ChatGPT" and token refresh,
 * run by ADORE in a one-off helper container whose only mount is the server's
 * ChatGPT credential directory (PI_CODING_AGENT_DIR).
 *
 *   login                        print {"event":"auth_url","url"}, read the pasted
 *                                redirect address from stdin, store the credential
 *                                with Pi's AuthStorage (lock, mode 0600), then
 *                                {"event":"signed-in"} or {"event":"error","code"}
 *   token --min-validity-seconds N
 *                                {"status":"ok","token","expires"} with an access
 *                                token valid for N seconds (refreshed under Pi's
 *                                lock when needed), or {"status":<code>}
 *
 * Output is one JSON object per line and never carries a refresh token, an
 * authorization code or a redirect address; only `token` prints an access
 * token. Error texts are reduced to cause codes. The pinned Pi's modules are
 * imported by path (they are not all exported by the package).
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";

const PI = process.env.ADORE_PI_PACKAGE || "/opt/pi/lib/node_modules/@earendil-works/pi-coding-agent";
const AI = [join(PI, "node_modules", "@earendil-works", "pi-ai"), join(PI, "..", "pi-ai")]
  .find((path) => existsSync(join(path, "package.json")));
const DIR = process.env.PI_CODING_AGENT_DIR || "";
const AUTH = join(DIR, "auth.json");
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function emit(value) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
}

function finish(value, code) {
  emit(value);
  process.exit(code);
}

/** Messages of an error and its causes, for classification only (never printed). */
function messages(error) {
  const parts = [];
  for (let item = error, depth = 0; item && depth < 6; item = item.cause, depth++) {
    parts.push(item instanceof Error ? item.message : String(item));
  }
  return parts.join(" | ");
}

/** One cause code for a failed login or refresh. */
function cause(error, refreshing) {
  const text = messages(error);
  if (/subscription_sharing_user_not_eligible|did not include chatgpt\.tokens\.use\.direct/i.test(text)) return "not-eligible";
  if (/expires too soon/i.test(text)) return "too-long";
  if (/authorization failed: access_denied/i.test(text)) return "denied";
  if (/authorization failed/i.test(text)) return "refused";
  if (/invalid_grant|token request failed \(40[013]\)|issued client ID/i.test(text)) {
    return refreshing ? "sign-in-again" : "code-rejected";
  }
  // Any other 4xx (a rate limit, a timeout, ...) is not a refused grant: a later
  // refresh may succeed, so it never asks for a new sign-in.
  if (/token request failed \(4\d\d\)/i.test(text)) return refreshing ? "unavailable" : "refused";
  if (/fetch failed|ECONN|ENOTFOUND|EAI_AGAIN|ETIMEDOUT|ENETUNREACH|network|timed? ?out|aborted|token request failed \(5\d\d\)/i.test(text)) {
    return "unavailable";
  }
  return "failed";
}

/** auth.json as Pi stores it; a missing file is empty, an unreadable one throws. */
function readAuth() {
  if (!existsSync(AUTH)) return {};
  const value = JSON.parse(readFileSync(AUTH, "utf-8").replace(/^﻿/, ""));
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("auth.json is not an object");
  return value;
}

async function load(path) {
  return import(pathToFileURL(path).href);
}

if (!DIR || !AI) finish({ status: "failed", event: "error", code: "failed" }, 1);
const [{ openaiChatGPTOAuth }, { refreshStoredOAuthCredential }, { AuthStorage }] = await Promise.all([
  load(join(AI, "dist", "auth", "oauth", "openai-chatgpt.js")),
  load(join(AI, "dist", "auth", "resolve.js")),
  load(join(PI, "dist", "core", "auth-storage.js")),
]);

async function login() {
  let deviceId = "";
  try {
    deviceId = readFileSync(join(DIR, "device-id"), "utf-8").trim();
    readAuth();
  } catch {
    finish({ event: "error", code: deviceId ? "unreadable" : "failed" }, 1);
  }
  if (!UUID.test(deviceId)) finish({ event: "error", code: "failed" }, 1);
  const input = createInterface({ input: process.stdin });
  const pasted = new Promise((resolve) => {
    input.once("line", resolve);
    input.once("close", () => resolve(null));
  });
  try {
    const credential = await openaiChatGPTOAuth.login({
      signal: new AbortController().signal,
      prompt: async (request) => {
        if (request.type !== "manual_code") throw new Error("unsupported prompt");
        const line = await pasted;
        if (line === null) throw new Error("Login cancelled");
        return line;
      },
      notify: (event) => {
        if (event.type === "auth_url") emit({ event: "auth_url", url: event.url });
      },
    }, { getDeviceId: () => deviceId });
    await AuthStorage.create(AUTH).modify("openai", async () => credential);
  } catch (error) {
    finish({ event: "error", code: cause(error, false) }, 1);
  }
  finish({ event: "signed-in" }, 0);
}

async function token(args) {
  const index = args.indexOf("--min-validity-seconds");
  const seconds = Number(args[index + 1]);
  if (index < 0 || !Number.isInteger(seconds) || seconds < 1) finish({ status: "failed" }, 1);
  const minimum = seconds * 1000;
  let stored;
  try {
    stored = readAuth().openai;
  } catch {
    finish({ status: "unreadable" }, 1);
  }
  if (!stored) finish({ status: "not-signed-in" }, 1);
  if (stored.type !== "oauth") finish({ status: "sign-in-again" }, 1);
  const needsRefresh = (credential) => Date.now() + minimum >= credential.expires;
  let credential = stored;
  if (needsRefresh(credential)) {
    try {
      credential = await refreshStoredOAuthCredential(
        AuthStorage.create(AUTH), "openai", openaiChatGPTOAuth, needsRefresh, AbortSignal.timeout(60_000));
    } catch (error) {
      finish({ status: cause(error, true) }, 1);
    }
    if (!credential) finish({ status: "not-signed-in" }, 1);
    if (needsRefresh(credential)) finish({ status: "too-long" }, 1);
  }
  finish({ status: "ok", token: credential.access, expires: credential.expires }, 0);
}

const [command, ...rest] = process.argv.slice(2);
if (command === "login") await login();
else if (command === "token") await token(rest);
else finish({ status: "failed", event: "error", code: "failed" }, 2);

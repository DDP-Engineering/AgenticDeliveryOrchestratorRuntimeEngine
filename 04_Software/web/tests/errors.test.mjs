/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ApiError, describeError, errorMessages } from "../src/errors.ts";

const locales = ["en", "fr", "de", "ro"];
const clientCodes = ["network_error", "unexpected_response", "request_failed"];

test("portable Gitea authentication explains the repository connection flow in four locales", () => {
  const terms = {
    en: ["Repository access", "Repository server", "Access token", "Verify and connect"],
    ro: ["Acces la repository", "Serverul depozitului", "Token de acces", "Verifică și conectează"],
    fr: ["Accès au dépôt", "Serveur du dépôt", "Jeton d’accès", "Vérifier et connecter"],
    de: ["Repository-Zugang", "Repository-Server", "Zugriffstoken", "Prüfen und verbinden"],
  };
  for (const locale of locales) {
    for (const code of ["gitea_auth_missing", "gitea_auth_login_missing", "gitea_auth_ambiguous", "gitea_auth_invalid"]) {
      const message = describeError(locale, new ApiError(code));
      for (const term of terms[locale]) assert.ok(message.includes(term), `${locale}:${code}:${term}`);
      assert.ok(!message.includes(code));
    }
  }
});

/** Every code the API source can emit: _error calls, code maps and literal bodies. */
function apiCodes() {
  const source = readFileSync(new URL("../../adore/web/app.py", import.meta.url), "utf8");
  const codes = new Set();
  for (const match of source.matchAll(/_error\([^,()]+,\s*"([a-z][a-z0-9_]*)"/g)) codes.add(match[1]);
  for (const match of source.matchAll(/"code":\s*"([a-z][a-z0-9_]*)"/g)) codes.add(match[1]);
  for (const match of source.matchAll(/^_[A-Z_]+_CODE = "([a-z][a-z0-9_]*)"$/gm)) codes.add(match[1]);
  for (const block of source.matchAll(/^_[A-Z_]+_CODES = \{([\s\S]*?)^\}|^_[A-Z_]+_CODES = \{([^\n]*)\}$/gm)) {
    for (const match of (block[1] ?? block[2]).matchAll(/:\s*"([a-z][a-z0-9_]*)"/g)) codes.add(match[1]);
  }
  return [...codes].sort();
}

test("the API source exposes the codes this test relies on", () => {
  const codes = apiCodes();
  for (const code of ["invalid_project_name", "password_change_required", "password_too_short",
    "invalid_request", "not_found", "request_rejected", "request_failed", "web_store_corrupt"]) {
    assert.ok(codes.includes(code), code);
  }
});

test("every API and client error code has a message in every locale", () => {
  const missing = [];
  for (const locale of locales) {
    for (const code of [...apiCodes(), ...clientCodes]) {
      if (!(errorMessages[locale]?.[code] ?? "").trim()) missing.push(`${locale}:${code}`);
    }
  }
  assert.deepEqual(missing, []);
});

test("known codes render the localized sentence and keep diagnostics", () => {
  assert.equal(describeError("fr", new ApiError("invalid_project_name")), errorMessages.fr.invalid_project_name);
  const text = describeError("en", new ApiError("project_setup_invalid", "forge.repo: must be owner/repo"));
  assert.ok(text.startsWith(errorMessages.en.project_setup_invalid));
  assert.ok(text.includes("forge.repo: must be owner/repo"));
});

test("unknown codes and unexpected failures use a localized generic message", () => {
  for (const locale of locales) {
    const text = describeError(locale, new ApiError("brand_new_code"));
    assert.ok(text.includes("brand_new_code"));
    assert.notEqual(text, "brand_new_code");
  }
  assert.ok(describeError("de", new TypeError("boom")).includes("boom"));
  assert.notEqual(describeError("de", new TypeError("boom")), "boom");
});

test("already localized text passes through unchanged", () => {
  assert.equal(describeError("ro", "Mesaj deja tradus"), "Mesaj deja tradus");
  assert.equal(describeError("en", ""), "");
});

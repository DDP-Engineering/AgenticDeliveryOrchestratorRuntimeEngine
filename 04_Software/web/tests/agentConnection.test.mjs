/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  connectionCopy, connectionOf, credentialNote, providerModels, providerName, validConnection, validEndpointUrl, validProviderCatalog,
} from "../src/agentConnection.ts";
import { modelConnectionCopy, modelGuidance, validModelEvidence } from "../src/modelEvidence.ts";
import { connectionRowVisible, settingRows, validPendingConfig } from "../src/settings.ts";

const locales = ["en", "fr", "de", "ro"];
const catalog = { pi_version: "1.4.0", providers: [{ id: "openai", name: "OpenAI", variable: "OPENAI_API_KEY", models: ["gpt-5.5"] }],
  chatgpt: { id: "chatgpt", models: ["gpt-5.6-luna"] }, custom: { id: "custom", variable: "ADORE_ENDPOINT_API_KEY", apis: ["openai-completions"] } };

test("connection transport accepts a provider with its endpoint only for custom", () => {
  assert.equal(validConnection({ provider: "openai", model: "gpt-5.5", base_url: "", api: "" }), true);
  assert.equal(validConnection({ provider: "openrouter", model: "~openai/gpt-luna-latest", base_url: "", api: "" }), true);
  assert.equal(validConnection({ provider: "custom", model: "qwen/qwen3.5-9b", base_url: "http://172.27.80.1:1234/v1", api: "openai-completions" }), true);
  for (const bad of [
    { provider: "openai", model: "gpt 5", base_url: "", api: "" },
    { provider: "openai", model: "m", base_url: "http://h/v1", api: "openai-completions" },
    { provider: "custom", model: "m", base_url: "", api: "openai-completions" },
    { provider: "custom", model: "m", base_url: "http://h/v1", api: "bedrock" },
    { provider: "openai", model: "m", base_url: "", api: "", api_key: "sk" },
    { provider: "openai", model: "m" }, null, [],
  ]) assert.equal(validConnection(bad), false, JSON.stringify(bad));
  for (const url of ["http://u:p@h/v1", "http://h/v1?key=1", "http://h/v1#x", "file:///etc/passwd", "http://h/\"v1", "not a url"]) {
    assert.equal(validEndpointUrl(url), false, url);
  }
});

test("the active connection hides endpoint fields unless the provider is custom", () => {
  assert.deepEqual(connectionOf({ executor: { provider: "openai", model: "gpt-5.5", endpoint: { base_url: "", api: "openai-completions" } } }),
    { provider: "openai", model: "gpt-5.5", base_url: "", api: "" });
  assert.deepEqual(connectionOf({ executor: { provider: "custom", model: "m", endpoint: { base_url: "http://h/v1", api: "openai-responses" } } }),
    { provider: "custom", model: "m", base_url: "http://h/v1", api: "openai-responses" });
  assert.equal(connectionRowVisible("executor.endpoint.base_url", "openai"), false);
  assert.equal(connectionRowVisible("executor.endpoint.base_url", "custom"), true);
  assert.equal(connectionRowVisible("executor.model", "openai"), true);
});

test("connection rows edit through one key and one reviewed JSON candidate", () => {
  const meta = key => ({ key, edit_key: "executor.connection", source: "project", editable: true, restart: true, type: "text", choices: [], minimum: null, maximum: null });
  const rows = settingRows({ executor: { provider: "openai", model: "gpt-5.5" } }, [meta("executor.provider"), meta("executor.model")]);
  assert.deepEqual(rows.map(row => [row.editKey, row.input]), [["executor.connection", "connection"], ["executor.connection", "connection"]]);
  const proposed = { provider: "custom", model: "m", base_url: "http://h/v1", api: "openai-completions" };
  const pending = { base_revision: "a".repeat(64), candidate_revision: "b".repeat(64), key: "executor.connection",
    value: JSON.stringify(proposed), proposed_value: proposed, created_at: "2026-11-02T00:00:00Z", restart_required: true };
  assert.equal(validPendingConfig(pending), true);
  assert.equal(validPendingConfig({ ...pending, value: "custom" }), false);
  assert.equal(validPendingConfig({ ...pending, proposed_value: "custom", value: "custom" }), false);
});

test("the credential note names the provider's variable, an optional endpoint key or ChatGPT", () => {
  assert.equal(validProviderCatalog(catalog), true);
  assert.equal(validProviderCatalog({ ...catalog, custom: { id: "custom", variable: "bad name", apis: [] } }), false);
  for (const locale of locales) {
    assert.ok(credentialNote("openai", catalog, locale).includes("OPENAI_API_KEY"), locale);
    assert.ok(credentialNote("custom", catalog, locale).includes("ADORE_ENDPOINT_API_KEY"), locale);
    assert.equal(credentialNote("chatgpt", catalog, locale), connectionCopy[locale].chatgptNote);
    assert.equal(providerName("custom", catalog, locale), connectionCopy[locale].custom);
  }
  assert.equal(providerName("openai", catalog, "de"), "OpenAI");
});

test("connection copy has the same keys in every locale and translated help", () => {
  const keys = Object.keys(connectionCopy.en).sort();
  for (const locale of ["fr", "de", "ro"]) {
    assert.deepEqual(Object.keys(connectionCopy[locale]).sort(), keys, locale);
    assert.notEqual(connectionCopy[locale].baseUrlHelp, connectionCopy.en.baseUrlHelp, locale);
    assert.ok(connectionCopy[locale].baseUrlHelp.includes("host.docker.internal"), locale);
  }
});

test("Test AI connection reasons each have their own guidance in every locale", () => {
  const project = "1".repeat(32), revision = "a".repeat(64);
  const reasons = { "credential-missing": "missing", "credential-invalid": "auth", "connection-failed": "connection",
    "model-unavailable": "model", "rate-limited": "rate", "provider-error": "provider" };
  for (const [reason, key] of Object.entries(reasons)) {
    const value = { project_id: project, revision, checked_at: "2026-11-01T02:00:00+00:00", executor: "pi",
      model: "qwen/qwen3.5-9b", ready: false, reason };
    assert.equal(validModelEvidence(value, project, revision, "pi", "qwen/qwen3.5-9b"), true, reason);
    for (const locale of locales) assert.equal(modelGuidance(reason, locale), modelConnectionCopy[locale][key], `${locale} ${reason}`);
  }
  assert.equal(new Set(Object.values(reasons).map(key => modelConnectionCopy.en[key])).size, Object.keys(reasons).length);
});

test("ChatGPT offers the subscription's models and the catalog must carry them", () => {
  assert.deepEqual(providerModels("chatgpt", catalog), ["gpt-5.6-luna"]);
  assert.deepEqual(providerModels("openai", catalog), ["gpt-5.5"]);
  assert.deepEqual(providerModels("chatgpt", null), []);
  assert.equal(validProviderCatalog(catalog), true);
  assert.equal(validProviderCatalog({ ...catalog, chatgpt: { id: "chatgpt" } }), false);
  for (const locale of locales) assert.doesNotMatch(connectionCopy[locale].chatgptNote, /not available|indisponible|nicht verfügbar|nu este încă/i);
});

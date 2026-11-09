/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { chatgptCopy, readChatGptStart, readChatGptView } from "../src/chatgptCopy.ts";
import { errorMessages } from "../src/errors.ts";

const locales = ["en", "fr", "de", "ro"];
const codes = ["chatgpt_redirect_invalid", "chatgpt_state_mismatch", "chatgpt_sign_in_not_pending",
  "chatgpt_credential_unreadable", "chatgpt_not_eligible", "chatgpt_access_denied", "chatgpt_code_rejected",
  "chatgpt_sign_in_refused", "chatgpt_sign_in_unavailable", "chatgpt_helper_failed"];

test("the sign-in panel has the same non-empty copy in every locale", () => {
  const keys = Object.keys(chatgptCopy.en).sort();
  for (const locale of locales) {
    assert.deepEqual(Object.keys(chatgptCopy[locale]).sort(), keys, locale);
    for (const key of keys) assert.ok(chatgptCopy[locale][key].trim(), `${locale}.${key}`);
  }
});

test("every refusal and failure has its own sentence in every locale", () => {
  for (const locale of locales) {
    const sentences = codes.map(code => errorMessages[locale][code]);
    assert.ok(sentences.every(text => typeof text === "string" && text.length > 20), locale);
    assert.equal(new Set(sentences).size, codes.length, locale);
  }
  assert.match(errorMessages.en.chatgpt_not_eligible, /cannot share/);
});

test("status and start transports are exact", () => {
  assert.deepEqual(readChatGptView({ status: "sign-in-again", pending: false }), { status: "sign-in-again", pending: false });
  for (const bad of [null, {}, { status: "signed-in" }, { status: "maybe", pending: false },
    { status: "signed-in", pending: "no" }, { status: "signed-in", pending: false, token: "x" }]) {
    assert.throws(() => readChatGptView(bad));
  }
  const link = "https://auth.openai.com/api/accounts/authorize?state=s";
  assert.equal(readChatGptStart({ authorize_url: link, expires_in: 900 }).authorize_url, link);
  for (const bad of [{ authorize_url: "https://evil.example/authorize", expires_in: 900 },
    { authorize_url: link, expires_in: 0 }, { authorize_url: link }, { authorize_url: link, expires_in: 900, extra: 1 }]) {
    assert.throws(() => readChatGptStart(bad));
  }
});

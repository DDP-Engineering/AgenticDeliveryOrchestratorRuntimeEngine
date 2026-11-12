/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { localFailureText, modelFailureText, modelTestHelp, validLocalProbe } from "../src/localDiagnostics.ts";

test("four locales distinguish local executor causes and safe exit status", () => {
  for (const locale of ["en", "fr", "de", "ro"]) {
    const texts = new Set();
    for (const reason of ["node-missing", "node-incompatible", "node-invalid", "pi-missing", "credential-missing", "executor-exit", "timeout"]) {
      const text = localFailureText(locale, {ready: false, reason, exit_code: reason === "executor-exit" ? 7 : null});
      assert.ok(text.length > 20); texts.add(text);
      if (reason === "executor-exit") assert.match(text, /7/);
    }
    assert.equal(texts.size, 7);
    assert.ok(validLocalProbe({ready: false, reason: "node-incompatible", exit_code: 0}, false));
    assert.ok(!validLocalProbe({ready: true, reason: "node-incompatible", exit_code: 0}, true));
    assert.equal(modelTestHelp(locale, true), modelTestHelp(locale, false));
    assert.ok(modelTestHelp(locale, true).length > 20);
    assert.notEqual(modelFailureText(locale, "tool-call-failed"), modelFailureText(locale, "credential-invalid"));
    assert.notEqual(modelFailureText(locale, "model-unavailable"), modelFailureText(locale, "connection-failed"));
    assert.ok(!modelFailureText(locale, "PRIVATE-OUTPUT").includes("PRIVATE"));
  }
});

// Render the actual view from source, without writing build assets or starting a browser.
test("Summary renders the local notice once and the explicit model cause", async () => {
  const {buildSync} = await import("esbuild");
  const {createRequire, Module} = await import("node:module");
  const require = createRequire(import.meta.url);
  const React = require("react");
  const {renderToStaticMarkup} = require("react-dom/server");
  function loadView(name) {
    const source = new URL(`../src/${name}.tsx`, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
    const code = buildSync({entryPoints: [source], bundle: true, platform: "node", format: "cjs", packages: "external", write: false, logLevel: "silent"}).outputFiles[0].text;
    const compiled = new Module(import.meta.url);
    compiled.paths = require.resolve.paths("react");
    compiled._compile(code, `${name}-render.cjs`);
    return compiled.exports;
  }
  const {ReadinessEvidence} = loadView("ReadinessEvidence");
  const {ModelConnection} = loadView("ModelConnection");
  const {localCopy} = await import("../src/localExecution.ts");
  const evidence = {workflow: "direct", checks: {git: true, forge_cli: true, forge_auth: true, container_runtime: true, executor_cli: false}, local_probe: {ready: false, reason: "node-incompatible", exit_code: 0}};
  for (const locale of ["en", "fr", "de", "ro"]) {
    const html = renderToStaticMarkup(React.createElement(ReadinessEvidence, {evidence, locale, local: true, modelReason: "unused", modelEvidence: {ready: false, reason: "credential-invalid", executor: "pi", model: "openai/test"}}));
    const escaped = text => renderToStaticMarkup(React.createElement("span", null, text)).replace(/^<span>|<\/span>$/g, "");
    assert.equal(html.split(escaped(localCopy[locale].notice)).length - 1, 1);
    assert.ok(html.includes(escaped(modelFailureText(locale, "credential-invalid"))));
    assert.ok(html.includes(escaped(localCopy[locale].nodeIncompatible)));
    const {workflowCopy} = await import("../src/readiness.ts");
    for (const workflow of ["aegis", "direct", "not-inspected"]) {
      const markup = renderToStaticMarkup(React.createElement(ReadinessEvidence, {evidence:{...evidence, workflow},locale,local:false}));
      assert.ok(markup.includes('class="workflow-information"'));
      assert.ok(markup.includes(escaped(workflowCopy[locale][workflow])));
      assert.ok(!markup.includes("aegis.toml"));
    }
    const project = "1".repeat(32), revision = "a".repeat(64);
    const view = renderToStaticMarkup(React.createElement(ModelConnection, {project, revision, locale, local: true, executor: "pi", model: "openai/test", saved: {project_id: project, revision, checked_at: "2020-01-01T00:00:00Z", executor: "pi", model: "openai/test", ready: false, reason: "tool-call-failed"}}));
    assert.ok(view.includes(escaped(modelTestHelp(locale, true))));
    assert.ok(view.includes(escaped(modelFailureText(locale, "tool-call-failed"))));
  }
});

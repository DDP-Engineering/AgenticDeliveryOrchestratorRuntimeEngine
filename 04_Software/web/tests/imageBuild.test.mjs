/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { test } from "node:test";
import assert from "node:assert/strict";
import { validImageBinding, validImageDraft, validImageOperation, validImageView, imageCopy } from "../src/imageBuild.ts";
import { validPendingConfig } from "../src/settings.ts";

const binding = { id: "a".repeat(32), project_id: "b".repeat(32), config_revision: "c".repeat(64),
  runtime: "docker", runtime_identity: "daemon", base_id: "sha256:" + "d".repeat(64),
  image_id: "sha256:" + "e".repeat(64), context_sha256: "f".repeat(64), draft_revision: "1".repeat(64),
  verified_checks: ["opencode --version", "rustc --version"] };

test("closed image bindings and pending review preserve exact verified identity", () => {
  assert.equal(validImageBinding(binding), true);
  for (const changes of [{id: "other"}, {image_id: "latest"}, {verified_checks: []},
      {extra: "secret"}, {project_id: null}]) assert.equal(validImageBinding({...binding, ...changes}), false);
  const pending = { base_revision: binding.config_revision, candidate_revision: "2".repeat(64),
    key: "container.image", value: binding.image_id, proposed_value: binding.image_id,
    created_at: "2026-10-07T12:00:00Z", restart_required: true, image_build: binding };
  assert.equal(validPendingConfig(pending), true);
  assert.equal(validPendingConfig({...pending, value: "latest", proposed_value: "latest"}), false);
  assert.equal(validPendingConfig({...pending, image_build: {...binding, config_revision: "3".repeat(64)}}), false);
});

test("operation phases and complete project snapshots fail closed", () => {
  const operation = {...binding, phase:"verified", tag:"adore-built-"+binding.project_id+":"+binding.id,
    error:"",host:{system:"Windows",account:"worker",machine:"server"}};
  assert.equal(validImageOperation(operation), true);
  for(const changes of [{phase:["verified"]},{phase:"unknown"},{verified_checks:[]},
      {error:"image_failed"},{extra:"control"},{host:{system:"Windows"}}])
    assert.equal(validImageOperation({...operation,...changes}), false);
  const view={project_id:binding.project_id,backend:"container",draft:null,
    template:"FROM base",template_checks:[],operations:[operation]};
  assert.equal(validImageView(view,binding.project_id),true);
  assert.equal(validImageView(view,"f".repeat(32)),false);
  assert.equal(validImageView({...view,operations:[operation,operation]},binding.project_id),false);
});

test("bounded draft input and all locales explain separate readiness responsibilities", () => {
  const draft = {schema: 1, project_id: binding.project_id, dockerfile: "FROM base\nUSER adore\n",
    checks: ["rustc --version"], network: "none", timeout_seconds: 600, memory_mib: 1024, revision: "1".repeat(64)};
  assert.equal(validImageDraft(draft), true);
  for (const changes of [{network: "host"}, {checks: [null]}, {memory_mib: true}, {revision: ""},
      {dockerfile: "x".repeat(65537)}, {schema: true}, {other: true}])
    assert.equal(validImageDraft({...draft, ...changes}), false);
  for (const locale of ["en", "ro", "de", "fr"]) {
    assert.ok(imageCopy[locale].help.length > 60);
    assert.ok(imageCopy[locale].local.length > 40);
    assert.ok(imageCopy[locale].uncertain.length > 40);
  }
});

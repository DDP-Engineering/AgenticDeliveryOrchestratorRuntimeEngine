/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import test from "node:test";
import assert from "node:assert/strict";
import { deleteCloneCopy, validClonePreview } from "../src/deleteCloneCopy.ts";

test("clone preview offers removal only with a path and explains every kept clone", () => {
  assert.equal(validClonePreview({ clone: { path: "/srv/adore/repos/a", removable: true, reason: "" } }), true);
  assert.equal(validClonePreview({ clone: { path: "", removable: true, reason: "" } }), false);
  assert.equal(validClonePreview({ clone: { path: "/srv/adore/repos/a", removable: true, reason: "shared" } }), false);
  assert.equal(validClonePreview({ clone: { path: "/elsewhere/a", removable: false, reason: "outside-repos" } }), true);
  assert.equal(validClonePreview({ clone: { path: "", removable: false, reason: "unknown" } }), true);
  assert.equal(validClonePreview({ clone: { path: "/srv/adore/repos/a", removable: false, reason: "other" } }), false);
  assert.equal(validClonePreview(null), false);
  // Every reason the server can send has a sentence in every locale.
  const reasons = ["outside-repos", "missing", "not-a-clone", "origin-mismatch", "shared", "worktrees", "uncommitted", "unknown"];
  for (const [locale, copy] of Object.entries(deleteCloneCopy))
    for (const reason of reasons) assert.ok(copy.reasons[reason]?.trim(), `${locale}: ${reason}`);
});

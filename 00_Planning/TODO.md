<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE TODO

This file tracks remaining ADORE planning items only. Historical findings that
have already been implemented, documented, and regression-tested should stay in
the component docs, changelog, or prerequisite reports instead of accumulating
here.

## Executor Live Verification

The executor factory and configuration surface now support `opencode`, `pi`,
`codex`, and `qwen`. The remaining work is live validation and any provider-
specific hardening that cannot be proven by offline unit tests.

### Pi

Run a live Pi spike inside the ADORE executor image:

- build the executor image with `@earendil-works/pi-coding-agent`;
- confirm `pi -p --mode json --model <model> <prompt>` can run the target
  `.agentic` workflow non-interactively;
- verify session header parsing and identify whether Pi exposes usable token
  usage/cost fields;
- solve or document the project-trust requirement for headless runs, because Pi
  loads project-local `.pi` guardrails and skills only after the project is
  trusted.

### Codex

Run a live Codex spike through the existing `[executor.codex]` command template:

- confirm `codex exec --json` works with ADORE's staged `CODEX_HOME`;
- verify `codex exec resume --last` continues gate context as expected;
- pin the JSON event fields used for session/thread id and token/cost capture;
- verify the `--ignore-user-config --disable plugins` posture prevents host
  Codex desktop/plugin state from leaking into the run.

### Qwen Code

Run a live Qwen spike through the existing `[executor.qwen]` command template:

- confirm `qwen -p --output-format json` works inside the project image;
- verify stateless per-gate execution is sufficient for the ADORE gate contract;
- pin Qwen's JSON stats shape for usage/cost capture if available;
- verify the target repo's `.qwen` hooks and deny list are loaded in headless
  mode and block push/MR/merge attempts.

## Prompt And Comment Text Externalization

Move ADORE-owned prompt text out of Python once the current prompt behavior is
stable enough to treat as a maintained interface.

Keep the hidden machine marker grammar in `adore/identity.py`, where creation and
parsing stay together. Externalize only human-visible wording and executor
instructions, for example:

- gate prompts;
- retry and delivery-fix prompts;
- clarification, reminder, timeout, and draft-MR comments;
- status comment wording.

The external format should preserve testability: prompt/comment rendering must
still be covered by offline tests, and secret redaction must remain enforced
before executor-visible text is emitted.

## Runtime-Project Image Scaffolding

ADORE now supports per-profile runtime-project images and documents the base
image pattern. The remaining improvement is an operator-friendly way to create a
project image during setup.

Possible implementation:

- add a documented `docker/Dockerfile.executor-project.template` or generate one
  from `adore init`;
- let the operator specify required tools during setup and translate them into
  a starting Dockerfile plus `[container] required_tool_checks`;
- keep the output project-specific and editable, rather than baking arbitrary
  project dependencies into the ADORE base image;
- document how the generated project image should be rebuilt when the target
  repository's toolchain changes.

## Native App / Executable Packaging

The current supported distribution is the trimmed runtime bundle created by
`02_Tools/package_runtime.*`. Investigate whether ADORE should also ship as:

- a Windows executable or installer;
- a Linux package;
- a self-contained app directory with a bundled Python runtime.

Any packaging change must preserve the current security properties:

- no secrets in the package;
- no target-project config bundled by default;
- package version derived from `04_Software/pyproject.toml`;
- generated package contents verified in CI or by the release script.

## Operator Presentation Material

The Markdown + SVG operator cheat sheets are implemented under
`01_Documentation/Operator_Cheat_Sheets/`. A separate stakeholder-facing deck is
still useful.

Create a short presentation for new operators and sponsors that explains:

- what ADORE does and does not do;
- the human merge boundary;
- the ticket/label lifecycle;
- profiles and runtime-project images;
- safe operating modes and monitoring;
- where to find the detailed operator cheat sheets.

Use a format that can be updated from repo-controlled sources where possible.

For the branding slide, use the AEGIS/ADORE mythology hook recorded in
`00_Planning/Onboarding_Wizards_Analysis_And_Proposal.md` §2.0: AEGIS is
Athena's shield ("under the aegis of" = under the protection and authority
of), ADORE bears the shield and delivers but never merges, and the
WAEGIS/WADORE wizards play Hephaestus, the smith who forged the aegis.

## Production Security Sign-Off

The container egress implementation exists, including `open`, `none`, and
`allowlist-proxy` modes plus deployment guardrails for unattended operation.
Before any unattended production run, each runtime project still needs an
explicit security decision.

For each project, record:

- selected `[container.egress] mode`;
- allowlisted hosts when using `allowlist-proxy`;
- model provider and data-flow approval;
- executor credential mode (`api-key` vs pilot-only `host-auth`);
- which secret names are allowed through `[executor] env_keys`;
- whether runtime dependency resolution is allowed during runs or dependencies
  must be pre-provisioned in the project image.

Open egress may remain acceptable for supervised pilots, but production should
prefer `allowlist-proxy` or a pre-provisioned no-network image.

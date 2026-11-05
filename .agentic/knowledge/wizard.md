<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Assisted configuration wizard

## Routing

Use this page for `adore init`, scripted setup answers and generated profile
TOML. Start at `04_Software/adore/wizard.py`; verify with
`04_Software/tests/test_wizard.py`. Shared config validation belongs to
`config.md`, and HTTP project creation to `web-interface.md`.

## Purpose and boundaries

Candidate validation precedes profile publication; prepare-only returns the candidate without probes or writes.

`04_Software/adore/wizard.py` implements `adore init`: it turns explicit
operator answers and environment guidance into a minimal, validated
runtime-project profile rather than asking an operator to hand-author every
TOML section.

## Public interface

`run_wizard()` drives the setup flow. `FieldSpec` and `ask()` provide the
validated prompt primitive; `ConsoleAsker` is interactive and `ScriptedAsker`
drives `--answers FILE` and offline tests. The result is a profile config and
metadata created through `ProfileStore`. With `prepare_only=True`, it returns
`WizardSetup(name, document, metadata)` without probes or profile writes; bad
answers carry `WizardError.field` for safe API findings.

## Invariants

Every answer is validated before output. Non-interactive bad input fails fast;
interactive input is re-prompted. The assembled TOML is written to a temporary
file and passed through the same `load_config`/`validate_config` path as the
runtime before it can replace a profile, so invalid profiles are never saved.
Secrets are never written: only required environment-variable names are
derived. The wizard validates branch-rule compatibility and reports missing
tools or unsuitable AEGIS payloads as setup guidance, not a hidden mutation.
Pi is the only coding agent, so the wizard asks no agent question. It asks the
provider (default `openai`, validated against `pi_providers.provider_ids()`:
a Pi API-key provider id, `chatgpt` for the server's ChatGPT Plus/Pro sign-in,
or `custom`), for `custom` the endpoint base URL and API type (default
`openai-completions`), then the model ID within the provider (`MODEL_ID_RE`;
default `gpt-5.5` only for `openai`). For `chatgpt` the model prompt lists the
catalog's `chatgpt_models` and defaults to the first of them; a container profile uses the api-key auth mode without a
question, and a local profile asks the installed native Pi argv (default
`branding.PI_NATIVE_COMMAND`) and api-key or existing (the local account's own
Pi sign-in). It writes `[executor] provider`, `model`, `command` only when it
differs from the default, `env_keys = []` (additional names; the provider's key
variable always reaches Pi) and `[executor.endpoint]` for `custom`. Container
next steps name the provider's credential variable. For `chatgpt` the first
next step is to sign in with ChatGPT once for the server in the web interface
(Settings -> Agent and model -> Sign in with ChatGPT). Config validation refuses
a `chatgpt` profile with a local run or a stage limit above 3000 s, so the
wizard never saves one.
The reported-cost prompt accepts finite nonnegative USD input; zero disables
that cap for a subscription/local model while other run limits remain.

Prepare-only mode validates the same candidate offline, with Docker as the
unprovided runtime default. CLI mode retains probes and persistence.

## Key behaviors

- REQ-FUNC-bf8a9a47: recommended/custom CLI launch defaults and web enrollment use 20; explicit values retain authority. Recommended active time is 5400 seconds, cumulative with waiting excluded. Wizard assembly tests inject only their known branch-rule process; full validation and golden assertions remain, and test_branch_naming.py exercises actual matching and process failures.

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Setup asks container/local first. Local profiles skip runtime/image detection, select managed Pi and an optional tools PATH and state execution-account/tooling responsibility. Prepared profiles include execution/local sections; web enrollment keeps pickup stopped.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-FUNC-3d8f6f5e` - offline preparation and field-specific safe findings;
  `test_web_enrollment.py` proves preparation and preserved default CLI mode.

- `REQ-FUNC-2df31adf` - the wizard writes Pi's provider and model without an agent choice.
- `REQ-FUNC-5771eecc` - generated configuration validates before it is saved.
- `REQ-FUNC-6c82ad42` - invalid/unconfirmed answers cannot create or overwrite a profile.
- `REQ-FUNC-7ce5b17a` - web project creation reuses guided answers and the
  same validation path.
- `REQ-REL-94e653aa` - generated cost caps retain the DCP subscription mode.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


It composes doctor probes, profiles, typed config validation, and an injected
command runner. `04_Software/tests/test_wizard.py` covers a golden valid
profile, answer failures, overwrite/confirmation safeguards, deterministic
non-interactive output, branch checks, and the no-invalid-save guarantee.

The wizard gives install and verify instructions for managed Pi; it never runs npm.

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

`04_Software/adore/wizard.py` implements `adore init`: it turns explicit
operator answers and environment guidance into a minimal, validated
runtime-project profile rather than asking an operator to hand-author every
TOML section.

## Public interface

`run_wizard()` drives the setup flow. `FieldSpec` and `ask()` provide the
validated prompt primitive; `ConsoleAsker` is interactive and `ScriptedAsker`
drives `--answers FILE` and offline tests. The result is a profile config and
metadata created through `ProfileStore`.

## Invariants

Every answer is validated before output. Non-interactive bad input fails fast;
interactive input is re-prompted. The assembled TOML is written to a temporary
file and passed through the same `load_config`/`validate_config` path as the
runtime before it can replace a profile, so invalid profiles are never saved.
Secrets are never written: only required environment-variable names are
derived. The wizard validates branch-rule compatibility and reports missing
tools or unsuitable AEGIS payloads as setup guidance, not a hidden mutation.
ADORE-managed host-auth staging is offered only for OpenCode and Codex; an
unsupported Pi/Qwen staging answer fails before the profile is written.

## Key behaviors

- `REQ-FUNC-5771eecc` - generated configuration validates before it is saved.
- `REQ-FUNC-6c82ad42` - invalid/unconfirmed answers cannot create or overwrite a profile.
- `REQ-FUNC-7ce5b17a` - web project creation reuses guided answers and the
  same validation path.

## Architecture

```mermaid
flowchart LR
    answers([Console or scripted answers]) --> wizard[run_wizard]
    wizard --> probes[Doctor probes]
    wizard --> validate[load_config and validate_config]
    validate --> profiles[(ProfileStore)]
```

The wizard generates a candidate and saves it only after validation succeeds.

## Files

It composes doctor probes, profiles, typed config validation, and an injected
command runner. `04_Software/tests/test_wizard.py` covers a golden valid
profile, answer failures, overwrite/confirmation safeguards, deterministic
non-interactive output, branch checks, and the no-invalid-save guarantee.

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Portable settings

## Routing

Use for portable working rules, `adore-project-settings`, JSON schema 1,
deterministic checksums and strict roundtrip. Start at
`04_Software/adore/portable_settings.py`, test with `test_portable_settings.py`.
Admin/API/UI integration belongs to `web-interface.md`; exact TOML enrollment
belongs to that page and profiles remain owned by `profiles.md`.

## Purpose and boundaries

Export validated active configuration as a complete closed portable allowlist;
parse only compatible defaults for new projects. Web API owns authorization,
snapshot IO and downloads. Profiles/enrollment own target identity, host setup
and paused publication. This module writes no project or runtime state.

## Public interface

`export_settings(bytes) -> bytes`; `parse_settings(bytes) -> dict`;
`PortableSettingsError.code` is value-free. `PORTABLE_FIELDS` enumerates every
included polling/readiness/recovery/budget key. Exact domains and omissions live
in `01_Documentation/Portable_Project_Settings.md` and linked active spec.

## Invariants

Export validates recognized declared source before the lenient loader and
existing config validator. Parsing requires complete keys, strict types/bounds,
no duplicate keys and the exact installed source version/contract. Checksum
detects changes without authenticity. No secrets, host/identity/access data,
credential/endpoint references, pending records or price history are copied.
Limits remain bounded; unknown fields and incompatible sources fail closed.

## Key behaviors

- REQ-FUNC-ffb9ed29 / REQ-UX-b75e1df8: Portable working rules retain their allowlist and exclude backend, local account/home/PATH/environment/cgroup and runtime identity. local.environment is a recognized named string map for metadata, not a transferable working rule.

Native ownership/auth route to `local-execution.md`; focused proof is
`04_Software/tests/test_local_execution.py`.


- `REQ-DATA-9528fad6`: deterministic complete portable roundtrip and strict errors.
- `REQ-SEC-f96d80d4`: authoritative Admin export with no unauthorized metadata.
- `REQ-UX-302fbce4`: localized explicit scoped preview and exact-byte download.

## Architecture

```mermaid
flowchart LR
    source[(Active TOML bytes)] --> export[export_settings]
    export --> structure[Declared structure and Config validation]
    structure --> allowlist[PORTABLE_FIELDS projection]
    allowlist --> package[Canonical envelope and checksum]
    package --> parse[parse_settings]
    parse --> result([Compatible portable defaults])
```

Both public boundaries validate complete inputs; no partial result or enrollment
write occurs. Source release provenance uses `adore.__version__`.

## Files

- `04_Software/tests/test_local_execution.py`: native integration/negative proof.


- `04_Software/adore/portable_settings.py`
- `04_Software/tests/test_portable_settings.py`
- `05_SoftwareDocu/Component_Portable_Settings.md`

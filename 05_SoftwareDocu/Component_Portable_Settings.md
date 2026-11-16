# Portable settings

## 1. Purpose

`adore.portable_settings` exports and parses strict portable working-rule defaults
for compatible new projects. The web API owns authorization and active snapshot
reading; enrollment and profile persistence remain separate responsibilities.

## 2. Responsibilities

Validate complete recognized source structure before typed configuration loading; validate configuration; project only `PORTABLE_FIELDS`;
encode deterministic schema-1 JSON; reject duplicate/malformed/incompatible
packages and return fresh portable values. Secrets, identity, host locations,
access state and references remain outside the format.

The complete portable rule allowlist contains fifteen fields; readiness contains acceptance and priority booleans. Extra component fields reject at source and JSON boundaries.

## 3. Implementation Overview

`export_settings(raw: bytes) -> bytes` checks 512-KiB UTF-8 TOML, recursively
recognizes dataclass-derived section/key/types and explicit dynamic-map domains,
uses `load_config`/`validate_config`, validates the closed portable projection
and returns canonical bytes. Executor command tables are recognized according
to their command/model structure, while the effective `commands` read-model
property is rejected as a declared TOML key. Unknown keys fail closed.
`parse_settings(raw: bytes) -> dict` bounds input to 64 KiB, rejects duplicate
keys/nonfinite constants, validates complete shape/types/domains and exact source
compatibility, verifies checksum and returns settings. Errors are value-free
`PortableSettingsError`; incompatible source has `portable_settings_incompatible`.

## 4. Dependencies

Python standard library; `adore.__version__` and the existing configuration
component. No external CLI, worker, network, runtime state or new dependency.

## 5. Inputs And Outputs

Active configuration bytes produce `kind=adore-project-settings`,
`schema_version=1`, exact source product/version/contract, complete settings and
checksum. Source version comes from the package, with no duplicate release
constant. The parser produces only the four-section allowlist. Export's private
temporary configuration snapshot is automatically removed on success or failure.

## 6. Data Contracts

The enumerated allowlist, numeric/list bounds, omissions, new-project default,
canonical encoding and exact-version compatibility are defined in
[Portable project settings](../01_Documentation/Portable_Project_Settings.md)
and the current `PORTABLE_FIELDS`/parser in `04_Software/adore/portable_settings.py`.
Checksum offers change detection only. Input errors never echo source values.

## 7. Workflow Integration

Admin-only `/config/portable-settings` exports one authoritative active snapshot.
Optional checksum binding returns a conflict if included values/source changed;
the API rechecks immutable project ownership after reading/exporting the snapshot.
Portable JSON export is an administrator API operation. The browser exposes
server-ready TOML and image-source export, not a separate portable JSON panel.
Target enrollment must supply and confirm target-host configuration separately.

## 9. Validation And Tests

`test_portable_settings.py` proves public roundtrip, deterministic source/default
projection, nested exclusion, strict schemas/types/bounds, source compatibility,
duplicates, corrupt checksums/encoding/size/depth. `test_web_portable_settings.py`
proves Admin snapshot/download and preview binding, Dev/session denial before IO,
missing/corrupt source errors and pending omission. Offline Chromium scenarios
cover the current raw-configuration export/import interface. Live acceptance
remains human work.

## 10. Limitations

The conservative format omits all credential/endpoint references, arbitrary
free-text policies and host-bound configuration. Consumers require exact installed
source version; no migration, enrollment write or import UI is provided here.

## Native execution contract

Portable working rules retain their allowlist and exclude backend, local account/PATH and runtime identity.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused native proof:
`04_Software/tests/test_local_execution.py`.

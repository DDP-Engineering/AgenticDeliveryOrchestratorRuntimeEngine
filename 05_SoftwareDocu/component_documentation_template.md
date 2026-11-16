# Component documentation template

Describe only current behavior. Keep relevant sections and link related contracts rather than
copying manuals, task journals or implementation history. Use repository-relative source paths.

## Purpose and sources

What the component owns and the files implementing it. State important boundaries.

## Public contract

Entry points, inputs/outputs, side effects and relationships to adjacent components.
Use examples only when the contract needs one; type hints already describe ordinary parameters.

## Invariants and failures

Persistence, identity, authorization and ownership rules; typed failures at trust boundaries.
Describe current refusal/recovery behavior without migration promises or speculative features.

## Dependencies and verification

Direct dependencies and focused public-contract tests. Name remaining manual acceptance boundaries
when applicable. Do not prescribe a full suite for unrelated documentation/setup changes.

Operator procedures belong in `01_Documentation`; automation usage in `02_Tools`.
AEGIS knowledge contains routing and essential invariants, with links to this component contract.

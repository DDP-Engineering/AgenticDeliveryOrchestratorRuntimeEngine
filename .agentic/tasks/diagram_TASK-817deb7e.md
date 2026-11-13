<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-817deb7e diagrams

Illustrates `## Design` in `TASK-817deb7e.md`. The Design text is authoritative.

## Structure

Node map: recipe_sources and executor_recipes added; RawConfiguration, app and
build_bundle changed; immutable Git reader, canonical base sources and operator
Docker Compose builder reused unchanged. Connections below are newly added.

```mermaid
flowchart LR
  classDef added fill:#e1f5ee,stroke:#0f6e56
  classDef changed fill:#faeeda,stroke:#854f0b
  classDef removed stroke-dasharray:4 3
  UI["RawConfiguration"]:::changed ==> API["web.app recipe routes"]:::changed
  API ==> Store["executor_recipes.RecipeStore"]:::added
  API ==> Resolve["executor_recipes.resolve_recipe"]:::added
  Git["build_bundle Git source reader"] ==> Resolve
  Builtin["docker/Dockerfile.executor-base and Pi inputs"] ==> Resolve
  Store ==> Resolve
  Resolve ==> Source["recipe_sources.recipe_archive"]:::added
  Source ==> Export["build_bundle.export_build_bundle"]:::changed
  Export ==> Builder["Operator Docker Compose build"]
```

## Sequence

```mermaid
sequenceDiagram
  participant Admin
  participant API as web.app
  participant Recipes as executor_recipes
  Admin->>API: Select source file / preview
  API->>Recipes: Validate sources and dependency graph
  Recipes-->>Admin: Candidate digest and missing bases
  Admin->>API: Save with observed binding digest
  API->>Recipes: Retain source and atomically bind image
  Admin->>API: Export saved project configuration
  API->>Recipes: Resolve every local base
  Recipes-->>Admin: Complete source ZIP or missing-base error
```

## State

```mermaid
stateDiagram-v2
  [*] --> Missing
  Missing --> Incomplete: Attach sources needing local bases
  Missing --> Available: Attach complete sources / bundled base
  Incomplete --> Available: Attach missing bases
  Available --> Available: Save reviewed replacement
  Available --> Incomplete: Replacement needs another base
  Available --> Refused: Corrupt stored bytes/schema
  Incomplete --> Refused: Corrupt stored bytes/schema
  Refused --> Missing: Operator deletes named corrupt data
```

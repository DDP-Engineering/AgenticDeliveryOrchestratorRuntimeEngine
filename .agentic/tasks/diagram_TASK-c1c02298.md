<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-c1c02298 diagrams

Illustrates `## Design` in `TASK-c1c02298.md`. The Design text is authoritative.

## Structure

Node classification from Design: `App.tsx`, `TicketWorkspace.tsx`, `ticketCopy.ts`,
`styles.css`, `PreferenceInput`/preference routes and `WebStore` are changed;
`forgeMarkdown.ts`, `ticketPreferences.ts`, `react-markdown` and `remark-gfm`
are added. `safeEvidenceLink` is reused unchanged. No nodes are removed.
New mode/renderer/library edges are added; the existing preference API/store
path, ticket copy/style connections and metadata safe-link call remain unchanged.

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    app["App.tsx"]:::changed ==> workspace["TicketWorkspace.tsx"]:::changed
    app ==> prefs["ticketPreferences.ts"]:::added
    workspace ==> prefs
    app --> api["PreferenceInput / preference routes"]:::changed
    api --> store["WebStore schema 16"]:::changed
    workspace ==> renderer["forgeMarkdown.ts / ForgeMarkdown"]:::added
    renderer ==> markdown["react-markdown"]:::added
    renderer ==> gfm["remark-gfm"]:::added
    workspace --> copy["ticketCopy.ts"]:::changed
    renderer ==> copy
    workspace --> css["styles.css"]:::changed
    workspace --> safe["safeEvidenceLink"]
```

## Sequence

```mermaid
sequenceDiagram
    participant User
    participant App as App.tsx
    participant View as TicketWorkspace.tsx
    participant API as preference routes
    participant Store as WebStore
    participant Render as ForgeMarkdown
    App->>API: GET /me/preferences (authenticated)
    API->>Store: preferences(current user)
    Store-->>API: ticket_body_mode null or enum
    API-->>App: validated preferences
    App->>View: mode (null defaults rendered)
    User->>View: Read tickets / Details
    View->>Render: source body and locale
    Render-->>View: React elements, literal HTML, inert images
    User->>View: Select Markdown source
    View->>App: request mode source
    App->>View: optimistic source, pending
    App->>API: PATCH ticket_body_mode source + CSRF
    API->>Store: transactional partial update
    alt successful save
        Store-->>API: current saved preferences
        API-->>App: success
        App->>View: source confirmed, pending cleared
    else invalid request or storage/network failure
        API-->>App: error
        App->>View: rollback confirmed mode, localized error, retry available
    end
    Note over App,View: Session generation suppresses old-account completions
```

## State

```mermaid
stateDiagram-v2
    [*] --> Rendered: absent preference
    [*] --> Source: saved source
    state "Rendered (confirmed)" as Rendered
    state "Markdown source (confirmed)" as Source
    state "Source shown / save pending" as SavingSource
    state "Rendered shown / save pending" as SavingRendered
    Rendered --> SavingSource: explicit source selection
    SavingSource --> Source: PATCH succeeds
    SavingSource --> Rendered: PATCH fails / show error
    Source --> SavingRendered: explicit rendered selection
    SavingRendered --> Rendered: PATCH succeeds
    SavingRendered --> Source: PATCH fails / show error
    Source --> Rendered: clear session
    SavingSource --> Rendered: clear session / ignore late response
    SavingRendered --> Rendered: clear session / ignore late response
```

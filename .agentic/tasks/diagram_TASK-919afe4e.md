<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Users credential dialogs

## Structure

```mermaid
flowchart LR
    Users --> AccountActionDialog
    AccountActionDialog --> UserCreation
    AccountActionDialog --> PasswordResetForm
    UserCreation --> NewPasswordFields
    PasswordResetForm --> NewPasswordFields
```

## Sequence

```mermaid
sequenceDiagram
    Admin->>PasswordResetForm: Save matching passwords
    PasswordResetForm->>API: Reset selected account
    API-->>PasswordResetForm: Verified result
```

## State

```mermaid
stateDiagram-v2
    Users --> Credentials: Add user or Reset password
    Credentials --> Users: Dismiss
    Credentials --> Users: Reset succeeded
    Credentials --> Credentials: Mismatch or failure
```

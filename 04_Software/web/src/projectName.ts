/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
/**
 * Project profile name rule shared by the Enroll new project and Import project config forms.
 * Browsers compile pattern attributes with the `v` flag, where a literal hyphen
 * inside a character class must be escaped.
 */
export const PROJECT_NAME_PATTERN = String.raw`[a-z0-9][a-z0-9._\-]{0,63}`;

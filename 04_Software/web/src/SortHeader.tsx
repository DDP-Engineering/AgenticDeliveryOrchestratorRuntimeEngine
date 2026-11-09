/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/

/** Column heading that sorts its table; aria-sort names the active direction. */
export function SortHeader<K extends string>({ label, sortKey, activeKey, descending, onSort }: { label: string; sortKey: K; activeKey: K; descending: boolean; onSort: (key: K) => void }) {
  const active = sortKey === activeKey;
  return <th aria-sort={active ? descending ? "descending" : "ascending" : undefined}><button type="button" className="sort-heading" onClick={() => onSort(sortKey)}>{label}<span aria-hidden="true">{active ? descending ? "↓" : "↑" : "↕"}</span></button></th>;
}

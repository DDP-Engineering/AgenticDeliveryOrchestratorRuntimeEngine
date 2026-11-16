/** Column heading that sorts its table; aria-sort names the active direction. */
export function SortHeader<K extends string>({ label, sortKey, activeKey, descending, onSort }: { label: string; sortKey: K; activeKey: K; descending: boolean; onSort: (key: K) => void }) {
  const active = sortKey === activeKey;
  return <th aria-sort={active ? descending ? "descending" : "ascending" : undefined}><button type="button" className="sort-heading" onClick={() => onSort(sortKey)}>{label}<span aria-hidden="true">{active ? descending ? "↓" : "↑" : "↕"}</span></button></th>;
}

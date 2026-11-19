import { useState } from "react";
import type { MessageKey } from "./i18n";
import type { Metrics } from "./metrics";
import { PagedTable } from "./PagedTable";
import { SortHeader } from "./SortHeader";

type ProjectRow = { name: string; repo?: string; metrics: Metrics };
type Column = {
  label: string;
  value: (row: ProjectRow) => string | number | null | undefined;
  display?: (row: ProjectRow) => string;
  detail?: (row: ProjectRow) => string | undefined;
};

export function ProjectComparisonTable({ rows, measures, locale, t }: {
  rows: ProjectRow[];
  measures: Column[];
  locale: string;
  t: (key: MessageKey) => string;
}) {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<{ key: string; descending: boolean }>({ key: "0", descending: false });
  const columns: Column[] = [{ label: t("project"), value: row => row.name, detail: row => row.repo }, ...measures];
  const column = columns[Number(sort.key)];
  const collator = new Intl.Collator(locale, { numeric: true, sensitivity: "base" });
  const number = new Intl.NumberFormat(locale);
  const display = (item: Column, row: ProjectRow) => {
    if (item.display) return item.display(row);
    const value = item.value(row);
    return typeof value === "number" ? number.format(value) : String(value ?? "");
  };
  const visible = rows.filter(row => columns.every((item, index) => {
    const query = filters[index]?.trim().toLocaleLowerCase(locale);
    return !query || [display(item, row), item.detail?.(row)].some(text => text?.toLocaleLowerCase(locale).includes(query));
  })).sort((left, right) => {
    const a = column.value(left), b = column.value(right);
    if (a == null || b == null) return a == null ? (b == null ? 0 : 1) : -1;
    const difference = typeof a === "number" && typeof b === "number" ? a - b : collator.compare(String(a), String(b));
    return sort.descending ? -difference : difference;
  });
  return <section className="panel">
    <h2>{t("projectComparison")}</h2>
    <PagedTable alwaysControls t={t} resetKey={JSON.stringify([filters, sort])}>
      <table aria-label={t("projectComparison")}>
        <thead>
          <tr>{columns.map((item, index) => <SortHeader key={index} label={item.label} sortKey={String(index)} activeKey={sort.key}
            descending={sort.descending} onSort={key => setSort(previous => ({ key, descending: previous.key === key && !previous.descending }))} />)}</tr>
          <tr>{columns.map((item, index) => <td key={index}>
            <input className="comparison-filter" type="search" aria-label={item.label} value={filters[index] ?? ""}
              onChange={event => setFilters({ ...filters, [index]: event.target.value })} />
          </td>)}</tr>
        </thead>
        <tbody>{visible.map(row => <tr key={row.name}>{columns.map((item, index) => <td key={index}>
          {display(item, row)}{item.detail?.(row) && <small className="field-hint">{item.detail(row)}</small>}
        </td>)}</tr>)}</tbody>
      </table>
    </PagedTable>
    {!visible.length && <p className="empty" role="status">{t("noMatchingProjects")}</p>}
  </section>;
}

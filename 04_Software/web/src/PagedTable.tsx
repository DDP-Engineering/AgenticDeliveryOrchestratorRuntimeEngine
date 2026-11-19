import { Children, cloneElement, isValidElement, useEffect, useState, type ReactElement, type ReactNode } from "react";
import type { MessageKey } from "./i18n";

export function PagedTable({ t, children, alwaysControls=false, onPageChange, resetKey }: { t: (key: MessageKey) => string; children: ReactElement<{ children?: ReactNode }>; alwaysControls?:boolean; onPageChange?:(page:number)=>void; resetKey?:string }) {
  const [size, setSize] = useState<10 | 25 | 50 | "all">(10);
  const [requestedPage, setRequestedPage] = useState(0);
  useEffect(() => setRequestedPage(0), [resetKey]);
  const sections = Children.toArray(children.props.children);
  const body = sections.find(section => isValidElement<{ children?: ReactNode }>(section) && section.type === "tbody") as ReactElement<{ children?: ReactNode }> | undefined;
  const rows = body ? Children.toArray(body.props.children) : [];
  const pageCount = size === "all" ? 1 : Math.max(1, Math.ceil(rows.length / size));
  const page = Math.min(requestedPage, pageCount - 1);
  useEffect(()=>onPageChange?.(page),[page,onPageChange]);
  const visible = size === "all" ? rows : rows.slice(page * size, (page + 1) * size);
  const table = body ? cloneElement(children, undefined, ...sections.map(section => section === body ? cloneElement(body, undefined, ...visible) : section)) : children;
  return <><div className="table-scroll">{table}</div>{(alwaysControls || rows.length > 10) && <div className="page-controls"><label>{t("rowsPerPage")}<select value={size} onChange={event => { setSize(event.target.value === "all" ? "all" : Number(event.target.value) as 10 | 25 | 50); setRequestedPage(0); }}><option value="10">10</option><option value="25">25</option><option value="50">50</option><option value="all">{t("all")}</option></select></label>{size !== "all" && <><button className="ghost" disabled={page === 0} onClick={() => setRequestedPage(page - 1)}>{t("previous")}</button><span>{rows.length ? page * size + 1 : 0}–{Math.min((page + 1) * size, rows.length)} / {rows.length}</span><button className="ghost" disabled={page + 1 >= pageCount} onClick={() => setRequestedPage(page + 1)}>{t("next")}</button></>}</div>}</>;
}

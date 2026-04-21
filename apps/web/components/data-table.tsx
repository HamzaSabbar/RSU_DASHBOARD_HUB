import { formatInteger } from "@/lib/format";

export type TableRow = {
  label: string;
  value: number;
  delta?: number | null;
  pctChange?: number | null;
};

export function DataTable({
  headers,
  rows,
}: {
  headers: [string, string] | [string, string, string, string];
  rows: TableRow[];
}): React.ReactElement {
  const showDelta = headers.length === 4;
  return (
    <div className="overflow-hidden rounded-md border border-brand-border">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-brand-muted">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-brand-border">
          {rows.map((r) => (
            <tr key={r.label}>
              <td className="px-3 py-2">{r.label}</td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {formatInteger(r.value)}
              </td>
              {showDelta ? (
                <>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {r.delta != null ? formatInteger(r.delta) : ""}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-mono tabular-nums ${
                      r.pctChange != null && r.pctChange >= 0
                        ? "text-brand-positive"
                        : r.pctChange != null
                          ? "text-brand-danger"
                          : ""
                    }`}
                  >
                    {r.pctChange != null
                      ? `${r.pctChange > 0 ? "+" : ""}${r.pctChange.toFixed(1).replace(".", ",")}%`
                      : ""}
                  </td>
                </>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import type { RezimeCsvRow } from "@/api/rezime";

type SortKey = "percentJasno" | "total";
type SortDir = "asc" | "desc";

export interface RezimeCsvTableProps {
  rows: RezimeCsvRow[];
}

export function RezimeCsvTable({ rows }: RezimeCsvTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("percentJasno");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const diff = av - bv;
      return sortDir === "asc" ? diff : -diff;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "percentJasno" ? "asc" : "desc");
    }
  }

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        CSV nema redova ili nije mogao biti učitan.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="px-3 py-2 font-medium">Pitanje</th>
            <th className="px-3 py-2 font-medium">Tagovi</th>
            <th className="px-3 py-2 font-medium text-center">Da</th>
            <th className="px-3 py-2 font-medium text-center">Ne</th>
            <SortableHeader
              label="Total"
              active={sortKey === "total"}
              dir={sortDir}
              onClick={() => toggleSort("total")}
            />
            <SortableHeader
              label="% Jasno"
              active={sortKey === "percentJasno"}
              dir={sortDir}
              onClick={() => toggleSort("percentJasno")}
            />
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, idx) => (
            <tr
              key={`${row.pitanje}-${idx}`}
              className="border-t hover:bg-muted/30"
            >
              <td className="px-3 py-2 max-w-md">
                <p className="line-clamp-2 font-medium" title={row.pitanje}>
                  {row.pitanje}
                </p>
                {row.odgovor && (
                  <p
                    className="line-clamp-1 text-xs text-muted-foreground"
                    title={row.odgovor}
                  >
                    {row.odgovor}
                  </p>
                )}
              </td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  {row.tagovi.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-[10px]">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </td>
              <td className="px-3 py-2 text-center tabular-nums">
                {row.yesCount}
              </td>
              <td className="px-3 py-2 text-center tabular-nums">
                {row.noCount}
              </td>
              <td className="px-3 py-2 text-center tabular-nums">
                {row.total}
              </td>
              <td className="px-3 py-2 text-center">
                <Badge variant={percentVariant(row.percentJasno, row.total)}>
                  {row.total === 0 ? "—" : `${row.percentJasno}%`}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function percentVariant(
  percent: number,
  total: number,
): "destructive" | "warning" | "success" | "secondary" {
  if (total === 0) return "secondary";
  if (percent < 60) return "destructive";
  if (percent < 80) return "warning";
  return "success";
}

function SortableHeader({
  label,
  active,
  dir,
  onClick,
}: {
  label: string;
  active: boolean;
  dir: SortDir;
  onClick: () => void;
}) {
  const Icon = !active ? ArrowUpDown : dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <th className="px-3 py-2 font-medium text-center">
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "inline-flex items-center gap-1 hover:text-foreground transition-colors",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        <Icon className="h-3 w-3" />
      </button>
    </th>
  );
}

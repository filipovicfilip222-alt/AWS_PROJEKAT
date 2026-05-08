import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Calendar,
  Clock,
  FileBarChart2,
  Sparkles,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { listMojiTermini } from "@/api/termini";
import type { ProfMojiTermin } from "@/api/types";

const REZIME_STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "outline" | "destructive" | "warning" | "success" | "info"
> = {
  generated: "success",
  csv_only: "warning",
  failed: "destructive",
  regenerating: "info",
};

const REZIME_STATUS_LABEL: Record<string, string> = {
  generated: "AI insights",
  csv_only: "Samo CSV",
  failed: "Greška",
  regenerating: "U toku",
};

function formatRelative(iso?: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "upravo sad";
  if (minutes < 60) return `pre ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `pre ${hours} h`;
  const days = Math.round(hours / 24);
  if (days < 30) return `pre ${days} d`;
  return date.toLocaleDateString("sr-Latn-RS");
}

function compareDesc(a: ProfMojiTermin, b: ProfMojiTermin): number {
  const aKey = `${a.datum}T${a.vremeOd ?? "00:00"}`;
  const bKey = `${b.datum}T${b.vremeOd ?? "00:00"}`;
  return bKey.localeCompare(aKey);
}

export default function Rezimei() {
  const q = useQuery({ queryKey: ["moji-termini"], queryFn: listMojiTermini });

  const items = (q.data?.items ?? [])
    .filter((t) => !!t.rezimeGeneratedAt)
    .sort(compareDesc);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-1">
            <Sparkles className="h-3 w-3" /> AI insights
          </span>
        }
        title="Rezimei"
        description="Termini sa generisanim rezime-om: feedback agregacija + AI uvidi. Generišu se 24h pre svakog termina."
      />

      {q.isLoading ? (
        <Spinner label="Učitavanje..." />
      ) : items.length === 0 ? (
        <EmptyState
          icon={FileBarChart2}
          title="Još nemaš generisanih rezime-a"
          description="Rezimei se generišu automatski 24h pre svakog termina. Možeš ih i ručno generisati iz rezime stranice termina."
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((t) => (
            <div
              key={t.terminId}
              className="rounded-xl border border-border bg-card shadow-card p-5 flex flex-col gap-4"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <FileBarChart2 className="h-4 w-4 text-accent shrink-0" />
                    <div className="text-base font-semibold tracking-tight leading-snug truncate">
                      {t.predmet}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 inline-flex items-center gap-1.5">
                    <Calendar className="h-3 w-3" />
                    {t.datum}
                    <Clock className="h-3 w-3 ml-2" />
                    {t.vremeOd}–{t.vremeDo}
                  </div>
                </div>
                {t.rezimeStatus && (
                  <Badge
                    variant={REZIME_STATUS_VARIANT[t.rezimeStatus] ?? "secondary"}
                  >
                    {REZIME_STATUS_LABEL[t.rezimeStatus] ?? t.rezimeStatus}
                  </Badge>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-md bg-muted px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Generisan
                  </div>
                  <div className="text-sm font-medium mt-0.5">
                    {formatRelative(t.rezimeGeneratedAt)}
                  </div>
                </div>
                <div className="rounded-md bg-muted px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Rezervacije
                  </div>
                  <div className="text-sm font-medium inline-flex items-center gap-1.5 mt-0.5">
                    <Users className="h-3.5 w-3.5" />
                    {t.rezervisanih}/{t.brojSlotova}
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-border/60 mt-auto">
                <Link to={`/profesor/termini/${t.terminId}/rezime`}>
                  <Button size="sm" className="w-full">
                    Otvori rezime
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

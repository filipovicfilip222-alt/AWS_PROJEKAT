import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Calendar,
  ClipboardList,
  Clock,
  FileBarChart2,
  PlusCircle,
  Settings2,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { listMojiTermini } from "@/api/termini";

function isPastOrToday(date: string): boolean {
  if (!date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(date + "T00:00:00");
  return target.getTime() <= today.getTime();
}

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "outline" | "destructive" | "warning" | "success" | "info"
> = {
  draft: "secondary",
  ai_processing: "info",
  ai_failed: "destructive",
  pending_approval: "warning",
  objavljen: "success",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  ai_processing: "AI obrada",
  ai_failed: "AI greška",
  pending_approval: "Approve",
  objavljen: "Objavljen",
};

export default function MojiTermini() {
  const q = useQuery({ queryKey: ["moji-termini"], queryFn: listMojiTermini });
  const items = q.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Profesor"
        title="Moji termini"
        description="Pregled svih tvojih termina po statusu, sa brzim akcijama."
        actions={
          <Link to="/profesor/termini/novi">
            <Button>
              <PlusCircle className="h-4 w-4" />
              Novi termin
            </Button>
          </Link>
        }
      />

      {q.isLoading ? (
        <Spinner label="Učitavanje..." />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="Još nemaš nijedan termin"
          description="Kreiraj prvi termin, uploaduj materijal, AI generiše Q&A i objavi studentima."
          action={
            <Link to="/profesor/termini/novi">
              <Button>
                <PlusCircle className="h-4 w-4" />
                Kreiraj termin
              </Button>
            </Link>
          }
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
                  <div className="text-base font-semibold tracking-tight leading-snug">
                    {t.predmet}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5 inline-flex items-center gap-1.5">
                    <Calendar className="h-3 w-3" />
                    {t.datum}
                    <Clock className="h-3 w-3 ml-2" />
                    {t.vremeOd}–{t.vremeDo}
                  </div>
                </div>
                <Badge variant={STATUS_VARIANT[t.status] ?? "secondary"}>
                  {STATUS_LABEL[t.status] ?? t.status}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-md bg-muted px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Slotovi
                  </div>
                  <div className="text-sm font-medium inline-flex items-center gap-1.5 mt-0.5">
                    <Users className="h-3.5 w-3.5" />
                    {t.rezervisanih}/{t.brojSlotova}
                  </div>
                </div>
                <div className="rounded-md bg-muted px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Pitanja
                  </div>
                  <div className="text-sm font-medium inline-flex items-center gap-1.5 mt-0.5">
                    <ClipboardList className="h-3.5 w-3.5" />
                    {t.hasQA ? "spremno" : "nema"}
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5 pt-3 border-t border-border/60 mt-auto">
                <Link to={`/termini/${t.terminId}`}>
                  <Button size="xs" variant="outline">
                    Detalji
                  </Button>
                </Link>
                <Link to={`/profesor/termini/${t.terminId}/uredi`}>
                  <Button size="xs" variant="outline">
                    <Settings2 className="h-3 w-3" />
                    Uredi
                  </Button>
                </Link>
                <Link to={`/profesor/termini/${t.terminId}/pitanja`}>
                  <Button size="xs" variant="outline">
                    <ClipboardList className="h-3 w-3" />
                    Pitanja
                  </Button>
                </Link>
                {(isPastOrToday(t.datum) || t.rezimeGeneratedAt) && (
                  <Link to={`/profesor/termini/${t.terminId}/rezime`}>
                    <Button size="xs" variant="outline">
                      <FileBarChart2 className="h-3 w-3" />
                      Rezime
                    </Button>
                  </Link>
                )}
                <Link
                  to={`/termini/${t.terminId}`}
                  className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-foreground hover:gap-1.5 transition-all"
                >
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

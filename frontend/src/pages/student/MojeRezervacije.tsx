import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Calendar, Clock, Users, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { listMojeRezervacije, otkaziRezervaciju } from "@/api/slots";
import { toApiError } from "@/api/client";
import type { Reservation } from "@/api/types";
import { cn } from "@/utils/cn";

function isFuture(r: Reservation): boolean {
  const now = new Date();
  const d = new Date(`${r.datum}T${r.vremeDo}`);
  return d.getTime() >= now.getTime();
}

function compareAsc(a: Reservation, b: Reservation): number {
  return `${a.datum}T${a.vremeOd}`.localeCompare(`${b.datum}T${b.vremeOd}`);
}

function diffHumanFromNow(datum: string, vremeOd: string): string {
  const target = new Date(`${datum}T${vremeOd}`);
  const diffMs = target.getTime() - Date.now();
  if (Number.isNaN(diffMs)) return "";
  if (diffMs < 0) return "u toku ili prošlo";
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 60) return `za ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `za ${hours} h`;
  const days = Math.round(hours / 24);
  return `za ${days} d`;
}

export default function MojeRezervacije() {
  const qc = useQueryClient();
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const rezQ = useQuery({ queryKey: ["moje-rez"], queryFn: listMojeRezervacije });
  const otkazi = useMutation({
    mutationFn: ({ tid, idx }: { tid: string; idx: string }) =>
      otkaziRezervaciju(tid, idx),
    onSuccess: () => {
      setErrMsg(null);
      qc.invalidateQueries({ queryKey: ["moje-rez"] });
    },
    onError: (e) => setErrMsg(toApiError(e).message),
  });

  const grouped = useMemo(() => {
    const items = rezQ.data?.items ?? [];
    const upcoming = items.filter(isFuture).sort(compareAsc);
    const past = items.filter((r) => !isFuture(r)).sort((a, b) => -compareAsc(a, b));
    return { upcoming, past };
  }, [rezQ.data]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Moje konsultacije"
        title="Moje rezervacije"
        description="Pregled aktivnih i prošlih termina. Otkazivanje je moguće do 24h pre konsultacije."
        actions={
          <Link to="/student/termini">
            <Button variant="outline" size="sm">
              <Calendar className="h-4 w-4" />
              Pregledaj termine
            </Button>
          </Link>
        }
      />

      {errMsg && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {errMsg}
        </div>
      )}

      {rezQ.isLoading ? (
        <Spinner label="Učitavanje..." />
      ) : grouped.upcoming.length === 0 && grouped.past.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="Nemaš rezervacija"
          description="Pretraži termine i rezerviši slot za sledeće konsultacije."
          action={
            <Link to="/student/termini">
              <Button size="sm">
                Pregledaj termine
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          }
        />
      ) : (
        <>
          {/* Upcoming */}
          {grouped.upcoming.length > 0 && (
            <Section
              title="Predstoje"
              count={grouped.upcoming.length}
              tone="primary"
            >
              <div className="grid gap-3 md:grid-cols-2">
                {grouped.upcoming.map((r) => (
                  <ReservationCard
                    key={`${r.terminId}#${r.slotIndex}`}
                    r={r}
                    upcoming
                    canCancel={otkazi.isPending}
                    onCancel={() =>
                      otkazi.mutate({ tid: r.terminId, idx: r.slotIndex })
                    }
                  />
                ))}
              </div>
            </Section>
          )}

          {/* Past */}
          {grouped.past.length > 0 && (
            <Section title="Završeno" count={grouped.past.length} tone="muted">
              <div className="grid gap-3 md:grid-cols-2">
                {grouped.past.map((r) => (
                  <ReservationCard
                    key={`${r.terminId}#${r.slotIndex}`}
                    r={r}
                    upcoming={false}
                  />
                ))}
              </div>
            </Section>
          )}
        </>
      )}
    </div>
  );
}

function Section({
  title,
  count,
  tone,
  children,
}: {
  title: string;
  count: number;
  tone: "primary" | "muted";
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-base">{title}</h2>
          <Badge variant={tone === "primary" ? "default" : "secondary"}>{count}</Badge>
        </div>
      </div>
      {children}
    </div>
  );
}

function ReservationCard({
  r,
  upcoming,
  canCancel,
  onCancel,
}: {
  r: Reservation;
  upcoming: boolean;
  canCancel?: boolean;
  onCancel?: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-card shadow-card p-5 flex flex-col gap-4",
        upcoming ? "border-border" : "border-border/60 opacity-90",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-base font-semibold tracking-tight leading-snug">
            {r.predmet}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5 truncate">
            {r.profesorIme}
          </div>
        </div>
        {upcoming ? (
          <Badge variant="info">{diffHumanFromNow(r.datum, r.vremeOd)}</Badge>
        ) : (
          <Badge variant="secondary">završeno</Badge>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-md bg-muted px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Datum
          </div>
          <div className="text-sm font-medium inline-flex items-center gap-1.5 mt-0.5">
            <Calendar className="h-3.5 w-3.5" />
            {r.datum}
          </div>
        </div>
        <div className="rounded-md bg-muted px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Vreme
          </div>
          <div className="text-sm font-medium inline-flex items-center gap-1.5 mt-0.5">
            <Clock className="h-3.5 w-3.5" />
            {r.vremeOd}–{r.vremeDo}
          </div>
        </div>
      </div>
      {typeof r.brojStudenata === "number" && r.brojStudenata > 1 && (
        <div className="text-xs text-muted-foreground inline-flex items-center gap-1.5">
          <Users className="h-3 w-3" />
          {r.brojStudenata} studenata u slot-u
        </div>
      )}
      <div className="flex items-center justify-between pt-3 border-t border-border/60 mt-auto">
        <Link to={`/termini/${r.terminId}`}>
          <Button variant="outline" size="sm">
            Otvori termin
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
        {upcoming && onCancel && (
          <Button
            variant="ghost"
            size="sm"
            disabled={canCancel}
            onClick={onCancel}
            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            <X className="h-3.5 w-3.5" />
            Otkaži
          </Button>
        )}
      </div>
    </div>
  );
}

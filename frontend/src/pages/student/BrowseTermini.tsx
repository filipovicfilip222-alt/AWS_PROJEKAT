import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Calendar,
  Clock,
  GraduationCap,
  MessageSquare,
  Search,
  Sparkles,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { listTermini } from "@/api/termini";
import { listPredmeti } from "@/api/search";

export default function BrowseTermini() {
  const [predmet, setPredmet] = useState<string>("");
  const [datum, setDatum] = useState<string>("");

  const predmetiQ = useQuery({ queryKey: ["predmeti"], queryFn: listPredmeti });
  const terminiQ = useQuery({
    queryKey: ["termini", predmet, datum],
    queryFn: () =>
      listTermini({
        ...(predmet ? { predmet } : {}),
        ...(datum ? { datum } : {}),
        status: "objavljen",
      }),
  });

  const items = terminiQ.data?.items ?? [];
  const hasFilters = !!(predmet || datum);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Konsultacije"
        title="Termini"
        description="Pretraži objavljene konsultacije po predmetu i datumu, izaberi slobodan slot."
        actions={
          <Link to="/student/pitaj">
            <Button variant="accent" size="sm">
              <Sparkles className="h-4 w-4" />
              Pitaj pre zakazivanja
            </Button>
          </Link>
        }
      />

      {/* Filter bar */}
      <div className="rounded-xl border border-border bg-card shadow-card p-4 sm:p-5 space-y-4">
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <div className="space-y-1.5">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Predmet
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select
                value={predmet}
                onChange={(e) => setPredmet(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-card pl-9 pr-8 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 appearance-none"
              >
                <option value="">Svi predmeti</option>
                {predmetiQ.data?.items.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Datum
            </label>
            <Input
              type="date"
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
            />
          </div>
          {hasFilters && (
            <Button
              variant="ghost"
              size="default"
              onClick={() => {
                setPredmet("");
                setDatum("");
              }}
              className="md:self-end"
            >
              <X className="h-4 w-4" />
              Resetuj
            </Button>
          )}
        </div>
        {hasFilters && (
          <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-border/60">
            <span className="text-xs text-muted-foreground">Aktivni filteri:</span>
            {predmet && (
              <Badge variant="outline" className="gap-1">
                <GraduationCap className="h-3 w-3" />
                {predmet}
                <button
                  onClick={() => setPredmet("")}
                  className="ml-0.5 hover:text-foreground"
                  aria-label="Ukloni"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
            {datum && (
              <Badge variant="outline" className="gap-1">
                <Calendar className="h-3 w-3" />
                {datum}
                <button
                  onClick={() => setDatum("")}
                  className="ml-0.5 hover:text-foreground"
                  aria-label="Ukloni"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
          </div>
        )}
      </div>

      {terminiQ.isLoading ? (
        <Spinner label="Učitavanje termina..." />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="Nema termina"
          description={
            hasFilters
              ? "Probaj da promeniš filtere ili ih resetuješ."
              : "Trenutno nema objavljenih termina. Vrati se kasnije."
          }
          action={
            hasFilters ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPredmet("");
                  setDatum("");
                }}
              >
                Resetuj filtere
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="text-xs text-muted-foreground">
            Pronađeno {items.length}{" "}
            {items.length === 1 ? "termin" : items.length < 5 ? "termina" : "termina"}
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {items.map((t) => (
              <Link
                key={t.terminId}
                to={`/termini/${t.terminId}`}
                className="group rounded-xl border border-border bg-card shadow-card p-5 hover:shadow-card-hover hover:-translate-y-0.5 hover:border-foreground/30 transition-all flex flex-col gap-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-base font-semibold tracking-tight leading-snug">
                      {t.predmet}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5 truncate">
                      {t.profesorIme}
                    </div>
                  </div>
                  {t.hasQA && (
                    <Badge variant="accent">
                      <MessageSquare className="h-3 w-3 mr-1" /> Q&A
                    </Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5" />
                    {t.datum}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5" />
                    {t.vremeOd}–{t.vremeDo}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-border/60 mt-auto">
                  <Badge variant="secondary">
                    {t.brojSlotova} slot{t.brojSlotova === 1 ? "" : "a"}
                  </Badge>
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-foreground group-hover:gap-2 transition-all">
                    Detalji <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

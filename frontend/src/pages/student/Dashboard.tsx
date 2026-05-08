import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  Calendar,
  Clock,
  MessageSquare,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/auth/useAuth";
import { listMojeRezervacije } from "@/api/slots";
import type { Reservation } from "@/api/types";
import { cn } from "@/utils/cn";

const QUICK_ACTIONS = [
  {
    to: "/student/pitaj",
    title: "Pitaj pre zakazivanja",
    desc: "AI pretraga kroz odobrenu Q&A bazu.",
    icon: Sparkles,
    accent: true,
  },
  {
    to: "/student/termini",
    title: "Pregled termina",
    desc: "Termini po predmetu i datumu.",
    icon: Calendar,
  },
  {
    to: "/student/rezervacije",
    title: "Moje rezervacije",
    desc: "Termini koje si već zakazao.",
    icon: BookOpen,
  },
];

function compareAsc(a: Reservation, b: Reservation): number {
  return `${a.datum}T${a.vremeOd}`.localeCompare(`${b.datum}T${b.vremeOd}`);
}

function isFuture(r: Reservation): boolean {
  const now = new Date();
  const d = new Date(`${r.datum}T${r.vremeDo}`);
  return d.getTime() >= now.getTime();
}

function formatLocaleDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("sr-Latn-RS", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export default function StudentDashboard() {
  const { user } = useAuth();
  const rezQ = useQuery({ queryKey: ["moje-rez"], queryFn: listMojeRezervacije });
  const next = (rezQ.data?.items ?? []).filter(isFuture).sort(compareAsc)[0];

  return (
    <div className="space-y-8">
      <div className="space-y-1.5">
        <h1 className="text-3xl font-semibold tracking-tight text-balance">
          Zdravo{user?.ime ? `, ${user.ime}` : ""} 👋
        </h1>
        <p className="text-muted-foreground">
          Sve što ti treba za uspešnu konsultaciju na jednom mestu.
        </p>
      </div>

      {/* Hero: next consultation */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-foreground text-background shadow-elevated">
        <div className="absolute -top-32 -right-20 h-80 w-80 rounded-full bg-accent/30 blur-3xl" />
        <div className="absolute -bottom-32 -left-20 h-80 w-80 rounded-full bg-primary/20 blur-3xl" />
        <div className="relative p-6 sm:p-8 grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-background/10 border border-background/15 px-3 py-1 text-[11px] font-medium uppercase tracking-wider">
              <Sparkles className="h-3 w-3" />
              Sledeća konsultacija
            </div>
            {next ? (
              <>
                <h2 className="font-display-soft text-2xl sm:text-3xl text-balance">
                  {next.predmet}
                </h2>
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-background/75">
                  <span className="inline-flex items-center gap-1.5">
                    <Calendar className="h-4 w-4" />
                    {formatLocaleDate(next.datum)}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Clock className="h-4 w-4" />
                    {next.vremeOd} – {next.vremeDo}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <BookOpen className="h-4 w-4" />
                    {next.profesorIme}
                  </span>
                </div>
              </>
            ) : (
              <>
                <h2 className="font-display-soft text-2xl sm:text-3xl text-balance">
                  Još nemaš zakazanu konsultaciju
                </h2>
                <p className="text-sm text-background/75 max-w-xl">
                  Pretraži termine svojih predmeta ili postavi pitanje AI tutoru pre
                  nego što rezervišeš slot.
                </p>
              </>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {next ? (
              <>
                <Link to={`/termini/${next.terminId}`}>
                  <Button
                    variant="outline"
                    className="bg-background text-foreground border-background hover:bg-background/90"
                  >
                    Otvori termin
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link to="/student/rezervacije">
                  <Button
                    variant="ghost"
                    className="text-background hover:bg-background/10"
                  >
                    Sve rezervacije
                  </Button>
                </Link>
              </>
            ) : (
              <>
                <Link to="/student/termini">
                  <Button
                    variant="outline"
                    className="bg-background text-foreground border-background hover:bg-background/90"
                  >
                    Pregledaj termine
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link to="/student/pitaj">
                  <Button
                    variant="ghost"
                    className="text-background hover:bg-background/10"
                  >
                    <Sparkles className="h-4 w-4" />
                    Pitaj AI
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="space-y-3">
        <div className="flex items-end justify-between">
          <h2 className="text-base">Brze akcije</h2>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {QUICK_ACTIONS.map(({ to, title, desc, icon: Icon, accent }) => (
            <Link key={to} to={to} className="group">
              <div
                className={cn(
                  "h-full rounded-xl border p-5 transition-all shadow-card hover:shadow-card-hover hover:-translate-y-0.5",
                  accent
                    ? "border-accent/30 bg-accent-muted"
                    : "border-border bg-card",
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-4">
                  <span
                    className={cn(
                      "inline-flex h-10 w-10 items-center justify-center rounded-lg",
                      accent
                        ? "bg-accent text-accent-foreground"
                        : "bg-foreground/5 text-foreground",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  {accent && <Badge variant="accent">AI</Badge>}
                </div>
                <h3 className="text-base leading-tight">{title}</h3>
                <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
                  {desc}
                </p>
                <div className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-foreground group-hover:gap-2 transition-all">
                  Otvori <ArrowRight className="h-3.5 w-3.5" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent reservations strip */}
      {(rezQ.data?.items ?? []).length > 0 && (
        <div className="space-y-3">
          <div className="flex items-end justify-between">
            <h2 className="text-base">Poslednje rezervacije</h2>
            <Link
              to="/student/rezervacije"
              className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
            >
              Sve <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {(rezQ.data?.items ?? []).slice(0, 3).map((r) => (
              <Link
                key={`${r.terminId}#${r.slotIndex}`}
                to={`/termini/${r.terminId}`}
                className="rounded-lg border border-border bg-card p-4 hover:border-foreground/30 hover:shadow-card-hover transition-all"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="text-sm font-semibold leading-tight">
                    {r.predmet}
                  </div>
                  <Badge variant="outline">{r.datum}</Badge>
                </div>
                <div className="text-xs text-muted-foreground inline-flex items-center gap-1.5">
                  <Clock className="h-3 w-3" />
                  {r.vremeOd}–{r.vremeDo}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Empty / hint */}
      {(rezQ.data?.items ?? []).length === 0 && !rezQ.isLoading && (
        <div className="rounded-xl border border-dashed border-border bg-card/40 p-6 text-center">
          <MessageSquare className="h-5 w-5 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">
            Tek si stigao? Probaj{" "}
            <Link to="/student/pitaj" className="font-medium text-foreground underline">
              Pitaj pre zakazivanja
            </Link>{" "}
            da vidiš šta drugi pitaju.
          </p>
        </div>
      )}
    </div>
  );
}

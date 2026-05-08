import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Calendar,
  CheckCircle2,
  ClipboardCheck,
  FileBarChart2,
  PlusCircle,
  Sparkles,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/common/StatCard";
import { useAuth } from "@/auth/useAuth";
import { listMojiTermini } from "@/api/termini";
import type { ProfMojiTermin } from "@/api/types";

function isFutureTermin(t: ProfMojiTermin): boolean {
  const target = new Date(`${t.datum}T${t.vremeDo}`);
  return target.getTime() >= Date.now();
}

export default function ProfesorDashboard() {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["moji-termini"], queryFn: listMojiTermini });
  const items = q.data?.items ?? [];

  const total = items.length;
  const upcoming = items.filter(isFutureTermin).length;
  const totalSlots = items.reduce((s, t) => s + (t.brojSlotova ?? 0), 0);
  const totalReserved = items.reduce((s, t) => s + (t.rezervisanih ?? 0), 0);
  const pendingApproval = items.filter(
    (t) => t.status === "pending_approval" || t.status === "ai_processing",
  ).length;

  const upcomingTermini = items
    .filter(isFutureTermin)
    .sort((a, b) =>
      `${a.datum}T${a.vremeOd}`.localeCompare(`${b.datum}T${b.vremeOd}`),
    )
    .slice(0, 4);

  const pendingTermini = items
    .filter(
      (t) => t.status === "pending_approval" || t.status === "ai_processing",
    )
    .slice(0, 3);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1.5">
          <h1 className="text-3xl font-semibold tracking-tight text-balance">
            Zdravo{user?.ime ? `, ${user.ime}` : ""} 👋
          </h1>
          <p className="text-muted-foreground">
            Pregled tvojih termina, AI obrade i rezervacija.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/profesor/termini/novi">
            <Button>
              <PlusCircle className="h-4 w-4" />
              Kreiraj termin
            </Button>
          </Link>
          <Link to="/profesor/rezimei">
            <Button variant="outline">
              <FileBarChart2 className="h-4 w-4" />
              Rezimei
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Predstojeći termini"
          value={upcoming}
          icon={Calendar}
          tone="primary"
          hint={`Od ukupno ${total}`}
        />
        <StatCard
          label="Rezervacije"
          value={`${totalReserved}/${totalSlots}`}
          icon={Users}
          tone="success"
          hint="Slotovi popunjeni"
        />
        <StatCard
          label="Na čekanju"
          value={pendingApproval}
          icon={ClipboardCheck}
          tone={pendingApproval > 0 ? "warning" : "neutral"}
          hint="Pitanja / AI obrada"
        />
        <StatCard
          label="Ukupno termina"
          value={total}
          icon={CheckCircle2}
          tone="accent"
        />
      </div>

      {/* Upcoming + pending */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Upcoming */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card shadow-card overflow-hidden">
          <div className="flex items-center justify-between gap-2 px-5 py-4 border-b border-border/60">
            <div>
              <h2 className="text-sm">Sledeći termini</h2>
              <p className="text-xs text-muted-foreground">
                Hronološki sortirano po datumu i vremenu.
              </p>
            </div>
            <Link
              to="/profesor/termini"
              className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
            >
              Sve <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="divide-y divide-border/60">
            {upcomingTermini.length === 0 ? (
              <div className="px-5 py-8 text-center text-sm text-muted-foreground">
                Nemaš zakazane buduće termine.
              </div>
            ) : (
              upcomingTermini.map((t) => (
                <Link
                  key={t.terminId}
                  to={`/termini/${t.terminId}`}
                  className="flex items-center gap-4 px-5 py-3.5 hover:bg-muted/60 transition-colors"
                >
                  <div className="flex flex-col items-center justify-center rounded-md border border-border bg-card w-12 py-1.5 shrink-0">
                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      {t.datum.slice(5, 7)}
                    </span>
                    <span className="text-base font-semibold leading-none">
                      {t.datum.slice(8, 10)}
                    </span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold leading-snug truncate">
                      {t.predmet}
                    </div>
                    <div className="text-xs text-muted-foreground inline-flex items-center gap-1.5 mt-0.5">
                      {t.vremeOd}–{t.vremeDo} · {t.rezervisanih}/{t.brojSlotova}{" "}
                      slotova
                    </div>
                  </div>
                  <Badge variant={t.status === "objavljen" ? "success" : "secondary"}>
                    {t.status}
                  </Badge>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Pending approvals */}
        <div className="rounded-xl border border-border bg-card shadow-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border/60">
            <h2 className="text-sm">Na čekanju</h2>
            <p className="text-xs text-muted-foreground">
              AI generisana pitanja čekaju aprovacij.
            </p>
          </div>
          <div className="divide-y divide-border/60">
            {pendingTermini.length === 0 ? (
              <div className="px-5 py-8 text-center text-sm text-muted-foreground">
                Sve uredno ✓
              </div>
            ) : (
              pendingTermini.map((t) => (
                <Link
                  key={t.terminId}
                  to={`/profesor/termini/${t.terminId}/pitanja`}
                  className="block px-5 py-3.5 hover:bg-muted/60 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold leading-snug truncate">
                        {t.predmet}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {t.datum} · {t.vremeOd}
                      </div>
                    </div>
                    <Badge variant={t.status === "ai_processing" ? "info" : "warning"}>
                      {t.status === "ai_processing" ? (
                        <span className="inline-flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> AI
                        </span>
                      ) : (
                        "approve"
                      )}
                    </Badge>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

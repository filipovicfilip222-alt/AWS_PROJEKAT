import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  GraduationCap,
  MessageSquare,
  UserPlus,
  Users,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import { getTermin } from "@/api/termini";
import { listQuestions } from "@/api/questions";
import { otkaziRezervaciju, rezervisiSlot } from "@/api/slots";
import { toApiError } from "@/api/client";
import { useAuth } from "@/auth/useAuth";
import type { Slot } from "@/api/types";
import { cn } from "@/utils/cn";

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

function studentInSlot(slot: Slot, sub: string | undefined): boolean {
  if (!sub) return false;
  return (slot.studenti ?? []).some((s) => s.studentId === sub);
}

export default function TerminDetails() {
  const { id = "" } = useParams<{ id: string }>();
  const { user } = useAuth();
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);

  const terminQ = useQuery({
    queryKey: ["termin", id],
    queryFn: () => getTermin(id),
    enabled: !!id,
  });
  const questionsQ = useQuery({
    queryKey: ["termin-questions", id],
    queryFn: () => listQuestions(id, { onlyApproved: true }),
    enabled: !!id,
  });

  const rezervisi = useMutation({
    mutationFn: (slotIndex: string) => rezervisiSlot(id, slotIndex),
    onSuccess: () => {
      setErr(null);
      qc.invalidateQueries({ queryKey: ["termin", id] });
      qc.invalidateQueries({ queryKey: ["moje-rez"] });
    },
    onError: (e) => setErr(toApiError(e).message),
  });

  const otkazi = useMutation({
    mutationFn: (slotIndex: string) => otkaziRezervaciju(id, slotIndex),
    onSuccess: () => {
      setErr(null);
      qc.invalidateQueries({ queryKey: ["termin", id] });
      qc.invalidateQueries({ queryKey: ["moje-rez"] });
    },
    onError: (e) => setErr(toApiError(e).message),
  });

  if (terminQ.isLoading) return <Spinner label="Učitavanje..." />;
  const data = terminQ.data;
  if (!data) return <p>Termin ne postoji.</p>;
  const { termin, slots } = data;

  const myExistingSlot = slots.find((s) => studentInSlot(s, user?.sub));
  const studentCanAct = user?.rola === "student" && termin.status === "objavljen";
  const maxStudenata = termin.maxStudenataPoSlotu ?? null;

  const totalReserved = slots.reduce((sum, s) => sum + (s.brojStudenata ?? 0), 0);
  const totalSlots = slots.length;
  const reservedSlots = slots.filter((s) => (s.brojStudenata ?? 0) > 0).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
          <Link
            to={user?.rola === "profesor" ? "/profesor/termini" : "/student/termini"}
            className="inline-flex items-center gap-1 hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Nazad
          </Link>
        }
        title={termin.predmet}
        description={
          <span className="inline-flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="inline-flex items-center gap-1.5">
              <GraduationCap className="h-3.5 w-3.5" />
              {termin.profesorIme}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              {termin.datum}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              {termin.vremeOd}–{termin.vremeDo}
            </span>
            {maxStudenata !== null && (
              <span className="inline-flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5" />
                limit {maxStudenata}
              </span>
            )}
          </span>
        }
        actions={
          <Badge variant={STATUS_VARIANT[termin.status] ?? "secondary"}>
            {termin.status}
          </Badge>
        }
      />

      {/* Stats strip */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        <Stat label="Slotovi" value={totalSlots} />
        <Stat
          label="Rezervisani"
          value={`${reservedSlots}/${totalSlots}`}
          tone={reservedSlots === totalSlots ? "success" : "neutral"}
        />
        <Stat label="Ukupno studenata" value={totalReserved} />
      </div>

      {termin.description && (
        <div className="rounded-xl border border-border bg-card shadow-card p-5 space-y-2">
          <h3 className="text-sm">Opis konsultacija</h3>
          <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">
            {termin.description}
          </p>
        </div>
      )}

      {/* Slotovi */}
      <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-4">
        <div>
          <h2 className="text-sm">Slotovi</h2>
          <p className="text-xs text-muted-foreground">
            {user?.rola === "student"
              ? "Možeš se priključiti slot-u sa drugim studentima ili rezervisati prazan."
              : "Pregled slotova i prijavljenih studenata."}
          </p>
        </div>
        {err && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {err}
          </div>
        )}
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {slots.map((s) => {
            const broj = s.brojStudenata ?? 0;
            const studenti = s.studenti ?? [];
            const mine = studentInSlot(s, user?.sub);
            const free = broj === 0;
            const full = maxStudenata !== null && broj >= maxStudenata;
            const blockedByOtherSlot =
              !mine && !!myExistingSlot && myExistingSlot.slotIndex !== s.slotIndex;

            return (
              <div
                key={s.slotIndex}
                className={cn(
                  "rounded-lg border p-3 transition-colors",
                  mine
                    ? "border-success/40 bg-success/5"
                    : full || blockedByOtherSlot
                      ? "border-border bg-muted/40 opacity-80"
                      : "border-border bg-card",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 font-medium text-sm">
                    <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                    {s.vremeOd}–{s.vremeDo}
                  </div>
                  {mine ? (
                    studentCanAct ? (
                      <Button
                        size="xs"
                        variant="outline"
                        disabled={otkazi.isPending}
                        onClick={() => otkazi.mutate(s.slotIndex)}
                      >
                        <X className="h-3 w-3" />
                        Otkaži
                      </Button>
                    ) : (
                      <Badge variant="success">
                        <CheckCircle2 className="h-3 w-3 mr-1" /> tvoj
                      </Badge>
                    )
                  ) : free ? (
                    studentCanAct ? (
                      <Button
                        size="xs"
                        disabled={rezervisi.isPending || blockedByOtherSlot}
                        title={
                          blockedByOtherSlot
                            ? "Već imaš rezervaciju u ovom terminu"
                            : undefined
                        }
                        onClick={() => rezervisi.mutate(s.slotIndex)}
                      >
                        Rezerviši
                      </Button>
                    ) : (
                      <Badge variant="outline">slobodan</Badge>
                    )
                  ) : full ? (
                    <Badge variant="secondary">popunjen</Badge>
                  ) : studentCanAct ? (
                    <Button
                      size="xs"
                      variant="outline"
                      disabled={rezervisi.isPending || blockedByOtherSlot}
                      title={
                        blockedByOtherSlot
                          ? "Već imaš rezervaciju u ovom terminu"
                          : undefined
                      }
                      onClick={() => rezervisi.mutate(s.slotIndex)}
                    >
                      <UserPlus className="h-3 w-3" />
                      Pridruži se
                    </Button>
                  ) : (
                    <Badge variant="secondary">
                      <Users className="h-3 w-3 mr-1" /> {broj}
                      {maxStudenata !== null ? `/${maxStudenata}` : ""}
                    </Badge>
                  )}
                </div>
                {!free && (
                  <p className="text-xs text-muted-foreground mt-1.5">
                    {user?.rola === "profesor" && studenti.length > 0 ? (
                      studenti.map((st) => st.studentIme).join(", ")
                    ) : (
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        {broj}
                        {maxStudenata !== null ? `/${maxStudenata}` : ""}{" "}
                        {broj === 1 ? "student" : "studenata"} prijavljeno
                      </span>
                    )}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Pitanja */}
      {(questionsQ.data?.items ?? []).length > 0 && (
        <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div>
              <h2 className="text-sm inline-flex items-center gap-1.5">
                <MessageSquare className="h-3.5 w-3.5" />
                Pitanja iz materijala
              </h2>
              <p className="text-xs text-muted-foreground">
                Potvrđeni Q&A par za pripremu pre konsultacija.
              </p>
            </div>
            <Badge variant="outline">{questionsQ.data?.items.length}</Badge>
          </div>
          <div className="space-y-2">
            {questionsQ.data?.items.map((q) => (
              <div
                key={q.questionId}
                className="rounded-lg border border-border bg-muted/40 p-4 space-y-2"
              >
                <p className="font-medium leading-snug">{q.pitanje}</p>
                <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">
                  {q.odgovor}
                </p>
                {q.tagovi.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {q.tagovi.map((t) => (
                      <Badge key={t} variant="outline" className="text-[10px]">
                        {t}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {user?.rola === "student" && (
        <div className="text-center">
          <Link
            to="/student/pitaj"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-foreground hover:underline"
          >
            <BookOpen className="h-4 w-4" />
            Postavi pitanje AI tutoru pre konsultacija
          </Link>
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: React.ReactNode;
  tone?: "neutral" | "success";
}) {
  return (
    <div className="rounded-lg border border-border bg-card shadow-card px-4 py-3">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "text-xl font-semibold tracking-tight mt-0.5",
          tone === "success" && "text-success",
        )}
      >
        {value}
      </div>
    </div>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowRight,
  Calendar,
  Clock,
  GraduationCap,
  Sparkles,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/common/PageHeader";
import { createTermin } from "@/api/termini";
import { toApiError } from "@/api/client";

function computeSlotCount(
  vremeOd: string,
  vremeDo: string,
  trajanjeMin: number,
): number {
  if (!vremeOd || !vremeDo || !trajanjeMin) return 0;
  const [h1, m1] = vremeOd.split(":").map(Number);
  const [h2, m2] = vremeDo.split(":").map(Number);
  const start = h1 * 60 + m1;
  const end = h2 * 60 + m2;
  if (end <= start) return 0;
  return Math.floor((end - start) / trajanjeMin);
}

export default function KreirajTermin() {
  const navigate = useNavigate();
  const [predmet, setPredmet] = useState("");
  const [datum, setDatum] = useState("");
  const [vremeOd, setVremeOd] = useState("10:00");
  const [vremeDo, setVremeDo] = useState("12:00");
  const [trajanjeSlot, setTrajanjeSlot] = useState(20);
  const [maxStudenata, setMaxStudenata] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  const slotCount = computeSlotCount(vremeOd, vremeDo, trajanjeSlot);

  const mut = useMutation({
    mutationFn: () =>
      createTermin({
        predmet,
        datum,
        vremeOd,
        vremeDo,
        trajanjeSlot,
        maxStudenataPoSlotu:
          maxStudenata.trim() === "" ? null : Number(maxStudenata),
      }),
    onSuccess: (data) => {
      navigate(`/profesor/termini/${data.terminId}/uredi`);
    },
    onError: (e) => setErr(toApiError(e).message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Profesor"
        title="Kreiraj termin"
        description="Definiši kada se konsultacije odvijaju. Posle kreiranja možeš dodati materijale za AI obradu."
      />

      <form
        className="grid gap-6 lg:grid-cols-[1fr_280px]"
        onSubmit={(e) => {
          e.preventDefault();
          setErr(null);
          mut.mutate();
        }}
      >
        <div className="space-y-5">
          {/* Section: Predmet */}
          <Section
            stepNum={1}
            title="Predmet"
            description="Naziv kursa za koji se zakazuju konsultacije."
          >
            <div className="relative">
              <GraduationCap className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                id="predmet"
                value={predmet}
                onChange={(e) => setPredmet(e.target.value)}
                placeholder="npr. Programiranje 1"
                required
                className="pl-9"
              />
            </div>
          </Section>

          {/* Section: Vreme */}
          <Section
            stepNum={2}
            title="Datum i vreme"
            description="Tačan datum i vremenski opseg konsultacija."
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="datum">Datum</Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  <Input
                    id="datum"
                    type="date"
                    value={datum}
                    onChange={(e) => setDatum(e.target.value)}
                    required
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="trajanje">Trajanje slota (min)</Label>
                <Input
                  id="trajanje"
                  type="number"
                  min={10}
                  max={60}
                  value={trajanjeSlot}
                  onChange={(e) => setTrajanjeSlot(Number(e.target.value) || 20)}
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="vo">Vreme od</Label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  <Input
                    id="vo"
                    type="time"
                    value={vremeOd}
                    onChange={(e) => setVremeOd(e.target.value)}
                    required
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="vd">Vreme do</Label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  <Input
                    id="vd"
                    type="time"
                    value={vremeDo}
                    onChange={(e) => setVremeDo(e.target.value)}
                    required
                    className="pl-9"
                  />
                </div>
              </div>
            </div>
          </Section>

          {/* Section: Limit */}
          <Section
            stepNum={3}
            title="Limit po slot-u (opciono)"
            description="Ostavi prazno ako studenti smeju neograničeno da se priključuju jednom slotu."
          >
            <div className="relative max-w-xs">
              <Users className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                id="maxStud"
                type="number"
                min={1}
                max={50}
                value={maxStudenata}
                onChange={(e) => setMaxStudenata(e.target.value)}
                placeholder="npr. 5"
                className="pl-9"
              />
            </div>
          </Section>
        </div>

        {/* Sticky summary */}
        <aside className="lg:sticky lg:top-20 self-start space-y-4">
          <div className="rounded-xl border border-border bg-card shadow-card p-5 space-y-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Pregled
              </div>
              <h3 className="font-display-soft text-xl mt-1">
                {predmet || "Predmet…"}
              </h3>
              <p className="text-sm text-muted-foreground mt-0.5">
                {datum || "—"} · {vremeOd}–{vremeDo}
              </p>
            </div>
            <div className="rounded-md bg-muted px-3 py-2 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Računato slotova</span>
              <span className="font-semibold">{slotCount || "—"}</span>
            </div>
            {err && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {err}
              </div>
            )}
            <Button
              type="submit"
              disabled={mut.isPending || !predmet || !datum || slotCount === 0}
              className="w-full"
              size="lg"
            >
              {mut.isPending ? "Kreiram..." : "Kreiraj termin"}
              <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-xs text-muted-foreground inline-flex items-start gap-1.5">
              <Sparkles className="h-3 w-3 mt-0.5 shrink-0" />
              Posle kreiranja, možeš da uploaduješ PDF/PPTX/sliku. AI generiše opis i 10
              Q&A za studente.
            </p>
          </div>
        </aside>
      </form>
    </div>
  );
}

function Section({
  stepNum,
  title,
  description,
  children,
}: {
  stepNum: number;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-4">
      <div className="flex items-start gap-3">
        <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-foreground text-background text-xs font-semibold">
          {stepNum}
        </span>
        <div className="space-y-0.5">
          <h2 className="text-sm">{title}</h2>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      <div className="space-y-3 pl-10">{children}</div>
    </div>
  );
}

import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { GraduationCap, MessageSquare, Search, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { QuestionDetailDialog } from "@/components/questions/QuestionDetailDialog";
import { listPredmeti, listTags, searchQuestions } from "@/api/search";
import type { MatchType, SearchResult } from "@/api/types";
import type { AiSourceRef } from "@/types/ai-tutor";
import { cn } from "@/utils/cn";

const MATCH_TYPE_LABEL: Record<MatchType, string> = {
  tag: "Tag",
  semantic: "Semantičko",
  hybrid: "Hibridno",
};

export default function PitajPreZakazivanja() {
  const [predmet, setPredmet] = useState<string>("");
  const [q, setQ] = useState<string>("");
  const [activeQuery, setActiveQuery] = useState<string>("");
  const [selected, setSelected] = useState<SearchResult | null>(null);

  const predmetiQ = useQuery({ queryKey: ["predmeti"], queryFn: listPredmeti });
  const tagsQ = useQuery({
    queryKey: ["tags", predmet],
    queryFn: () => listTags(predmet),
    enabled: !!predmet,
  });
  const resultsQ = useQuery({
    queryKey: ["search", predmet, activeQuery],
    queryFn: () =>
      searchQuestions(predmet, activeQuery || undefined, { mode: "hybrid" }),
    enabled: !!predmet,
  });

  const sourceMap = useMemo(() => {
    const map = new Map<string, SearchResult>();
    (resultsQ.data?.results ?? []).forEach((r) => map.set(r.questionId, r));
    return map;
  }, [resultsQ.data?.results]);

  const resolveSources = useCallback(
    (questionIds: string[]): AiSourceRef[] => {
      const refs: AiSourceRef[] = [];
      for (const qid of questionIds) {
        const r = sourceMap.get(qid);
        if (!r) continue;
        refs.push({
          questionId: r.questionId,
          pitanje: r.pitanje,
          predmet: r.predmet,
          terminId: r.terminId,
        });
      }
      return refs;
    },
    [sourceMap],
  );

  const handleChangeQuestion = useCallback(
    (questionId: string) => {
      const next = sourceMap.get(questionId);
      if (next) setSelected(next);
    },
    [sourceMap],
  );

  const results = resultsQ.data?.results ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-1 text-accent">
            <Sparkles className="h-3 w-3" /> AI pretraga
          </span>
        }
        title={
          <span className="font-display-italic text-3xl sm:text-4xl">
            &ldquo;PitajPreZakazivanja&rdquo;
          </span>
        }
        description="Pretraži bazu odobrenih pitanja po predmetu, otvori bilo koje da postaviš dodatna pitanja AI tutoru pre nego što rezervišeš slot."
      />

      {/* Step 1: Predmet picker */}
      <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-foreground text-background text-[10px]">
            1
          </span>
          Izaberi predmet
        </div>
        <div className="relative max-w-md">
          <GraduationCap className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <select
            value={predmet}
            onChange={(e) => {
              setPredmet(e.target.value);
              setQ("");
              setActiveQuery("");
            }}
            className="flex h-11 w-full rounded-md border border-input bg-card pl-9 pr-8 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 appearance-none"
          >
            <option value="">— izaberi predmet —</option>
            {predmetiQ.data?.items.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
      </div>

      {predmet && (
        <>
          {/* Step 2: Search + tags */}
          <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-foreground text-background text-[10px]">
                  2
                </span>
                Pretraži ili klikni tag
              </div>
              <p className="text-xs text-muted-foreground">
                Hibridna pretraga: tagovi + semantička sličnost.
              </p>
            </div>
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                setActiveQuery(q);
              }}
            >
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  placeholder="Npr. rekurzija, kako radi stack..."
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button type="submit">
                <Search className="h-4 w-4" /> Traži
              </Button>
            </form>
            {(tagsQ.data?.items ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-2 border-t border-border/60">
                {tagsQ.data?.items.map((t) => (
                  <button
                    key={t.tag}
                    type="button"
                    onClick={() => {
                      setQ(t.tag);
                      setActiveQuery(t.tag);
                    }}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all",
                      q === t.tag
                        ? "border-foreground bg-foreground text-background"
                        : "border-border bg-muted text-foreground hover:border-foreground/40",
                    )}
                  >
                    {t.tag}
                    <span className="text-[10px] opacity-60">{t.count}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Step 3: Results */}
          {resultsQ.isLoading ? (
            <Spinner label="Pretraga..." />
          ) : results.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="Nema direktnog poklapanja"
              description="Probaj drugu ključnu reč ili otvori neko slično pitanje pa pitaj AI tutora detaljnije."
            />
          ) : (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                {results.length} rezultat{results.length === 1 ? "" : "a"}
              </div>
              <div className="grid gap-2.5">
                {results.map((r) => (
                  <button
                    key={r.questionId}
                    type="button"
                    onClick={() => setSelected(r)}
                    className="text-left rounded-xl border border-border bg-card shadow-card p-5 hover:shadow-card-hover hover:border-accent/30 hover:bg-accent-muted/30 transition-all"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="text-base leading-snug text-balance flex-1">
                        {r.pitanje}
                      </h3>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <Badge variant="accent" className="whitespace-nowrap">
                          {Math.round(r.score * 100)}% poklapanje
                        </Badge>
                        <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                          {MATCH_TYPE_LABEL[r.matchType]}
                        </span>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground mb-3">
                      {r.profesorIme} · {r.terminDatum}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {r.tagovi.map((t) => (
                        <Badge
                          key={t}
                          variant={r.matchedTags.includes(t) ? "default" : "outline"}
                          className="text-[10px]"
                        >
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <QuestionDetailDialog
        open={!!selected}
        onOpenChange={(o) => !o && setSelected(null)}
        question={
          selected
            ? {
                questionId: selected.questionId,
                pitanje: selected.pitanje,
                odgovor: selected.odgovor,
                tagovi: selected.tagovi,
                matchedTags: selected.matchedTags,
                profesorIme: selected.profesorIme,
                terminId: selected.terminId,
                terminDatum: selected.terminDatum,
                predmet: selected.predmet,
              }
            : null
        }
        onChangeQuestion={handleChangeQuestion}
        resolveSources={resolveSources}
      />
    </div>
  );
}

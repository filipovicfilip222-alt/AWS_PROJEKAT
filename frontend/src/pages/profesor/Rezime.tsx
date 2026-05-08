import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, RefreshCw, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { RezimeInsightsView } from "@/components/rezime/RezimeInsights";
import { RezimeCsvTable } from "@/components/rezime/RezimeCsvTable";
import { getRezime, regenerateRezime } from "@/api/rezime";
import { toApiError } from "@/api/client";

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "outline" | "destructive" | "warning" | "success" | "info"
> = {
  generated: "success",
  csv_only: "warning",
  failed: "destructive",
  regenerating: "info",
};

export default function Rezime() {
  const { id = "" } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const rezimeQ = useQuery({
    queryKey: ["rezime", id],
    queryFn: () => getRezime(id),
    enabled: !!id,
  });

  const regen = useMutation({
    mutationFn: () => regenerateRezime(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rezime", id] });
    },
  });

  if (rezimeQ.isLoading) return <Spinner label="Učitavanje rezime-a..." />;

  const data = rezimeQ.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
          <Link
            to={`/profesor/termini/${id}/uredi`}
            className="inline-flex items-center gap-1 hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Nazad na termin
          </Link>
        }
        title="Rezime termina"
        description="Feedback agregacija po pitanju + AI uvidi (high-confusion, dobro razumljiva pitanja, preporuke)."
        actions={
          data?.available && (
            <div className="flex items-center gap-2 flex-wrap">
              {data.csvDownloadUrl && (
                <a href={data.csvDownloadUrl} target="_blank" rel="noreferrer noopener">
                  <Button variant="outline" size="sm">
                    <Download className="h-3.5 w-3.5" /> CSV
                  </Button>
                </a>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() => regen.mutate()}
                disabled={regen.isPending}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                {regen.isPending ? "..." : "Regeneriši"}
              </Button>
            </div>
          )
        }
      />

      {!data?.available ? (
        <div className="rounded-xl border border-border bg-card shadow-card p-6 text-center space-y-4">
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-accent-muted text-accent mx-auto">
            <Sparkles className="h-5 w-5" />
          </span>
          <div className="space-y-1">
            <h2 className="text-base">Rezime još nije generisan</h2>
            <p className="text-sm text-muted-foreground">
              {data?.message ?? "Rezime se generiše 24h pre termina."}
            </p>
          </div>
          <Button onClick={() => regen.mutate()} disabled={regen.isPending}>
            <RefreshCw className="h-4 w-4" />
            {regen.isPending ? "Pokrećem..." : "Generiši odmah"}
          </Button>
          {regen.isSuccess && (
            <p className="text-xs text-muted-foreground">
              {regen.data?.message ?? "Generisanje pokrenuto, osveži za 30 sekundi."}
            </p>
          )}
          {regen.isError && (
            <p className="text-xs text-destructive">
              {toApiError(regen.error).message}
            </p>
          )}
        </div>
      ) : (
        <>
          <div className="rounded-xl border border-border bg-card shadow-card p-5 flex flex-wrap items-center gap-4 justify-between">
            <div className="flex items-center gap-3">
              <Badge
                variant={
                  (data.status && STATUS_VARIANT[data.status]) ?? "secondary"
                }
              >
                {data.status ?? "—"}
              </Badge>
              <span className="text-sm text-muted-foreground">
                Generisan: {data.generatedAt}
              </span>
            </div>
          </div>

          {data.insights ? (
            <RezimeInsightsView insights={data.insights} />
          ) : data.status === "csv_only" ? (
            <EmptyState
              icon={Sparkles}
              title="AI insights nije dostupan"
              description="Možeš preuzeti CSV iznad ili pokrenuti regeneraciju."
            />
          ) : null}

          <div className="rounded-xl border border-border bg-card shadow-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border/60">
              <h3 className="text-sm">CSV pregled</h3>
              <p className="text-xs text-muted-foreground">
                Sva pitanja sa brojem glasova i procentom razumevanja. Klikni kolonu
                da promeniš sortiranje.
              </p>
            </div>
            <div className="p-5">
              <RezimeCsvTable rows={data.csvRows ?? []} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

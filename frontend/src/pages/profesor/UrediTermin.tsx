import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ClipboardList,
  CloudUpload,
  Eye,
  FileText,
  Globe2,
  Trash2,
  Upload,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { PageHeader } from "@/components/common/PageHeader";
import {
  deleteTermin,
  getTermin,
  objaviTermin,
  updateTermin,
} from "@/api/termini";
import { deleteMaterial, getUploadUrl, uploadFileToS3 } from "@/api/materials";
import { toApiError } from "@/api/client";
import { cn } from "@/utils/cn";

function detectFileType(name: string): "pdf" | "pptx" | "image" | null {
  const lower = name.toLowerCase();
  if (lower.endsWith(".pdf")) return "pdf";
  if (lower.endsWith(".pptx")) return "pptx";
  if (/\.(png|jpe?g|webp|gif)$/.test(lower)) return "image";
  return null;
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

export default function UrediTermin() {
  const { id = "" } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const [progress, setProgress] = useState<number | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [predmet, setPredmet] = useState<string | null>(null);
  const [datum, setDatum] = useState<string | null>(null);
  const [maxStud, setMaxStud] = useState<string | null>(null);
  const [updateErr, setUpdateErr] = useState<string | null>(null);

  const terminQ = useQuery({
    queryKey: ["termin", id],
    queryFn: () => getTermin(id),
    enabled: !!id,
    refetchInterval: (q) => {
      const status = q.state.data?.termin.status;
      return status === "ai_processing" ? 3000 : false;
    },
  });

  const update = useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateTermin(id, payload),
    onSuccess: () => {
      setUpdateErr(null);
      qc.invalidateQueries({ queryKey: ["termin", id] });
    },
    onError: (e) => setUpdateErr(toApiError(e).message),
  });

  const objavi = useMutation({
    mutationFn: () => objaviTermin(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["termin", id] }),
  });

  const delTermin = useMutation({
    mutationFn: () => deleteTermin(id),
    onSuccess: () => navigate("/profesor/termini"),
  });

  const delMat = useMutation({
    mutationFn: (mid: string) => deleteMaterial(id, mid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["termin", id] }),
  });

  const onUpload = async (file: File) => {
    setUploadErr(null);
    setProgress(0);
    try {
      const ftype = detectFileType(file.name);
      if (!ftype)
        throw new Error("Podržani formati: PDF, PPTX, slike (PNG/JPG/WEBP/GIF)");
      const url = await getUploadUrl(id, {
        fileName: file.name,
        fileType: ftype,
        sizeBytes: file.size,
      });
      await uploadFileToS3(url.url, url.fields, file, setProgress);
      setProgress(100);
      qc.invalidateQueries({ queryKey: ["termin", id] });
    } catch (e) {
      setUploadErr(toApiError(e).message);
    } finally {
      setTimeout(() => setProgress(null), 1500);
    }
  };

  if (terminQ.isLoading) return <Spinner label="Učitavanje..." />;
  const data = terminQ.data;
  if (!data) return <p>Termin ne postoji.</p>;
  const { termin, materials } = data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-1">
            Profesor · Termin
          </span>
        }
        title="Uredi termin"
        description={`${termin.datum} · ${termin.vremeOd}–${termin.vremeDo}`}
        actions={
          <Badge variant={STATUS_VARIANT[termin.status] ?? "secondary"}>
            {termin.status}
          </Badge>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          {/* Detalji */}
          <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-4">
            <div>
              <h2 className="text-sm">Detalji</h2>
              <p className="text-xs text-muted-foreground">
                Promene se ne objavljuju automatski studentima.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Predmet</Label>
                <Input
                  value={predmet ?? termin.predmet}
                  onChange={(e) => setPredmet(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Datum</Label>
                <Input
                  type="date"
                  value={datum ?? termin.datum}
                  onChange={(e) => setDatum(e.target.value)}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label>Maksimalno studenata po slotu (opciono)</Label>
                <Input
                  type="number"
                  min={1}
                  max={50}
                  value={maxStud ?? (termin.maxStudenataPoSlotu ?? "")}
                  onChange={(e) => setMaxStud(e.target.value)}
                  placeholder="Ostavi prazno za neograničeno"
                />
              </div>
            </div>
            {updateErr && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {updateErr}
              </div>
            )}
            <div className="flex items-center gap-2 pt-3 border-t border-border/60">
              <Button
                size="sm"
                disabled={update.isPending}
                onClick={() =>
                  update.mutate({
                    ...(predmet ? { predmet } : {}),
                    ...(datum ? { datum } : {}),
                    ...(maxStud !== null
                      ? {
                          maxStudenataPoSlotu:
                            maxStud.trim() === "" ? null : Number(maxStud),
                        }
                      : {}),
                  })
                }
              >
                Sačuvaj izmene
              </Button>
              <Link to={`/termini/${id}`}>
                <Button size="sm" variant="ghost">
                  <Eye className="h-3.5 w-3.5" />
                  Pregled studenta
                </Button>
              </Link>
            </div>
          </div>

          {/* Materijali */}
          <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-4">
            <div>
              <h2 className="text-sm">Materijali</h2>
              <p className="text-xs text-muted-foreground">
                Max 3 fajla, do 10 MB. AI generiše opis i 10 Q&A.
              </p>
            </div>

            <label
              className={cn(
                "flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-xl p-6 text-center transition-colors",
                materials.length >= 3 || progress !== null
                  ? "border-border/60 bg-muted/40 cursor-not-allowed"
                  : "border-border hover:border-foreground/40 hover:bg-muted/40 cursor-pointer",
              )}
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-foreground text-background">
                <CloudUpload className="h-4 w-4" />
              </span>
              <span className="text-sm font-medium">
                {materials.length >= 3
                  ? "Maksimalan broj fajlova"
                  : "Klikni ili prevuci fajl ovde"}
              </span>
              <span className="text-xs text-muted-foreground">
                PDF, PPTX, PNG, JPG, WEBP, GIF · max 10MB
              </span>
              <input
                type="file"
                className="hidden"
                accept=".pdf,.pptx,.png,.jpg,.jpeg,.webp,.gif"
                disabled={materials.length >= 3 || progress !== null}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void onUpload(file);
                  e.target.value = "";
                }}
              />
            </label>
            {progress !== null && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground inline-flex items-center gap-1.5">
                    <Upload className="h-3 w-3" />
                    Upload u toku
                  </span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}
            {uploadErr && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {uploadErr}
              </div>
            )}

            <div className="space-y-2">
              {materials.length === 0 && (
                <p className="text-xs text-muted-foreground italic">
                  Nema upload-ovanih materijala.
                </p>
              )}
              {materials.map((m) => (
                <div
                  key={m.materialId}
                  className="rounded-lg border border-border bg-muted/40 p-3 flex items-center gap-3"
                >
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-card border border-border shrink-0">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{m.fileName}</div>
                    <div className="text-xs text-muted-foreground inline-flex flex-wrap items-center gap-x-2 mt-0.5">
                      <span>{(m.sizeBytes / 1024).toFixed(1)} KB</span>
                      <span>·</span>
                      <span className="uppercase">{m.fileType}</span>
                      {m.processedAt && (
                        <Badge variant="success" className="text-[10px] px-1.5 py-0">
                          obrađeno
                        </Badge>
                      )}
                      {m.processingError && (
                        <span className="text-destructive">
                          · {m.processingError}
                        </span>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => delMat.mutate(m.materialId)}
                    disabled={delMat.isPending}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar actions */}
        <aside className="space-y-3 lg:sticky lg:top-20 self-start">
          <div className="rounded-xl border border-border bg-card shadow-card p-5 space-y-3">
            <h3 className="text-sm">Akcije</h3>
            <Link to={`/profesor/termini/${id}/pitanja`} className="block">
              <Button variant="outline" className="w-full justify-start">
                <ClipboardList className="h-4 w-4" />
                Pregled pitanja
              </Button>
            </Link>
            {termin.status !== "objavljen" && (
              <Button
                onClick={() => objavi.mutate()}
                disabled={objavi.isPending}
                className="w-full justify-start"
              >
                <Globe2 className="h-4 w-4" />
                {objavi.isPending ? "Objavljujem..." : "Objavi termin"}
              </Button>
            )}
          </div>
          <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-5 space-y-2">
            <h3 className="text-sm text-destructive">Brisanje termina</h3>
            <p className="text-xs text-muted-foreground">
              Brisanje uklanja termin, slotove i materijale. Operacija je nepovratna.
            </p>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                if (confirm("Sigurno briše termin?")) delTermin.mutate();
              }}
              disabled={delTermin.isPending}
              className="w-full"
            >
              <Trash2 className="h-4 w-4" />
              Obriši termin
            </Button>
          </div>
        </aside>
      </div>
    </div>
  );
}

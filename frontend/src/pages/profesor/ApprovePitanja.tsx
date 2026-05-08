import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  CheckCheck,
  ClipboardList,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { getTermin } from "@/api/termini";
import {
  approveQuestion,
  createQuestion,
  deleteQuestion,
  listQuestions,
  retryAi,
  updateQuestion,
} from "@/api/questions";
import { toApiError } from "@/api/client";

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

export default function ApprovePitanja() {
  const { id = "" } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [editId, setEditId] = useState<string | null>(null);
  const [editPitanje, setEditPitanje] = useState("");
  const [editOdgovor, setEditOdgovor] = useState("");
  const [editTagovi, setEditTagovi] = useState("");
  const [newPitanje, setNewPitanje] = useState("");
  const [newOdgovor, setNewOdgovor] = useState("");
  const [newTagovi, setNewTagovi] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const terminQ = useQuery({
    queryKey: ["termin", id],
    queryFn: () => getTermin(id),
    enabled: !!id,
    refetchInterval: (q) =>
      q.state.data?.termin.status === "ai_processing" ? 3000 : false,
  });
  const questionsQ = useQuery({
    queryKey: ["termin-questions-all", id],
    queryFn: () => listQuestions(id),
    enabled: !!id && terminQ.data?.termin.status !== "ai_processing",
  });

  const updateMut = useMutation({
    mutationFn: (vars: {
      qid: string;
      pitanje?: string;
      odgovor?: string;
      tagovi?: string[];
    }) =>
      updateQuestion(vars.qid, {
        terminId: id,
        pitanje: vars.pitanje,
        odgovor: vars.odgovor,
        tagovi: vars.tagovi,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["termin-questions-all", id] });
      setEditId(null);
    },
    onError: (e) => setErr(toApiError(e).message),
  });
  const approveMut = useMutation({
    mutationFn: (vars: { qid: string; approved: boolean }) =>
      approveQuestion(vars.qid, vars.approved, id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["termin-questions-all", id] }),
  });
  const approveAllMut = useMutation({
    mutationFn: async (pendingIds: string[]) => {
      await Promise.all(pendingIds.map((qid) => approveQuestion(qid, true, id)));
      return pendingIds.length;
    },
    onSuccess: (count) => {
      setSuccessMsg(`Potvrđeno ${count} pitanja`);
      window.setTimeout(() => setSuccessMsg(null), 4000);
      qc.invalidateQueries({ queryKey: ["termin-questions-all", id] });
    },
    onError: (e) => setErr(toApiError(e).message),
  });
  const delMut = useMutation({
    mutationFn: (qid: string) => deleteQuestion(qid, id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["termin-questions-all", id] }),
  });
  const retryMut = useMutation({
    mutationFn: () => retryAi(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["termin", id] });
      qc.invalidateQueries({ queryKey: ["termin-questions-all", id] });
    },
    onError: (e) => setErr(toApiError(e).message),
  });
  const createMut = useMutation({
    mutationFn: () =>
      createQuestion(id, {
        pitanje: newPitanje,
        odgovor: newOdgovor,
        tagovi: newTagovi
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["termin-questions-all", id] });
      setNewPitanje("");
      setNewOdgovor("");
      setNewTagovi("");
      setShowNew(false);
    },
    onError: (e) => setErr(toApiError(e).message),
  });

  const status = terminQ.data?.termin.status;
  const isProcessing = status === "ai_processing";
  const items = questionsQ.data?.items ?? [];
  const approvedCount = items.filter((q) => q.approved).length;
  const pendingCount = items.filter((q) => !q.approved).length;

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
        title="Pitanja termina"
        description="Pregled, edit i potvrđivanje pitanja pre objave studentima."
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            {status && (
              <Badge variant={STATUS_VARIANT[status] ?? "secondary"}>{status}</Badge>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                const pendingIds = items
                  .filter((q) => !q.approved)
                  .map((q) => q.questionId);
                if (pendingIds.length === 0) return;
                const ok = window.confirm(
                  `Potvrditi svih ${pendingIds.length} pitanja? Ova akcija se ne može poništiti masovno.`,
                );
                if (!ok) return;
                approveAllMut.mutate(pendingIds);
              }}
              disabled={
                pendingCount === 0 || approveAllMut.isPending || isProcessing
              }
              title="Potvrdi sva pitanja na čekanju"
            >
              {approveAllMut.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCheck className="h-3.5 w-3.5" />
              )}
              {pendingCount > 0 ? `Potvrdi sve (${pendingCount})` : "Potvrdi sve"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => retryMut.mutate()}
              disabled={isProcessing || retryMut.isPending}
              title="Pokreni AI ponovo"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Pokreni AI
            </Button>
          </div>
        }
      />

      {/* Stats strip */}
      {!isProcessing && items.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <Badge variant="default">
            <Check className="h-3 w-3 mr-1" /> {approvedCount} potvrđeno
          </Badge>
          {pendingCount > 0 && (
            <Badge variant="warning">{pendingCount} na čekanju</Badge>
          )}
          <Badge variant="outline">{items.length} ukupno</Badge>
        </div>
      )}

      {successMsg && (
        <div className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          {successMsg}
        </div>
      )}

      {err && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {err}
        </div>
      )}

      {isProcessing && (
        <div className="rounded-xl border border-info/30 bg-info/10 p-6 flex flex-col items-center text-center gap-3">
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-info/20 text-info">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-base">AI obrađuje materijal...</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Ovo može da traje 10–30 sekundi. Stranica se osvežava automatski.
            </p>
          </div>
          <Spinner label="Generisanje Q&A..." />
        </div>
      )}

      {status === "ai_failed" && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-5 space-y-1">
          <h3 className="text-base text-destructive">AI processing nije uspeo</h3>
          <p className="text-sm text-muted-foreground">
            Probaj da pokreneš AI ponovo, uploaduj drugi fajl, ili dodaj pitanja
            ručno ispod.
          </p>
        </div>
      )}

      {questionsQ.data && (
        <div className="space-y-3">
          {items.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title="Još nema pitanja"
              description="Sačekaj da AI završi obradu ili dodaj pitanja ručno."
            />
          ) : (
            items.map((q) => (
              <div
                key={q.questionId}
                className="rounded-xl border border-border bg-card shadow-card overflow-hidden"
              >
                <div className="px-5 py-3 border-b border-border/60 flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <Badge variant={q.source === "ai" ? "accent" : "outline"}>
                      {q.source === "ai" ? (
                        <span className="inline-flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> AI
                        </span>
                      ) : (
                        "manual"
                      )}
                    </Badge>
                    {q.approved ? (
                      <Badge variant="success">potvrđeno</Badge>
                    ) : (
                      <Badge variant="warning">na čekanju</Badge>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="xs"
                      variant={q.approved ? "outline" : "default"}
                      onClick={() =>
                        approveMut.mutate({ qid: q.questionId, approved: !q.approved })
                      }
                    >
                      <Check className="h-3 w-3" />
                      {q.approved ? "Skini potvrdu" : "Potvrdi"}
                    </Button>
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => {
                        setEditId(q.questionId);
                        setEditPitanje(q.pitanje);
                        setEditOdgovor(q.odgovor);
                        setEditTagovi((q.tagovi || []).join(", "));
                      }}
                    >
                      <Pencil className="h-3 w-3" />
                      Uredi
                    </Button>
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => delMut.mutate(q.questionId)}
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                <div className="p-5 space-y-3">
                  {editId === q.questionId ? (
                    <div className="space-y-3">
                      <div className="space-y-1.5">
                        <Label className="text-xs">Pitanje</Label>
                        <Textarea
                          value={editPitanje}
                          onChange={(e) => setEditPitanje(e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Odgovor</Label>
                        <Textarea
                          value={editOdgovor}
                          onChange={(e) => setEditOdgovor(e.target.value)}
                          rows={4}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Tagovi (zarezom razdvojeni)</Label>
                        <Input
                          value={editTagovi}
                          onChange={(e) => setEditTagovi(e.target.value)}
                          placeholder="rekurzija, stack, memorija"
                        />
                      </div>
                      <div className="flex gap-2 pt-2 border-t border-border/60">
                        <Button
                          size="sm"
                          onClick={() =>
                            updateMut.mutate({
                              qid: q.questionId,
                              pitanje: editPitanje,
                              odgovor: editOdgovor,
                              tagovi: editTagovi
                                .split(",")
                                .map((t) => t.trim())
                                .filter(Boolean),
                            })
                          }
                          disabled={updateMut.isPending}
                        >
                          Sačuvaj
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setEditId(null)}
                        >
                          Otkaži
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="font-semibold leading-snug">{q.pitanje}</p>
                      <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">
                        {q.odgovor}
                      </p>
                      {q.tagovi.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-2">
                          {q.tagovi.map((t) => (
                            <Badge key={t} variant="outline" className="text-[10px]">
                              {t}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Add manually */}
      <div className="rounded-xl border border-border bg-card shadow-card p-5 sm:p-6 space-y-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm">Dodaj pitanje ručno</h3>
            <p className="text-xs text-muted-foreground">
              Ako AI ne radi ili želiš dodatno pitanje.
            </p>
          </div>
          <Button
            size="sm"
            variant={showNew ? "ghost" : "outline"}
            onClick={() => setShowNew((v) => !v)}
          >
            {showNew ? (
              <>
                <X className="h-3.5 w-3.5" /> Sakrij
              </>
            ) : (
              <>
                <Plus className="h-3.5 w-3.5" /> Novo
              </>
            )}
          </Button>
        </div>
        {showNew && (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Pitanje</Label>
              <Textarea
                value={newPitanje}
                onChange={(e) => setNewPitanje(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Odgovor</Label>
              <Textarea
                value={newOdgovor}
                onChange={(e) => setNewOdgovor(e.target.value)}
                rows={4}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Tagovi (zarezom razdvojeni)</Label>
              <Input value={newTagovi} onChange={(e) => setNewTagovi(e.target.value)} />
            </div>
            <Button
              onClick={() => createMut.mutate()}
              disabled={
                createMut.isPending ||
                !newPitanje ||
                !newOdgovor ||
                !newTagovi.trim()
              }
            >
              <Plus className="h-4 w-4" />
              Dodaj pitanje
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

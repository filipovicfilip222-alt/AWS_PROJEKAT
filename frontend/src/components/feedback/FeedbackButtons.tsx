import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ThumbsDown, ThumbsUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { getMyFeedback, submitFeedback, type FeedbackVote } from "@/api/feedback";
import { toApiError } from "@/api/client";

export interface FeedbackButtonsProps {
  questionId: string;
  terminId?: string;
  enabled?: boolean;
}

export function FeedbackButtons({
  questionId,
  terminId,
  enabled = true,
}: FeedbackButtonsProps) {
  const qc = useQueryClient();
  const queryKey = ["my-feedback", questionId];

  const myQ = useQuery({
    queryKey,
    queryFn: () => getMyFeedback(questionId),
    enabled,
  });

  const mut = useMutation({
    mutationFn: (vote: FeedbackVote) => submitFeedback(questionId, vote, terminId),
    onMutate: async (vote: FeedbackVote) => {
      await qc.cancelQueries({ queryKey });
      const prev = qc.getQueryData<{ vote: FeedbackVote | null }>(queryKey);
      qc.setQueryData(queryKey, { vote });
      return { prev };
    },
    onError: (_err, _vote, ctx) => {
      if (ctx?.prev) qc.setQueryData(queryKey, ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey }),
  });

  const currentVote = myQ.data?.vote ?? null;
  const isLoading = myQ.isLoading;
  const errMsg = mut.isError ? toApiError(mut.error).message : null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Jasno?</span>
        <Button
          size="sm"
          variant={currentVote === "yes" ? "default" : "outline"}
          disabled={!enabled || mut.isPending || isLoading}
          onClick={() => mut.mutate("yes")}
        >
          <ThumbsUp className="h-3 w-3 mr-1" /> Da
        </Button>
        <Button
          size="sm"
          variant={currentVote === "no" ? "destructive" : "outline"}
          disabled={!enabled || mut.isPending || isLoading}
          onClick={() => mut.mutate("no")}
        >
          <ThumbsDown className="h-3 w-3 mr-1" /> Ne
        </Button>
        {isLoading && <Spinner />}
      </div>
      {currentVote && (
        <p className="text-xs text-muted-foreground">
          Već si glasao: <strong>{currentVote === "yes" ? "Da" : "Ne"}</strong>. Možeš
          promeniti glas.
        </p>
      )}
      {errMsg && <p className="text-xs text-destructive">{errMsg}</p>}
    </div>
  );
}

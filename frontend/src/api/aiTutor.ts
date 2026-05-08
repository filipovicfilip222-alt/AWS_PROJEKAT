import { apiClient } from "./client";
import type { AiTutorResponse } from "./types";
import type { AiAskRequest, AiAskRequestContext } from "@/types/ai-tutor";

export interface AskAiTutorPayload {
  predmet: string;
  question: string;
  terminId?: string | null;
  context?: AiAskRequestContext;
}

export async function askAiTutor(payload: AskAiTutorPayload): Promise<AiTutorResponse> {
  const body: AiAskRequest = {
    predmet: payload.predmet,
    question: payload.question,
    terminId: payload.terminId ?? null,
    context: payload.context,
  };
  const { data } = await apiClient.post<AiTutorResponse>("/ai/ask", body);
  return data;
}

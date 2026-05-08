import { apiClient } from "./client";

export type FeedbackVote = "yes" | "no";

export interface FeedbackSubmitResponse {
  questionId: string;
  vote: FeedbackVote;
  status: "new" | "changed" | "unchanged";
}

export interface MyFeedbackResponse {
  vote: FeedbackVote | null;
  updatedAt?: string;
}

export async function submitFeedback(
  questionId: string,
  vote: FeedbackVote,
  terminId?: string,
) {
  const { data } = await apiClient.post<FeedbackSubmitResponse>(
    `/questions/${questionId}/feedback`,
    { vote, ...(terminId ? { terminId } : {}) },
  );
  return data;
}

export async function getMyFeedback(questionId: string) {
  const { data } = await apiClient.get<MyFeedbackResponse>(
    `/questions/${questionId}/feedback/me`,
  );
  return data;
}

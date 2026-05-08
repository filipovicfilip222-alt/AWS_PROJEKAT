import { apiClient } from "./client";
import type { Question } from "./types";

export async function listQuestions(terminId: string, opts?: { onlyApproved?: boolean }) {
  const { data } = await apiClient.get<{ items: Question[]; count: number }>(
    `/termini/${terminId}/questions`,
    { params: opts?.onlyApproved ? { onlyApproved: "true" } : {} },
  );
  return data;
}

export async function createQuestion(
  terminId: string,
  payload: { pitanje: string; odgovor: string; tagovi: string[] },
) {
  const { data } = await apiClient.post(`/termini/${terminId}/questions`, payload);
  return data;
}

export async function updateQuestion(
  questionId: string,
  payload: {
    terminId?: string;
    pitanje?: string;
    odgovor?: string;
    tagovi?: string[];
    approved?: boolean;
  },
) {
  const { data } = await apiClient.patch(`/questions/${questionId}`, payload);
  return data;
}

export async function deleteQuestion(questionId: string, terminId?: string) {
  const { data } = await apiClient.delete(`/questions/${questionId}`, {
    params: terminId ? { terminId } : {},
  });
  return data;
}

export async function approveQuestion(
  questionId: string,
  approved: boolean,
  terminId?: string,
) {
  const { data } = await apiClient.post(`/questions/${questionId}/approve`, {
    approved,
    terminId,
  });
  return data;
}

export async function retryAi(terminId: string) {
  const { data } = await apiClient.post(`/termini/${terminId}/ai/process`);
  return data;
}

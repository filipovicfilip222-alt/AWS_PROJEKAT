import { apiClient } from "./client";
import type { SearchMode, SearchResult } from "./types";

export async function listPredmeti() {
  const { data } = await apiClient.get<{ items: string[]; count: number }>("/predmeti");
  return data;
}

export async function listTags(predmet: string) {
  const { data } = await apiClient.get<{ items: { tag: string; count: number }[]; count: number }>(
    "/search/tags",
    { params: { predmet } },
  );
  return data;
}

export async function searchQuestions(
  predmet: string,
  q?: string,
  options?: { mode?: SearchMode; limit?: number },
) {
  const { data } = await apiClient.get<{ results: SearchResult[]; count: number }>(
    "/search/questions",
    {
      params: {
        predmet,
        ...(q ? { q } : {}),
        ...(options?.mode ? { mode: options.mode } : {}),
        ...(options?.limit ? { limit: options.limit } : {}),
      },
    },
  );
  return data;
}

import { apiClient } from "./client";

export interface InsightSummary {
  totalQuestions: number;
  totalFeedback: number;
  averageJasno: number;
  questionsWithoutFeedback: number;
}

export interface InsightTopProblematic {
  rank: number;
  questionId: string;
  pitanje: string;
  percentJasno: number;
  totalFeedback: number;
  preporuka: string;
}

export interface InsightTagPattern {
  tag: string;
  questionCount: number;
  averageJasno: number;
  interpretation: string;
}

export interface InsightBezFeedback {
  questionId: string;
  pitanje: string;
  razlog: string;
}

export interface RezimeInsights {
  generatedAt?: string;
  terminId?: string;
  predmet?: string;
  summary?: InsightSummary;
  topProblematic?: InsightTopProblematic[];
  tagPatterns?: InsightTagPattern[];
  preporukeZaSledeceKonsultacije?: string[];
  bezFeedbackUpozorenje?: InsightBezFeedback[];
}

export interface RezimeCsvRow {
  pitanje: string;
  odgovor: string;
  tagovi: string[];
  yesCount: number;
  noCount: number;
  total: number;
  percentJasno: number;
}

export interface RezimeResponse {
  available: boolean;
  message?: string;
  generatedAt?: string;
  csvDownloadUrl?: string;
  csvRows?: RezimeCsvRow[] | null;
  insights?: RezimeInsights | null;
  status?: "generated" | "csv_only" | "failed" | "regenerating" | "unknown";
}

export async function getRezime(terminId: string) {
  const { data } = await apiClient.get<RezimeResponse>(
    `/termini/${terminId}/rezime`,
  );
  return data;
}

export async function regenerateRezime(terminId: string) {
  const { data } = await apiClient.post<{ started: boolean; message: string }>(
    `/termini/${terminId}/rezime/regenerate`,
  );
  return data;
}

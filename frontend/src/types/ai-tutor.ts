export type AiConfidence = "high" | "medium" | "low";
export type AiMessageRole = "user" | "ai";

export interface AiSourceRef {
  questionId: string;
  pitanje: string;
  predmet: string;
  terminId: string;
}

export interface AiTutorMessage {
  id: string;
  role: AiMessageRole;
  content: string;
  confidence?: AiConfidence;
  sources?: AiSourceRef[];
  preporukaZakazivanja?: boolean;
  createdAt: string;
  isError?: boolean;
}

export interface AiTutorContext {
  contextQuestionId: string;
  contextQuestion: string;
  contextAnswer: string;
  predmet: string;
  terminId: string | null;
}

export interface AiTutorSessionState {
  isOpen: boolean;
  context: AiTutorContext | null;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  error: string | null;
}

export interface AiAskConversationMessage {
  role: AiMessageRole;
  content: string;
}

export interface AiAskRequestContext {
  contextQuestionId: string;
  contextQuestion: string;
  contextAnswer: string;
  conversationHistory: AiAskConversationMessage[];
}

export interface AiAskRequest {
  predmet: string;
  question: string;
  terminId: string | null;
  context?: AiAskRequestContext;
}

export interface AiAskResponse {
  odgovor: string;
  confidence: AiConfidence;
  sources: string[];
  preporukaZakazivanja: boolean;
}

export type ResolveSources = (questionIds: string[]) => AiSourceRef[];

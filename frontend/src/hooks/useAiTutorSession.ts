import { useCallback, useState } from "react";
import { ulid } from "ulid";

import { askAiTutor } from "@/api/aiTutor";
import { toApiError } from "@/api/client";
import type {
  AiAskConversationMessage,
  AiTutorContext,
  AiTutorMessage,
  ResolveSources,
} from "@/types/ai-tutor";

const MAX_HISTORY_TURNS = 5;
const CLOSE_CLEANUP_MS = 350;

interface UseAiTutorSessionOptions {
  /**
   * Callback to hydrate AiSourceRef objects from raw questionIds returned
   * by the backend. Implement at the page level using available search data.
   */
  resolveSources?: ResolveSources;
}

export interface UseAiTutorSessionResult {
  isOpen: boolean;
  context: AiTutorContext | null;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  error: string | null;
  openWithContext: (ctx: AiTutorContext, firstQuestion?: string) => void;
  close: () => void;
  sendMessage: (content: string) => void;
}

export function useAiTutorSession(
  options: UseAiTutorSessionOptions = {},
): UseAiTutorSessionResult {
  const { resolveSources } = options;

  const [isOpen, setIsOpen] = useState(false);
  const [context, setContext] = useState<AiTutorContext | null>(null);
  const [messages, setMessages] = useState<AiTutorMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessageInternal = useCallback(
    async (content: string, ctx: AiTutorContext, history: AiTutorMessage[]) => {
      const userMessage: AiTutorMessage = {
        id: ulid(),
        role: "user",
        content,
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsGenerating(true);
      setError(null);

      const conversationHistory: AiAskConversationMessage[] = history
        .slice(-MAX_HISTORY_TURNS * 2)
        .map((m) => ({ role: m.role, content: m.content }));

      try {
        const response = await askAiTutor({
          predmet: ctx.predmet,
          question: content,
          terminId: ctx.terminId,
          context: {
            contextQuestionId: ctx.contextQuestionId,
            contextQuestion: ctx.contextQuestion,
            contextAnswer: ctx.contextAnswer,
            conversationHistory,
          },
        });

        const sources = resolveSources ? resolveSources(response.sources) : [];

        const aiMessage: AiTutorMessage = {
          id: ulid(),
          role: "ai",
          content: response.odgovor,
          confidence: response.confidence,
          sources,
          preporukaZakazivanja: response.preporukaZakazivanja,
          createdAt: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, aiMessage]);
      } catch (err) {
        const apiErr = toApiError(err);
        let userMsg: string;
        if (apiErr.status === 429) {
          userMsg =
            "Dnevni limit AI pitanja je dostignut. Pokušaj sutra ili zakaži konsultacije.";
        } else if (apiErr.status === 503) {
          userMsg = "AI tutor trenutno nije dostupan. Pokušaj kasnije.";
        } else if (apiErr.status >= 500 || apiErr.status === 0) {
          userMsg = "Došlo je do greške. Pokušaj ponovo.";
        } else {
          userMsg = apiErr.message || "Došlo je do greške. Pokušaj ponovo.";
        }

        const errorMessage: AiTutorMessage = {
          id: ulid(),
          role: "ai",
          content: userMsg,
          createdAt: new Date().toISOString(),
          isError: true,
        };

        setMessages((prev) => [...prev, errorMessage]);
        setError(userMsg);
      } finally {
        setIsGenerating(false);
      }
    },
    [resolveSources],
  );

  const openWithContext = useCallback(
    (ctx: AiTutorContext, firstQuestion?: string) => {
      setContext(ctx);
      setMessages([]);
      setError(null);
      setIsOpen(true);
      if (firstQuestion && firstQuestion.trim().length >= 10) {
        void sendMessageInternal(firstQuestion.trim(), ctx, []);
      }
    },
    [sendMessageInternal],
  );

  const close = useCallback(() => {
    setIsOpen(false);
    window.setTimeout(() => {
      setContext(null);
      setMessages([]);
      setError(null);
      setIsGenerating(false);
    }, CLOSE_CLEANUP_MS);
  }, []);

  const sendMessage = useCallback(
    (content: string) => {
      if (!context) return;
      const trimmed = content.trim();
      if (trimmed.length < 10) return;
      void sendMessageInternal(trimmed, context, messages);
    },
    [context, messages, sendMessageInternal],
  );

  return {
    isOpen,
    context,
    messages,
    isGenerating,
    error,
    openWithContext,
    close,
    sendMessage,
  };
}

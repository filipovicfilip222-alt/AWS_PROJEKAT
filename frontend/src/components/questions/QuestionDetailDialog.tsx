import { useEffect } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { AiInputBar } from "@/components/ai/AiInputBar";
import { AiTutorBottomSheet } from "@/components/ai/AiTutorBottomSheet";
import { AiTutorPanel } from "@/components/ai/AiTutorPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FeedbackButtons } from "@/components/feedback/FeedbackButtons";
import { useAiTutorSession } from "@/hooks/useAiTutorSession";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { easings } from "@/styles/motion";
import type { ResolveSources } from "@/types/ai-tutor";

export interface QuestionDetailQuestion {
  questionId: string;
  pitanje: string;
  odgovor: string;
  tagovi: string[];
  matchedTags?: string[];
  profesorIme?: string;
  terminId: string;
  terminDatum: string;
  predmet?: string;
}

export interface QuestionDetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  question: QuestionDetailQuestion | null;
  /**
   * Called when the user clicks an AI source card. Should switch the
   * popup's question to the referenced one (if available).
   */
  onChangeQuestion?: (questionId: string) => void;
  /**
   * Hydrates raw questionIds from the AI tutor response into AiSourceRef
   * objects using whatever data the host page already has.
   */
  resolveSources?: ResolveSources;
  showFeedback?: boolean;
}

function isPastDate(date: string): boolean {
  if (!date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(date + "T00:00:00");
  return target.getTime() < today.getTime();
}

const AI_PANEL_WIDTH = 400;

export function QuestionDetailDialog({
  open,
  onOpenChange,
  question,
  onChangeQuestion,
  resolveSources,
  showFeedback = true,
}: QuestionDetailDialogProps) {
  const navigate = useNavigate();
  // Inline AI panel only when there's enough room: dialog (600) + gap (12) +
  // panel (400) ≈ 1012px, plus padding. Below this we fall back to bottom sheet.
  const isDesktop = useMediaQuery("(min-width: 1100px)");
  const tutor = useAiTutorSession({ resolveSources });

  // Close chat session whenever the dialog itself closes
  useEffect(() => {
    if (!open && tutor.isOpen) {
      tutor.close();
    }
  }, [open, tutor]);

  if (!question) return null;

  const past = isPastDate(question.terminDatum);
  const matched = new Set(question.matchedTags ?? []);
  const inlineChatOpen = isDesktop && tutor.isOpen;

  const handleAiSubmit = (firstQuestion: string) => {
    if (!question.predmet) return;
    tutor.openWithContext(
      {
        contextQuestionId: question.questionId,
        contextQuestion: question.pitanje,
        contextAnswer: question.odgovor,
        predmet: question.predmet,
        terminId: question.terminId ?? null,
      },
      firstQuestion,
    );
  };

  const handleSourceClick = (questionId: string) => {
    if (onChangeQuestion) {
      onChangeQuestion(questionId);
    }
    tutor.close();
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />

        <DialogPrimitive.Content
          asChild
          onEscapeKeyDown={(e) => {
            if (tutor.isOpen) {
              e.preventDefault();
              tutor.close();
            }
          }}
          onInteractOutside={(e) => {
            if (tutor.isOpen) {
              e.preventDefault();
            }
          }}
        >
          <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-40 outline-none">
            <div className="flex items-stretch gap-3 max-w-[98vw]">
              {/* Question detail card */}
              <div className="relative w-[600px] max-w-[95vw] max-h-[85vh] overflow-hidden bg-card border border-border rounded-xl shadow-elevated flex flex-col">
                <DialogPrimitive.Close
                  className="absolute right-3 top-3 z-10 p-1.5 rounded-md opacity-70 hover:opacity-100 hover:bg-muted transition focus:outline-none focus:ring-2 focus:ring-ring"
                  aria-label="Zatvori"
                >
                  <X className="h-4 w-4" />
                </DialogPrimitive.Close>

                <div className="flex flex-col gap-4 px-6 pt-6 pb-4 overflow-y-auto flex-1">
                  <header className="pr-8 space-y-1.5">
                    <DialogPrimitive.Title className="text-lg font-semibold leading-snug tracking-tight">
                      {question.pitanje}
                    </DialogPrimitive.Title>
                    <DialogPrimitive.Description className="text-sm text-muted-foreground">
                      {question.profesorIme ?? ""}
                      {question.profesorIme && question.terminDatum ? " · " : ""}
                      {question.terminDatum}
                      {question.predmet ? ` · ${question.predmet}` : ""}
                    </DialogPrimitive.Description>
                  </header>

                  <section>
                    <p className="text-sm whitespace-pre-line leading-relaxed">
                      {question.odgovor}
                    </p>
                  </section>

                  {question.tagovi.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {question.tagovi.map((t) => (
                        <Badge
                          key={t}
                          variant={matched.has(t) ? "default" : "outline"}
                        >
                          {t}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {showFeedback && (
                    <div className="border-t pt-4">
                      <FeedbackButtons
                        questionId={question.questionId}
                        terminId={question.terminId}
                        enabled={open}
                      />
                    </div>
                  )}

                  {question.predmet && (
                    <AiInputBar
                      onSubmit={handleAiSubmit}
                      disabled={tutor.isGenerating}
                    />
                  )}
                </div>

                <footer className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 border-t border-border bg-card px-6 py-3">
                  <Button variant="outline" onClick={() => onOpenChange(false)}>
                    Zatvori
                  </Button>
                  <Button
                    disabled={past}
                    title={past ? "Termin je prošao" : undefined}
                    onClick={() => {
                      onOpenChange(false);
                      navigate(`/termini/${question.terminId}`);
                    }}
                  >
                    Zakaži konsultacije
                  </Button>
                </footer>
              </div>

              {/* AI tutor panel inline (desktop only). Animates width
                  + opacity so the dialog visually stays in place while
                  the panel slides in to the right with a small gap. */}
              <AnimatePresence initial={false}>
                {inlineChatOpen && (
                  <motion.aside
                    key="ai-tutor-inline"
                    initial={{ width: 0, opacity: 0, x: 16 }}
                    animate={{ width: AI_PANEL_WIDTH, opacity: 1, x: 0 }}
                    exit={{ width: 0, opacity: 0, x: 16 }}
                    transition={{ duration: 0.28, ease: easings.out }}
                    style={{ maxWidth: "40vw" }}
                    className="overflow-hidden bg-card border border-border rounded-xl shadow-elevated max-h-[85vh] shrink-0"
                    role="dialog"
                    aria-label="AI Tutor chat"
                  >
                    <div
                      style={{ width: AI_PANEL_WIDTH, maxWidth: "40vw" }}
                      className="h-full"
                    >
                      <AiTutorPanel
                        isOpen={tutor.isOpen}
                        onClose={tutor.close}
                        messages={tutor.messages}
                        isGenerating={tutor.isGenerating}
                        contextQuestion={tutor.context?.contextQuestion ?? null}
                        onSendMessage={tutor.sendMessage}
                        onSourceClick={handleSourceClick}
                      />
                    </div>
                  </motion.aside>
                )}
              </AnimatePresence>
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>

      {/* Mobile / narrow viewports use bottom sheet */}
      {!isDesktop && (
        <AiTutorBottomSheet
          isOpen={tutor.isOpen}
          onClose={tutor.close}
          messages={tutor.messages}
          isGenerating={tutor.isGenerating}
          contextQuestion={tutor.context?.contextQuestion ?? null}
          onSendMessage={tutor.sendMessage}
          onSourceClick={handleSourceClick}
        />
      )}
    </DialogPrimitive.Root>
  );
}

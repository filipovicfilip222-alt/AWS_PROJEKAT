import { useEffect, useRef } from "react";
import { Drawer } from "vaul";
import { X } from "lucide-react";

import type { AiTutorMessage } from "@/types/ai-tutor";

import { AiDisclaimerFooter } from "./AiDisclaimerFooter";
import { AiEmptyState } from "./AiEmptyState";
import { AiMessageBubble } from "./AiMessageBubble";
import { AiTutorInput } from "./AiTutorInput";
import { AiTypingIndicator } from "./AiTypingIndicator";
import { AiTutorBrandMark } from "./AiTutorBrandMark";

interface AiTutorBottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  contextQuestion: string | null;
  onSendMessage: (content: string) => void;
  onSourceClick: (questionId: string) => void;
}

export function AiTutorBottomSheet({
  isOpen,
  onClose,
  messages,
  isGenerating,
  contextQuestion,
  onSendMessage,
  onSourceClick,
}: AiTutorBottomSheetProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length, isGenerating]);

  return (
    <Drawer.Root
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 bg-black/40 z-50" />
        <Drawer.Content
          className="fixed bottom-0 left-0 right-0 h-[75vh] bg-card border-t border-border rounded-t-xl flex flex-col z-50 outline-none"
          aria-label="AI Tutor chat"
        >
          <div className="flex justify-center pt-3 pb-1 shrink-0">
            <div className="w-10 h-1 rounded-full bg-border" />
          </div>

          <header className="flex items-center justify-between gap-3 px-5 py-3 border-b border-border shrink-0 bg-gradient-to-r from-accent-muted via-card to-card">
            <Drawer.Title className="sr-only">AI Tutor</Drawer.Title>
            <AiTutorBrandMark />
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              aria-label="Zatvori chat"
            >
              <X className="w-4 h-4" />
            </button>
          </header>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
            <div className="flex flex-col gap-4">
              {messages.length === 0 && !isGenerating && contextQuestion && (
                <AiEmptyState
                  contextQuestion={contextQuestion}
                  onExampleClick={onSendMessage}
                />
              )}
              {messages.map((msg) => (
                <AiMessageBubble
                  key={msg.id}
                  message={msg}
                  onSourceClick={onSourceClick}
                />
              ))}
              {isGenerating && <AiTypingIndicator />}
            </div>
          </div>

          <AiTutorInput onSend={onSendMessage} disabled={isGenerating} />
          <AiDisclaimerFooter />
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}

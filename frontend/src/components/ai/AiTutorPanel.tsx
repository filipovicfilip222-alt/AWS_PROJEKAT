import { useEffect, useRef } from "react";
import { X } from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import type { AiTutorMessage } from "@/types/ai-tutor";

import { AiDisclaimerFooter } from "./AiDisclaimerFooter";
import { AiEmptyState } from "./AiEmptyState";
import { AiMessageBubble } from "./AiMessageBubble";
import { AiTutorInput } from "./AiTutorInput";
import { AiTypingIndicator } from "./AiTypingIndicator";
import { AiTutorBrandMark } from "./AiTutorBrandMark";

interface AiTutorPanelProps {
  isOpen: boolean;
  onClose: () => void;
  messages: AiTutorMessage[];
  isGenerating: boolean;
  contextQuestion: string | null;
  onSendMessage: (content: string) => void;
  onSourceClick: (questionId: string) => void;
}

/**
 * Inline chat panel UI. Parent is responsible for positioning, sizing
 * and mount/unmount animation. This component only renders the chat
 * surface itself (header, scrollable messages, input, disclaimer).
 */
export function AiTutorPanel({
  isOpen,
  onClose,
  messages,
  isGenerating,
  contextQuestion,
  onSendMessage,
  onSourceClick,
}: AiTutorPanelProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length, isGenerating]);

  if (!isOpen) return null;

  return (
    <div className="flex flex-col h-full w-full bg-card">
      <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-gradient-to-r from-accent-muted via-card to-card">
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

      <ScrollArea className="flex-1 min-h-0">
        <div ref={scrollRef} className="px-4 py-4">
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
      </ScrollArea>

      <AiTutorInput onSend={onSendMessage} disabled={isGenerating} />

      <AiDisclaimerFooter />
    </div>
  );
}

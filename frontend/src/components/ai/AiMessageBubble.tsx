import { motion } from "framer-motion";
import { AlertCircle, Sparkles } from "lucide-react";

import { easings } from "@/styles/motion";
import type { AiTutorMessage } from "@/types/ai-tutor";

import { AiConfidenceBadge } from "./AiConfidenceBadge";
import { AiSourceCard } from "./AiSourceCard";

interface AiMessageBubbleProps {
  message: AiTutorMessage;
  onSourceClick: (questionId: string) => void;
}

const bubbleVariants = {
  hidden: { opacity: 0, y: 8, scale: 0.96 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.2, ease: easings.out },
  },
};

export function AiMessageBubble({ message, onSourceClick }: AiMessageBubbleProps) {
  const isAi = message.role === "ai";
  const isError = !!message.isError;

  return (
    <motion.div
      variants={bubbleVariants}
      initial="hidden"
      animate="visible"
      className={`flex flex-col gap-2 ${isAi ? "items-start" : "items-end"}`}
    >
      {isAi && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground px-1">
          {isError ? (
            <AlertCircle className="w-3 h-3 text-destructive" />
          ) : (
            <Sparkles className="w-3 h-3 text-accent" />
          )}
          AI Tutor
        </div>
      )}

      <div
        className={[
          "max-w-[85%] px-4 py-3 rounded-2xl text-sm",
          isAi
            ? isError
              ? "bg-destructive/10 border border-destructive/20 text-foreground rounded-tl-sm"
              : "bg-aiBubble border border-aiBubble-border text-aiBubble-foreground rounded-tl-sm"
            : "bg-userBubble border border-userBubble-border text-userBubble-foreground rounded-tr-sm",
        ].join(" ")}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
      </div>

      {isAi && message.confidence && !isError && (
        <div className="flex items-center gap-2 px-1">
          <AiConfidenceBadge confidence={message.confidence} />
        </div>
      )}

      {isAi && message.sources && message.sources.length > 0 && (
        <div className="w-full flex flex-col gap-1.5 mt-1">
          <span className="text-xs text-muted-foreground px-1">Bazirano na pitanjima:</span>
          <div className="flex flex-col gap-1.5">
            {message.sources.map((src) => (
              <AiSourceCard
                key={src.questionId}
                source={src}
                onClick={() => onSourceClick(src.questionId)}
              />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

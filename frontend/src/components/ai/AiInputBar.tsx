import { useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, Send } from "lucide-react";

import { Textarea } from "@/components/ui/textarea";
import { easings } from "@/styles/motion";

interface AiInputBarProps {
  onSubmit: (question: string) => void;
  placeholder?: string;
  isCompactByDefault?: boolean;
  disabled?: boolean;
}

export function AiInputBar({
  onSubmit,
  placeholder = "Pitaj AI tutora...",
  isCompactByDefault = true,
  disabled = false,
}: AiInputBarProps) {
  const [isExpanded, setIsExpanded] = useState(!isCompactByDefault);
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed.length < 10 || disabled) return;
    onSubmit(trimmed);
    setValue("");
    setIsExpanded(false);
  };

  return (
    <motion.div
      animate={{ height: isExpanded ? "auto" : 48 }}
      transition={{ duration: 0.2, ease: easings.out }}
      className="rounded-lg border border-border bg-accent-muted/30 overflow-hidden"
    >
      <div className="flex items-start gap-2 p-3">
        <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" />

        {!isExpanded ? (
          <button
            type="button"
            onClick={() => setIsExpanded(true)}
            disabled={disabled}
            className="flex-1 text-left text-sm text-muted-foreground hover:text-foreground transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          >
            {placeholder}
          </button>
        ) : (
          <div className="flex-1 flex flex-col gap-2">
            <Textarea
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  handleSubmit();
                }
                if (e.key === "Escape") {
                  setIsExpanded(false);
                  setValue("");
                }
              }}
              placeholder="Detaljno pitanje za AI tutora..."
              className="min-h-[80px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-sm p-0 shadow-none"
              maxLength={500}
              disabled={disabled}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {value.length}/500 · ⌘+Enter za slanje
              </span>
              <motion.button
                type="button"
                whileTap={{ scale: 0.95 }}
                whileHover={{ scale: 1.02 }}
                onClick={handleSubmit}
                disabled={value.trim().length < 10 || disabled}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent text-accent-foreground text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-3.5 h-3.5" />
                Pitaj
              </motion.button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

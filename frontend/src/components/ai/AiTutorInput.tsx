import { useState } from "react";
import { motion } from "framer-motion";
import { Send } from "lucide-react";

import { Textarea } from "@/components/ui/textarea";

interface AiTutorInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function AiTutorInput({ onSend, disabled }: AiTutorInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed.length < 10 || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const isDisabled = !!disabled;

  return (
    <div className="border-t border-border p-3 bg-background">
      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Postavi pitanje..."
          className="min-h-[44px] max-h-[120px] resize-none text-sm flex-1"
          maxLength={500}
          disabled={isDisabled}
        />
        <motion.button
          type="button"
          whileTap={{ scale: 0.95 }}
          whileHover={{ scale: 1.05 }}
          onClick={handleSubmit}
          disabled={value.trim().length < 10 || isDisabled}
          className="shrink-0 inline-flex items-center justify-center w-10 h-10 rounded-md bg-accent text-accent-foreground disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Pošalji"
        >
          <Send className="w-4 h-4" />
        </motion.button>
      </div>
      <div className="text-[10px] text-muted-foreground mt-1.5 px-1">
        {value.length}/500 · Enter za slanje · Shift+Enter za novi red
      </div>
    </div>
  );
}

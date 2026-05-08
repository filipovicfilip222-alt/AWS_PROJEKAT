import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export function AiTypingIndicator() {
  return (
    <div className="flex flex-col gap-2 items-start">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground px-1">
        <Sparkles className="w-3 h-3 text-accent" />
        AI Tutor
      </div>
      <div className="flex items-center gap-1 px-4 py-3 bg-accent-muted border border-accent/20 rounded-2xl rounded-tl-sm">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-accent"
            animate={{
              y: [0, -3, 0],
              opacity: [0.4, 1, 0.4],
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.15,
            }}
          />
        ))}
      </div>
    </div>
  );
}

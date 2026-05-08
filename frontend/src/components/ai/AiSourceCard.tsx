import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

import type { AiSourceRef } from "@/types/ai-tutor";

interface AiSourceCardProps {
  source: AiSourceRef;
  onClick: () => void;
}

export function AiSourceCard({ source, onClick }: AiSourceCardProps) {
  return (
    <motion.button
      type="button"
      whileHover={{ y: -1 }}
      transition={{ duration: 0.15 }}
      onClick={onClick}
      className="flex items-start justify-between gap-2 p-2.5 rounded-md bg-card border border-border hover:border-accent/40 hover:shadow-sm transition-all text-left w-full"
    >
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-foreground line-clamp-2">{source.pitanje}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">{source.predmet}</p>
      </div>
      <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
    </motion.button>
  );
}

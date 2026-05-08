import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

import { easings } from "@/styles/motion";

interface AiEmptyStateProps {
  contextQuestion: string;
  onExampleClick: (example: string) => void;
}

const EXAMPLES: ReadonlyArray<string> = [
  "Pojednostavi ovo",
  "Daj mi konkretan primer",
  "Objasni sa analogijom",
  "Šta je veza sa drugim temama?",
];

export function AiEmptyState({ contextQuestion, onExampleClick }: AiEmptyStateProps) {
  const truncated =
    contextQuestion.length > 80 ? contextQuestion.slice(0, 80) + "..." : contextQuestion;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: easings.out }}
      className="flex flex-col gap-3 p-1"
    >
      <div className="flex items-start gap-2 rounded-2xl rounded-tl-sm bg-aiBubble border border-aiBubble-border px-4 py-3">
        <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" />
        <div className="text-sm text-aiBubble-foreground leading-relaxed">
          <p className="font-medium mb-1">Spreman sam da pomognem.</p>
          <p>
            Pitaj me bilo šta o pitanju{" "}
            <span className="italic">"{truncated}"</span>. Mogu da pojednostavim, dam primere ili
            objasnim detaljnije.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 px-1">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => onExampleClick(ex)}
            className="text-xs px-2.5 py-1 rounded-full border border-border bg-card hover:bg-accent-muted hover:border-accent/40 hover:text-foreground transition-colors text-muted-foreground"
          >
            {ex}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

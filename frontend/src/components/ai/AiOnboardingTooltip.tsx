import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

import { easings } from "@/styles/motion";

interface AiOnboardingTooltipProps {
  flagKey: string;
  message: string;
  side?: "top" | "bottom";
  delay?: number;
  children: React.ReactNode;
}

export function AiOnboardingTooltip({
  flagKey,
  message,
  side = "top",
  delay = 600,
  children,
}: AiOnboardingTooltipProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const seen = window.localStorage.getItem(flagKey);
      if (seen) return;
    } catch {
      return;
    }
    const t = window.setTimeout(() => setShow(true), delay);
    return () => window.clearTimeout(t);
  }, [flagKey, delay]);

  const dismiss = () => {
    setShow(false);
    try {
      window.localStorage.setItem(flagKey, "1");
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="relative">
      {children}
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, y: side === "top" ? 6 : -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: side === "top" ? 6 : -6 }}
            transition={{ duration: 0.2, ease: easings.out }}
            className={[
              "absolute left-3 right-3 z-30 rounded-md bg-foreground text-background text-xs px-3 py-2 shadow-lg flex items-start gap-2",
              side === "top" ? "bottom-full mb-2" : "top-full mt-2",
            ].join(" ")}
            role="status"
          >
            <span className="flex-1 leading-snug">{message}</span>
            <button
              type="button"
              onClick={dismiss}
              className="opacity-70 hover:opacity-100"
              aria-label="Zatvori"
            >
              <X className="w-3 h-3" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

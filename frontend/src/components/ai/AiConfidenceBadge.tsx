import type { AiConfidence } from "@/types/ai-tutor";

const config: Record<AiConfidence, { label: string; classes: string }> = {
  high: {
    label: "Visoka pouzdanost",
    classes: "bg-success/10 text-success border-success/20",
  },
  medium: {
    label: "Srednja pouzdanost",
    classes: "bg-warning/10 text-warning border-warning/20",
  },
  low: {
    label: "Niska pouzdanost — preporučuju se konsultacije",
    classes: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

export function AiConfidenceBadge({ confidence }: { confidence: AiConfidence }) {
  const { label, classes } = config[confidence];
  return (
    <span
      className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full border ${classes}`}
    >
      {label}
    </span>
  );
}

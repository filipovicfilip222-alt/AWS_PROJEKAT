import { Info } from "lucide-react";

export function AiDisclaimerFooter() {
  return (
    <div className="px-4 py-2.5 bg-muted/40 border-t border-border">
      <p className="text-[10px] text-muted-foreground flex items-start gap-1.5 leading-relaxed">
        <Info className="w-3 h-3 shrink-0 mt-0.5" />
        <span>
          Odgovor je generisan AI-em. Za potpuno pouzdan odgovor zakaži konsultacije sa
          profesorom.
        </span>
      </p>
    </div>
  );
}

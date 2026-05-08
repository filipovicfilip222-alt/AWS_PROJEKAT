import { Loader2 } from "lucide-react";
import { cn } from "@/utils/cn";

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <div className="flex items-center gap-2 text-muted-foreground">
      <Loader2 className={cn("h-4 w-4 animate-spin", className)} />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

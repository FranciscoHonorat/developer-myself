import { cn } from "@/lib/utils";

/** Wordmark `dev/myself` com cursor de terminal. */
export function Brand({ className }: { className?: string }) {
  return (
    <span className={cn("font-mono text-sm font-semibold tracking-tight", className)}>
      <span className="text-muted-foreground">dev/</span>
      <span>myself</span>
      <span aria-hidden className="ml-0.5 text-primary motion-safe:animate-pulse">
        ▍
      </span>
    </span>
  );
}

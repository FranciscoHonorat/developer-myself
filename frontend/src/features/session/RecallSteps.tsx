import { cn } from "@/lib/utils";

const STEPS = ["Responder", "Conferir", "Corrigir"] as const;

/** Onde o aprendiz está no teste de memória: 1 Responder · 2 Conferir · 3 Corrigir. */
export function RecallSteps({ current }: { current: 1 | 2 | 3 }) {
  return (
    <ol
      aria-label="Etapas do teste"
      className="flex flex-wrap items-center gap-2 font-mono text-xs"
    >
      {STEPS.map((label, i) => {
        const n = i + 1;
        const state = n < current ? "done" : n === current ? "current" : "todo";
        return (
          <li
            key={label}
            aria-current={state === "current" ? "step" : undefined}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-2.5 py-1",
              state === "current" && "border-primary bg-accent text-accent-foreground",
              state === "done" && "border-primary/40 text-primary",
              state === "todo" && "text-muted-foreground",
            )}
          >
            <span aria-hidden>{n}</span>
            <span>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

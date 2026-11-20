import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { useWeek } from "@/api/hooks";
import { hours, WEEKDAY_SHORT } from "@/api/weekLabels";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { WeekDetails } from "./WeekDetails";

/** A semana em uma faixa (minutos por dia, folgas); "Ver semana" abre a grade e o ritmo. */
export function WeekStrip() {
  const week = useWeek();
  const [open, setOpen] = useState(false);
  const days = week.data?.days ?? [];

  return (
    <section aria-labelledby="h-week" className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2
          id="h-week"
          className="font-mono text-xs uppercase tracking-wider text-muted-foreground"
        >
          semana
        </h2>
        <Button variant="ghost" size="sm" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          {open ? "Fechar semana" : "Ver semana"}
          <ChevronDown aria-hidden className={cn("transition-transform", open && "rotate-180")} />
        </Button>
      </div>
      {days.length > 0 && (
        <ol className="grid grid-cols-7 gap-1.5">
          {days.map((d, i) => (
            <li
              key={d.date}
              className={cn(
                "flex flex-col items-center gap-1 rounded-lg border bg-card px-1 py-2",
                i === 0 && "border-primary/50",
              )}
            >
              <span className={cn("text-xs", i === 0 ? "text-primary" : "text-muted-foreground")}>
                {WEEKDAY_SHORT[d.weekday] ?? d.name}
              </span>
              <span className="font-mono text-[11px] tabular-nums">
                {d.is_rest ? "folga" : hours(d.minutes)}
              </span>
            </li>
          ))}
        </ol>
      )}
      {open && <WeekDetails />}
    </section>
  );
}

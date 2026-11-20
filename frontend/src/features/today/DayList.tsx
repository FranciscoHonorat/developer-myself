import { Circle, CircleCheck, CircleDot } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DayItem } from "./day";
import { StartButton } from "./StartButton";

const KIND = { REVIEW: "Revisar", STUDY: "Estudar" } as const;
const ICON = { done: CircleCheck, next: CircleDot, later: Circle } as const;

/** O resto do dia: o que já foi feito, o próximo e o que vem depois. */
export function DayList({ items, sessionActive }: { items: DayItem[]; sessionActive: boolean }) {
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="h-day" className="flex flex-col gap-3">
      <h2 id="h-day" className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        hoje
      </h2>
      <ul aria-label="Resto do dia" className="flex flex-col divide-y rounded-xl border bg-card">
        {items.map((item) => {
          const Icon = ICON[item.state];
          return (
            <li key={item.contentId} className="flex items-center gap-3 px-4 py-3">
              <Icon
                aria-hidden
                className={cn(
                  "size-5 shrink-0",
                  item.state === "done" ? "text-primary" : "text-muted-foreground",
                )}
              />
              <div className="min-w-0 flex-1">
                <p
                  className={cn(
                    "truncate text-sm",
                    item.state === "done" && "text-muted-foreground line-through",
                  )}
                >
                  <span className="text-muted-foreground">{KIND[item.kind]} · </span>
                  {item.title}
                </p>
                <p className="font-mono text-xs text-muted-foreground">
                  {item.pomodoros > 0 && `${item.pomodoros}×25m · `}d{item.day}/{item.totalDays}
                  {item.state === "done" && " · feito"}
                </p>
              </div>
              {item.state === "later" && (
                <StartButton
                  contentId={item.contentId}
                  label="Iniciar"
                  ariaLabel={`Iniciar ${item.title}`}
                  variant="ghost"
                  size="sm"
                  disabled={sessionActive}
                />
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

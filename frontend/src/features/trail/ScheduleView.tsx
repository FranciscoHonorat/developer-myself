import { Circle, CircleCheck } from "lucide-react";
import { useSchedule } from "@/api/hooks";
import { DAY_KIND_LABEL } from "@/api/scheduleLabels";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { DayPlanView } from "./DayPlanView";

/** Os 30 dias do conteúdo: dias concluídos marcados, o de hoje destacado. */
export function ScheduleView({ contentId }: { contentId: string }) {
  const schedule = useSchedule(contentId, true);
  if (schedule.isPending) return <Skeleton className="h-24 w-full" />;
  if (schedule.isError) return <ErrorState error={schedule.error} compact />;
  const s = schedule.data;

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-background/40 p-3">
      <p className="text-xs text-muted-foreground">
        {s.area} · <span className="font-mono">[{s.depth}]</span> {s.depth_goal}
      </p>
      {s.note && <p className="text-xs text-muted-foreground">{s.note}</p>}
      <ol className="flex max-h-80 flex-col gap-1 overflow-y-auto pr-1">
        {s.days.map((d) => {
          const isToday = d.day === s.current_day;
          return (
            <li
              key={d.day}
              aria-current={isToday ? "step" : undefined}
              className={cn(
                "rounded-md px-2 py-1.5 text-xs",
                isToday && "border border-primary/50 bg-accent/50 p-3",
              )}
            >
              {isToday ? (
                <div className="flex flex-col gap-2">
                  <strong className="font-mono text-primary">dia {d.day} · hoje</strong>
                  <DayPlanView plan={d} />
                </div>
              ) : (
                <span className={cn("flex items-center gap-2", d.done && "text-muted-foreground")}>
                  {d.done ? (
                    <CircleCheck aria-label="feito" className="size-3.5 text-primary" />
                  ) : (
                    <Circle aria-hidden className="size-3.5 text-muted-foreground" />
                  )}
                  <span className="font-mono">d{d.day}</span> · {DAY_KIND_LABEL[d.kind]} · {d.focus}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

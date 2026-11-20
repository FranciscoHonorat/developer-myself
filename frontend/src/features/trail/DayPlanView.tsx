import { DAY_KIND_LABEL } from "@/api/scheduleLabels";
import type { DayPlan } from "@/api/types";
import { Badge } from "@/components/ui/badge";

/** Um dia do cronograma: foco, atividade e o aquecimento de memória (1, 3 e 7 dias). */
export function DayPlanView({ plan }: { plan: DayPlan }) {
  return (
    <div className="flex flex-col gap-1.5 text-sm">
      <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">{DAY_KIND_LABEL[plan.kind]}</Badge> {plan.phase}
      </p>
      <p className="font-medium">{plan.focus}</p>
      <p className="text-muted-foreground">{plan.activity}</p>
      {plan.warmup.length > 0 && (
        <div className="text-xs text-muted-foreground">
          Aquecimento de memória (5 min, sem abrir o material):
          <ul className="mt-1 list-disc pl-5">
            {plan.warmup.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

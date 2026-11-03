import { DAY_KIND_LABEL } from "../api/scheduleLabels";
import type { DayPlan } from "../api/types";

/** Um dia do cronograma: foco, atividade e o aquecimento de memória (1, 3 e 7 dias). */
export function DayPlanView({ plan }: { plan: DayPlan }) {
  return (
    <div className="dayplan">
      <p className="small muted">
        <span className="pill">{DAY_KIND_LABEL[plan.kind]}</span> {plan.phase}
      </p>
      <p>
        <strong>{plan.focus}</strong>
      </p>
      <p className="small">{plan.activity}</p>
      {plan.warmup.length > 0 && (
        <div className="small muted">
          Aquecimento de memória (5 min, sem abrir o material):
          <ul>
            {plan.warmup.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

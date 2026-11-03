import { useSchedule } from "../api/hooks";
import { DAY_KIND_LABEL } from "../api/scheduleLabels";
import { DayPlanView } from "./DayPlanView";
import { ErrorText } from "./ErrorText";

/** Os 30 dias do conteúdo: dias concluídos marcados, o de hoje destacado. */
export function ScheduleView({ contentId }: { contentId: string }) {
  const schedule = useSchedule(contentId, true);
  if (schedule.isPending) return <p className="small muted">Carregando cronograma…</p>;
  if (schedule.isError) return <ErrorText error={schedule.error} />;
  const s = schedule.data;

  return (
    <div className="schedule">
      <p className="small muted">
        {s.area} · [{s.depth}] {s.depth_goal}
      </p>
      {s.note && <p className="small muted">{s.note}</p>}
      <ol className="days">
        {s.days.map((d) => {
          const isToday = d.day === s.current_day;
          return (
            <li
              key={d.day}
              className={isToday ? "day today-day" : d.done ? "day done" : "day"}
              aria-current={isToday ? "step" : undefined}
            >
              {isToday ? (
                <>
                  <strong>Dia {d.day} · hoje</strong>
                  <DayPlanView plan={d} />
                </>
              ) : (
                <span className="small">
                  {d.done ? "✅" : "⬜"} Dia {d.day} · {DAY_KIND_LABEL[d.kind]} · {d.focus}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

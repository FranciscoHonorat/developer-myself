import { useToday } from "../api/hooks";
import type { TodayItem } from "../api/types";
import { BLOCK_LABEL, daysLabel, hours } from "../api/weekLabels";
import { DayPlanView } from "./DayPlanView";

/** O que fazer hoje: os blocos do dia (revisões primeiro) e o detalhe de cada conteúdo. */
export function TodayCard() {
  const today = useToday();
  if (!today.data) return null;
  const { studies, reviews, blocks } = today.data;
  if (studies.length === 0 && reviews.length === 0) return null;
  const total = blocks.reduce((s, b) => s + b.minutes, 0);

  return (
    <section className="card today" aria-labelledby="h-today">
      <h2 id="h-today">
        📅 Hoje {total > 0 && <span className="muted small">· {hours(total)}</span>}
      </h2>
      {blocks.length > 0 && (
        <ol className="blocks" aria-label="Blocos de hoje">
          {blocks.map((b) => (
            <li key={b.content_id}>
              <span className="pill">{BLOCK_LABEL[b.kind]}</span> <strong>{b.title}</strong>{" "}
              <span className="muted small">
                · {b.pomodoros}×25 min · {daysLabel(b)}
              </span>
            </li>
          ))}
        </ol>
      )}
      <ol className="today-list">
        {reviews.map((item) => (
          <TodayEntry key={item.content_id} label="Revisar" item={item} />
        ))}
        {studies.map((item) => (
          <TodayEntry key={item.content_id} label="Estudar" item={item} />
        ))}
      </ol>
    </section>
  );
}

function TodayEntry({ label, item }: { label: string; item: TodayItem }) {
  return (
    <li>
      <p>
        <strong>
          {label}: {item.title}
        </strong>{" "}
        <span className="muted small">
          · dia {item.day} de {item.total_days}
        </span>
      </p>
      <DayPlanView plan={item.plan} />
    </li>
  );
}

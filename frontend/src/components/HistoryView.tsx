import { useHistory, useStats } from "../api/hooks";
import {
  formatDuration,
  LEVEL_LABEL,
  REASON_LABEL,
  RECALL_LABEL,
  SESSION_LABEL,
} from "../api/labels";
import { ErrorText } from "./ErrorText";

export function HistoryView() {
  const stats = useStats();
  const history = useHistory();

  return (
    <div className="stack">
      {stats.data && (
        <section className="stats" aria-label="Estatísticas dos últimos 30 dias">
          <Stat label="Sequência" value={`${stats.data.current_streak_days} dias`} />
          <Stat label="Pontos (30d)" value={stats.data.total_points} />
          <Stat label="Sessões (30d)" value={stats.data.total_sessions} />
          <Stat label="Horas (30d)" value={(stats.data.total_minutes / 60).toFixed(1)} />
        </section>
      )}
      {stats.data && (
        <section className="card">
          <h2>Últimos 30 dias</h2>
          <div className="chart" role="img" aria-label="Minutos estudados por dia">
            {stats.data.daily.map((d) => {
              const max = Math.max(60, ...stats.data.daily.map((x) => x.minutes));
              return (
                <div
                  key={d.day}
                  className={d.points > 0 ? "col scored" : "col"}
                  style={{ height: `${(d.minutes / max) * 100}%` }}
                  title={`${d.day}: ${d.minutes} min, ${d.points} pts`}
                />
              );
            })}
          </div>
        </section>
      )}
      <ErrorText error={stats.error ?? history.error} />

      <section>
        <h2>Sessões</h2>
        {history.data?.length === 0 && <p className="muted">Nenhuma sessão ainda.</p>}
        <ul className="history">
          {history.data?.map((s) => (
            <li key={s.event_id} className="card">
              <div className="row between">
                <strong>
                  {s.awarded ? "🟢" : "⚪"} {s.content_title}
                </strong>
                <span className="muted small">
                  {new Date(s.finished_at).toLocaleString("pt-BR")}
                </span>
              </div>
              <p className="small muted">
                {SESSION_LABEL[s.kind]} · {formatDuration(s.duration_seconds)}
                {s.level_after && ` · ${LEVEL_LABEL[s.level_after]}`}
                {s.recall_rating && ` · lembrava: ${RECALL_LABEL[s.recall_rating]}`}
                {s.reason && ` · ${REASON_LABEL[s.reason] ?? s.reason}`}
              </p>
              {s.notes_studied && (
                <dl className="notes">
                  <dt>Estudei</dt>
                  <dd>{s.notes_studied}</dd>
                  <dt>Entendi</dt>
                  <dd>{s.notes_understood}</dd>
                  <dt>Revisar</dt>
                  <dd>{s.notes_to_review}</dd>
                </dl>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card stat">
      <div className="stat-value">{value}</div>
      <div className="small muted">{label}</div>
    </div>
  );
}

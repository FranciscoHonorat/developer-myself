import { type FormEvent, useState } from "react";
import { useChangePreferences, useWeek } from "../api/hooks";
import type { Week } from "../api/types";
import { BLOCK_LABEL, daysLabel, hours, WEEKDAY_SHORT } from "../api/weekLabels";
import { ErrorText } from "./ErrorText";

/** A semana planejada: grade dia × competência (minutos) e os blocos de cada dia. */
export function WeekView() {
  const week = useWeek();
  if (week.isPending) return <p className="muted">Montando a semana…</p>;
  if (week.isError) return <ErrorText error={week.error} />;
  const w = week.data;
  const hasBlocks = w.days.some((d) => d.blocks.length > 0);

  return (
    <div className="stack">
      <PreferencesForm week={w} />
      {!hasBlocks ? (
        <p className="muted">Nenhum conteúdo em andamento ou para revisar ainda.</p>
      ) : (
        <>
          <Grid week={w} />
          <section aria-labelledby="h-days">
            <h2 id="h-days">Dia a dia</h2>
            <div className="grid">
              {w.days.map((d, i) => (
                <article key={d.date} className="card" aria-label={`${d.name} ${d.date}`}>
                  <h3>
                    {i === 0 ? "Hoje · " : ""}
                    {d.name}{" "}
                    <span className="muted small">
                      {new Date(`${d.date}T12:00:00`).toLocaleDateString("pt-BR")}
                    </span>
                  </h3>
                  {d.is_rest ? (
                    <p className="muted">🌿 Folga</p>
                  ) : (
                    <>
                      <p className="small muted">
                        {hours(d.minutes)} · {d.competencies.length} competências
                      </p>
                      <ol className="blocks">
                        {d.blocks.map((b) => (
                          <li key={b.content_id}>
                            <span className="pill">{BLOCK_LABEL[b.kind]}</span>{" "}
                            <strong>{b.competency_name}</strong> · {b.pomodoros}×{w.study_minutes}{" "}
                            min
                            <div className="small">
                              {b.title} · {daysLabel(b)}: {b.focus}
                            </div>
                          </li>
                        ))}
                      </ol>
                    </>
                  )}
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

/** Tabela dia × competência: o número é o dado (minutos), sem gráfico a decifrar. */
function Grid({ week }: { week: Week }) {
  const comps: { key: string; name: string }[] = [];
  for (const d of week.days)
    for (const b of d.blocks)
      if (!comps.some((c) => c.key === b.competency))
        comps.push({ key: b.competency, name: b.competency_name });
  const minutes = (dayIndex: number, comp: string) =>
    (week.days[dayIndex]?.blocks ?? [])
      .filter((b) => b.competency === comp)
      .reduce((sum, b) => sum + b.minutes, 0);
  const total = (comp: string) => week.days.reduce((s, _, i) => s + minutes(i, comp), 0);

  return (
    <section className="card" aria-labelledby="h-grid">
      <h2 id="h-grid">Semana por competência</h2>
      <p className="small muted">
        Minutos por dia, em pomodoros de {week.pomodoro_minutes} min ({week.study_minutes} de estudo
        + {week.pomodoro_minutes - week.study_minutes} de pausa). Revisões primeiro: elas liberam a
        pontuação do estudo.
      </p>
      <div className="table-scroll">
        <table className="contrib week-grid">
          <thead>
            <tr>
              <th scope="col">Competência</th>
              {week.days.map((d) => (
                <th key={d.date} scope="col" className="num">
                  {WEEKDAY_SHORT[d.weekday]}
                </th>
              ))}
              <th scope="col" className="num">
                Semana
              </th>
            </tr>
          </thead>
          <tbody>
            {comps.map((c) => (
              <tr key={c.key}>
                <th scope="row">{c.name}</th>
                {week.days.map((d, i) => {
                  const m = minutes(i, c.key);
                  return (
                    <td key={d.date} className={m ? "num cell-on" : "num muted"}>
                      {m || "·"}
                    </td>
                  );
                })}
                <td className="num">{hours(total(c.key))}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Total</th>
              {week.days.map((d) => (
                <td key={d.date} className="num">
                  {d.is_rest ? "folga" : hours(d.minutes)}
                </td>
              ))}
              <td className="num">{hours(week.days.reduce((s, d) => s + d.minutes, 0))}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

const OPTIONS = [180, 210, 240];

function PreferencesForm({ week }: { week: Week }) {
  const [minutes, setMinutes] = useState(week.minutes_per_day);
  const [rest, setRest] = useState<number[]>(week.rest_days);
  const change = useChangePreferences();
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    change.mutate({ minutes, restDays: rest });
  };
  const toggle = (d: number) =>
    setRest((r) => (r.includes(d) ? r.filter((x) => x !== d) : [...r, d].sort()));

  return (
    <form className="card stack" onSubmit={onSubmit} aria-label="Preferências de estudo">
      <h2>Ritmo</h2>
      <fieldset className="row wrap">
        <legend className="small">Tempo de estudo por dia</legend>
        {OPTIONS.map((m) => (
          <label key={m} className={minutes === m ? "chip selected" : "chip"}>
            <input
              type="radio"
              name="minutes"
              checked={minutes === m}
              onChange={() => setMinutes(m)}
            />
            {hours(m)}
          </label>
        ))}
      </fieldset>
      <fieldset className="row wrap">
        <legend className="small">Dias de folga</legend>
        {WEEKDAY_SHORT.map((label, d) => (
          <label key={label} className={rest.includes(d) ? "chip selected" : "chip"}>
            <input type="checkbox" checked={rest.includes(d)} onChange={() => toggle(d)} />
            {label}
          </label>
        ))}
      </fieldset>
      <div className="row">
        <button type="submit" className="primary" disabled={change.isPending}>
          Salvar ritmo
        </button>
        {change.isSuccess && <span className="small ok-text">Semana recalculada.</span>}
      </div>
      <ErrorText error={change.error} />
    </form>
  );
}

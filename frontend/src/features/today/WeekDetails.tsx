import { useWeek } from "@/api/hooks";
import type { Week } from "@/api/types";
import { BLOCK_LABEL, daysLabel, hours, WEEKDAY_SHORT } from "@/api/weekLabels";
import { ErrorState } from "@/components/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PreferencesForm } from "@/features/account/PreferencesForm";
import { cn } from "@/lib/utils";

/** A semana planejada: ritmo, grade dia × competência (minutos) e os blocos de cada dia. */
export function WeekDetails() {
  const week = useWeek();
  if (week.isPending) return <Skeleton className="h-48 w-full" />;
  if (week.isError) return <ErrorState error={week.error} onRetry={() => week.refetch()} />;
  const w = week.data;
  const hasBlocks = w.days.some((d) => d.blocks.length > 0);

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border bg-card p-4 sm:p-5">
        <h3 className="mb-4 text-base font-semibold">Ritmo</h3>
        <PreferencesForm prefs={{ minutes_per_day: w.minutes_per_day, rest_days: w.rest_days }} />
      </section>
      {!hasBlocks ? (
        <p className="text-sm text-muted-foreground">
          Nenhum conteúdo em andamento ou para revisar ainda.
        </p>
      ) : (
        <>
          <Grid week={w} />
          <section aria-labelledby="h-days" className="flex flex-col gap-3">
            <h3 id="h-days" className="text-base font-semibold">
              Dia a dia
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {w.days.map((d, i) => (
                <article
                  key={d.date}
                  aria-label={`${d.name} ${d.date}`}
                  className={cn(
                    "flex flex-col gap-2 rounded-xl border bg-card p-4",
                    i === 0 && "border-primary/50",
                  )}
                >
                  <h4 className="text-sm font-semibold">
                    {i === 0 ? "Hoje · " : ""}
                    {d.name}{" "}
                    <span className="font-mono text-xs font-normal text-muted-foreground">
                      {new Date(`${d.date}T12:00:00`).toLocaleDateString("pt-BR")}
                    </span>
                  </h4>
                  {d.is_rest ? (
                    <p className="text-sm text-muted-foreground">Folga</p>
                  ) : (
                    <>
                      <p className="font-mono text-xs text-muted-foreground">
                        {hours(d.minutes)} · {d.competencies.length} competências
                      </p>
                      <ol className="flex flex-col gap-2 text-sm">
                        {d.blocks.map((b) => (
                          <li key={b.content_id} className="flex flex-col gap-0.5">
                            <span className="flex flex-wrap items-center gap-1.5">
                              <Badge variant="outline">{BLOCK_LABEL[b.kind]}</Badge>
                              <strong className="font-medium">{b.competency_name}</strong>
                              <span className="font-mono text-xs text-muted-foreground">
                                {b.pomodoros}×{w.study_minutes}m
                              </span>
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {b.title} · {daysLabel(b)}: {b.focus}
                            </span>
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
    <section
      aria-labelledby="h-grid"
      className="flex flex-col gap-2 rounded-xl border bg-card p-4 sm:p-5"
    >
      <h3 id="h-grid" className="text-base font-semibold">
        Semana por competência
      </h3>
      <p className="text-xs text-muted-foreground">
        Minutos por dia, em pomodoros de {week.pomodoro_minutes} min ({week.study_minutes} de estudo
        + {week.pomodoro_minutes - week.study_minutes} de pausa). Revisões primeiro: elas liberam a
        pontuação do estudo.
      </p>
      <div className="-mx-1 overflow-x-auto">
        <table className="w-full min-w-[32rem] border-collapse text-sm [&_td]:px-2 [&_td]:py-1.5 [&_th]:px-2 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-medium [&_tr]:border-b">
          <thead>
            <tr>
              <th scope="col">Competência</th>
              {week.days.map((d) => (
                <th key={d.date} scope="col" className="text-right font-mono tabular-nums">
                  {WEEKDAY_SHORT[d.weekday]}
                </th>
              ))}
              <th scope="col" className="text-right font-mono tabular-nums">
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
                    <td
                      key={d.date}
                      className={cn(
                        "text-right font-mono tabular-nums",
                        m ? "text-primary" : "text-muted-foreground",
                      )}
                    >
                      {m || "·"}
                    </td>
                  );
                })}
                <td className="text-right font-mono tabular-nums">{hours(total(c.key))}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Total</th>
              {week.days.map((d) => (
                <td key={d.date} className="text-right font-mono tabular-nums">
                  {d.is_rest ? "folga" : hours(d.minutes)}
                </td>
              ))}
              <td className="text-right font-mono tabular-nums">
                {hours(week.days.reduce((s, d) => s + d.minutes, 0))}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

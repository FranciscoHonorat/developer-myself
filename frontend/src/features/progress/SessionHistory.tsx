import { CircleCheck, CircleSlash, Flame } from "lucide-react";
import { useHistory, useStats } from "@/api/hooks";
import {
  formatDuration,
  GRADE_LABEL,
  HISTORY_LABEL,
  LEVEL_LABEL,
  REASON_LABEL,
  RECALL_LABEL,
} from "@/api/labels";
import type { RecallGrade } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const GRADE_TONE: Record<RecallGrade, string> = {
  MISSED: "border-destructive/50 text-destructive",
  PARTIAL: "border-warning/50 text-warning",
  RECALLED: "border-primary/50 text-primary",
};

export function SessionHistory() {
  const stats = useStats();
  const history = useHistory();
  const sessions = history.data?.pages.flatMap((p) => p.items);

  return (
    <div className="flex flex-col gap-6">
      {stats.isPending && <Skeleton className="h-24 w-full" />}
      {stats.data && (
        <section
          aria-label="Estatísticas dos últimos 30 dias"
          className={cn(
            "grid grid-cols-2 gap-3",
            stats.data.recall_accuracy != null ? "sm:grid-cols-5" : "sm:grid-cols-4",
          )}
        >
          <Stat label="Sequência" value={`${stats.data.current_streak_days} dias`} />
          <Stat label="Pontos (30d)" value={stats.data.total_points} />
          <Stat label="Sessões (30d)" value={stats.data.total_sessions} />
          <Stat label="Horas (30d)" value={(stats.data.total_minutes / 60).toFixed(1)} />
          {stats.data.recall_accuracy != null && (
            <Stat
              label={`Domínio (${stats.data.recall_questions_recalled ?? 0}/${stats.data.recall_questions_total ?? 0})`}
              value={`${stats.data.recall_accuracy}%`}
            />
          )}
        </section>
      )}
      {stats.data && stats.data.daily.length > 0 && (
        <section className="flex flex-col gap-3 rounded-xl border bg-card p-4 sm:p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold">Últimos 30 dias</h2>
            <p className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span aria-hidden className="size-2.5 rounded-sm bg-[var(--series-1)]" /> pontuou
              </span>
              <span className="flex items-center gap-1.5">
                <span aria-hidden className="size-2.5 rounded-sm bg-[var(--seq-track)]" /> sem ponto
              </span>
            </p>
          </div>
          <div
            role="img"
            aria-label="Minutos estudados por dia"
            className="flex h-32 items-end gap-0.5 border-b"
          >
            {stats.data.daily.map((d) => {
              const max = Math.max(60, ...stats.data.daily.map((x) => x.minutes));
              return (
                <div
                  key={d.day}
                  title={`${d.day}: ${d.minutes} min, ${d.points} pts`}
                  className={cn(
                    "flex-1 rounded-t-sm",
                    d.points > 0 ? "bg-[var(--series-1)]" : "bg-[var(--seq-track)]",
                  )}
                  style={{ height: `${Math.max(d.minutes > 0 ? 3 : 0, (d.minutes / max) * 100)}%` }}
                />
              );
            })}
          </div>
        </section>
      )}
      <ErrorState error={stats.error ?? history.error} compact />

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Sessões</h2>
        {history.isPending && <Skeleton className="h-24 w-full" />}
        {sessions?.length === 0 && (
          <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
            Nenhuma sessão ainda.
          </p>
        )}
        <ul className="flex flex-col gap-3">
          {sessions?.map((s) => (
            <li key={s.event_id} className="flex flex-col gap-2 rounded-xl border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="flex items-center gap-2 font-medium">
                  {s.kind === "WARMUP" ? (
                    <Flame aria-label="aquecimento" className="size-4 text-primary" />
                  ) : s.awarded ? (
                    <CircleCheck aria-label="pontuou" className="size-4 text-primary" />
                  ) : (
                    <CircleSlash aria-label="sem ponto" className="size-4 text-muted-foreground" />
                  )}
                  {s.content_title}
                </strong>
                <span className="font-mono text-xs text-muted-foreground">
                  {new Date(s.finished_at).toLocaleString("pt-BR")}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {HISTORY_LABEL[s.kind]} · {formatDuration(s.duration_seconds)}
                {s.level_after && ` · ${LEVEL_LABEL[s.level_after]}`}
                {s.recall_rating && ` · lembrava: ${RECALL_LABEL[s.recall_rating]}`}
                {s.reason && ` · ${REASON_LABEL[s.reason] ?? s.reason}`}
              </p>
              {s.notes_studied && (
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                  <dt className="text-muted-foreground">Estudei</dt>
                  <dd className="[overflow-wrap:anywhere]">{s.notes_studied}</dd>
                  <dt className="text-muted-foreground">Entendi</dt>
                  <dd className="[overflow-wrap:anywhere]">{s.notes_understood}</dd>
                  <dt className="text-muted-foreground">Revisar</dt>
                  <dd className="[overflow-wrap:anywhere]">{s.notes_to_review}</dd>
                </dl>
              )}
              {s.recall_test && s.recall_test.length > 0 && (
                <details className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
                  <summary className="cursor-pointer text-xs text-muted-foreground">
                    Teste de memória
                  </summary>
                  <ol className="mt-2 flex flex-col gap-3">
                    {s.recall_test.map((item) => (
                      <li key={item.text} className="flex flex-col gap-1">
                        <strong className="text-sm font-medium">{item.text}</strong>
                        <p className="whitespace-pre-wrap text-sm text-muted-foreground [overflow-wrap:anywhere]">
                          {item.answer || "(em branco)"}
                        </p>
                        <span
                          className={cn(
                            "self-start rounded-full border px-2 py-0.5 text-xs",
                            GRADE_TONE[item.grade],
                          )}
                        >
                          {GRADE_LABEL[item.grade]}
                        </span>
                      </li>
                    ))}
                  </ol>
                </details>
              )}
            </li>
          ))}
        </ul>
        {history.hasNextPage && (
          <Button
            variant="outline"
            className="self-center"
            onClick={() => void history.fetchNextPage()}
            disabled={history.isFetchingNextPage}
          >
            {history.isFetchingNextPage ? "Carregando…" : "Carregar mais"}
          </Button>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="font-mono text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

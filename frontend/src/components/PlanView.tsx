import { useState } from "react";
import { usePlan } from "../api/hooks";
import type { Outcome } from "../api/types";
import { ActiveSessionPanel } from "./ActiveSessionPanel";
import { AddContentForm } from "./AddContentForm";
import { ContentCard } from "./ContentCard";
import { ErrorText } from "./ErrorText";
import { OutcomeBanner } from "./OutcomeBanner";
import { ReviewSuggestion } from "./ReviewSuggestion";
import { TodayCard } from "./TodayCard";

export function PlanView() {
  const plan = usePlan();
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  if (plan.isPending) return <p className="muted">Carregando trilha…</p>;
  if (plan.isError) return <ErrorText error={plan.error} />;

  const { contents, active_session: active } = plan.data;
  const current = contents.filter((c) => c.status === "IN_PROGRESS");
  const review = contents.filter((c) => c.status === "CONSOLIDATED" || c.status === "FINISHED");
  const queue = contents
    .filter((c) => c.status === "LOCKED")
    .sort((a, b) => (a.queue_position ?? 0) - (b.queue_position ?? 0));

  return (
    <div className="stack">
      {plan.data.needs_review_today && !active && (
        <div className="banner warn" role="status">
          📌 Revise um conteúdo consolidado antes de estudar o atual. Sem a revisão do dia, a sessão
          de estudo não pontua.
        </div>
      )}
      {plan.data.reviewed_today && (
        <div className="banner ok" role="status">
          ✅ Revisão do dia feita. Sessões de estudo podem pontuar hoje.
        </div>
      )}

      {!active && <TodayCard />}

      {outcome && <OutcomeBanner outcome={outcome} onClose={() => setOutcome(null)} />}

      {active && (
        <ActiveSessionPanel
          session={active}
          serverTime={plan.data.server_time}
          onFinished={setOutcome}
        />
      )}

      <section aria-labelledby="h-current">
        <h2 id="h-current">
          Em andamento{" "}
          <span className="muted small">
            ({current.length} de {plan.data.max_in_progress} vagas)
          </span>
        </h2>
        {current.length === 0 && (
          <p className="muted">
            Nada em andamento. Adicione um conteúdo abaixo: o primeiro da fila começa na hora.
          </p>
        )}
        {current.map((c) => (
          <ContentCard key={c.id} content={c} hasActiveSession={active !== null} />
        ))}
      </section>

      <AddContentForm />

      <ReviewSuggestion />

      {review.length > 0 && (
        <section aria-labelledby="h-review">
          <h2 id="h-review">Para revisar</h2>
          <div className="grid">
            {review.map((c) => (
              <ContentCard key={c.id} content={c} hasActiveSession={active !== null} />
            ))}
          </div>
        </section>
      )}

      {queue.length > 0 && (
        <section aria-labelledby="h-queue">
          <h2 id="h-queue">Fila</h2>
          <div className="grid">
            {queue.map((c) => (
              <ContentCard key={c.id} content={c} hasActiveSession={active !== null} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

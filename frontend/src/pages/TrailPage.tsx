import type { ReactNode } from "react";
import { usePlan } from "@/api/hooks";
import { recallTestOn } from "@/api/recall";
import type { Content, Plan } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { AddContentDialog } from "@/features/trail/AddContentDialog";
import { ContentCard } from "@/features/trail/ContentCard";

function Section({
  id,
  title,
  extra,
  children,
}: {
  id: string;
  title: string;
  extra?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <h2 id={id} className="flex items-baseline gap-3 text-lg font-semibold">
        {title}
        {extra}
      </h2>
      {children}
    </section>
  );
}

function Cards({ contents, plan }: { contents: Content[]; plan: Plan }) {
  const active = plan.active_session;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {contents.map((c) => (
        <ContentCard
          key={c.id}
          content={c}
          hasActiveSession={active !== null}
          notebookLocked={recallTestOn(active, c.id)}
        />
      ))}
    </div>
  );
}

/** O acervo: o que está em andamento, o que revisar e a fila. */
export function TrailPage() {
  const plan = usePlan();

  if (plan.isPending) {
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-44 w-full" />
      </div>
    );
  }
  if (plan.isError) return <ErrorState error={plan.error} onRetry={() => plan.refetch()} />;

  const p = plan.data;
  const current = p.contents.filter((c) => c.status === "IN_PROGRESS");
  const review = p.contents.filter((c) => c.status === "CONSOLIDATED" || c.status === "FINISHED");
  const queue = p.contents
    .filter((c) => c.status === "LOCKED")
    .sort((a, b) => (a.queue_position ?? 0) - (b.queue_position ?? 0));

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Trilha</h1>
        <AddContentDialog />
      </header>

      <Section
        id="h-current"
        title="Em andamento"
        extra={
          <span className="font-mono text-xs font-normal text-muted-foreground">
            {current.length}/{p.max_in_progress} vagas
          </span>
        }
      >
        {current.length === 0 ? (
          <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
            Nada em andamento. Adicione um conteúdo: o primeiro da fila começa na hora.
          </p>
        ) : (
          <Cards contents={current} plan={p} />
        )}
      </Section>

      {review.length > 0 && (
        <Section id="h-review" title="Para revisar">
          <Cards contents={review} plan={p} />
        </Section>
      )}

      {queue.length > 0 && (
        <Section id="h-queue" title="Fila">
          <Cards contents={queue} plan={p} />
        </Section>
      )}
    </div>
  );
}

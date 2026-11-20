import type { ReactNode } from "react";
import { usePlan } from "@/api/hooks";
import { recallTestOn } from "@/api/recall";
import type { Content, Plan } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Pagination } from "@/components/Pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { AddContentDialog } from "@/features/trail/AddContentDialog";
import { ContentCard } from "@/features/trail/ContentCard";
import { paginate } from "@/lib/paginate";
import { usePageParam } from "@/lib/usePageParam";

/** Cartões por página em "Para revisar" e "Fila" (grade de 2 colunas: 3 linhas). */
export const TRAIL_PAGE_SIZE = 6;

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

/** Seção longa em páginas; a página vive na URL (`?{param}=N`). */
function PagedCards({
  contents,
  plan,
  param,
  label,
}: {
  contents: Content[];
  plan: Plan;
  param: string;
  label: string;
}) {
  const [requested, setPage] = usePageParam(param);
  const { items, page, totalPages } = paginate(contents, requested ?? 1, TRAIL_PAGE_SIZE);
  return (
    <>
      <Cards contents={items} plan={plan} />
      <Pagination page={page} totalPages={totalPages} onChange={setPage} label={label} />
    </>
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
          <PagedCards contents={review} plan={p} param="revisar" label="Para revisar" />
        </Section>
      )}

      {queue.length > 0 && (
        <Section id="h-queue" title="Fila">
          <PagedCards contents={queue} plan={p} param="fila" label="Fila" />
        </Section>
      )}
    </div>
  );
}

import type { ReactNode } from "react";
import { usePlan, useReorderQueue } from "@/api/hooks";
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

function Cards({
  contents,
  plan,
  queueOrder,
  onReorder,
  reordering = false,
}: {
  contents: Content[];
  plan: Plan;
  queueOrder?: string[] | undefined;
  onReorder?: ((ids: string[]) => void) | undefined;
  reordering?: boolean | undefined;
}) {
  const active = plan.active_session;
  const move = (id: string, delta: -1 | 1) => {
    if (!queueOrder || !onReorder) return;
    const idx = queueOrder.indexOf(id);
    const target = idx + delta;
    if (idx < 0 || target < 0 || target >= queueOrder.length) return;
    const next = [...queueOrder];
    const current = next[idx];
    const swapped = next[target];
    if (!current || !swapped) return;
    next[idx] = swapped;
    next[target] = current;
    onReorder(next);
  };
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {contents.map((c) => {
        const pos = queueOrder ? queueOrder.indexOf(c.id) : -1;
        return (
          <ContentCard
            key={c.id}
            content={c}
            hasActiveSession={active !== null}
            notebookLocked={recallTestOn(active, c.id)}
            onMoveUp={pos > 0 ? () => move(c.id, -1) : undefined}
            onMoveDown={
              queueOrder && pos >= 0 && pos < queueOrder.length - 1
                ? () => move(c.id, 1)
                : undefined
            }
            reordering={reordering}
          />
        );
      })}
    </div>
  );
}

/** Seção longa em páginas; a página vive na URL (`?{param}=N`). */
function PagedCards({
  contents,
  plan,
  param,
  label,
  queueOrder,
  onReorder,
  reordering,
}: {
  contents: Content[];
  plan: Plan;
  param: string;
  label: string;
  queueOrder?: string[];
  onReorder?: (ids: string[]) => void;
  reordering?: boolean;
}) {
  const [requested, setPage] = usePageParam(param);
  const { items, page, totalPages } = paginate(contents, requested ?? 1, TRAIL_PAGE_SIZE);
  return (
    <>
      <Cards
        contents={items}
        plan={plan}
        queueOrder={queueOrder}
        onReorder={onReorder}
        reordering={reordering}
      />
      <Pagination page={page} totalPages={totalPages} onChange={setPage} label={label} />
    </>
  );
}

/** O acervo: o que está em andamento, o que revisar e a fila. */
export function TrailPage() {
  const plan = usePlan();
  const reorder = useReorderQueue();

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
  const daily = current.filter((c) => c.daily).length;
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
            {current.filter((c) => !c.daily).length}/{p.max_in_progress} vagas
            {daily > 0 ? ` · ${daily} de todo dia` : ""}
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
          <PagedCards
            contents={queue}
            plan={p}
            param="fila"
            label="Fila"
            queueOrder={queue.map((q) => q.id)}
            onReorder={(ids) => reorder.mutate(ids)}
            reordering={reorder.isPending}
          />
          <ErrorState error={reorder.error} compact />
        </Section>
      )}
    </div>
  );
}

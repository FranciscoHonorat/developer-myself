import { ChevronLeft, Lock } from "lucide-react";
import { Link, useParams } from "react-router";
import { useNotebooks, usePlan } from "@/api/hooks";
import { STATUS_LABEL } from "@/api/labels";
import { recallTestOn } from "@/api/recall";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { NotebookEditor } from "@/features/notebook/NotebookEditor";
import { MOBILE_QUERY, useMediaQuery } from "@/lib/useMediaQuery";
import { cn } from "@/lib/utils";

/** Caderno: matérias à esquerda, o caderno da escolhida (pela URL) à direita. */
export function NotebookPage() {
  const plan = usePlan();
  const summaries = useNotebooks();
  const { contentId } = useParams();
  const isMobile = useMediaQuery(MOBILE_QUERY);

  const contents = plan.data?.contents ?? [];
  const byContent = new Map((summaries.data ?? []).map((s) => [s.content_id, s]));
  const current = contents.find((c) => c.id === contentId);

  if (plan.isPending) {
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }
  if (plan.data && contents.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Caderno</h1>
        <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
          Adicione um conteúdo na{" "}
          <Link to="/trilha" className="text-primary underline">
            Trilha
          </Link>{" "}
          para ter um caderno.
        </p>
      </div>
    );
  }

  const showList = !isMobile || !contentId;
  const showEditor = !isMobile || Boolean(contentId);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Caderno</h1>
      <div className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
        {showList && (
          <nav aria-label="Matérias" className="rounded-xl border bg-card p-2">
            <ul className="flex flex-col gap-1">
              {contents.map((c) => {
                const summary = byContent.get(c.id);
                const active = c.id === contentId;
                return (
                  <li key={c.id}>
                    <Link
                      to={`/caderno/${c.id}`}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex flex-col gap-0.5 rounded-lg px-3 py-2 outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring",
                        active && "bg-accent text-accent-foreground hover:bg-accent",
                      )}
                    >
                      <strong className="truncate text-sm font-medium">{c.title}</strong>
                      <span className="font-mono text-xs text-muted-foreground">
                        {summary && summary.chars > 0
                          ? `${summary.chars.toLocaleString("pt-BR")} caracteres` +
                            (summary.updated_at
                              ? ` · ${new Date(summary.updated_at).toLocaleDateString("pt-BR")}`
                              : "")
                          : STATUS_LABEL[c.status]}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        )}
        {showEditor && (
          <section className="flex flex-col gap-3 rounded-xl border bg-card p-4 sm:p-5">
            {isMobile && (
              <Link
                to="/caderno"
                aria-label="Voltar às matérias"
                className="flex items-center gap-1 self-start text-sm text-muted-foreground hover:text-foreground"
              >
                <ChevronLeft aria-hidden className="size-4" /> Matérias
              </Link>
            )}
            {current && recallTestOn(plan.data?.active_session ?? null, current.id) ? (
              <p className="flex items-start gap-2 text-sm text-muted-foreground">
                <Lock aria-hidden className="mt-0.5 size-4 shrink-0" />
                Teste de memória em andamento: responda sem consultar. O caderno desta matéria abre
                no painel da sessão depois de conferir as respostas.
              </p>
            ) : current ? (
              <NotebookEditor key={current.id} contentId={current.id} title={current.title} tall />
            ) : (
              <p className="text-sm text-muted-foreground">Escolha uma matéria.</p>
            )}
          </section>
        )}
      </div>
      <ErrorState error={plan.error ?? summaries.error} compact />
    </div>
  );
}

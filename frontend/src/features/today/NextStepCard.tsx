import { Info } from "lucide-react";
import type { DayItem } from "./day";
import { StartButton } from "./StartButton";

const KIND = { REVIEW: "revisão", STUDY: "estudo" } as const;

/** O maior elemento do Hoje: o que fazer agora e o botão para começar. */
export function NextStepCard({
  item,
  mustReviewFirst,
}: {
  item: DayItem;
  mustReviewFirst: boolean;
}) {
  return (
    <section
      aria-labelledby="h-next"
      className="relative overflow-hidden rounded-2xl border border-primary/40 bg-card p-5 sm:p-6"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-24 size-64 rounded-full bg-primary/10 blur-3xl"
      />
      <p className="font-mono text-xs font-semibold uppercase tracking-wider text-primary">
        › próximo · {KIND[item.kind]}
      </p>
      <h2 id="h-next" className="mt-1 text-2xl font-semibold tracking-tight">
        {item.title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{item.focus}</p>
      <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-muted-foreground">
        {item.pomodoros > 0 && <span>{item.pomodoros}×25m</span>}
        <span>
          d{item.day}/{item.totalDays}
        </span>
      </p>
      {mustReviewFirst && item.kind === "REVIEW" && (
        <p className="mt-3 flex items-start gap-2 text-sm text-warning">
          <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
          Revise antes de estudar: sem a revisão do dia, o estudo não pontua.
        </p>
      )}
      <StartButton
        contentId={item.contentId}
        label={item.kind === "REVIEW" ? "Iniciar revisão" : "Iniciar estudo"}
        size="lg"
        className="mt-5 w-full sm:w-auto"
      />
    </section>
  );
}

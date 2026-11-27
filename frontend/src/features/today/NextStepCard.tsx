import { Compass, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DayItem } from "./day";
import { StartButton } from "./StartButton";

const KIND = { REVIEW: "revisão", STUDY: "estudo" } as const;

/** O maior elemento do Hoje: o que fazer agora, o porquê e escolha entre opções do dia. */
export function NextStepCard({
  item,
  purpose,
  alternatives = [],
  onSelect,
  mustReviewFirst,
}: {
  item: DayItem;
  purpose?: string | null | undefined;
  alternatives?: DayItem[];
  onSelect?: (contentId: string) => void;
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
        › {item.state === "next" ? "próximo" : "sua escolha"} · {KIND[item.kind]}
      </p>
      <h2 id="h-next" className="mt-1 text-2xl font-semibold tracking-tight">
        {item.title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{item.focus}</p>
      {purpose && (
        <p className="mt-2 flex items-start gap-1.5 text-sm text-foreground/85">
          <Compass aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
          <span>{purpose}</span>
        </p>
      )}
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
      {mustReviewFirst && item.kind === "STUDY" && (
        <p className="mt-3 flex items-start gap-2 text-sm text-warning">
          <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
          Há uma revisão sugerida para hoje — você pode começar por aqui se preferir, mas a
          pontuação do estudo libera depois da revisão.
        </p>
      )}
      <StartButton
        contentId={item.contentId}
        label={item.kind === "REVIEW" ? "Iniciar revisão" : "Iniciar estudo"}
        size="lg"
        className="mt-5 w-full sm:w-auto"
      />
      {alternatives.length > 1 && onSelect && (
        <fieldset className="mt-5 flex flex-col gap-2 border-t pt-4">
          <legend className="mb-1 text-xs text-muted-foreground">
            Autonomia — prefere começar por outro foco hoje?
          </legend>
          <div className="flex flex-wrap gap-2">
            {alternatives.map((alt) => {
              const selected = alt.contentId === item.contentId;
              return (
                <button
                  key={alt.contentId}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => onSelect(alt.contentId)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    selected
                      ? "border-primary bg-accent font-medium text-accent-foreground"
                      : "text-muted-foreground hover:border-foreground/30 hover:text-foreground",
                  )}
                >
                  {KIND[alt.kind]} · {alt.title}
                </button>
              );
            })}
          </div>
        </fieldset>
      )}
    </section>
  );
}

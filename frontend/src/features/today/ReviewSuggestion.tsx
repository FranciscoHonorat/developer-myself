import { Brain } from "lucide-react";
import { useRecommendations } from "@/api/hooks";
import { cn } from "@/lib/utils";

const MODEL_LABEL: Record<string, string> = {
  "rede-neural": "rede neural",
  regra: "regra de repetição espaçada",
};

/** Mostra o que a rede neural acha que você está mais perto de esquecer. */
export function ReviewSuggestion() {
  const recs = useRecommendations();
  const items = recs.data?.items ?? [];
  if (items.length === 0 || !recs.data) return null;

  return (
    <section
      aria-labelledby="h-suggestion"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4 sm:p-5"
    >
      <div className="flex flex-col gap-1">
        <h2 id="h-suggestion" className="flex items-center gap-2 text-base font-semibold">
          <Brain aria-hidden className="size-4 text-primary" />O que revisar primeiro
        </h2>
        <p className="text-xs text-muted-foreground">
          Estimativa da {MODEL_LABEL[recs.data.model] ?? recs.data.model} da chance de você ainda
          lembrar de cada conteúdo. Comece pelo de menor chance.
        </p>
        <p className="text-xs text-muted-foreground">
          {recs.data.model_info.real_samples > 0
            ? `Treinada com ${recs.data.model_info.real_samples} autoavaliações suas.`
            : "Ainda treinada só com dados simulados: suas autoavaliações nas revisões vão ensiná-la."}
        </p>
      </div>
      <ol className="flex flex-col gap-2">
        {items.slice(0, 5).map((item) => {
          const pct = Math.round(item.recall_probability * 100);
          return (
            <li
              key={item.content_id}
              className="grid grid-cols-[minmax(0,1fr)_6rem_3rem] items-center gap-3 text-sm"
            >
              <span className="truncate">{item.title}</span>
              <meter
                aria-label={`Chance de lembrar ${item.title}`}
                min={0}
                max={100}
                low={50}
                optimum={100}
                value={pct}
                className="sr-only"
              />
              <span
                aria-hidden
                className="h-1.5 overflow-hidden rounded-full bg-[var(--seq-track)]"
              >
                <span
                  className={cn(
                    "block h-full rounded-full",
                    pct < 50 ? "bg-rust" : "bg-[var(--seq-fill)]",
                  )}
                  style={{ width: `${pct}%` }}
                />
              </span>
              <span className="text-right font-mono text-xs tabular-nums text-muted-foreground">
                {pct}%
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

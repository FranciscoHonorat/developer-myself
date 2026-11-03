import { useRecommendations } from "../api/hooks";

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
    <section className="card" aria-labelledby="h-suggestion">
      <h2 id="h-suggestion">🧠 O que revisar primeiro</h2>
      <p className="small muted">
        Estimativa da {MODEL_LABEL[recs.data.model] ?? recs.data.model} da chance de você ainda
        lembrar de cada conteúdo. Comece pelo de menor chance.
      </p>
      <p className="small muted">
        {recs.data.model_info.real_samples > 0
          ? `Treinada com ${recs.data.model_info.real_samples} autoavaliações suas.`
          : "Ainda treinada só com dados simulados: suas autoavaliações nas revisões vão ensiná-la."}
      </p>
      <ol className="suggestions">
        {items.slice(0, 5).map((item) => {
          const pct = Math.round(item.recall_probability * 100);
          return (
            <li key={item.content_id}>
              <span>{item.title}</span>
              <meter
                aria-label={`Chance de lembrar ${item.title}`}
                min={0}
                max={100}
                low={50}
                optimum={100}
                value={pct}
              />
              <span className="small muted">{pct}%</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

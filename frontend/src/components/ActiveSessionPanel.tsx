import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useCancelSession, useFinishSession } from "../api/hooks";
import { charsWithoutSpaces, formatDuration, RECALL_LABEL, SESSION_LABEL } from "../api/labels";
import type { ActiveSession, Outcome } from "../api/types";
import { ErrorText } from "./ErrorText";

const MIN_SECONDS = 25 * 60;
const MIN_CHARS = 50;

interface Props {
  session: ActiveSession;
  serverTime: string;
  onFinished: (outcome: Outcome) => void;
}

/** O timer é só visual: quem marca início/fim e decide os pontos é o servidor. */
export function ActiveSessionPanel({ session, serverTime, onFinished }: Props) {
  const offset = useMemo(() => Date.parse(serverTime) - Date.now(), [serverTime]);
  const [now, setNow] = useState(() => Date.now() + offset);
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now() + offset), 1000);
    return () => window.clearInterval(id);
  }, [offset]);

  const [studied, setStudied] = useState("");
  const [understood, setUnderstood] = useState("");
  const [toReview, setToReview] = useState("");
  const [recall, setRecall] = useState<number | null>(null);
  const isReview = session.kind === "REVIEW";
  const finish = useFinishSession();
  const cancel = useCancelSession();

  const elapsed = (now - Date.parse(session.started_at)) / 1000;
  const chars = charsWithoutSpaces(studied, understood, toReview);
  const allFilled = [studied, understood, toReview].every((f) => f.trim() !== "");
  const progress = Math.min(1, elapsed / MIN_SECONDS);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    finish.mutate(
      {
        studied,
        understood,
        to_review: toReview,
        ...(isReview && recall !== null ? { recall_rating: recall } : {}),
      },
      {
        onSuccess: (outcome) => {
          setStudied("");
          setUnderstood("");
          setToReview("");
          setRecall(null);
          onFinished(outcome);
        },
      },
    );
  };

  return (
    <section className="card session" aria-labelledby="h-session">
      <div className="session-head">
        <div>
          <h2 id="h-session">
            {session.kind ? SESSION_LABEL[session.kind] : "Sessão"}: {session.content_title}
          </h2>
          <p className="muted">
            Iniciada às {new Date(session.started_at).toLocaleTimeString("pt-BR")}. Expira às{" "}
            {new Date(session.expires_at).toLocaleTimeString("pt-BR")}.
          </p>
        </div>
        <div className="timer" role="timer" aria-label="Tempo decorrido">
          {formatDuration(elapsed)}
        </div>
      </div>
      <div className="bar" aria-hidden="true">
        <div className="bar-fill" style={{ width: `${progress * 100}%` }} />
      </div>
      <p className="hint">
        {elapsed < MIN_SECONDS
          ? `Faltam ${formatDuration(MIN_SECONDS - elapsed)} para a sessão valer ponto.`
          : "✅ Tempo mínimo atingido."}
      </p>

      <form onSubmit={onSubmit} className="stack">
        {isReview && (
          <fieldset className="recall">
            <legend id="recall-legend">
              Antes de revisar, quanto você lembrava?{" "}
              <span className="muted small">(ensina a rede neural)</span>
            </legend>
            <div role="radiogroup" aria-labelledby="recall-legend" className="row wrap">
              {Object.entries(RECALL_LABEL).map(([value, label]) => (
                <label key={value} className={recall === Number(value) ? "chip selected" : "chip"}>
                  <input
                    type="radio"
                    name="recall"
                    value={value}
                    checked={recall === Number(value)}
                    onChange={() => setRecall(Number(value))}
                  />
                  {value} · {label}
                </label>
              ))}
            </div>
          </fieldset>
        )}
        <label>
          O que estudei
          <textarea value={studied} onChange={(e) => setStudied(e.target.value)} rows={2} />
        </label>
        <label>
          O que entendi
          <textarea value={understood} onChange={(e) => setUnderstood(e.target.value)} rows={2} />
        </label>
        <label>
          O que preciso revisar
          <textarea value={toReview} onChange={(e) => setToReview(e.target.value)} rows={2} />
        </label>
        <p className={chars >= MIN_CHARS && allFilled ? "hint ok-text" : "hint"}>
          {chars}/{MIN_CHARS} caracteres (sem espaços)
          {!allFilled && " · preencha os três campos"}
        </p>
        <ErrorText error={finish.error ?? cancel.error} />
        <div className="row">
          <button
            type="submit"
            className="primary"
            disabled={finish.isPending || (isReview && recall === null)}
          >
            Finalizar sessão
          </button>
          <button
            type="button"
            className="ghost"
            disabled={cancel.isPending}
            onClick={() => {
              if (window.confirm("Cancelar a sessão? Ela não vai pontuar.")) cancel.mutate();
            }}
          >
            Cancelar
          </button>
        </div>
      </form>
    </section>
  );
}

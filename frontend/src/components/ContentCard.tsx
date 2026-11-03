import { useState } from "react";
import {
  useFinishContent,
  useRemoveContent,
  useRenameContent,
  useStartSession,
} from "../api/hooks";
import { KIND_LABEL, LEVEL_LABEL, STATUS_LABEL } from "../api/labels";
import type { Content } from "../api/types";
import { ChallengeList } from "./ChallengeList";
import { ErrorText } from "./ErrorText";
import { ScheduleView } from "./ScheduleView";

interface Props {
  content: Content;
  hasActiveSession: boolean;
}

export function ContentCard({ content, hasActiveSession }: Props) {
  const start = useStartSession();
  const finish = useFinishContent();
  const [showChallenges, setShowChallenges] = useState(content.status === "IN_PROGRESS");
  const [showSchedule, setShowSchedule] = useState(false);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(content.title);
  const rename = useRenameContent();
  const remove = useRemoveContent();
  const hasProgress =
    content.points > 0 ||
    content.last_session_at !== null ||
    content.challenges.some((c) => c.solved);
  const locked = content.status === "LOCKED";
  const finishable = content.status === "IN_PROGRESS" || content.status === "CONSOLIDATED";
  // Espelha a regra do servidor só para a UX; quem decide é o domínio.
  const atMaxLevel = content.level === "ADVANCED";
  const next = content.next_level;
  const sessionLabel = content.status === "IN_PROGRESS" ? "Estudar" : "Revisar";

  return (
    <article
      className={`card content status-${content.status.toLowerCase()}`}
      aria-label={content.title}
    >
      <header className="content-head">
        <div>
          {editing ? (
            <form
              className="row"
              onSubmit={(e) => {
                e.preventDefault();
                rename.mutate(
                  { contentId: content.id, title },
                  { onSuccess: () => setEditing(false) },
                );
              }}
            >
              <input
                aria-label="Novo título"
                value={title}
                maxLength={200}
                onChange={(e) => setTitle(e.target.value)}
              />
              <button type="submit" className="ghost" disabled={rename.isPending}>
                Salvar
              </button>
            </form>
          ) : (
            <h3>{content.title}</h3>
          )}
          <p className="muted small">
            {KIND_LABEL[content.kind]} ·{" "}
            <span className="pill">{STATUS_LABEL[content.status]}</span> ·{" "}
            <span className="pill level">{LEVEL_LABEL[content.level]}</span>
          </p>
        </div>
        <div className="points">
          {content.points}
          <span className="small"> pts</span>
        </div>
      </header>

      {locked && (
        <p className="hint">
          🔒 #{content.queue_position} na fila. {content.lock_reason}
        </p>
      )}

      {next && !locked && (
        <div className="progress">
          <p className="small muted">Para {LEVEL_LABEL[next.level]}:</p>
          <Meter label="Pontos" value={content.points} max={next.points_required} />
          <Meter label="Desafios" value={next.challenges_solved} max={next.challenges_required} />
        </div>
      )}

      <div className="row wrap">
        {!locked && (
          <button
            type="button"
            className="primary"
            disabled={hasActiveSession || start.isPending}
            title={hasActiveSession ? "Já existe uma sessão em andamento" : undefined}
            onClick={() => start.mutate(content.id)}
          >
            ▶ {sessionLabel}
          </button>
        )}
        <button type="button" className="ghost" onClick={() => setShowSchedule((v) => !v)}>
          📅 Cronograma
        </button>
        <button type="button" className="ghost" onClick={() => setShowChallenges((v) => !v)}>
          🎯 Desafios ({content.challenges.filter((c) => c.solved).length}/
          {content.challenges.length})
        </button>
        {finishable && (
          <button
            type="button"
            className="ghost"
            disabled={!atMaxLevel || finish.isPending}
            title={atMaxLevel ? undefined : "Chegue a Avançado para concluir"}
            onClick={() => {
              if (window.confirm(`Marcar "${content.title}" como concluído?`))
                finish.mutate(content.id);
            }}
          >
            ✔ Concluir
          </button>
        )}
      </div>
      {finishable && !atMaxLevel && (
        <p className="hint">🏁 Chegue a Avançado para concluir este conteúdo.</p>
      )}
      <div className="row wrap">
        <button type="button" className="link small" onClick={() => setEditing((v) => !v)}>
          ✎ Renomear
        </button>
        {!hasProgress && (
          <button
            type="button"
            className="link small"
            disabled={remove.isPending}
            onClick={() => {
              if (window.confirm(`Remover "${content.title}" da trilha?`))
                remove.mutate(content.id);
            }}
          >
            🗑 Remover
          </button>
        )}
      </div>
      <ErrorText error={start.error ?? finish.error ?? rename.error ?? remove.error} />
      {showSchedule && <ScheduleView contentId={content.id} />}

      {showChallenges && <ChallengeList content={content} />}
    </article>
  );
}

function Meter({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max === 0 ? 100 : Math.min(100, (value / max) * 100);
  return (
    <div className="meter">
      <span className="small">
        {label}: {value}/{max}
      </span>
      <div
        className="bar"
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div className="bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

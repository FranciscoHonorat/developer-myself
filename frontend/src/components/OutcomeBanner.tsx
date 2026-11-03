import { formatDuration, LEVEL_LABEL, REASON_LABEL, SESSION_LABEL } from "../api/labels";
import type { Outcome } from "../api/types";

export function OutcomeBanner({ outcome, onClose }: { outcome: Outcome; onClose: () => void }) {
  return (
    <div className={outcome.awarded ? "banner ok" : "banner warn"} role="status">
      <div>
        {outcome.awarded ? <strong>🎉 +1 ponto! </strong> : <strong>Sessão sem ponto. </strong>}
        {SESSION_LABEL[outcome.kind]} de {formatDuration(outcome.duration_seconds)}. Total:{" "}
        {outcome.total_points} pts · {LEVEL_LABEL[outcome.level]}
        {outcome.reason && <div>{REASON_LABEL[outcome.reason] ?? outcome.reason}</div>}
        {outcome.unlocked_content_id && <div>🔓 O próximo conteúdo da fila foi liberado!</div>}
      </div>
      <button type="button" className="ghost" aria-label="Fechar" onClick={onClose}>
        ✕
      </button>
    </div>
  );
}

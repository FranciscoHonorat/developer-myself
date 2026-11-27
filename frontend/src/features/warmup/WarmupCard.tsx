import { useCallback, useState } from "react";
import { ApiError } from "@/api/client";
import {
  useCancelWarmup,
  useFinishWarmup,
  useStartSession,
  useStartWarmup,
  useWarmup,
} from "@/api/hooks";
import type { ActiveWarmup, RecallAnswer, WarmupNext } from "@/api/types";
import { Button } from "@/components/ui/button";
import { clearRecallDraft, RecallTest } from "@/features/session/RecallTest";

const draftKey = (warmup: ActiveWarmup) => `warmup:${warmup.started_at}`;
/** Só este código quer dizer "o aquecimento já não existe"; outros 409 (ex.: outra aba) não. */
const isGone = (err: unknown) => err instanceof ApiError && err.code === "NoActiveWarmupError";

/**
 * Aquecimento (~2 min): o menor passo possível para começar o dia. Responder sem consultar,
 * conferir e concluir — parar ali é um desfecho válido, sem cobrança.
 */
export function WarmupCard() {
  const status = useWarmup();
  const start = useStartWarmup();
  const [done, setDone] = useState<{ next: WarmupNext | null } | null>(null);
  const [expired, setExpired] = useState(false);

  if (done !== null) return <WarmupDone next={done.next} onClose={() => setDone(null)} />;
  if (!status.data) return null;
  const { available, done_today: doneToday, active } = status.data;

  if (active !== null) {
    return (
      <WarmupPanel
        key={active.started_at}
        warmup={active}
        onDone={setDone}
        onExpired={() => setExpired(true)}
      />
    );
  }
  if (doneToday) {
    return <p className="text-sm text-muted-foreground">✅ Aquecimento feito hoje</p>;
  }
  if (!available) return null;

  return (
    <section
      aria-labelledby="h-warmup"
      className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-card p-4"
    >
      <div className="flex flex-col gap-1">
        <h2 id="h-warmup" className="font-semibold">
          🔥 Aquecimento · 2 perguntas · ~2 min
        </h2>
        <p className="text-sm text-muted-foreground">
          {expired
            ? "Esse aquecimento expirou — que tal um novo?"
            : `Tente lembrar de ${status.data.content?.title ?? "o que estudou"} sem consultar.`}
        </p>
      </div>
      <Button
        disabled={start.isPending}
        onClick={() => {
          setExpired(false);
          start.mutate();
        }}
      >
        Começar
      </Button>
    </section>
  );
}

function WarmupPanel(props: {
  warmup: ActiveWarmup;
  onDone: (result: { next: WarmupNext | null }) => void;
  onExpired: () => void;
}) {
  const { warmup, onDone, onExpired } = props;
  const finish = useFinishWarmup();
  const cancel = useCancelWarmup();
  const [answers, setAnswers] = useState<RecallAnswer[] | null>(null);
  const onChange = useCallback((a: RecallAnswer[] | null) => setAnswers(a), []);

  const submit = () => {
    if (answers === null) return;
    finish
      .mutateAsync(answers)
      .then((result) => {
        clearRecallDraft(draftKey(warmup));
        onDone(result);
      })
      .catch((err: unknown) => {
        if (isGone(err)) {
          clearRecallDraft(draftKey(warmup));
          onExpired();
        }
      });
  };

  return (
    <section
      aria-labelledby="h-warmup-panel"
      className="flex flex-col gap-4 rounded-2xl border bg-card p-4"
    >
      <h2 id="h-warmup-panel" className="font-semibold">
        🔥 Aquecimento
      </h2>
      <RecallTest questions={warmup.questions} storageKey={draftKey(warmup)} onChange={onChange} />
      <div className="flex flex-wrap gap-2">
        <Button disabled={answers === null || finish.isPending} onClick={submit}>
          Concluir aquecimento
        </Button>
        <Button
          variant="ghost"
          disabled={cancel.isPending}
          onClick={() => {
            clearRecallDraft(draftKey(warmup));
            cancel.mutate();
          }}
        >
          Agora não
        </Button>
      </div>
      {finish.isError && !isGone(finish.error) ? (
        <p role="alert" className="text-sm text-destructive">
          {finish.error.message}
        </p>
      ) : null}
    </section>
  );
}

function WarmupDone(props: { next: WarmupNext | null; onClose: () => void }) {
  const { next, onClose } = props;
  const startSession = useStartSession();
  const verb = next?.kind === "REVIEW" ? "revisar" : "estudar";

  return (
    <section
      aria-live="polite"
      className="flex flex-col items-start gap-3 rounded-2xl border bg-card p-4"
    >
      <p className="font-semibold">
        {next === null
          ? "✅ Aquecimento feito."
          : `✅ Aquecimento feito. Bora ${verb} "${next.title}"?`}
      </p>
      <div className="flex flex-wrap gap-2">
        {next !== null ? (
          <Button
            disabled={startSession.isPending}
            onClick={() => startSession.mutateAsync(next.content_id).then(onClose, () => {})}
          >
            Iniciar sessão
          </Button>
        ) : null}
        <Button variant="outline" onClick={onClose}>
          Por hoje é só
        </Button>
      </div>
    </section>
  );
}

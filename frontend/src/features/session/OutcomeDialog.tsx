import { Brain, CircleSlash, PartyPopper, Sparkles, Target, Unlock } from "lucide-react";
import { formatDuration, LEVEL_LABEL, REASON_LABEL, SESSION_LABEL } from "@/api/labels";
import type { Outcome } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/** O que o servidor decidiu sobre a sessão: maestria, competência e ponto. */
export function OutcomeDialog({
  outcome,
  onClose,
}: {
  outcome: Outcome | null;
  onClose: () => void;
}) {
  const leveledUp =
    outcome !== null &&
    outcome.level_before !== undefined &&
    outcome.level !== outcome.level_before;
  const challengeNudge =
    outcome !== null &&
    outcome.next_level != null &&
    outcome.points_for_next_level != null &&
    outcome.challenges_for_next_level != null &&
    (outcome.challenges_solved ?? 0) < outcome.challenges_for_next_level &&
    outcome.total_points >= Math.ceil(outcome.points_for_next_level / 2);

  return (
    <Dialog open={outcome !== null} onOpenChange={(open) => !open && onClose()}>
      {outcome && (
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="mb-2 flex size-12 items-center justify-center rounded-full bg-accent">
              {outcome.awarded ? (
                <PartyPopper aria-hidden className="size-6 text-primary" />
              ) : (
                <CircleSlash aria-hidden className="size-6 text-warning" />
              )}
            </div>
            <DialogTitle>{outcome.awarded ? "+1 ponto!" : "Sessão sem ponto."}</DialogTitle>
            <DialogDescription>
              {SESSION_LABEL[outcome.kind]} de {formatDuration(outcome.duration_seconds)}.
              {outcome.reason && <> {REASON_LABEL[outcome.reason] ?? outcome.reason}</>}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="font-mono">
              {outcome.total_points} pts
            </Badge>
            <Badge variant="outline">{LEVEL_LABEL[outcome.level]}</Badge>
          </div>
          {leveledUp && (
            <p className="flex items-center gap-2 rounded-lg border border-primary/40 bg-accent px-3 py-2 text-sm font-medium text-accent-foreground">
              <Sparkles aria-hidden className="size-4 shrink-0 text-primary" />
              Novo nível alcançado: {LEVEL_LABEL[outcome.level]}!
            </p>
          )}
          {(outcome.recall_total ?? 0) > 0 && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Brain aria-hidden className="size-4 shrink-0 text-primary" />
              Teste de memória: {outcome.recall_recalled ?? 0}/{outcome.recall_total} acertadas sem
              consultar.
            </p>
          )}
          {outcome.next_level &&
            outcome.points_for_next_level != null &&
            outcome.challenges_for_next_level != null && (
              <div className="rounded-lg border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                Rumo a{" "}
                <strong className="text-foreground">{LEVEL_LABEL[outcome.next_level]}</strong>:{" "}
                <span className="font-mono tabular-nums">
                  {outcome.total_points}/{outcome.points_for_next_level} pts
                </span>{" "}
                ·{" "}
                <span className="font-mono tabular-nums">
                  {outcome.challenges_solved ?? 0}/{outcome.challenges_for_next_level} desafios
                </span>
              </div>
            )}
          {challengeNudge && (
            <p className="flex items-start gap-2 text-xs text-muted-foreground">
              <Target aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
              Zona de desafio: seus pontos avançaram bem — resolver um desafio prático agora
              consolida esse domínio.
            </p>
          )}
          {outcome.unlocked_content_id && (
            <p className="flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm text-accent-foreground">
              <Unlock aria-hidden className="size-4" />O próximo conteúdo da fila foi liberado!
            </p>
          )}
          <DialogFooter>
            <Button onClick={onClose}>Continuar</Button>
          </DialogFooter>
        </DialogContent>
      )}
    </Dialog>
  );
}

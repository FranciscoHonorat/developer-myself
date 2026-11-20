import { CircleSlash, PartyPopper, Unlock } from "lucide-react";
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

/** O que o servidor decidiu sobre a sessão: pontuou ou não, e por quê. */
export function OutcomeDialog({
  outcome,
  onClose,
}: {
  outcome: Outcome | null;
  onClose: () => void;
}) {
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

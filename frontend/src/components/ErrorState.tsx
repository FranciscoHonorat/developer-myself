import { CircleAlert, RotateCw } from "lucide-react";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  error: unknown;
  /** Mostra "Tentar de novo" quando há o que repetir (ex.: `query.refetch`). */
  onRetry?: () => void;
  compact?: boolean;
}

/** Erro com a mensagem da API (ou de conexão) e, se der, como tentar de novo. */
export function ErrorState({ error, onRetry, compact = false }: Props) {
  if (!error) return null;
  const message = error instanceof ApiError ? error.message : "Falha de conexão com o servidor.";
  return (
    <div
      role="alert"
      className={cn(
        "flex items-center gap-3 rounded-lg border border-destructive/40 text-sm text-destructive",
        compact ? "px-3 py-2" : "p-4",
      )}
    >
      <CircleAlert aria-hidden className="size-4 shrink-0" />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw aria-hidden /> Tentar de novo
        </Button>
      )}
    </div>
  );
}

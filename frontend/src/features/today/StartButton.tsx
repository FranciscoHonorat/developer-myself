import { Play } from "lucide-react";
import { useStartSession } from "@/api/hooks";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";

interface Props {
  contentId: string;
  label: string;
  /** Nome acessível, quando o rótulo visível não basta (ex.: "Iniciar Go"). */
  ariaLabel?: string;
  disabled?: boolean;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
  className?: string;
}

/** Inicia a sessão; o painel aparece quando o plano recarrega com a sessão ativa. */
export function StartButton({
  contentId,
  label,
  ariaLabel,
  disabled = false,
  variant = "default",
  size = "default",
  className,
}: Props) {
  const start = useStartSession();
  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        aria-label={ariaLabel}
        disabled={disabled || start.isPending}
        onClick={() => start.mutate(contentId)}
      >
        <Play aria-hidden className="fill-current" />
        {label}
      </Button>
      {start.error && <ErrorState error={start.error} compact />}
    </>
  );
}
